"""Visible receipts through the text controller, after cancellation wins later."""
from test_assistant import make_config

from aeris.assistant import AerisAssistant
from aeris.models import ActionRequest, ActionResult
from aeris.state import CancellationToken


def test_cancelled_copy_retains_actual_destination_in_controller_reply(tmp_path):
    class CancelAfterCommit(CancellationToken):
        def commit(self, effect):
            result = super().commit(effect)
            self.cancel()
            return result
    source, destination = tmp_path / "source.txt", tmp_path / "retained.txt"
    source.write_text("fixture bytes", encoding="utf-8")
    assistant = AerisAssistant(make_config(tmp_path, dry_run=False))
    try:
        turn = assistant.handle(f'copy file "{source}" to "{destination}"', lambda *_: True,
                                token=CancelAfterCommit())
        assert not turn.success
        assert destination.read_bytes() == source.read_bytes()
        assert str(destination) in turn.reply and "retained" in turn.reply.lower()
        assert turn.results[0].error == "cancelled_after_publication"
    finally:
        assistant.close()


def test_uncertain_source_receipt_does_not_claim_source_retained():
    details = AerisAssistant._visible_details(ActionRequest("files.move"), ActionResult(False, "uncertain",
        {"published": True, "source": "fixture-source", "destination": "fixture-destination", "outcome_uncertain": True}))
    assert "fixture-destination" in details and "removal unverified" in details
    assert "(retained)" not in details
