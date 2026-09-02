from __future__ import annotations

import re
from pathlib import Path

from .models import ActionRequest, PlannedResponse


def _clean_value(value: str) -> str:
    return value.strip().strip("\"'")


_WAKE_NAMES = (
    "aeris",
    "airis",
    "aris",
    "arish",
    "eris",
    "haris",
    "iris",
    "एरिस",
    "ऐरिस",
    "हैरिस",
)
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


def has_wake_word(value: str, preferred: str = "aeris") -> bool:
    names = tuple(dict.fromkeys((preferred.strip().lower(), *_WAKE_NAMES)))
    wake_names = "|".join(re.escape(name) for name in names if name)
    return bool(
        re.match(
            rf"^(?:(?:ok|okay|hey|hello)[\s,.:;-]+)?(?:{wake_names})\b",
            value.strip(),
            flags=re.I,
        )
    )


def strip_wake_word(value: str, preferred: str = "aeris") -> str:
    names = tuple(dict.fromkeys((preferred.strip().lower(), *_WAKE_NAMES)))
    wake_names = "|".join(re.escape(name) for name in names if name)
    return re.sub(
        rf"^(?:(?:ok|okay|hey|hello)[\s,.:;-]+)?(?:{wake_names})\b[\s,.:;-]*",
        "",
        value.strip(),
        count=1,
        flags=re.I,
    ).strip()


def _strip_voice_wrappers(value: str) -> str:
    command = value.strip()
    wake_names = "|".join(re.escape(name) for name in _WAKE_NAMES)
    command = re.sub(
        rf"^(?:(?:ok|okay|hey|hello)[\s,.:;-]+)?(?:{wake_names})\b[\s,.:;-]*",
        "",
        command,
        flags=re.I,
    )
    command = re.sub(r"^(?:please\s+|can you\s+|could you\s+|would you\s+)+", "", command, flags=re.I)
    return command.strip()


def _normalize_command(value: str) -> str:
    normalized = value.lower().replace("%", " percent ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(r"[\s,.:;!?-]+$", "", normalized)
    normalized = re.sub(r"\s+(?:please|now)$", "", normalized)
    return normalized


def _extract_level(value: str) -> int | None:
    digit = re.search(r"(?<!\d)(100|\d{1,2})(?!\d)", value)
    if digit:
        return int(digit.group(1))

    tokens = re.findall(r"[a-z]+", value.lower().replace("-", " "))
    for index, token in enumerate(tokens):
        if token not in _ONES and token not in _TENS and token != "hundred":
            continue
        total = 0
        consumed = False
        for number_token in tokens[index:]:
            if number_token in _ONES:
                total += _ONES[number_token]
                consumed = True
            elif number_token in _TENS:
                total += _TENS[number_token]
                consumed = True
            elif number_token == "hundred" and consumed:
                total = max(total, 1) * 100
            else:
                break
        if consumed and 0 <= total <= 100:
            return total
    return None


class LocalRouter:
    """Fast, offline routing for common and predictable commands."""

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
        original = _strip_voice_wrappers(source_text)
        normalized = _normalize_command(original)
        if not normalized:
            return PlannedResponse(reply="I did not hear a command.")

        if normalized in {
            "help",
            "commands",
            "offline help",
            "offline commands",
            "what can you do",
        }:
            return PlannedResponse(reply=self.HELP)
        if normalized in {"status", "aeris status", "system status"}:
            return self._action(original, "system.status")
        if normalized in {"stop", "stop aeris", "emergency stop", "kill switch"}:
            return self._action(original, "system.stop")
        if normalized in {"resume", "resume aeris", "start aeris"}:
            return self._action(original, "system.resume")
        if normalized in {"computer health", "system health", "pc health", "computer info", "system info"}:
            return self._action(original, "system.health")
        if normalized in {"battery", "battery status", "check battery", "how much battery"}:
            return self._action(original, "system.battery")
        if normalized in {"lock pc", "lock computer", "lock laptop", "lock windows"}:
            return self._action(original, "system.lock")
        if normalized in {"sleep pc", "sleep computer", "sleep laptop", "put computer to sleep"}:
            return self._action(original, "system.sleep")
        if normalized in {"shut down pc", "shutdown pc", "shut down computer", "shutdown computer"}:
            return self._action(original, "system.shutdown")
        if normalized in {"restart pc", "restart computer", "restart laptop", "reboot pc"}:
            return self._action(original, "system.restart")
        if normalized in {"cancel shutdown", "cancel restart", "abort shutdown"}:
            return self._action(original, "system.cancel_shutdown")

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
        if normalized in {"open downloads", "open downloads folder", "show downloads"}:
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
        if normalized in {"open youtube", "launch youtube"}:
            return self._action(original, "browser.open_url", url="https://www.youtube.com")
        if normalized in {"open gmail", "launch gmail"}:
            return self._action(original, "browser.open_url", url="https://mail.google.com")
        url = re.match(r"^(?:open|go to) (https?://\S+|[\w.-]+\.[a-z]{2,}(?:/\S*)?)$", original, re.I)
        if url:
            return self._action(original, "browser.open_url", url=_clean_value(url.group(1)))

        if normalized in {"increase volume", "volume up", "turn volume up"}:
            return self._action(original, "desktop.change_volume", delta=10)
        if normalized in {"decrease volume", "volume down", "turn volume down"}:
            return self._action(original, "desktop.change_volume", delta=-10)
        if normalized in {"mute", "mute volume", "unmute", "unmute volume"}:
            return self._action(original, "desktop.media_control", action="mute")
        if "volume" in normalized:
            level = _extract_level(normalized)
            if level is not None and re.search(r"\b(?:set|change|make|put|volume)\b", normalized):
                return self._action(source_text, "desktop.set_volume", level=level)

        if normalized in {"increase brightness", "brightness up", "turn brightness up"}:
            return self._action(original, "desktop.change_brightness", delta=10)
        if normalized in {"decrease brightness", "brightness down", "turn brightness down"}:
            return self._action(original, "desktop.change_brightness", delta=-10)
        if "brightness" in normalized:
            level = _extract_level(normalized)
            if level is not None and re.search(r"\b(?:set|change|make|put|brightness)\b", normalized):
                return self._action(source_text, "desktop.set_brightness", level=level)

        media = {
            "play": "play_pause",
            "pause": "play_pause",
            "play music": "play_pause",
            "pause music": "play_pause",
            "next song": "next",
            "next track": "next",
            "previous song": "previous",
            "previous track": "previous",
            "stop music": "stop",
        }
        if normalized in media:
            return self._action(original, "desktop.media_control", action=media[normalized])

        if normalized in {"take screenshot", "take a screenshot", "screenshot", "capture screen"}:
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
        open_app = re.match(r"^(?:open|launch|start) (.+)$", normalized, re.I)
        if open_app:
            return self._action(original, "desktop.open_app", name=_clean_value(open_app.group(1)).lower())
        return None

    @staticmethod
    def _action(source_text: str, tool: str, **arguments: object) -> PlannedResponse:
        return PlannedResponse(actions=[ActionRequest(tool=tool, arguments=arguments, source_text=source_text)])
