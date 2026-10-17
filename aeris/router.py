from __future__ import annotations

import re
from pathlib import Path

from .activation import TEXT_WAKE_ALIASES, extract_addressed_command, strip_address
from .models import ActionRequest, PlannedResponse


def _clean_value(value: str) -> str:
    return value.strip().strip("\"'")


_ONES = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
_TENS = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}
_HINDI_NUMBERS = {
    "das": 10, "bees": 20, "tees": 30, "chalis": 40, "pachas": 50,
    "saath": 60, "sattar": 70, "assi": 80, "nabbe": 90, "sau": 100
}


def has_wake_word(value: str, preferred: str = "aeris") -> bool:
    return extract_addressed_command(value, (preferred, *TEXT_WAKE_ALIASES)) is not None


def strip_wake_word(value: str, preferred: str = "aeris") -> str:
    return strip_address(value, (preferred, *TEXT_WAKE_ALIASES))


def _strip_voice_wrappers(value: str, preferred: str = "aeris") -> str:
    command = strip_wake_word(value, preferred)
    command = re.sub(r"^(?:please\s+|can you\s+|could you\s+|would you\s+)+", "", command, flags=re.I)
    return command.strip()


def _normalize_command(value: str) -> str:
    normalized = value.lower().replace("%", " percent ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(r"[\s,.:;!?-]+$", "", normalized)
    normalized = re.sub(r"\s+(?:please|now)$", "", normalized)
    return normalized


def _extract_level(value: str) -> int | None:
    """Parse a whole unsigned integral percentage; never salvage a numeric substring."""
    value = value.strip()
    if re.fullmatch(r"(?:100|[0-9]{1,2})", value):
        return int(value)
    if value in _HINDI_NUMBERS:
        return _HINDI_NUMBERS[value]
    if value in _ONES:
        return _ONES[value]
    if value in _TENS:
        return _TENS[value]
    if value in {"one hundred", "hundred"}:
        return 100
    tokens = value.split()
    if len(tokens) == 2 and tokens[0] in _TENS and tokens[1] in _ONES and 1 <= _ONES[tokens[1]] <= 9:
        return _TENS[tokens[0]] + _ONES[tokens[1]]
    return None


class LocalRouter:
    """Fast, offline routing for common and predictable commands."""

    def __init__(self, wake_word: str = "aeris"):
        self.wake_word = wake_word

    HELP = (
        "Offline commands include: open Chrome or YouTube; search Google or YouTube; set volume or "
        "brightness; control music and windows; download https://example.com/file.zip; install VLC; "
        "search apps for OBS; list app updates; open Downloads; create, copy, move, read, or find allowed "
        "files; copy to or read the clipboard; look at my screen and explain this error; write Python code "
        "for an expense tracker; show computer health or battery; take a screenshot; check "
        "Gmail; lock, sleep, restart, or shut down the PC. Downloads, installs, file changes, email sending, "
        "and power actions require permission."
    )

    def route(self, text: str) -> PlannedResponse | None:
        source_text = text.strip()
        original = _strip_voice_wrappers(source_text, self.wake_word)
        normalized = _normalize_command(original)
        if not normalized:
            return PlannedResponse(reply="I did not hear a command.")

        # These are statements/questions, not permission to perform a mentioned action.
        # Return a local answer so a planner cannot reinterpret the denied command.
        if original[:1] in {'"', "'", "“", "‘", "`"} or re.search(
            r"\b(?:don['’]t|do not|never|if|unless|imagine|suppose|hypothetically|"
            r"said|says|told|asked|mat|nahi)\b", normalized
        ) and not re.match(r"^(?:type|send email|create note|make note|search|google|write|generate|remind me|set a reminder)\b", normalized):
            return PlannedResponse(reply="No action taken. Give one direct command when you want me to act.")
        data_command = re.match(r'^(?:type|send email|create note|make note|search|google|write|generate|remind me|set a reminder|look at|check|analyze|analyse|read)\b', normalized)
        clauses = re.split(r'\s*(?:,\s*(?:and\s+)?|\s+(?:and|then|aur)\s+)\s*', original, flags=re.I)
        if len(clauses) > 1 and not data_command and normalized != 'check system health and status':
            safe_tools = {'desktop.open_app', 'desktop.set_volume', 'desktop.change_volume',
                          'desktop.set_brightness', 'desktop.change_brightness', 'desktop.media_control',
                          'desktop.window_action', 'system.health', 'system.battery', 'system.status'}
            actions = []
            for clause in clauses[:13]:
                clause = re.sub(r'^(?:and|then)\s+', '', clause, flags=re.I)
                routed = self.route(clause) if clause.strip() else None
                if not routed or len(routed.actions) != 1 or routed.actions[0].tool not in safe_tools:
                    return PlannedResponse(reply='No action taken. One part of this task is unsupported or ambiguous. Use direct app, volume, brightness, media or window commands.')
                actions.extend(routed.actions)
            if len(clauses) > 12:
                return PlannedResponse(reply='No action taken. A task can contain at most twelve steps.')
            return PlannedResponse(actions=actions)
        if re.search(
            r"(?:\b(?:and|then|also|aur)\b|[;\n])\s*(?:then\s+)?"
            r"(?:set|change|open|close|launch|install|uninstall|delete|move|copy|volume|brightness|mute|shutdown|restart)\b",
            normalized,
        ) and not re.match(r"^(?:type|send email|create note|make note|search|google|write|generate|remind me|set a reminder)\b", normalized):
            return PlannedResponse(reply="No action taken. Please give these commands one at a time; compound actions are not supported yet.")

        if normalized in {
            "help",
            "commands",
            "offline help",
            "offline commands",
            "what can you do",
        }:
            return PlannedResponse(reply=self.HELP)
        organize = re.fullmatch(r'organize documents in (.+)', original, re.I)
        if organize:
            return self._action(original, 'files.organize', path=_clean_value(organize[1]))
        undo_batch = re.fullmatch(r'undo organization ([0-9a-f]{32})', normalized)
        if undo_batch:
            return self._action(original, 'files.undo_organization', batch_id=undo_batch[1])
        if normalized in {"status", "aeris status", "system status"}:
            return self._action(original, "system.status")
        if normalized in {"stop", "stop aeris", "emergency stop", "kill switch"}:
            return self._action(original, "system.stop")
        if normalized in {"resume", "resume aeris", "start aeris"}:
            return self._action(original, "system.resume")
        if normalized == "check system health and status":
            return PlannedResponse(actions=[ActionRequest("system.health", source_text=source_text),
                                            ActionRequest("system.status", source_text=source_text)])
        if normalized in {"test network connectivity", "network test"}:
            return self._action(original, "system.network_test", host="www.microsoft.com")
        if normalized in {"computer health", "system health", "pc health", "computer info", "system info", "mera computer health check karo"}:
            return self._action(original, "system.health")
        if normalized in {"battery", "battery status", "check battery", "how much battery"}:
            return self._action(original, "system.battery")
        if normalized in {"lock pc", "lock computer", "lock laptop", "lock windows", "computer lock karo"}:
            return self._action(original, "system.lock")
        if normalized in {"sleep pc", "sleep computer", "sleep laptop", "put computer to sleep"}:
            return self._action(original, "system.sleep")
        if normalized in {"shut down pc", "shutdown pc", "shut down computer", "shutdown computer"}:
            return self._action(original, "system.shutdown")
        if normalized in {"restart pc", "restart computer", "restart laptop", "reboot pc"}:
            return self._action(original, "system.restart")
        if normalized in {"cancel shutdown", "cancel restart", "abort shutdown"}:
            return self._action(original, "system.cancel_shutdown")

        if normalized in {"list reminders", "show reminders", "my reminders"}:
            return self._action(original, "reminder.list")
        identifier = r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
        cancel_reminder = re.fullmatch(r"cancel reminder " + identifier, normalized)
        if cancel_reminder:
            return self._action(original, "reminder.cancel", reminder_id=cancel_reminder[1])
        snooze = re.fullmatch(r"snooze reminder " + identifier + r"(?: for)? ([0-9]+) minutes?", normalized)
        if snooze:
            return self._action(original, "reminder.snooze", reminder_id=snooze[1], minutes=int(snooze[2]))
        day = r"(?:today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
        when = rf"(?:in [0-9]+ (?:second|minute|hour|day)s?|{day}(?: at [0-9]{{1,2}}(?::[0-9]{{2}})?\s*(?:am|pm)?)?|[0-9]{{4}}-\S+)"
        reminder = re.fullmatch(rf"(?:remind me|set a reminder)(?: (daily|weekly))? ({when}) to (.+)", original, re.I)
        if reminder:
            args = {"when": reminder[2], "message": reminder[3]}
            if reminder[1]:
                args["recurrence"] = reminder[1].lower()
            return self._action(original, "reminder.set", **args)
        reminder = re.fullmatch(rf"remind me to (.+) ({when})", original, re.I)
        if reminder:
            return self._action(original, "reminder.set", message=reminder[1], when=reminder[2])
        if re.match(r"^(?:remind me|set a reminder|cancel reminder|snooze reminder)\b", normalized):
            return PlannedResponse(reply="Use 'remind me in 15 minutes to stretch', 'remind me tomorrow at 9am to study', or select a reminder in the Reminders tab.")

        screen_question = re.match(
            r"^(?:look at|check|analyze|analyse|read) (?:my|the) screen(?: and|,)?\s*(.*)$",
            original,
            re.I | re.DOTALL,
        )
        if screen_question:
            question = _clean_value(screen_question.group(1)) or "Explain what is visible on my screen."
            return self._action(original, "vision.inspect_screen", question=question)
        if normalized in {
            "what is on my screen",
            "what's on my screen",
            "explain my screen",
            "help me with this screen",
            "read the error on my screen",
        }:
            return self._action(original, "vision.inspect_screen", question=original)

        coding = re.match(
            r"^(?:write|create|generate)(?: me)? (?:a )?(?:(python|javascript|java|c\+\+|c sharp|html) )?"
            r"(?:code|program|project|app|application)(?: for| to| that)? (.+)$",
            original,
            re.I | re.DOTALL,
        )
        if coding:
            language = f"Use {coding.group(1)}. " if coding.group(1) else ""
            return self._action(
                original,
                "coding.create_project",
                prompt=language + _clean_value(coding.group(2)),
            )
        build_app = re.match(
            r"^build(?: me)? (?:a|an) (.+?) (?:app|application|program|project)$",
            original,
            re.I | re.DOTALL,
        )
        if build_app:
            return self._action(
                original,
                "coding.create_project",
                prompt=f"Build a {_clean_value(build_app.group(1))} application.",
            )

        download = re.match(
            r"^(?:download|get)(?: file)?(?: from)? (https?://\S+?)(?: (?:as|name it) (.+))?$",
            original,
            re.I,
        )
        if download:
            arguments: dict[str, object] = {"url": _clean_value(download.group(1)).rstrip(".,!?")}
            if download.group(2):
                arguments["filename"] = _clean_value(download.group(2))
            return PlannedResponse(
                actions=[ActionRequest(tool="downloads.download", arguments=arguments, source_text=original)]
            )
        if normalized in {"open downloads", "open downloads folder", "show downloads", "downloads folder kholo"}:
            return self._action(original, "downloads.open_folder")
        if normalized in {"clear incomplete downloads", "remove incomplete downloads"}:
            return self._action(original, "downloads.clear_partial")

        local_installer = re.match(r"^install (?:downloaded )?installer (.+)$", original, re.I)
        if local_installer:
            return self._action(
                original, "packages.install_file", path=_clean_value(local_installer.group(1))
            )
        package_search = re.match(
            r"^(?:search|find)(?: available)? apps?(?: for)? (.+)$", original, re.I
        )
        if package_search:
            return self._action(
                original, "packages.search", query=_clean_value(package_search.group(1))
            )
        if normalized in {"list installed apps", "show installed apps", "list installed software"}:
            return self._action(original, "packages.list_installed")
        if normalized in {"list app updates", "show app updates", "check app updates", "available updates"}:
            return self._action(original, "packages.list_updates")
        package_change = re.match(
            r"^(install|uninstall|update)(?: app| software| package)? (.+)$", original, re.I
        )
        if package_change:
            operation = package_change.group(1).lower()
            return self._action(
                original,
                f"packages.{operation}",
                package=_clean_value(package_change.group(2)),
            )
        download_install = re.match(r"^download and install (.+)$", original, re.I)
        if download_install:
            return self._action(
                original, "packages.install", package=_clean_value(download_install.group(1))
            )

        youtube = re.match(r"^(?:search|find)(?: on)? youtube(?: for)? (.+)$", original, re.I)
        if youtube:
            return self._action(original, "browser.search_youtube", query=_clean_value(youtube.group(1)))
        web = re.match(r"^(?:search(?: the)? web(?: for)?|google) (.+)$", original, re.I)
        if web:
            return self._action(original, "browser.search_web", query=_clean_value(web.group(1)))
        if normalized in {"open youtube", "launch youtube", "youtube kholo"}:
            return self._action(original, "browser.open_url", url="https://www.youtube.com")
        if normalized in {"open gmail", "launch gmail"}:
            return self._action(original, "browser.open_url", url="https://mail.google.com")
        url = re.match(r"^(?:open|go to) (https?://\S+|[\w.-]+\.[a-z]{2,}(?:/\S*)?)$", original, re.I)
        if url:
            return self._action(original, "browser.open_url", url=_clean_value(url.group(1)))

        if normalized in {"increase volume", "volume up", "turn volume up", "volume badhao"}:
            return self._action(original, "desktop.change_volume", delta=10)
        if normalized in {"decrease volume", "volume down", "turn volume down", "volume kam karo"}:
            return self._action(original, "desktop.change_volume", delta=-10)
        if normalized in {"mute", "mute volume", "unmute", "unmute volume"}:
            return self._action(original, "desktop.media_control", action="unmute" if normalized.startswith("unmute") else "mute")
        if normalized in {"increase brightness", "brightness up", "turn brightness up"}:
            return self._action(original, "desktop.change_brightness", delta=10)
        if normalized in {"decrease brightness", "brightness down", "turn brightness down", "screen ki brightness kam karo"}:
            return self._action(original, "desktop.change_brightness", delta=-10)
        control = re.fullmatch(
            r"(?:(?:set|change|make|put) (?:the )?)?(volume|awaz|brightness) "
            r"(?:(?:to|at|for) )?(.+?)(?: percent)?(?: kar do| bus)?", normalized,
        )
        if control:
            level = _extract_level(control.group(2))
            if level is not None:
                tool = "desktop.set_brightness" if control.group(1) == "brightness" else "desktop.set_volume"
                return self._action(source_text, tool, level=level)
            return PlannedResponse(reply="No action taken. Use a whole percentage from 0 to 100, for example 'set volume to 35'.")
        if re.search(r"\b(?:volume|awaz|brightness)\b", normalized) and not re.match(
            r"^(?:type|send email|create note|make note|search|google|write|generate)\b", normalized
        ):
            return PlannedResponse(reply="No action taken. Use one direct volume or brightness command with a whole percentage from 0 to 100.")

        media = {
            "play": "play",
            "pause": "pause",
            "play music": "play",
            "pause music": "pause",
            "pause the song": "pause",
            "stop the music": "stop",
            "play the song": "play",
            "toggle playback": "play_pause",
            "toggle music": "play_pause",
            "toggle mute": "toggle_mute",
            "next song": "next",
            "next track": "next",
            "previous song": "previous",
            "previous track": "previous",
            "stop music": "stop",
        }
        if normalized in media:
            return self._action(original, "desktop.media_control", action=media[normalized])

        if normalized in {"take screenshot", "take a screenshot", "screenshot", "capture screen", "screenshot le lo"}:
            return self._action(original, "desktop.screenshot")
        clipboard_copy = re.match(r"^(?:copy|put) (.+?) (?:to|on) (?:the )?clipboard$", original, re.I | re.DOTALL)
        if clipboard_copy:
            return self._action(
                original, "desktop.clipboard_copy", text=_clean_value(clipboard_copy.group(1))
            )
        if normalized in {"read clipboard", "what is on clipboard", "show clipboard"}:
            return self._action(original, "desktop.clipboard_read")
        window_actions = {
            "show desktop": "show_desktop",
            "switch window": "switch_window",
            "switch app": "switch_window",
            "task view": "task_view",
            "minimize all windows": "minimize_all",
            "maximize window": "maximize_current",
            "maximize current window": "maximize_current",
            "minimize window": "minimize_current",
            "minimize current window": "minimize_current",
            'minimize this window': 'minimize_current',
            'maximize this window': 'maximize_current',
        }
        if normalized in window_actions:
            return self._action(original, "desktop.window_action", action=window_actions[normalized])
        if normalized in {"close current window", "close this window"}:
            return self._action(original, "desktop.close_current_window")
        typed = re.match(r"^type (.+)$", original, re.I | re.DOTALL)
        if typed:
            return self._action(original, "desktop.type_text", text=typed.group(1))

        email = re.match(
            r"^send email to (\S+@\S+) subject (.+?) (?:message|body) (.+)$",
            original,
            re.I | re.DOTALL,
        )
        if email:
            return self._action(
                original,
                "email.send",
                to=_clean_value(email.group(1)),
                subject=_clean_value(email.group(2)),
                body=_clean_value(email.group(3)),
            )
        if normalized in {"check my email", "check my emails", "show recent emails", "read my emails"}:
            return self._action(original, "email.list_recent", count=5)
        if normalized in {"read latest email", "read my latest email", "latest email"}:
            return self._action(original, "email.read_latest")

        found = re.match(r"^(?:find|search for) (?:a )?file(?: named| called)? (.+)$", original, re.I)
        if found:
            return self._action(original, "files.find", query=_clean_value(found.group(1)))
        listed = re.match(r"^(?:list|show) files(?: in)? (.+)$", original, re.I)
        if listed:
            return self._action(original, "files.list", path=_clean_value(listed.group(1)))
        read_file = re.match(r"^read file (.+)$", original, re.I)
        if read_file:
            return self._action(original, "files.read", path=_clean_value(read_file.group(1)))
        open_file = re.match(r"^open file (.+)$", original, re.I)
        if open_file:
            return self._action(original, "files.open", path=_clean_value(open_file.group(1)))
        delete_file = re.match(r"^(?:delete|remove) file (.+)$", original, re.I)
        if delete_file:
            return self._action(original, "files.delete", path=_clean_value(delete_file.group(1)))
        open_folder = re.match(r"^open folder (.+)$", original, re.I)
        if open_folder:
            return self._action(original, "files.open_folder", path=_clean_value(open_folder.group(1)))
        create_folder = re.match(r"^(?:create|make)(?: a)? folder (.+)$", original, re.I)
        if create_folder:
            return self._action(original, "files.create_folder", path=_clean_value(create_folder.group(1)))
        create_note = re.match(r"^(?:create|make)(?: a)? note (.+?) (?:saying|with text) (.+)$", original, re.I | re.DOTALL)
        if create_note:
            path = _clean_value(create_note.group(1))
            if not Path(path).suffix:
                path += ".txt"
            return self._action(
                original,
                "files.write_text",
                path=path,
                text=_clean_value(create_note.group(2)),
            )
        copy_file = re.match(r"^copy file (.+?) to (.+)$", original, re.I)
        if copy_file:
            return self._action(
                original,
                "files.copy",
                source=_clean_value(copy_file.group(1)),
                destination=_clean_value(copy_file.group(2)),
            )
        move_file = re.match(r"^(?:move|rename) file (.+?) to (.+)$", original, re.I)
        if move_file:
            return self._action(
                original,
                "files.move",
                source=_clean_value(move_file.group(1)),
                destination=_clean_value(move_file.group(2)),
            )

        close_app = re.match(r"^(?:close|quit|exit) (.+)$", normalized, re.I)
        if close_app:
            return self._action(original, "desktop.close_app", name=_clean_value(close_app.group(1)).lower())
        open_app = re.match(r"^(?:(?:open|launch|start)\s+(.+))|(?:(.+)\s+open karo)$", normalized, re.I)
        if open_app:
            name = _clean_value(open_app.group(1) or open_app.group(2)).lower()
            return self._action(original, "desktop.open_app", name=name)
        return None

    @staticmethod
    def _action(source_text: str, tool: str, **arguments: object) -> PlannedResponse:
        return PlannedResponse(actions=[ActionRequest(tool=tool, arguments=arguments, source_text=source_text)])
