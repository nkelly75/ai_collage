"""Proof-only P001/P002 layout subset from project-02, using synthetic 3:4 photos."""

import io
import json

from PIL import Image

from ai_collage.engine.models import CollageError


PROMPTS = (
    "Photo 1 is bridge. Make a simple collage using all four photos, with a charcoal background, generous margins and rounded corners.",
    "Swap the locations of photo 1 and photo 3.",
)


def recipe(*, revised: bool = False) -> dict:
    positions = [(0.27, 0.3), (0.73, 0.3), (0.27, 0.72), (0.73, 0.72)]
    if revised:
        positions[0], positions[2] = positions[2], positions[0]
    return {
        "schema_version": 3,
        "canvas": {"width": 1200, "height": 1800, "background": "#2B2B2B"},
        "layers": [
            {"photo_id": number, "mode": "whole",
             "box": {"center_x": x, "center_y": y, "width": 0.36},
             "border": {"width_px": 8, "color": "#F2F2F2"},
             "corner_radius_px": 18, "rotation_degrees": 0.0}
            for number, (x, y) in enumerate(positions, 1)
        ],
    }


def generated_photos() -> list[bytes]:
    result = []
    for color in ("red", "blue", "green", "yellow"):
        with Image.new("RGB", (30, 40), color) as image, io.BytesIO() as stream:
            image.save(stream, format="PNG")
            result.append(stream.getvalue())
    return result


class ScriptedModel:
    async def complete(self, context, requests, purpose):
        index = len(requests.attempts())
        if index >= 4 or requests.persistence.project_id != "proof":
            raise CollageError("The proof fixture is exhausted or belongs to a different project.")
        stage = "generation" if index % 2 else "interpretation"
        prompt = PROMPTS[index // 2]
        if requests.stage != stage or purpose != f"proof: {stage}" or context["user_request"] != prompt:
            raise CollageError("Unexpected proof stage, correction or prompt; no fallback dispatch.")
        requests.reserve(purpose, len(json.dumps(context, allow_nan=False).encode("utf-8")) + 4096)
        if stage == "generation":
            response = recipe(revised=index == 3)
        elif index == 0:
            response = {
                "action": "fresh", "references": [],
                "name_updates": [{"name": "bridge", "photo_id": 1, "quote": "Photo 1 is bridge"}],
            }
        else:
            response = {
                "action": "edit", "source": "current", "name_updates": [],
                "references": [{"text": "photo 1", "photo_id": 1}, {"text": "photo 3", "photo_id": 3}],
            }
        attempt = requests.attempts()[-1]
        requests.finish(attempt.model_copy(update={"status": "complete"}))
        return json.dumps(response)
