from __future__ import annotations

from io import BytesIO

from ..models import ActionResult


class ScreenVision:
    """Capture the visible desktop only when invoked through Aeris permissions."""

    def __init__(self, api_key: str | None, model: str):
        self.api_key = api_key
        self.model = model

    def inspect(self, arguments: dict[str, object]) -> ActionResult:
        if not self.api_key:
            return ActionResult(
                False,
                "Screen understanding needs GEMINI_API_KEY. Normal offline computer commands still work.",
                error="ai_not_configured",
            )
        question = str(arguments.get("question", "Explain what is visible and suggest the next useful action."))
        question = question.strip()[:3_000]
        if not question:
            question = "Explain what is visible and suggest the next useful action."

        try:
            from google import genai
            from google.genai import types
            from PIL import ImageGrab
        except ImportError:
            return ActionResult(
                False,
                "Install the Aeris AI and Windows extras to understand the screen.",
                error="missing_dependency",
            )

        try:
            image = ImageGrab.grab(all_screens=True)
            image.thumbnail((1920, 1080))
            buffer = BytesIO()
            image.convert("RGB").save(buffer, format="JPEG", quality=82, optimize=True)
            instruction = (
                "You are Aeris, a permission-first Windows screen assistant. Analyze only the pixels in this "
                "single screenshot. Do not claim access to hidden windows, files, browser history, or the camera. "
                "Never reproduce passwords, API keys, private tokens, recovery codes, or payment details; mask them. "
                "When code or an error is visible, explain the cause and give precise safe next steps. Keep the answer "
                f"practical and concise. User request: {question}"
            )
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model,
                contents=[
                    instruction,
                    types.Part.from_bytes(data=buffer.getvalue(), mime_type="image/jpeg"),
                ],
            )
        except Exception:
            return ActionResult(
                False,
                "Aeris could not understand the screen. Check the internet connection and Gemini configuration.",
                error="screen_vision_failed",
            )

        answer = (response.text or "").strip()
        if not answer:
            return ActionResult(False, "The screen model returned no explanation.", error="empty_ai_response")
        return ActionResult(
            True,
            "Screen analysis completed.",
            data={"analysis": answer, "capture_retained": False},
        )
