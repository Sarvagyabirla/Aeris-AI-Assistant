import queue
import threading
import time
import uuid
from concurrent.futures import Future
from urllib.parse import urljoin, urlparse

from ..models import ActionResult


class PlaywrightWorker(threading.Thread):
    def __init__(self, allowed_domains: tuple[str, ...]):
        super().__init__(daemon=True)
        self.allowed_domains = allowed_domains
        self.command_queue = queue.Queue(maxsize=8)
        self.ready = threading.Event()
        self.stopping = threading.Event()
        self.startup_error = None
        self.start()

    def run(self):
        try:
            self._run_browser()
        except Exception:
            self.startup_error = "Browser unavailable. Install Playwright and its Chromium runtime, then retry."
        finally:
            self.ready.set()
            self.stopping.set()

    def _run_browser(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, timeout=15000)
            context = browser.new_context(service_workers="block", accept_downloads=False)
            def policy(route):
                # Explicit redirect handling: never let Chromium follow an
                # unchecked destination after route.continue_().
                destination = route.request.url
                try:
                    for _ in range(6):
                        if self.stopping.is_set() or not allowed_url(destination, self.allowed_domains):
                            route.abort()
                            return
                        response = route.fetch(url=destination, max_redirects=0, timeout=10000)
                        if response.status in {301, 302, 303, 307, 308}:
                            location = response.headers.get("location")
                            if not location:
                                route.abort()
                                return
                            destination = urljoin(destination, location)
                            continue
                        route.fulfill(response=response)
                        return
                    route.abort()
                except Exception:
                    route.abort()
            context.route("**/*", policy)
            page = context.new_page()
            context.on("page", lambda popup: popup.close() if popup is not page else None)
            self.ready.set()
            
            while not self.stopping.is_set():
                try:
                    identity, cmd, args, future, token, deadline = self.command_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                if future.cancelled() or time.monotonic() >= deadline or (token and token.is_cancelled):
                    continue
                def deliver(result):
                    if not future.cancelled():
                        future.set_result(result)
                if cmd == "quit":
                    break
                
                try:
                    if cmd == "navigate":
                        url = args[0]
                        domain = urlparse(url).netloc.lower()
                        if not allowed_url(url, self.allowed_domains):
                            deliver(ActionResult(False, f"Domain {domain} is not allowed."))
                            continue
                            
                        page.goto(url, wait_until="domcontentloaded", timeout=15000)
                        if not allowed_url(page.url, self.allowed_domains):
                            raise ValueError("Final page is not allowed")
                        deliver(ActionResult(True, f"Navigated to {page.title()}", data={"url": page.url, "title": page.title()}))
                    
                    elif cmd == "extract":
                        text = page.evaluate("document.body.innerText")
                        preview = text[:5000] + ("..." if len(text) > 5000 else "")
                        deliver(ActionResult(True, "Extracted text from page.", data={"content": preview, "url": page.url, "command_id": identity, "captured_at": time.time()}))
                        
                    elif cmd == "click":
                        if page.url != args[1] or not allowed_url(page.url, self.allowed_domains):
                            raise ValueError("Page changed since approval")
                        selector = args[0]
                        locator = page.locator(selector)
                        if locator.count() != 1:
                            raise ValueError("Target must match exactly one element")
                        if token:
                            token.raise_if_cancelled()
                        locator.click(timeout=5000)
                        deliver(ActionResult(True, "Click delivered; task completion is not yet verified.", data={"url": page.url}))
                        
                    elif cmd == "fill":
                        if page.url != args[2] or not allowed_url(page.url, self.allowed_domains):
                            raise ValueError("Page changed since approval")
                        selector, text = args[0], args[1]
                        locator = page.locator(selector)
                        if locator.count() != 1:
                            raise ValueError("Target must match exactly one element")
                        if token:
                            token.raise_if_cancelled()
                        locator.fill(text, timeout=5000)
                        if locator.input_value(timeout=5000) != text:
                            raise ValueError("Input value verification failed")
                        deliver(ActionResult(True, "Input value verified."))
                        
                except Exception:
                    deliver(ActionResult(False, f"Browser {cmd} failed; check policy, target uniqueness and runtime readiness.", error="playwright_error"))
            browser.close()

    def execute(self, cmd, *args, token=None) -> ActionResult:
        deadline = time.monotonic() + 20
        while not self.ready.wait(0.05):
            if token:
                token.raise_if_cancelled()
            if time.monotonic() >= deadline:
                self.stopping.set()
                return ActionResult(False, "Browser startup timed out.", error="browser_timeout")
        if self.startup_error or not self.is_alive() or self.stopping.is_set():
            return ActionResult(False, self.startup_error or "Browser worker is unavailable.", error="browser_unavailable")
        future = Future()
        deadline = time.monotonic() + 20
        try:
            self.command_queue.put_nowait((uuid.uuid4().hex, cmd, args, future, token, deadline))
        except queue.Full:
            return ActionResult(False, "Browser is busy.", error="browser_busy")
        while not future.done():
            if (token and token.is_cancelled) or time.monotonic() >= deadline or not self.is_alive():
                future.cancel()
                if token:
                    token.raise_if_cancelled()
                return ActionResult(False, "Browser wait ended; write outcome may be uncertain. Do not blindly retry.", error="browser_timeout")
            self.stopping.wait(0.05)
        return future.result()

    def close(self, timeout=20):
        self.stopping.set()
        self.join(timeout)
        return not self.is_alive()

class BrowserAdvancedTools:
    def __init__(self, allowed_domains: tuple[str, ...]):
        self.allowed_domains = allowed_domains
        self._worker = None
        self._lock = threading.Lock()

    def _get_worker(self) -> PlaywrightWorker:
        with self._lock:
            if self._worker is None or not self._worker.is_alive():
                self._worker = PlaywrightWorker(self.allowed_domains)
            return self._worker

    def close(self):
        return self._worker.close() if self._worker else True

    def navigate(self, arguments: dict[str, object], token=None) -> ActionResult:
        return self._get_worker().execute("navigate", str(arguments["url"]), token=token)

    def extract(self, arguments: dict[str, object], token=None) -> ActionResult:
        return self._get_worker().execute("extract", token=token)

    def click(self, arguments: dict[str, object], token=None) -> ActionResult:
        return self._get_worker().execute("click", str(arguments["selector"]), str(arguments["expected_url"]), token=token)

    def fill(self, arguments: dict[str, object], token=None) -> ActionResult:
        return self._get_worker().execute("fill", str(arguments["selector"]), str(arguments["text"]), str(arguments["expected_url"]), token=token)


def allowed_url(url: str, domains: tuple[str, ...]) -> bool:
    """Exact host matches; subdomains require an explicit *.example.com rule."""
    import ipaddress
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").rstrip(".").encode("idna").decode().lower()
        if parsed.scheme not in {"http", "https"} or not host or parsed.username or parsed.password:
            return False
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        for entry in domains:
            if entry == "*":
                continue
            policy = urlparse(entry if "://" in entry else "https://" + entry)
            rule = (policy.hostname or "").rstrip(".").lower()
            if host == rule or (rule.startswith("*.") and host.endswith("." + rule[2:])):
                if "://" in entry and parsed.scheme != policy.scheme:
                    continue
                if port == (policy.port or (443 if parsed.scheme == "https" else 80)):
                    return True
        if "*" not in domains or port not in {80, 443} or host == "localhost":
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return "." in host and not host.endswith((".local", ".internal", ".localhost"))
    except (ValueError, UnicodeError):
        return False

