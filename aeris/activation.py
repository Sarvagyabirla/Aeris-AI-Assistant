"""Addressed speech extraction, not a trained wake-word model."""
import re


def extract_addressed_command(text: str, phrases: tuple[str, ...]) -> str | None:
    for phrase in phrases:
        if not phrase.strip():
            continue
        pattern = r"^\s*(?:hey[\s,]+)?" + re.escape(phrase.strip()) + r"(?!\w)[\s,.:;!?-]*"
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            return text[match.end():].strip()
    return None