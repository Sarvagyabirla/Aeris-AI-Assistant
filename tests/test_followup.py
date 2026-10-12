from test_assistant import make_config

from aeris.assistant import AerisAssistant


def test_followup_uses_recent_control_then_expires(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))
    now = [100.0]
    assistant.followup.clock = lambda: now[0]
    assert assistant.handle("set volume to 35").results[0].dry_run
    result = assistant.handle("make it 40")
    assert "desktop.set_volume(level=40)" in result.reply
    now[0] += 31
    expired = assistant.handle("make it 50")
    assert not expired.results and "Which control" in expired.reply


def test_intervening_command_or_stop_invalidates_reference(tmp_path):
    assistant = AerisAssistant(make_config(tmp_path))
    assistant.handle("set brightness to 50")
    assistant.handle("help")
    assert not assistant.handle("make it 40").results
    assistant.handle("set volume to 35")
    assert not assistant.handle("make it 140").results
    assistant.handle("stop Aeris")
    assistant.handle("resume Aeris")
    assert not assistant.handle("make it 40").results