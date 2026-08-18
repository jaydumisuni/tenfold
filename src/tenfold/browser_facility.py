from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import importlib.metadata
from pathlib import Path
from urllib.parse import urlparse

from .contracts import TaskPacket
from .facility import ArtifactEvidence, FacilityError, FacilityEvidence, FacilityKind, stable_digest, validate_task


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


class PlaywrightFacility:
    capability = "browser.playwright"

    def __init__(self, artifact_root: str | Path, *, source_root: str | Path | None = None, executable_path: str | None = None):
        self.artifact_root = Path(artifact_root).resolve()
        self.source_root = None if source_root is None else Path(source_root).resolve()
        self.executable_path = executable_path

    @staticmethod
    def _allowed(url: str, allowed_hosts: tuple[str, ...]) -> bool:
        parsed = urlparse(url)
        if parsed.scheme == "file":
            return True
        return parsed.scheme in {"http", "https"} and parsed.hostname in set(allowed_hosts)

    def run(self, task: TaskPacket, scenario: BrowserScenario, *, request_id: str, foreman_epoch: int) -> FacilityEvidence:
        validate_task(task, capability=self.capability, permission="execute", foreman_epoch=foreman_epoch)
        if scenario.source_binding != task.source_binding:
            raise FacilityError("browser scenario source binding mismatch")
        if not self._allowed(scenario.url, scenario.allowed_hosts):
            raise FacilityError("browser target outside allowed hosts")
        from playwright.sync_api import sync_playwright
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        artifacts: list[ArtifactEvidence] = []
        observations: list[str] = []
        console: list[str] = []
        errors: list[str] = []
        request_digest = stable_digest(scenario)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, executable_path=self.executable_path)
            page = browser.new_page()
            page.on("console", lambda msg: console.append(msg.text))
            page.on("pageerror", lambda err: errors.append(str(err)))

            def route_handler(route):
                if self._allowed(route.request.url, scenario.allowed_hosts):
                    route.continue_()
                else:
                    route.abort("blockedbyclient")
            page.route("**/*", route_handler)
            parsed = urlparse(scenario.url)
            if parsed.scheme == "file":
                source_path = Path(parsed.path).resolve()
                if self.source_root is None:
                    raise FacilityError("local browser source requires an explicit source root")
                if self.source_root not in source_path.parents and source_path != self.source_root:
                    raise FacilityError("browser source file escapes source root")
                if not source_path.is_file():
                    raise FacilityError("browser source file does not exist")
                page.set_content(source_path.read_text(encoding="utf-8"), wait_until="domcontentloaded")
            else:
                page.goto(scenario.url, wait_until="domcontentloaded")
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
            observations.extend((f"final_url={page.url}", f"title={page.title()}", f"console_messages={len(console)}", f"page_errors={len(errors)}"))
            browser.close()
        try:
            pw_version = importlib.metadata.version("playwright")
        except Exception:
            pw_version = "unknown"
        ok = not errors
        return FacilityEvidence(FacilityKind.BROWSER, request_id, task.task_id, task.assignment_id, task.attempt, task.source_binding, request_digest, ok, "completed" if ok else "failed", tuple(observations), tuple(artifacts), tuple(errors), (("playwright_version", pw_version),))
