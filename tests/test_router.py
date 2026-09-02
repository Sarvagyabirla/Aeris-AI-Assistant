import pytest

from aeris.router import LocalRouter, has_wake_word, strip_wake_word


@pytest.mark.parametrize(
    ("command", "tool", "key", "value"),
    [
        ("open chrome", "desktop.open_app", "name", "chrome"),
        ("search YouTube for Python DSA", "browser.search_youtube", "query", "Python DSA"),
        ("Google latest AI news", "browser.search_web", "query", "latest AI news"),
        ("set volume to 42", "desktop.set_volume", "level", 42),
        ("Set volume for 60 bus.", "desktop.set_volume", "level", 60),
        ("Set the volume at sixty percent", "desktop.set_volume", "level", 60),
        ("Okay, Arish. Open YouTube.", "browser.open_url", "url", "https://www.youtube.com"),
        ("Please open Chrome", "desktop.open_app", "name", "chrome"),
        ("Hey Aeris, set brightness to seventy five percent", "desktop.set_brightness", "level", 75),
        ("increase brightness", "desktop.change_brightness", "delta", 10),
        ("find file resume", "files.find", "query", "resume"),
        ("take a screenshot", "desktop.screenshot", None, None),
        ("check my emails", "email.list_recent", "count", 5),
        (
            "download https://example.com/archive.zip",
            "downloads.download",
            "url",
            "https://example.com/archive.zip",
        ),
        ("install VLC", "packages.install", "package", "VLC"),
        ("search apps for OBS", "packages.search", "query", "OBS"),
        ("list app updates", "packages.list_updates", None, None),
        ("open downloads folder", "downloads.open_folder", None, None),
        ("computer health", "system.health", None, None),
        ("check battery", "system.battery", None, None),
        ("show desktop", "desktop.window_action", "action", "show_desktop"),
        ("read clipboard", "desktop.clipboard_read", None, None),
        (
            "look at my screen and explain this error",
            "vision.inspect_screen",
            "question",
            "explain this error",
        ),
        (
            "write Python code for an expense tracker",
            "coding.create_project",
            "prompt",
            "Use Python. an expense tracker",
        ),
    ],
)
def test_common_routes(command, tool, key, value):
    plan = LocalRouter().route(command)
    assert plan is not None
    assert plan.actions[0].tool == tool
    if key:
        assert plan.actions[0].arguments[key] == value


def test_send_email_route_captures_preview_fields():
    plan = LocalRouter().route(
        "send email to test@example.com subject Project update message The build passed."
    )
    action = plan.actions[0]
    assert action.tool == "email.send"
    assert action.arguments == {
        "to": "test@example.com",
        "subject": "Project update",
        "body": "The build passed.",
    }


def test_unknown_command_returns_none():
    assert LocalRouter().route("perform an undefined cosmic ritual") is None


def test_offline_help_is_local():
    plan = LocalRouter().route("offline help")
    assert plan is not None
    assert not plan.actions
    assert "Offline commands" in plan.reply


def test_download_filename_is_routed():
    plan = LocalRouter().route("download https://example.com/file.bin as course.zip")
    assert plan is not None
    assert plan.actions[0].arguments == {
        "url": "https://example.com/file.bin",
        "filename": "course.zip",
    }


def test_file_creation_and_move_are_routed():
    note = LocalRouter().route("create note ideas saying Build Aeris")
    assert note is not None
    assert note.actions[0].tool == "files.write_text"
    assert note.actions[0].arguments == {"path": "ideas.txt", "text": "Build Aeris"}

    move = LocalRouter().route("move file notes.txt to Archive\\notes.txt")
    assert move is not None
    assert move.actions[0].tool == "files.move"


def test_wake_word_detection_requires_aeris_name():
    assert has_wake_word("Okay Aeris, open Chrome")
    assert has_wake_word("Hey Arish, open YouTube")
    assert not has_wake_word("Please open Chrome")
    assert has_wake_word("Nova, open Chrome", "nova")
    assert strip_wake_word("Okay Nova, open Chrome", "nova") == "open Chrome"


def test_build_app_is_routed_to_coding_workspace():
    plan = LocalRouter().route("build a weather app")
    assert plan is not None
    assert plan.actions[0].tool == "coding.create_project"
    assert plan.actions[0].arguments["prompt"] == "Build a weather application."
