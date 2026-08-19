from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import importlib.metadata
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

from .contracts import TaskPacket
from .facility import ArtifactEvidence, FacilityError, FacilityEvidence, FacilityKind, stable_digest, validate_live_task


@dataclass(frozen=True)
class BrowserStep:
    action: str
    selector: str = ""
    value: str = ""
    name: str = ""


@dataclass(frozen=True)
class BrowserScenario:
    scenario_id: str
    url: str
    steps: tuple[BrowserStep, ...]
    source_binding: str
    allowed_hosts: tuple[str, ...] = ()


def browser_host_resource(host: str) -> str:
    return f"browser-host:{host.lower()}"


def browser_request_binding(scenario: BrowserScenario, request_id: str) -> str:
    return stable_digest({
        "facility": "browser.playwright",
        "request_id": request_id,
        "scenario_digest": stable_digest(scenario),
    })


class PlaywrightFacility:
    capability = "browser.playwright"
    network_authority_enabled = False

    @staticmethod
    def _browser_launch_args() -> list[str]:
        return [
            "--disable-background-networking",
            "--host-resolver-rules=MAP * ~NOTFOUND",
            "--host-resolver-retry-attempts=0",
        ]

    @staticmethod
    def _network_disable_script() -> str:
        return r"""
for (const name of ["RTCPeerConnection", "webkitRTCPeerConnection", "WebTransport"]) {
  try {
    Object.defineProperty(globalThis, name, {value: undefined, writable: false, configurable: false});
  } catch (_) {}
}
"""

    def __init__(
        self,
        artifact_root: str | Path,
        authority_store,
        *,
        source_root: str | Path | None = None,
        executable_path: str | None = None,
    ):
        self.artifact_root = Path(artifact_root).resolve()
        self.authority_store = authority_store
        self.source_root = None if source_root is None else Path(source_root).resolve()
        self.executable_path = executable_path

    @staticmethod
    def _remote_allowed(url: str, allowed_hosts: tuple[str, ...]) -> bool:
        parsed = urlparse(url)
        return parsed.scheme in {"http", "https"} and parsed.hostname in set(allowed_hosts)

    @staticmethod
    def _websocket_allowed(url: str, allowed_hosts: tuple[str, ...]) -> bool:
        # Retained as a contract helper for future network-enabled facility work.
        parsed = urlparse(url)
        return parsed.scheme in {"ws", "wss"} and parsed.hostname in set(allowed_hosts)

    @staticmethod
    def _requires_network_lease(scenario: BrowserScenario) -> bool:
        parsed = urlparse(scenario.url)
        return parsed.scheme in {"http", "https"} or bool(scenario.allowed_hosts)

    @staticmethod
    def _local_source_path(url: str) -> Path:
        parsed = urlparse(url)
        if parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}:
            raise FacilityError("browser local source is not a local file URL")
        return Path(url2pathname(parsed.path)).resolve()

    def _local_source_allowed(self, url: str) -> bool:
        if self.source_root is None:
            return False
        try:
            source_path = self._local_source_path(url)
        except FacilityError:
            return False
        return source_path == self.source_root or self.source_root in source_path.parents

    def _request_allowed(self, url: str, allowed_hosts: tuple[str, ...]) -> bool:
        parsed = urlparse(url)
        if parsed.scheme == "file":
            return self._local_source_allowed(url)
        # Current TF-21 implementation intentionally has no remote network authority.
        return False

    def run(self, task: TaskPacket, scenario: BrowserScenario, *, request_id: str, foreman_epoch: int) -> FacilityEvidence:
        if scenario.source_binding != task.source_binding:
            raise FacilityError("browser scenario source binding mismatch")
        parsed = urlparse(scenario.url)
        if scenario.allowed_hosts:
            raise FacilityError("browser network authority is not enabled; lease does not authorize allowed hosts")
        if parsed.scheme != "file":
            raise FacilityError("browser target outside allowed hosts; network authority is not enabled")
        if self.source_root is None:
            raise FacilityError("local browser source requires an explicit source root")
        if not self._local_source_allowed(scenario.url):
            raise FacilityError("browser source file escapes source root")

        validate_live_task(
            task,
            self.authority_store,
            capability=self.capability,
            permission="execute",
            foreman_epoch=foreman_epoch,
            require_lease=False,
            request_binding=browser_request_binding(scenario, request_id),
        )

        from playwright.sync_api import sync_playwright

        self.artifact_root.mkdir(parents=True, exist_ok=True)
        artifacts: list[ArtifactEvidence] = []
        observations: list[str] = []
        console: list[str] = []
        errors: list[str] = []
        request_digest = stable_digest(scenario)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=self.executable_path,
                args=self._browser_launch_args(),
            )
            context = browser.new_context(service_workers="block", offline=True)
            context.add_init_script(script=self._network_disable_script())

            def route_handler(route):
                if self._request_allowed(route.request.url, ()):
                    route.continue_()
                else:
                    route.abort("blockedbyclient")

            def websocket_handler(websocket):
                websocket.close(code=1008, reason="Tenfold browser network authority is disabled")

            context.route("**/*", route_handler)
            context.route_web_socket("**/*", websocket_handler)
            page = context.new_page()
            page.on("console", lambda msg: console.append(msg.text))
            page.on("pageerror", lambda err: errors.append(str(err)))
            source_path = self._local_source_path(scenario.url)
            if not source_path.is_file():
                raise FacilityError("browser source file does not exist")
            page.set_content(source_path.read_text(encoding="utf-8"), wait_until="domcontentloaded")
            for index, step in enumerate(scenario.steps):
                if step.action == "click":
                    page.locator(step.selector).click()
                elif step.action == "fill":
                    page.locator(step.selector).fill(step.value)
                elif step.action == "press":
                    page.locator(step.selector).press(step.value)
                elif step.action == "expect_text":
                    actual = page.locator(step.selector).inner_text()
                    if step.value not in actual:
                        raise FacilityError(f"expected text not observed at step {index}")
                    observations.append(f"expect_text:{step.selector}:{step.value}")
                elif step.action == "screenshot":
                    name = step.name or f"{scenario.scenario_id}-{index}.png"
                    target = self.artifact_root / name
                    page.screenshot(path=str(target), full_page=True)
                    data = target.read_bytes()
                    artifacts.append(ArtifactEvidence(str(target), sha256(data).hexdigest(), len(data), "image/png"))
                else:
                    raise FacilityError(f"unsupported browser action: {step.action}")
            observations.extend(
                (
                    f"final_url={page.url}",
                    f"title={page.title()}",
                    f"console_messages={len(console)}",
                    f"page_errors={len(errors)}",
                    "network_authority=disabled",
                )
            )
            context.close()
            browser.close()
        try:
            playwright_version = importlib.metadata.version("playwright")
        except Exception:
            playwright_version = "unknown"
        ok = not errors
        return FacilityEvidence(
            FacilityKind.BROWSER,
            request_id,
            task.task_id,
            task.assignment_id,
            task.attempt,
            task.source_binding,
            request_digest,
            ok,
            "completed" if ok else "failed",
            tuple(observations),
            tuple(artifacts),
            tuple(errors),
            (("playwright_version", playwright_version), ("network_authority", "disabled")),
        )
