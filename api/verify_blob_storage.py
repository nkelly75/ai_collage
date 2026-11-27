"""Explicit, bounded real-account HTTP proof; never collected by ordinary pytest."""

import argparse
from hashlib import sha256
import io
import json
import logging
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from uuid import uuid4

from azure.core import MatchConditions
from azure.identity import AzureCliCredential
from azure.storage.blob import ContainerClient
import httpx
from PIL import Image

from ai_collage.storage.blob import BlobProjectStorage
from api.blob_proof import ProofTransport
from api.storage_config import BLOB_VARIABLES, DEV_ACCOUNT_URL, DEV_CONTAINER, DEV_SUBSCRIPTION


PROCESS_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$rootProcessId = [int]$env:COLLAGE_PROOF_HOST_PID
$processes = @(Get-CimInstance Win32_Process)
$ids = [Collections.Generic.HashSet[int]]::new()
[void]$ids.Add($rootProcessId)
do {
    $changed = $false
    foreach ($process in $processes) {
        if ($ids.Contains([int]$process.ParentProcessId) -and $ids.Add([int]$process.ProcessId)) {
            $changed = $true
        }
    }
} while ($changed)
if ($env:COLLAGE_PROOF_STOP -eq '1') {
    foreach ($processId in @($ids | Where-Object { $_ -ne $rootProcessId }) + @($rootProcessId)) {
        try {
            Stop-Process -Id $processId -Force -ErrorAction Stop
        } catch [Microsoft.PowerShell.Commands.ProcessCommandException] {
            if ($_.FullyQualifiedErrorId -notlike 'NoProcessFoundForGivenId,*') { throw }
        }
    }
} else {
    $owners = @(Get-NetTCPConnection -LocalPort ([int]$env:COLLAGE_PROOF_PORT) -State Listen)
    if (-not $owners -or @($owners | Where-Object { -not $ids.Contains([int]$_.OwningProcess) }).Count) {
        throw 'Proof refused a listener not owned by its Functions process tree.'
    }
}
"""


def generated_photos() -> list[bytes]:
    result = []
    for format, size, color in [("JPEG", (20, 10), "red"), ("PNG", (12, 24), "blue")]:
        with Image.new("RGB", size, color) as image, io.BytesIO() as output:
            options = {}
            if format == "JPEG":
                exif = Image.Exif()
                exif[274] = 6
                options["exif"] = exif
            image.save(output, format=format, **options)
            result.append(output.getvalue())
    if sum(map(len, result)) > 1024 * 1024:
        raise ValueError("Generated proof photos exceed their allowance.")
    return result


class Proof:
    def __init__(self, output: Path):
        if not output.is_absolute():
            raise ValueError("Use an absolute, new output directory.")
        output.mkdir(parents=False, exist_ok=False)
        self.output = output
        self.namespace = "proof-019b-" + uuid4().hex
        self.ledger = output / "requests.jsonl"
        self.ledger.write_text("", encoding="utf-8")
        self.http_count = 0
        self.process: subprocess.Popen | None = None
        self.host_log = None
        self.report = {
            "status": "incomplete", "namespace": self.namespace, "account": DEV_ACCOUNT_URL,
            "container": DEV_CONTAINER, "http_requests": 0, "blob_requests": 0,
            "owned_objects": [], "deleted_objects": [], "checks": [],
            "inventory_complete": False, "cleanup_complete": False,
        }

    def process_action(self, *, stop=False):
        if self.process is None:
            if stop:
                return
            raise RuntimeError("No owned Functions launcher has been started.")
        if self.process.poll() is not None:
            raise RuntimeError("The owned Functions launcher exited; inspect its host log.")
        subprocess.run(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", PROCESS_SCRIPT],
            env={**os.environ, "COLLAGE_PROOF_HOST_PID": str(self.process.pid),
                 "COLLAGE_PROOF_PORT": str(self.port), "COLLAGE_PROOF_STOP": "1" if stop else "0"},
            check=True, text=True, timeout=30,
        )

    def stop(self):
        if self.process is not None:
            self.process_action(stop=True)
            self.process.wait(timeout=15)
            self.process = None
        if self.host_log is not None:
            self.host_log.close()
            self.host_log = None

    def request(self, method, path, **kwargs):
        if self.http_count >= 30:
            raise RuntimeError("The local HTTP proof allowance is exhausted.")
        self.http_count += 1
        with httpx.Client(timeout=httpx.Timeout(60, connect=5), trust_env=False) as client:
            return client.request(method, f"http://127.0.0.1:{self.port}/api/{path}", **kwargs)

    def start(self, phase):
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            self.port = reservation.getsockname()[1]
        environment = {name: value for name, value in os.environ.items() if name not in BLOB_VARIABLES}
        environment.update({
            "AI_COLLAGE_DATA_DIR": str(self.output / phase),
            "AI_COLLAGE_BLOB_ACCOUNT_URL": DEV_ACCOUNT_URL,
            "AI_COLLAGE_BLOB_CONTAINER": DEV_CONTAINER,
            "AI_COLLAGE_BLOB_SUBSCRIPTION_ID": DEV_SUBSCRIPTION,
            "AI_COLLAGE_BLOB_NAMESPACE": self.namespace,
            "AI_COLLAGE_BLOB_PROOF_LEDGER": str(self.ledger),
        })
        self.host_log = (self.output / f"{phase}.log").open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-File",
             str(Path(__file__).with_name("start.ps1")), "-StorageBackend", "Blob", "-Port", str(self.port)],
            env=environment, stdout=self.host_log, stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(f"Functions failed to start; inspect {phase}.log.")
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=1):
                    break
            except OSError:
                time.sleep(0.5)
        else:
            raise TimeoutError("Functions did not open its listener.")
        self.process_action()
        for _ in range(6):
            response = self.request("GET", "projects")
            if response.status_code == 200:
                return response.json()["projects"]
            if response.status_code not in {404, 503} or "storage_unavailable" in response.text:
                raise RuntimeError(f"API startup failed: HTTP {response.status_code}: {response.text}")
            time.sleep(1)
        raise TimeoutError("Functions did not finish indexing its routes.")

    def verify_project(self, originals):
        response = self.request("GET", "projects/proof")
        response.raise_for_status()
        expected = {
            "project_id": "proof", "canvas": {"width": 900, "height": 1600},
            "photos": [{"photo_id": 1, "width": 10, "height": 20},
                       {"photo_id": 2, "width": 12, "height": 24}],
        }
        if response.json() != expected:
            raise AssertionError("Reopened project metadata does not match the generated fixture.")
        for number, (original, extension, media) in enumerate(zip(
            originals, ("jpg", "png"), ("image/jpeg", "image/png"), strict=True,
        ), 1):
            photo = self.request("GET", f"projects/proof/photos/{number}")
            photo.raise_for_status()
            if (
                photo.content != original or photo.headers.get("content-type", "").split(";", 1)[0].strip() != media
                or photo.headers.get("cache-control") != "no-store"
                or photo.headers.get("x-content-type-options") != "nosniff"
            ):
                raise AssertionError("Original photo bytes or response headers changed.")
            (self.output / f"download-{number}.{extension}").write_bytes(photo.content)

    def cleanup(self):
        if self.process is not None:
            raise RuntimeError("Stop the owned Functions host before proof cleanup.")
        with AzureCliCredential(subscription=DEV_SUBSCRIPTION, process_timeout=10) as credential:
            with ContainerClient(
                DEV_ACCOUNT_URL, DEV_CONTAINER, credential=credential, retry_total=0,
                connection_timeout=10, read_timeout=30, transport=ProofTransport(self.ledger),
            ) as container:
                storage = BlobProjectStorage(container, self.namespace)
                completion = storage.completion("proof")
                project, _ = storage.load("proof")
                prefix = storage.candidate_prefix(completion)
                expected = {
                    storage.completion_key("proof"), prefix + "project.json",
                    prefix + "conversation/state.json",
                    *(prefix + "photos/" + photo.asset_id for photo in project.photos),
                }
                found = {blob.name for blob in container.list_blobs(name_starts_with=storage.prefix)}
                if found != expected:
                    raise RuntimeError("Unexpected proof inventory; preserving all objects for review.")
                ordered = [storage.completion_key("proof")] + sorted(expected - {storage.completion_key("proof")})
                self.report["owned_objects"] = ordered
                self.report["inventory_complete"] = True
                etags = {key: container.get_blob_client(key).get_blob_properties().etag for key in ordered}
                for key in ordered:
                    container.delete_blob(key, etag=etags[key], match_condition=MatchConditions.IfNotModified)
                    self.report["deleted_objects"].append(key)
                self.report["cleanup_complete"] = True

    def run(self):
        originals = generated_photos()
        self.report["photo_sha256"] = [sha256(raw).hexdigest() for raw in originals]
        self.report["photo_bytes"] = sum(map(len, originals))
        try:
            if self.start("first-root") != []:
                raise RuntimeError("The fresh proof namespace is not empty.")
            self.report["checks"].append("fresh namespace empty")
            created = self.request(
                "POST", "projects", data={"metadata": json.dumps({
                    "project_id": "proof", "canvas": {"width": 900, "height": 1600},
                })},
                files=[("photo_1", ("one.jpg", originals[0], "image/jpeg")),
                       ("photo_2", ("two.png", originals[1], "image/png"))],
            )
            if created.status_code != 201 or created.headers.get("location") != "/api/projects/proof":
                raise RuntimeError(f"Create failed: HTTP {created.status_code}: {created.text}")
            listed = self.request("GET", "projects")
            listed.raise_for_status()
            expected_list = [{"project_id": "proof", "canvas": {"width": 900, "height": 1600}, "photo_count": 2}]
            if listed.json() != {"projects": expected_list}:
                raise AssertionError("Published project was not listed correctly.")
            self.verify_project(originals)
            duplicate = self.request(
                "POST", "projects", data={"metadata": json.dumps({
                    "project_id": "proof", "canvas": {"width": 900, "height": 1600},
                })},
                files=[("photo_1", ("one.jpg", originals[0], "image/jpeg")),
                       ("photo_2", ("two.png", originals[1], "image/png"))],
            )
            if duplicate.status_code != 409 or duplicate.json()["error"]["code"] != "project_exists":
                raise AssertionError("Duplicate creation was not rejected.")
            unsupported = self.request("GET", "projects/proof/conversation")
            if unsupported.status_code != 501 or unsupported.json()["error"]["code"] != "blob_slice_only":
                raise AssertionError("Unsupported conversation access was not rejected.")
            self.report["checks"].append("create/list/detail/originals/duplicate/unsupported")
            self.stop()
            if self.start("second-root") != expected_list:
                raise AssertionError("Restart with a fresh local root lost the Blob project.")
            self.verify_project(originals)
            for phase in ("first-root", "second-root"):
                if (self.output / phase / "users" / "local-dev" / "projects").exists():
                    raise AssertionError("Blob mode created a durable local project copy.")
            self.report["checks"].append("restart/new local root/reopen/exact originals")
            self.stop()
            self.cleanup()
            self.report["checks"].append("exact owned inventory cleaned, completion first")
            self.report["status"] = "passed"
        finally:
            active_error = sys.exception()
            try:
                self.stop()
            except (OSError, RuntimeError, subprocess.SubprocessError):
                self.report["status"] = "incomplete"
                if active_error is None:
                    raise
                logging.exception("Could not stop the owned proof host; inspect the recorded host logs.")
            finally:
                self.report["http_requests"] = self.http_count
                self.report["blob_requests"] = len(self.ledger.read_text(encoding="utf-8").splitlines())
                self.report["remaining_owned_objects"] = sorted(
                    set(self.report["owned_objects"]) - set(self.report["deleted_objects"])
                )
                (self.output / "report.json").write_text(json.dumps(self.report, indent=2) + "\n", encoding="utf-8")
                print(f"Proof {self.report['status']}; evidence: {self.output}")
                print(f"HTTP requests: {self.http_count}/30; Blob requests: {self.report['blob_requests']}/200")
                if self.report["status"] != "passed":
                    print(f"Preserve namespace {self.namespace}; do not rerun or guess at cleanup.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-azure", action="store_true", help="Explicitly authorize this bounded real-account run.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Absolute new directory for generated downloads, logs and evidence.")
    arguments = parser.parse_args()
    if not arguments.allow_azure:
        parser.error("--allow-azure is required; this is not an offline check")
    if os.name != "nt":
        parser.error("This local Functions proof currently requires Windows PowerShell/Core Tools.")
    Proof(arguments.output_dir).run()


if __name__ == "__main__":
    main()
