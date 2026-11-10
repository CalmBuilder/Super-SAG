"""Capture the original desktop Svelte layout in Chromium with a test bridge.

All files, model responses and native/Tauri operations are synthetic. This is
not a Web backend, a Windows installation test, or a functional acceptance.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = Path(os.environ.get("SAG_VISUAL_EVIDENCE_DIR", ROOT / ".cache/visual-baseline"))

# This bridge is used only by the browser test and the explicitly marked
# development-only visual preview. It cannot access a real desktop or service.
BRIDGE = (ROOT / "tests/visual/fixture.js").read_text()


def unused_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def layout(page) -> dict:
    return page.evaluate("""() => Object.fromEntries(
      ['.sidebar', '.brand-row', '.workspace-switch', '.welcome', '.ask-content'].map(selector => {
        const el = document.querySelector(selector);
        if (!el) throw new Error('Missing layout element '+selector);
        const r = el.getBoundingClientRect(), s = getComputedStyle(el);
        return [selector, {x:r.x,y:r.y,width:r.width,height:r.height,font:s.fontFamily,color:s.color}];
      })
    )""")


def assert_same_layout(expected: dict, actual: dict) -> None:
    for selector, fields in expected.items():
        for key, value in fields.items():
            if isinstance(value, (float, int)):
                assert abs(value - actual[selector][key]) <= 1, (selector, key, value, actual[selector][key])
            else:
                assert value == actual[selector][key], (selector, key, value, actual[selector][key])


def main() -> None:
    vite = ROOT / "node_modules/.bin/vite"
    if not vite.is_file():
        raise SystemExit("Run npm ci before the browser baseline check.")
    reference = (ROOT / "pros/SAG-Wiki").resolve()
    target = EVIDENCE.resolve()
    if target == reference or reference in target.parents:
        raise SystemExit("Evidence must not be written to the static SAG-Wiki reference.")
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    port = unused_port()
    origin = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryFile(mode="w+") as log:
        process = subprocess.Popen(
            [str(vite), "--host", "127.0.0.1", "--port", str(port), "--strictPort"],
            cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise RuntimeError("Vite exited before the baseline check.")
                try:
                    with urlopen(origin, timeout=1) as response:
                        if response.status == 200:
                            break
                except (OSError, URLError):
                    time.sleep(.2)
            else:
                raise RuntimeError("Vite did not start within 30 seconds.")
            errors: list[str] = []
            narrow_observation = None
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
                context = browser.new_context(
                    viewport={"width": 1600, "height": 1067}, locale="zh-CN", reduced_motion="reduce"
                )
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.add_init_script(BRIDGE)
                page.goto(origin, wait_until="networkidle")
                expect(page.get_by_role("heading", name="向你的文件提问")).to_be_visible()
                expect(page.get_by_text("示例知识库", exact=True)).to_be_visible()
                desktop_layout = layout(page)
                page.screenshot(path=str(EVIDENCE / "desktop-ask.png"))
                page.locator(".workspace-switch button").nth(1).click()
                expect(page.get_by_role("heading", name="搜索你的文件")).to_be_visible()
                page.screenshot(path=str(EVIDENCE / "desktop-search.png"))
                page.locator('[aria-label="添加文件夹"]').first.click()
                expect(page.get_by_role("dialog", name="添加文件夹")).to_be_visible()
                expect(page.get_by_text("项目资料", exact=True)).to_be_visible()
                page.screenshot(path=str(EVIDENCE / "desktop-folder-picker.png"))
                page.get_by_role("button", name="索引选项").click()
                expect(page.get_by_text("应用于本次添加的文件夹。已有手写忽略规则会保留。", exact=True)).to_be_visible()
                page.screenshot(path=str(EVIDENCE / "desktop-index-options.png"))
                page.get_by_role("button", name="取消", exact=True).click()
                page.locator(".sidebar-settings").click()
                expect(page.get_by_role("dialog", name="设置")).to_be_visible()
                page.screenshot(path=str(EVIDENCE / "desktop-settings.png"))

                # This route is a test-only preview of the exact same desktop
                # components. It has its own explicit synthetic bridge and a
                # persistent notice; it is not the future Web product.
                preview = context.new_page()
                preview.on("pageerror", lambda error: errors.append(str(error)))
                preview.goto(origin + "/tests/visual/", wait_until="networkidle")
                expect(preview.get_by_text("仅样式预览 · 虚构数据 · 真实业务未接入", exact=True)).to_be_visible()
                expect(preview.get_by_role("heading", name="向你的文件提问")).to_be_visible()
                assert_same_layout(desktop_layout, layout(preview))
                assert preview.evaluate("""async () => {
                  try { await window.__TAURI_INTERNALS__.invoke('save_document', {path:'/demo/x',body:'x'}); return false; }
                  catch { return true; }
                }""")
                preview.screenshot(path=str(EVIDENCE / "web-visual-preview.png"))
                preview.locator(".workspace-switch button").nth(1).click()
                expect(preview.get_by_role("heading", name="搜索你的文件")).to_be_visible()
                preview.locator('[aria-label="添加文件夹"]').first.click()
                expect(preview.get_by_role("dialog", name="添加文件夹")).to_be_visible()
                preview.get_by_role("button", name="索引选项").click()
                expect(preview.get_by_text("应用于本次添加的文件夹。已有手写忽略规则会保留。", exact=True)).to_be_visible()
                preview.get_by_role("button", name="取消", exact=True).click()
                preview.locator(".sidebar-settings").click()
                expect(preview.get_by_role("dialog", name="设置")).to_be_visible()

                # Desktop geometry stays aligned. On narrow screens the browser
                # deliberately differs from the original's fixed 960px width.
                for width, height in ((1280, 850), (320, 720)):
                    original = context.new_page()
                    original.set_viewport_size({"width": width, "height": height})
                    original.on("pageerror", lambda error: errors.append(str(error)))
                    original.add_init_script(BRIDGE)
                    original.goto(origin, wait_until="networkidle")
                    expect(original.get_by_role("heading", name="向你的文件提问")).to_be_visible()
                    narrow = context.new_page()
                    narrow.set_viewport_size({"width": width, "height": height})
                    narrow.on("pageerror", lambda error: errors.append(str(error)))
                    narrow.goto(origin + "/tests/visual/", wait_until="networkidle")
                    expect(narrow.get_by_role("heading", name="向你的文件提问")).to_be_visible()
                    if width == 1280:
                        assert_same_layout(layout(original), layout(narrow))
                    if width == 320:
                        narrow_observation = narrow.evaluate("""() => {
                          const r = document.querySelector('.welcome').getBoundingClientRect();
                          return {viewport:innerWidth, welcome_right:r.right, clipped:r.right>innerWidth,
                            document_width:document.documentElement.scrollWidth};
                        }""")
                        assert not narrow_observation['clipped']
                        assert narrow_observation['document_width'] <= width
                    narrow.screenshot(path=str(EVIDENCE / f"web-preview-{width}.png"))
                    original.close()
                    narrow.close()
                version = browser.version
                context.close()
                browser.close()
            if errors:
                raise AssertionError("Browser page errors: " + "; ".join(errors))
            (EVIDENCE / "result.json").write_text(json.dumps({
                "browser": "Chromium " + version,
                "viewport": "1600x1067",
                "source": "working-tree desktop Svelte; static reference remains untouched",
                "fixture": "synthetic files, settings and mocked Tauri bridge; no backend",
                "checks": ["ask", "search", "folder picker", "index options", "settings", "visual-only preview matches desktop geometry at 1600 and 1280 pixels", "320px preview avoids the desktop fixed-width clipping", "preview rejects a synthetic write"],
                "page_errors": errors,
                "narrow_observation": narrow_observation,
                "limits": ["not a real Windows installation", "not a Web backend or functional acceptance", "this smoke test does not establish complete mobile usability"],
            }, ensure_ascii=False, indent=2) + "\n")
            print("Visual baseline captured in real Chromium:", EVIDENCE)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
