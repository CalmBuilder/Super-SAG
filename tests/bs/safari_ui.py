"""Run the visual-stage cases in actual Safari using Apple's WebDriver.

Must run on macOS with Safari WebDriver enabled. Synthetic fixture data is
isolated to a loopback origin and does not exercise real Web business.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

if sys.platform != 'darwin':
    raise SystemExit('Actual Safari testing requires macOS.')
ROOT = Path(__file__).resolve().parents[2]
output = Path(os.environ.get('SAG_BS_UI_EVIDENCE_DIR', ROOT / '.cache/bs-ui')).resolve()
reference = (ROOT / 'pros').resolve()
if output == reference or reference in output.parents:
    raise SystemExit('Evidence cannot be written inside the reference checkout.')
output.mkdir(parents=True, exist_ok=True)
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
origin = f'http://127.0.0.1:{port}'
cases: list[dict[str, object]] = []


def record(case: str, **details: object) -> None:
    cases.append({'case': case, 'status': 'passed', **details})


with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as log:
    server = subprocess.Popen(
        ['node', str(ROOT / 'node_modules/vite/bin/vite.js'), '--config', 'vite.web.config.ts',
         '--host', '127.0.0.1', '--port', str(port), '--strictPort'],
        cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
    )
    driver = None
    try:
        for _ in range(150):
            if server.poll() is not None:
                raise RuntimeError('Vite exited before Safari testing.')
            try:
                with urlopen(origin + '/tests/bs/index.html', timeout=1) as response:
                    if response.status == 200:
                        break
            except (OSError, URLError):
                time.sleep(.2)
        else:
            raise RuntimeError('The isolated Vite server did not start within 30 seconds.')

        driver = webdriver.Safari()
        wait = WebDriverWait(driver, 20)

        def css(selector: str):
            return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))

        def clickable(selector: str):
            def ready(current):
                try:
                    element = current.find_element(By.CSS_SELECTOR, selector)
                    if not element.is_displayed() or not element.is_enabled():
                        return False
                    reachable = current.execute_script('''const e=arguments[0], r=e.getBoundingClientRect();
                      const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
                      return !e.closest('[inert]') && !!hit && (e===hit || e.contains(hit));''', element)
                    return element if reachable else False
                except StaleElementReferenceException:
                    return False
            return wait.until(ready)

        def visit(scenario: str = 'normal', lang: str = 'zh-CN', theme: str = 'light') -> None:
            driver.get(f'{origin}/tests/bs/index.html?scenario={scenario}&lang={lang}&theme={theme}')
            css('.browser-client')

        def nav(label: str) -> None:
            button = wait.until(EC.element_to_be_clickable((By.XPATH, f"//nav[contains(@class,'workspace-switch')]//button[.//span[normalize-space()='{label}']]")))
            button.click()

        def no_errors() -> None:
            assert driver.execute_script('return window.__BS_TEST__.pageErrors') == []

        driver.set_window_rect(width=1280, height=800)
        visit()
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.welcome h1'), '向你的文件提问'))
        assert css('.brand').text == 'Super-SAG'
        assert driver.execute_script("return typeof window.__TAURI_INTERNALS__") == 'undefined'
        nav('搜索')
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.search-page h1'), '搜索你的文件'))
        nav('文件')
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.content'), '已索引文件'))
        nav('问答')
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.welcome h1'), '向你的文件提问'))
        driver.save_screenshot(str(output / 'safari-workspace.png'))
        no_errors()
        record('desktop-sized navigation and shared workspace', width=1280)

        initial_width = css('.sidebar').rect['width']
        clickable('[aria-label="收起侧边栏"]').click()
        wait.until(lambda current: 'compact-sidebar' in current.find_element(By.CSS_SELECTOR, '.real-client').get_attribute('class').split())
        wait.until(lambda current: current.find_element(By.CSS_SELECTOR, '.sidebar').rect['width'] < initial_width - 30)
        assert css('.sidebar').rect['width'] < initial_width
        clickable('[aria-label="展开侧边栏"]').click()
        wait.until(lambda current: 'compact-sidebar' not in current.find_element(By.CSS_SELECTOR, '.real-client').get_attribute('class').split())
        wait.until(lambda current: abs(current.find_element(By.CSS_SELECTOR, '.sidebar').rect['width'] - initial_width) <= 1)
        assert abs(css('.sidebar').rect['width'] - initial_width) <= 1
        no_errors()
        record('desktop-sized sidebar collapse and expand')

        ActionChains(driver).key_down(Keys.COMMAND).send_keys('k').key_up(Keys.COMMAND).perform()
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.search-page h1'), '搜索你的文件'))
        nav('问答')
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.welcome h1'), '向你的文件提问'))
        no_errors()
        record('page keyboard shortcut opens search')

        css('[aria-label="设置"]').click()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[role="dialog"]')))
        css('[aria-label="关闭设置"]').click()
        wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, '[role="dialog"]')))
        clickable('[aria-label="切换明暗主题"]').click()
        wait.until(lambda current: current.execute_script('return document.documentElement.dataset.theme') == 'dark')
        no_errors()
        record('settings open/close and theme change')

        visit(scenario='theme-error')
        clickable('[aria-label="切换明暗主题"]').click()
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '#notice'), '测试保存主题失败'))
        assert driver.execute_script('return document.documentElement.dataset.theme') == 'light'
        no_errors()
        record('theme save failure retains prior theme')

        visit(lang='en', theme='dark')
        wait.until(lambda current: current.execute_script('return document.documentElement.lang') == 'en')
        assert driver.execute_script('return document.documentElement.dataset.theme') == 'dark'
        assert css('.workspace-switch').text.find('Search') >= 0
        no_errors()
        record('English and dark theme')

        visit(scenario='empty')
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '.folder-empty-state')))
        assert len(driver.find_elements(By.CSS_SELECTOR, '.tree-row')) == 0
        no_errors()
        record('empty library')

        visit(scenario='many')
        wait.until(lambda current: len(current.find_elements(By.CSS_SELECTOR, '.tree-row')) == 120)
        assert driver.execute_script('const e=document.querySelector(".tree");return e.scrollHeight>e.clientHeight')
        no_errors()
        record('120 long folder names with scrolling')

        visit(scenario='tree')
        css('[aria-label="展开示例知识库"]').click()
        css('[aria-label="展开一级"]').click()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[aria-label="展开二级"]')))
        css('[aria-label="折叠一级"]').click()
        css('[aria-label="折叠示例知识库"]').click()
        wait.until(lambda current: len(current.find_elements(By.CSS_SELECTOR, '.tree-row')) == 1)
        no_errors()
        record('nested folder expansion and collapse')

        visit(scenario='tree-error')
        css('[aria-label="展开示例知识库"]').click()
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '#notice'), '测试读取目录失败'))
        assert css('[aria-label="展开示例知识库"]').get_attribute('aria-expanded') == 'false'
        no_errors()
        record('folder expansion failure preserves collapsed state')

        driver.get(origin + '/web/index.html')
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.startup-error'), 'Web 服务尚未接通'))
        driver.execute_script('''
          localStorage.setItem('super-sag.web.v1.sag.sidebar.expanded', '{bad');
          localStorage.setItem('super-sag.web.v1.sag.search.history', '{}');
        ''')
        visit(scenario='tree')
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.welcome h1'), '向你的文件提问'))
        assert driver.execute_script("return localStorage.getItem('super-sag.web.v1.sag.sidebar.expanded')") == '{bad'
        assert driver.execute_script("return localStorage.getItem('super-sag.web.v1.sag.search.history')") == '{}'
        nav('搜索')
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.search-page h1'), '搜索你的文件'))
        assert not driver.find_elements(By.CSS_SELECTOR, '.search-history')
        no_errors()
        record('malformed browser preferences do not block startup and remain unchanged')
        driver.execute_script('''
          localStorage.removeItem('super-sag.web.v1.sag.sidebar.expanded');
          localStorage.removeItem('super-sag.web.v1.sag.search.history');
        ''')

        driver.get(origin + '/web/index.html')
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.startup-error'), 'Web 服务尚未接通'))
        driver.execute_script('''
          localStorage.setItem('sag.sidebar.expanded', '{old invalid value');
          localStorage.setItem('sag.search.history', '["old"]');
          localStorage.setItem('sag.onboarding.seen', 'legacy');
          localStorage.setItem('unrelated', 'keep');
          localStorage.setItem('super-sag.web.v1.other', 'keep');
        ''')
        visit(scenario='tree')
        css('[aria-label="展开示例知识库"]').click()
        wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[aria-label="展开一级"]')))
        assert driver.execute_script("return localStorage.getItem('sag.sidebar.expanded')") == '{old invalid value'
        assert driver.execute_script("return localStorage.getItem('super-sag.web.v1.sag.sidebar.expanded')") is not None
        css('[aria-label="设置"]').click()
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='数据与隐私']"))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='清除所有数据']"))).click()
        css('[aria-label="确认清除所有数据"]').click()
        wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, '[role="dialog"]')))
        assert driver.execute_script("return localStorage.getItem('sag.sidebar.expanded')") == '{old invalid value'
        assert driver.execute_script("return localStorage.getItem('sag.search.history')") == '["old"]'
        assert driver.execute_script("return localStorage.getItem('sag.onboarding.seen')") == 'legacy'
        assert driver.execute_script("return localStorage.getItem('unrelated')") == 'keep'
        assert driver.execute_script("return localStorage.getItem('super-sag.web.v1.other')") == 'keep'
        assert driver.execute_script("return localStorage.getItem('super-sag.web.v1.sag.sidebar.expanded')") is None
        no_errors()
        record('old same-origin storage is ignored and preserved after simulated clear')

        for width in (320, 375, 768, 959, 960):
            driver.set_window_rect(width=width, height=800)
            visit()
            actual = driver.execute_script('return window.innerWidth')
            if actual != width:
                raise AssertionError(f'Safari requested viewport {width}, actual viewport {actual}; no boundary claim is possible')
            if width <= 959:
                toggle = css('[aria-label="展开侧边栏"].browser-sidebar-toggle')
                toggle.click()
                wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '.sidebar')))
                assert driver.execute_script('return document.querySelector("main.workspace").inert') is True
                wait.until(lambda current: current.execute_script('return document.activeElement === document.querySelector(\'.sidebar-titlebar [aria-label="收起侧边栏"]\')'))
                css('.sidebar-titlebar [aria-label="收起侧边栏"]').click()
                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, '.sidebar')))
                wait.until(lambda current: current.execute_script('return document.activeElement === arguments[0]', toggle))
                toggle.click()
                css('.sidebar [aria-label="设置"]').click()
                wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, '[role="dialog"]')))
                css('[aria-label="关闭设置"]').click()
                wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, '[role="dialog"]')))
                wait.until(lambda current: current.execute_script('return document.activeElement === arguments[0]', toggle))
            else:
                assert not driver.find_elements(By.CSS_SELECTOR, '.browser-sidebar-toggle')
                assert css('.sidebar').is_displayed()
            no_errors()
            record('responsive sidebar boundary', width=width)

        driver.set_window_rect(width=960, height=800)
        visit()
        driver.set_window_rect(width=959, height=800)
        assert driver.execute_script('return window.innerWidth') == 959
        css('[aria-label="展开侧边栏"].browser-sidebar-toggle').click()
        wait.until(lambda current: current.execute_script('return document.querySelector("main.workspace").inert') is True)
        driver.set_window_rect(width=960, height=800)
        assert driver.execute_script('return window.innerWidth') == 960
        wait.until(lambda current: not current.find_elements(By.CSS_SELECTOR, '.browser-sidebar-toggle'))
        assert css('.sidebar').is_displayed()
        assert driver.execute_script('return document.querySelector("main.workspace").inert') is False
        driver.set_window_rect(width=959, height=800)
        assert driver.execute_script('return window.innerWidth') == 959
        wait.until(lambda current: css('[aria-label="展开侧边栏"].browser-sidebar-toggle').get_attribute('aria-expanded') == 'false')
        wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, '.sidebar')))
        no_errors()
        record('resize across sidebar boundary while open')

        for width in (320, 375):
            driver.set_window_rect(width=width, height=800)
            visit()
            css('[aria-label="展开侧边栏"].browser-sidebar-toggle').click()
            row = css('.tree-row')
            ActionChains(driver).move_to_element(row).perform()
            css('[aria-label="示例知识库 的文件夹选项"]').click()
            item = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[@role='menuitem' and normalize-space()='搜索']")))
            assert driver.execute_script('const e=arguments[0],r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))', item)
            item.click()
            wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.search-page h1'), '搜索你的文件'))
            wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, '.sidebar')))
            assert driver.execute_script('return document.querySelector("main.workspace").inert') is False
            no_errors()
            record('folder menu can navigate without blocking workspace', width=width)

        driver.set_window_rect(width=1280, height=800)
        visit(scenario='offline')
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.startup-error'), '测试服务不可用'))
        css('.startup-error button').click()
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.startup-error'), '测试服务不可用'))
        no_errors()
        record('startup failure and retry')

        driver.get(origin + '/web/index.html')
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.startup-error'), 'Web 服务尚未接通'))
        assert driver.execute_script('return typeof window.__BS_TEST__') == 'undefined'
        assert driver.execute_script('return typeof window.__TAURI_INTERNALS__') == 'undefined'
        assert driver.execute_script("return localStorage.getItem('sag.sidebar.expanded')") == '{old invalid value'
        record('product entry rejects unavailable business without a fixture')

        source_names = ['src/App.svelte', 'src/lib/platform.ts', 'src/lib/storage.ts', 'src/lib/remember-scroll.ts',
                        'src/bs/platform.ts', 'src/bs/sidebar.ts', 'src/bs/workspace.css', 'src/bs/mount.ts',
                        'tests/bs/fixture.ts', 'tests/bs/safari_ui.py']
        report = {
            'scope': 'actual Safari with isolated synthetic fixture; not Windows desktop or real Web business acceptance',
            'browser': driver.capabilities.get('browserName'),
            'browser_version': driver.capabilities.get('browserVersion'),
            'platform': driver.capabilities.get('platformName'),
            'windows_source_baseline': '9459f4b90617a2042d20848eea6560e0d6812ebe',
            'cases': cases,
            'source_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in source_names},
        }
        (output / 'safari-result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'browser': report['browser'], 'version': report['browser_version'], 'cases': len(cases)}, ensure_ascii=False))
    finally:
        failed = sys.exc_info()[0] is not None
        if driver is not None:
            if failed:
                driver.save_screenshot(str(output / 'safari-failure.png'))
            driver.quit()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait(timeout=10)
        if failed:
            log.seek(0)
            print(f'Vite output:\n{log.read()}', file=sys.stderr)
