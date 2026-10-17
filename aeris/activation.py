"""Addressed speech extraction, not a trained wake-word model."""
import re

# Legacy text aliases are explicit. Passive listening uses only the configured phrase;
# accepting an alias as typed input never opts the microphone into that alias.
TEXT_WAKE_ALIASES = ("aeris", "airis", "aris", "arish", "eris", "haris", "iris", "एरिस", "ऐरिस", "हैरिस")


def extract_addressed_command(text: str, phrases: tuple[str, ...]) -> str | None:
    # Longest first avoids truncating a configured multi-word phrase at an alias.
    for phrase in sorted(set(phrases), key=len, reverse=True):
        if not phrase.strip():
            continue
        pattern = r"^\s*(?:(?:ok|okay|hey|hello)[\s,.:;-]+)?" + re.escape(phrase.strip()) + r"(?!\w)[\s,.:;!?-]*"
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            return text[match.end():].strip()
    return None


def strip_address(text: str, phrases: tuple[str, ...]) -> str:
    command = extract_addressed_command(text, phrases)
    return text.strip() if command is None else command
