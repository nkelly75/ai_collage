"""Explicit, bounded real-account HTTP proof; never collected by ordinary pytest."""

import argparse
from hashlib import sha256
import json
import logging
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from uuid import uuid4

from azure.core import MatchConditions
from azure.identity import AzureCliCredential
from azure.storage.blob import ContainerClient
import httpx

from ai_collage.storage.blob import BlobProjectStorage
from api.blob_proof import ProofLimits, ProofTransport, limits_path, owned_key
from api.proof_fixture import PROMPTS, generated_photos
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


class Proof:
    def __init__(self, output: Path, *, http_requests: int, blob_requests: int):
        if not output.is_absolute():
            raise ValueError("Use an absolute, new output directory.")
        self.namespace = "proof-019c-" + uuid4().hex
        self.limits = ProofLimits(
            namespace=self.namespace, http_requests=http_requests, blob_requests=blob_requests,
        )
        output.mkdir(parents=False, exist_ok=False)
        self.output = output
        self.ledger = output / "requests.jsonl"
        self.ledger.write_text("", encoding="utf-8")
        limits_path(self.ledger).write_text(self.limits.model_dump_json(), encoding="utf-8")
        self.inventory = self.ledger.with_suffix(".objects.jsonl")
        self.http_count = 0
        self.process: subprocess.Popen | None = None
        self.host_log = None
        self.report = {
            "status": "incomplete", "namespace": self.namespace, "account": DEV_ACCOUNT_URL,
            "container": DEV_CONTAINER, "http_requests": 0, "blob_requests": 0,
            "owned_objects": [], "deleted_objects": [], "checks": [],
            "inventory_complete": False, "cleanup_complete": False,
            "model_calls": 0, "limits": self.limits.model_dump(),
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
        if self.http_count >= self.limits.http_requests:
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
            "AI_COLLAGE_STORAGE_BACKEND": "blob", "AI_COLLAGE_LIVE": "0",
            "AI_COLLAGE_API_AUTHORITY": f"127.0.0.1:{self.port}",
            "AI_COLLAGE_UI_ORIGIN": "http://127.0.0.1:5173",
            "PYTHON_SCRIPT_FILE_NAME": "proof_function_app.py",
            "FUNCTIONS_WORKER_RUNTIME": "python", "FUNCTIONS_CORE_TOOLS_TELEMETRY_OPTOUT": "1",
            "AzureWebJobsSecretStorageType": "files", "FUNCTIONS_REQUEST_BODY_SIZE_LIMIT": "167772160",
            "VIRTUAL_ENV": str(Path(__file__).parent / ".venv"),
            "PATH": str(Path(__file__).parent / ".venv" / "Scripts") + os.pathsep + os.environ["PATH"],
            "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
        })
        for name in (
            "AI_COLLAGE_CALL_BUDGET_PATH", "AI_COLLAGE_MAX_CALLS", "AI_COLLAGE_TRIAL_PROJECT",
            "AzureWebJobsStorage", "AzureWebJobsDashboard", "APPLICATIONINSIGHTS_CONNECTION_STRING",
            "APPINSIGHTS_INSTRUMENTATIONKEY",
        ):
            environment.pop(name, None)
        func = shutil.which("func.exe") or str(
            Path(os.environ["ProgramFiles"]) / "Microsoft" / "Azure Functions Core Tools" / "func.exe",
        )
        version = subprocess.run([func, "--version"], capture_output=True, text=True, check=True, timeout=15)
        parts = version.stdout.strip().split(".")
        if not all(part.isdecimal() for part in parts) or tuple(map(int, parts)) < (4, 17, 0) or parts[0] != "4":
            raise RuntimeError("Use Core Tools 4.17.0 or newer 4.x for the proof.")
        self.host_log = (self.output / f"{phase}.log").open("w", encoding="utf-8")
        self.process = subprocess.Popen(
            [func, "start", "--address", "127.0.0.1", "--port", str(self.port),
             "--cors", "http://127.0.0.1:5173"],
            cwd=Path(__file__).parent, env=environment, stdout=self.host_log, stderr=subprocess.STDOUT,
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
            "project_id": "proof", "canvas": {"width": 1200, "height": 1800},
            "photos": [{"photo_id": number, "width": 30, "height": 40} for number in range(1, 5)],
        }
        if response.json() != expected:
            raise AssertionError("Reopened project metadata does not match the generated fixture.")
        for number, original in enumerate(originals, 1):
            photo = self.request("GET", f"projects/proof/photos/{number}")
            photo.raise_for_status()
            if (
                photo.content != original or photo.headers.get("content-type", "").split(";", 1)[0].strip() != "image/png"
                or photo.headers.get("cache-control") != "no-store"
                or photo.headers.get("x-content-type-options") != "nosniff"
            ):
                raise AssertionError("Original photo bytes or response headers changed.")
            (self.output / f"download-{number}.png").write_bytes(photo.content)

    def cleanup(self):
        if self.process is not None:
            raise RuntimeError("Stop the owned Functions host before proof cleanup.")
        with AzureCliCredential(subscription=DEV_SUBSCRIPTION, process_timeout=10) as credential:
            with ContainerClient(
                DEV_ACCOUNT_URL, DEV_CONTAINER, credential=credential, retry_total=0,
                connection_timeout=10, read_timeout=30, transport=ProofTransport(self.ledger),
            ) as container:
                storage = BlobProjectStorage(container, self.namespace)
                if not self.inventory.is_file():
                    raise RuntimeError("No confirmed proof upload inventory; preserve all objects.")
                confirmed = {}
                for line in self.inventory.read_text(encoding="utf-8").splitlines():
                    entry = json.loads(line)
                    if set(entry) != {"key", "etag"} or not isinstance(entry["etag"], str) or not entry["etag"] or not owned_key(
                        self.namespace, entry["key"],
                    ):
                        raise RuntimeError("Invalid proof upload inventory; preserve all objects.")
                    confirmed[entry["key"]] = entry["etag"]
                expected = set(confirmed)
                if storage.completion_key("proof") not in expected:
                    raise RuntimeError("Proof head is not confirmed in its inventory.")
                found = {blob.name for blob in container.list_blobs(name_starts_with=storage.prefix)}
                if found != expected:
                    raise RuntimeError("Unexpected proof inventory; preserving all objects for review.")
                ordered = [storage.completion_key("proof")] + sorted(expected - {storage.completion_key("proof")})
                self.report["owned_objects"] = ordered
                self.report["inventory_complete"] = True
                etags = {key: container.get_blob_client(key).get_blob_properties().etag for key in ordered}
                if etags != confirmed:
                    raise RuntimeError("Proof objects changed since their confirmed uploads; preserve the inventory.")
                for key in ordered:
                    container.delete_blob(key, etag=etags[key], match_condition=MatchConditions.IfNotModified)
                    self.report["deleted_objects"].append(key)
                self.report["cleanup_complete"] = True

    def run(self):
        originals = generated_photos()
        if len(originals) != 4 or sum(map(len, originals)) > 1024 * 1024:
            raise RuntimeError("Proof photos exceed the approved fixture bounds.")
        self.report["photo_sha256"] = [sha256(raw).hexdigest() for raw in originals]
        self.report["photo_bytes"] = sum(map(len, originals))
        try:
            if self.start("first-root") != []:
                raise RuntimeError("The fresh proof namespace is not empty.")
            self.report["checks"].append("fresh namespace empty")
            created = self.request(
                "POST", "projects", data={"metadata": json.dumps({
                    "project_id": "proof", "canvas": {"width": 1200, "height": 1800},
                })},
                files=[(f"photo_{n}", (f"{n}.png", raw, "image/png")) for n, raw in enumerate(originals, 1)],
            )
            if created.status_code != 201 or created.headers.get("location") != "/api/projects/proof":
                raise RuntimeError(f"Create failed: HTTP {created.status_code}: {created.text}")
            listed = self.request("GET", "projects")
            listed.raise_for_status()
            expected_list = [{"project_id": "proof", "canvas": {"width": 1200, "height": 1800}, "photo_count": 4}]
            if listed.json() != {"projects": expected_list}:
                raise AssertionError("Published project was not listed correctly.")
            self.verify_project(originals)
            duplicate = self.request(
                "POST", "projects", data={"metadata": json.dumps({
                    "project_id": "proof", "canvas": {"width": 1200, "height": 1800},
                })},
                files=[(f"photo_{n}", (f"{n}.png", raw, "image/png")) for n, raw in enumerate(originals, 1)],
            )
            if duplicate.status_code != 409 or duplicate.json()["error"]["code"] != "project_exists":
                raise AssertionError("Duplicate creation was not rejected.")
            self.report["checks"].append("create/list/detail/originals/duplicate")
            requests = []
            for prompt in PROMPTS:
                view = self.request("GET", "projects/proof/conversation")
                view.raise_for_status()
                submission = {"request_id": str(uuid4()), "prompt": prompt, "revision": view.json()["revision"]}
                prepared = self.request("POST", "projects/proof/conversation/requests", json=submission)
                prepared.raise_for_status()
                if prepared.json()["status"] != "prepared":
                    raise AssertionError("Scripted interpretation did not prepare generation.")
                completed = self.request(
                    "POST", f"projects/proof/conversation/requests/{submission['request_id']}/generate",
                    json={"revision": prepared.json()["revision"]},
                )
                completed.raise_for_status()
                if completed.json()["status"] != "completed":
                    raise AssertionError("Scripted generation did not complete.")
                requests.append(submission["request_id"])
            previews = {}
            for proposal in ("P001", "P002"):
                response = self.request("GET", f"projects/proof/proposals/{proposal}/preview")
                response.raise_for_status()
                previews[proposal] = response.content
                (self.output / f"{proposal}.png").write_bytes(response.content)
            view = self.request("GET", "projects/proof/conversation")
            view.raise_for_status()
            action_id = str(uuid4())
            selected = self.request("POST", "projects/proof/conversation/selections", json={
                "action_id": action_id, "proposal_id": "P001",
                "revision": view.json()["revision"], "abandon_pending": False,
            })
            selected.raise_for_status()
            if selected.json()["status"] != "completed":
                raise AssertionError("Scripted history selection did not complete.")
            saved = self.request("GET", "projects/proof/conversation")
            saved.raise_for_status()
            if saved.json()["baseline"] != {"proposal_id": "P001"} or len(saved.json()["proposals"]) != 2:
                raise AssertionError("Selected baseline or retained history differs.")
            self.report["preview_sha256"] = {p: sha256(raw).hexdigest() for p, raw in previews.items()}
            self.report["checks"].append("four scripted stages/history/selection/full PNG")
            self.stop()
            if self.start("second-root") != expected_list:
                raise AssertionError("Restart with a fresh local root lost the Blob project.")
            self.verify_project(originals)
            restored = self.request("GET", "projects/proof/conversation")
            restored.raise_for_status()
            if restored.json() != saved.json():
                raise AssertionError("Conversation changed across the fresh-root restart.")
            for request_id in requests:
                status = self.request("GET", f"projects/proof/conversation/requests/{request_id}")
                status.raise_for_status()
                if status.json()["status"] != "completed":
                    raise AssertionError("Completed operation was not restored.")
            action = self.request("GET", f"projects/proof/conversation/selections/{action_id}")
            action.raise_for_status()
            if action.json()["status"] != "completed":
                raise AssertionError("Selection action was not restored.")
            for proposal, original in previews.items():
                downloaded = self.request("GET", f"projects/proof/proposals/{proposal}/preview")
                downloaded.raise_for_status()
                if downloaded.content != original:
                    raise AssertionError("Stored PNG changed across restart.")
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
                print(f"HTTP requests: {self.http_count}/{self.limits.http_requests}; "
                      f"Blob requests: {self.report['blob_requests']}/{self.limits.blob_requests}")
                if self.report["status"] != "passed":
                    print(f"Preserve namespace {self.namespace}; do not rerun or guess at cleanup.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-azure", action="store_true", help="Explicitly authorize this bounded real-account run.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Absolute new directory for generated downloads, logs and evidence.")
    parser.add_argument("--max-http-requests", required=True, type=int, help="Separately approved local HTTP ceiling.")
    parser.add_argument("--max-blob-requests", required=True, type=int, help="Separately approved Blob send ceiling, including cleanup.")
    arguments = parser.parse_args()
    if not arguments.allow_azure:
        parser.error("--allow-azure is required; this is not an offline check")
    if os.name != "nt":
        parser.error("This local Functions proof currently requires Windows PowerShell/Core Tools.")
    Proof(
        arguments.output_dir, http_requests=arguments.max_http_requests, blob_requests=arguments.max_blob_requests,
    ).run()


if __name__ == "__main__":
    main()
