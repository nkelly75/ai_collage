"""Dedicated model-free proof entrypoint; the ordinary launcher cannot select this file."""

from contextlib import contextmanager

from ai_collage.application.conversation import ConversationFlow, ConversationSettings
from proof_fixture import ScriptedModel
import function_app
from storage_config import backend, blob_settings, project_flow


@contextmanager
def fixture_conversation_flow():
    if backend() != "blob" or blob_settings().ledger is None:
        raise RuntimeError("The proof entrypoint requires explicit isolated Blob proof accounting.")
    with project_flow() as projects:
        yield ConversationFlow(
            projects.store, ConversationSettings(live=True), ScriptedModel(), storage=projects.storage,
        )


function_app.conversation_flow = fixture_conversation_flow
app = function_app.app
