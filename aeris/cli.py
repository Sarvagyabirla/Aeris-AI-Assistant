from __future__ import annotations

import argparse
import ctypes
import os
import sys

from .assistant import AerisAssistant
from .config import AerisConfig
from .integrations.voice import VoiceService, VoiceUnavailableError
from .models import ActionRequest, PermissionLevel

_GUI_MUTEX: int | None = None


def _acquire_gui_instance() -> bool:
    global _GUI_MUTEX
    if os.name != "nt":
        return True
    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel32.CreateMutexW(None, False, "Local\\AerisCognitiveDesktop")
    if not handle:
        return True
    if int(kernel32.GetLastError()) == 183:
        kernel32.CloseHandle(handle)
        return False
    _GUI_MUTEX = int(handle)
    return True


def approval_prompt(request: ActionRequest, level: PermissionLevel, preview: str) -> bool:
    heading = "SESSION PERMISSION" if level is PermissionLevel.SESSION else "CONFIRM ACTION"
    print(f"\n[{heading}] {preview}")
    if request.tool == "email.send":
        print(f"To: {request.arguments.get('to')}\nSubject: {request.arguments.get('subject')}")
        print(f"Message: {request.arguments.get('body')}")
    elif request.tool == "downloads.download":
        print(f"URL: {request.arguments.get('url')}")
        print("The file will be saved, scanned when Defender is available, and not executed.")
    elif request.tool == "vision.inspect_screen":
        print(f"Question: {request.arguments.get('question')}")
        print("The visible screens will be captured once, sent to the configured AI model, and not saved.")
    elif request.tool == "coding.create_project":
        print(f"Request: {request.arguments.get('prompt')}")
        print("A new project will be validated and written without running or overwriting code.")
    elif request.tool in {
        "packages.install",
        "packages.update",
        "packages.uninstall",
        "packages.install_file",
    }:
        print(f"Target: {request.arguments.get('package') or request.arguments.get('path', '')}")
    try:
        answer = input("Allow? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nApproval denied because no interactive confirmation was available.")
        return False
    return answer in {"y", "yes"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Aeris permission-first Windows assistant")
    parser.add_argument("--once", help="Run one text command and exit")
    parser.add_argument("--voice", action="store_true", help="Use push-to-talk voice mode")
    parser.add_argument("--gui", action="store_true", help="Open the Aeris desktop interface")
    parser.add_argument("--live", action="store_true", help="Execute actions instead of dry-run simulation")
    parser.add_argument("--no-ai", action="store_true", help="Disable Gemini planning")
    return parser


def _assistant_from_args(args: argparse.Namespace) -> AerisAssistant:
    loaded = AerisConfig.load()
    config = loaded.with_overrides(
        dry_run=not args.live,
        ai_enabled=loaded.ai_enabled and not args.no_ai,
    )
    return AerisAssistant(config)


def text_loop(assistant: AerisAssistant) -> int:
    print("Aeris is ready. Type 'help' for commands or 'exit' to leave.")
    print("Mode:", "LIVE" if not assistant.config.dry_run else "DRY RUN")
    while True:
        try:
            text = input("\nYou > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return 0
        if text.lower() in {"exit", "quit", "goodbye"}:
            print("Goodbye.")
            return 0
        turn = assistant.handle(text, approval_prompt)
        print(f"Aeris > {turn.reply}")


def voice_loop(assistant: AerisAssistant) -> int:
    voice = VoiceService(
        assistant.config.voice_model,
        assistant.config.voice_record_seconds,
        assistant.config.voice_device,
        assistant.config.voice_language,
    )
    print("Aeris voice mode. Press Enter to speak, or type q and Enter to exit.")
    print("Mode:", "LIVE" if not assistant.config.dry_run else "DRY RUN")
    while True:
        choice = input("\nPress Enter to listen > ").strip().lower()
        if choice in {"q", "quit", "exit"}:
            return 0
        print(f"Listening for {assistant.config.voice_record_seconds} seconds...")
        try:
            text = voice.listen_once()
        except VoiceUnavailableError as exc:
            print(f"Voice unavailable: {exc}")
            return 2
        if not text:
            print("I did not hear speech. Try again.")
            continue
        print(f"You > {text}")
        turn = assistant.handle(text, approval_prompt)
        print(f"Aeris > {turn.reply}")
        try:
            voice.speak(turn.reply.splitlines()[0][:500])
        except VoiceUnavailableError:
            pass


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    assistant = _assistant_from_args(args)
    if args.gui:
        if not _acquire_gui_instance():
            if os.name == "nt":
                ctypes.windll.user32.MessageBoxW(0, "Aeris is already running.", "Aeris", 0x40)
            return 0
        from .ui import launch_desktop

        return launch_desktop(assistant)
    if args.once:
        turn = assistant.handle(args.once, approval_prompt)
        print(turn.reply)
        return 0 if all(result.success for result in turn.results) else 1
    if args.voice:
        return voice_loop(assistant)
    return text_loop(assistant)


if __name__ == "__main__":
    sys.exit(main())
