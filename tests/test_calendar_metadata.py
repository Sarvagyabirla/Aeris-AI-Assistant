from pathlib import Path
from types import SimpleNamespace

from aeris.integrations.google_calendar import GoogleCalendarClient
from aeris.state import CancellationToken


def test_calendar_preserves_end_all_day_timezone_and_source_metadata():
    client = GoogleCalendarClient(Path("fixture-never-read.json"))
    response = {"timeZone": "Asia/Kolkata", "summary": "Fixture calendar", "items": [{
        "id": "fixture-event", "summary": "Fixture holiday", "start": {"date": "2026-10-17"},
        "end": {"date": "2026-10-18"}}]}
    client._calendar = SimpleNamespace(events=lambda: SimpleNamespace(list=lambda **_: SimpleNamespace(execute=lambda: response)))
    result = client.list_events({"count": 5})
    assert result.success
    assert result.data["events"][0]["end"] == "2026-10-18"
    assert result.data["events"][0]["all_day"] is True
    assert result.data["timezone"] == "Asia/Kolkata" and result.data["calendar_id"] == "primary"


def test_cancelled_calendar_response_is_not_displayed():
    client = GoogleCalendarClient(Path("fixture-never-read.json"))
    token = CancellationToken()
    def execute():
        token.cancel()
        return {"items": [{"summary": "PRIVATE_FIXTURE_EVENT", "start": {"date": "2026-10-17"}}]}
    client._calendar = SimpleNamespace(events=lambda: SimpleNamespace(list=lambda **_: SimpleNamespace(execute=execute)))
    result = client.list_events({"count": 5}, token=token)
    assert result.error == "cancelled" and "PRIVATE_FIXTURE_EVENT" not in str(result)
