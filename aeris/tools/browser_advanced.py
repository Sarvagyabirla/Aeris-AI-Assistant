import queue
import threading
from urllib.parse import urlparse

from ..models import ActionResult


class PlaywrightWorker(threading.Thread):
    def __init__(self, allowed_domains: tuple[str, ...]):
        super().__init__(daemon=True)
        self.allowed_domains = allowed_domains
        self.command_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.start()

    def run(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            
            while True:
                cmd, args = self.command_queue.get()
                if cmd == "quit":
                    break
                
                try:
                    if cmd == "navigate":
                        url = args[0]
                        domain = urlparse(url).netloc.lower()
                        if "*" not in self.allowed_domains and not any(d in domain for d in self.allowed_domains):
                            self.result_queue.put(ActionResult(False, f"Domain {domain} is not allowed."))
                            continue
                            
                        page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        self.result_queue.put(ActionResult(True, f"Navigated to {page.title()}", data={"url": url, "title": page.title()}))
                    
                    elif cmd == "extract":
                        text = page.evaluate("document.body.innerText")
                        preview = text[:5000] + ("..." if len(text) > 5000 else "")
                        self.result_queue.put(ActionResult(True, "Extracted text from page.", data={"content": preview}))
                        
                    elif cmd == "click":
                        selector = args[0]
                        page.locator(selector).first.click(timeout=5000)
                        page.wait_for_load_state("domcontentloaded")
                        self.result_queue.put(ActionResult(True, f"Clicked '{selector}'. Current title: {page.title()}"))
                        
                    elif cmd == "fill":
                        selector, text = args[0], args[1]
                        page.locator(selector).first.fill(text, timeout=5000)
                        self.result_queue.put(ActionResult(True, f"Filled '{selector}' with provided text."))
                        
                except Exception as e:
                    self.result_queue.put(ActionResult(False, f"Failed to {cmd}: {e}", error="playwright_error"))

    def execute(self, cmd, *args) -> ActionResult:
        self.command_queue.put((cmd, args))
        return self.result_queue.get()

class BrowserAdvancedTools:
    def __init__(self, allowed_domains: tuple[str, ...]):
        self.allowed_domains = allowed_domains
        self._worker = None
        self._lock = threading.Lock()

    def _get_worker(self) -> PlaywrightWorker:
        with self._lock:
            if self._worker is None:
                self._worker = PlaywrightWorker(self.allowed_domains)
            return self._worker

    def navigate(self, arguments: dict[str, object]) -> ActionResult:
        return self._get_worker().execute("navigate", str(arguments["url"]))

    def extract(self, arguments: dict[str, object]) -> ActionResult:
        return self._get_worker().execute("extract")

    def click(self, arguments: dict[str, object]) -> ActionResult:
        return self._get_worker().execute("click", str(arguments["selector"]))

    def fill(self, arguments: dict[str, object]) -> ActionResult:
        return self._get_worker().execute("fill", str(arguments["selector"]), str(arguments["text"]))

