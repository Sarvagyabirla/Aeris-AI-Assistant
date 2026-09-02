from aeris.cli import approval_prompt, build_parser
from aeris.models import ActionRequest, PermissionLevel


def test_approval_prompt_fails_closed_without_input(monkeypatch):
    def no_input(_):
        raise EOFError

    monkeypatch.setattr("builtins.input", no_input)
    approved = approval_prompt(
        ActionRequest("email.send", {"to": "test@example.com", "subject": "Hi", "body": "Hello"}),
        PermissionLevel.CONFIRM,
        "email.send(...)",
    )
    assert approved is False


def test_gui_flag_is_supported():
    args = build_parser().parse_args(["--gui"])
    assert args.gui is True
