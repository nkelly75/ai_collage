"""Single-writer local projects; publish the current pointer last."""

import json
import os
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

from .geometry import resolve_layout
from .imaging import load_photo, render_layout
from .models import (
    MAX_FILE_BYTES,
    MAX_JSON_BYTES,
    OWNER_ID,
    CollageError,
    InputLayout,
    Photo,
    Project,
    ResolvedLayout,
    validate_project_id,
)


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CollageError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise CollageError(f"Non-finite JSON number is unsupported: {value}")


def read_json(path: Path) -> object:
    with path.open("rb") as stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise CollageError(f"{path}: JSON exceeds the 1 MiB document limit.")
    try:
        return json.loads(
            raw.decode("utf-8-sig"),
            object_pairs_hook=_unique_pairs,
            parse_constant=_invalid_constant,
        )
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise CollageError(f"{path}: invalid JSON: {exc}") from exc


def _write_json(path: Path, value: Project | ResolvedLayout) -> None:
    raw = (value.model_dump_json(indent=2) + "\n").encode("utf-8")
    if len(raw) > MAX_JSON_BYTES:
        raise CollageError(f"{path}: JSON exceeds the 1 MiB document limit.")
    path.write_bytes(raw)


def _contained(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise CollageError(f"Path escapes its data directory: {path}")
    return resolved


class ProjectStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir.resolve()
        self.owner_dir = _contained(
            self.data_dir, self.data_dir / "users" / OWNER_ID
        )
        self.uploads_dir = _contained(self.owner_dir, self.owner_dir / "uploads")
        self.projects_dir = _contained(self.owner_dir, self.owner_dir / "projects")

    def project_dir(self, project_id: str) -> Path:
        return _contained(
            self.projects_dir, self.projects_dir / validate_project_id(project_id)
        )

    def load(self, project_id: str) -> Project:
        directory = self.project_dir(project_id)
        path = _contained(directory, directory / "project.json")
        project = Project.model_validate(read_json(path))
        if project.project_id != project_id:
            raise CollageError("Project metadata does not match the requested project ID.")
        self.photo_paths(project)
        return project

    def photo_paths(self, project: Project) -> dict[int, Path]:
        paths = {}
        for photo in project.photos:
            relative = Path(photo.imported_path)
            if (
                relative.parent != Path("uploads")
                or relative.stem != photo.asset_id
                or relative.suffix not in {".jpg", ".png"}
            ):
                raise CollageError(f"Invalid imported path for photo {photo.photo_id}.")
            paths[photo.photo_id] = _contained(
                self.uploads_dir, self.owner_dir / relative
            )
        return paths

    def create(self, project_id: str, images: list[Path]) -> Project:
        directory = self.project_dir(project_id)
        if directory.exists():
            raise CollageError(f"Project already exists: {project_id}")
        if not 2 <= len(images) <= 6:
            raise CollageError("Import between 2 and 6 photos.")
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        published_assets: list[Path] = []
        committed = False
        with tempfile.TemporaryDirectory(prefix=".create-", dir=self.projects_dir) as temp:
            staging = Path(temp)
            staged_project = staging / "project"
            staged_project.mkdir()
            (staged_project / "layouts").mkdir()
            (staged_project / "renders").mkdir()
            photos = []
            staged_assets = []
            try:
                for number, source in enumerate(images, start=1):
                    if source.stat().st_size > MAX_FILE_BYTES:
                        raise CollageError(f"{source}: photo exceeds the 25 MiB file limit.")
                    asset_id = uuid4().hex
                    staged_asset = staging / asset_id
                    shutil.copyfile(source, staged_asset)
                    image, extension = load_photo(staged_asset)
                    with image:
                        photo = Photo(
                            photo_id=number,
                            asset_id=asset_id,
                            imported_path=str(Path("uploads") / f"{asset_id}{extension}"),
                            original_filename=source.name,
                            width=image.width,
                            height=image.height,
                        )
                    photos.append(photo)
                    staged_assets.append(staged_asset)
                project = Project(
                    schema_version=2,
                    owner_id=OWNER_ID,
                    project_id=project_id,
                    photos=photos,
                    current_version=None,
                )
                _write_json(staged_project / "project.json", project)
                paths = self.photo_paths(project)
                for photo, source in zip(photos, staged_assets, strict=True):
                    destination = paths[photo.photo_id]
                    if destination.exists():
                        raise CollageError(f"Imported asset already exists: {destination}")
                    source.rename(destination)
                    published_assets.append(destination)
                staged_project.rename(directory)
                committed = True
                return project
            finally:
                if not committed:
                    for asset in published_assets:
                        asset.unlink()

    def version_paths(self, project_id: str, version: int) -> tuple[Path, Path]:
        directory = self.project_dir(project_id)
        return (
            _contained(directory, directory / "layouts" / f"v{version:04d}.json"),
            _contained(directory, directory / "renders" / f"v{version:04d}.png"),
        )

    def apply_layout(self, project_id: str, layout_path: Path) -> tuple[ResolvedLayout, Path]:
        project = self.load(project_id)
        if project.current_version is not None:
            self.load_layout(project, project.current_version)
        layout = InputLayout.model_validate(read_json(layout_path))
        version = (project.current_version or 0) + 1
        resolved = resolve_layout(layout, project.photos, version)
        paths = self.photo_paths(project)
        saved_layout, output = self.version_paths(project_id, version)
        if saved_layout.exists() or output.exists():
            raise CollageError(
                f"Version {version} files already exist; refusing to overwrite. "
                "Inspect local state before retrying."
            )
        directory = self.project_dir(project_id)
        published: list[Path] = []
        committed = False
        with tempfile.TemporaryDirectory(prefix=".apply-", dir=directory) as temp:
            staging = Path(temp)
            try:
                render_layout(resolved, project.photos, paths, staging / "render.png")
                _write_json(staging / "layout.json", resolved)
                _write_json(
                    staging / "project.json",
                    project.model_copy(update={"current_version": version}),
                )
                (staging / "layout.json").rename(saved_layout)
                published.append(saved_layout)
                (staging / "render.png").rename(output)
                published.append(output)
                os.replace(staging / "project.json", directory / "project.json")
                committed = True
            finally:
                if not committed:
                    for path in reversed(published):
                        path.unlink()
        return resolved, output

    def load_layout(self, project: Project, version: int) -> ResolvedLayout:
        if type(version) is not int or version < 1:
            raise CollageError("Version must be a positive integer.")
        if project.current_version is None or version > project.current_version:
            raise CollageError(f"No accepted layout version {version}.")
        saved_layout, _ = self.version_paths(project.project_id, version)
        resolved = ResolvedLayout.model_validate(read_json(saved_layout))
        if resolved.version != version:
            raise CollageError("Saved layout revision does not match its filename.")
        expected = resolve_layout(resolved.recipe, project.photos, version)
        if resolved != expected:
            raise CollageError("Saved layout derived geometry is inconsistent.")
        return resolved

    def render(self, project_id: str, version: int | None = None) -> Path:
        project = self.load(project_id)
        if version is None:
            version = project.current_version
        if version is None:
            raise CollageError("Project has no accepted layout yet.")
        resolved = self.load_layout(project, version)
        _, output = self.version_paths(project_id, version)
        with tempfile.TemporaryDirectory(
            prefix=".render-", dir=self.project_dir(project_id)
        ) as temp:
            staged_output = Path(temp) / "render.png"
            render_layout(resolved, project.photos, self.photo_paths(project), staged_output)
            os.replace(staged_output, output)
        return output

    def inspect(self, project_id: str) -> dict[str, object]:
        project = self.load(project_id)
        paths = self.photo_paths(project)
        versions = []
        for version in range(1, (project.current_version or 0) + 1):
            self.load_layout(project, version)
            layout, output = self.version_paths(project_id, version)
            versions.append(
                {"version": version, "layout_path": str(layout), "render_path": str(output)}
            )
        return {
            "project_id": project.project_id,
            "owner_id": project.owner_id,
            "project_path": str(self.project_dir(project_id)),
            "current_version": project.current_version,
            "photos": [
                {
                    **photo.model_dump(),
                    "aspect_ratio": photo.width / photo.height,
                    "path": str(paths[photo.photo_id]),
                }
                for photo in project.photos
            ],
            "versions": versions,
        }
