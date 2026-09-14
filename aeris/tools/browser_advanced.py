import threading

from ..models import ActionResult

class PlaywrightContext:
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_context(cls) -> "PlaywrightContext":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def navigate(self, url: str) -> ActionResult:
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
            return ActionResult(True, f"Navigated to {self.page.title()}", data={"url": url, "title": self.page.title()})
        except Exception as e:
            return ActionResult(False, f"Failed to navigate: {e}", error="playwright_error")

    def extract_text(self) -> ActionResult:
        try:
            text = self.page.evaluate("document.body.innerText")
            preview = text[:5000] + ("..." if len(text) > 5000 else "")
            return ActionResult(True, "Extracted text from page.", data={"content": preview})
        except Exception as e:
            return ActionResult(False, f"Failed to extract text: {e}", error="playwright_error")

    def click(self, selector: str) -> ActionResult:
        try:
            self.page.locator(selector).first.click(timeout=5000)
            self.page.wait_for_load_state("domcontentloaded")
            return ActionResult(True, f"Clicked '{selector}'. Current title: {self.page.title()}")
        except Exception as e:
            return ActionResult(False, f"Failed to click '{selector}': {e}", error="playwright_error")

    def fill(self, selector: str, text: str) -> ActionResult:
        try:
            self.page.locator(selector).first.fill(text, timeout=5000)
            return ActionResult(True, f"Filled '{selector}' with provided text.")
        except Exception as e:
            return ActionResult(False, f"Failed to fill '{selector}': {e}", error="playwright_error")


class BrowserAdvancedTools:
    def __init__(self):
        # Instantiate later to avoid playwright startup delay if unused
        pass
        
    def _ctx(self) -> PlaywrightContext:
        return PlaywrightContext.get_context()

    def navigate(self, arguments: dict[str, object]) -> ActionResult:
        return self._ctx().navigate(str(arguments["url"]))

    def extract(self, arguments: dict[str, object]) -> ActionResult:
        return self._ctx().extract_text()

    def click(self, arguments: dict[str, object]) -> ActionResult:
        return self._ctx().click(str(arguments["selector"]))

    def fill(self, arguments: dict[str, object]) -> ActionResult:
        return self._ctx().fill(str(arguments["selector"]), str(arguments["text"]))
