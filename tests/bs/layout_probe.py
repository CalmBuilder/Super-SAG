"""Shared geometry probe for installed desktop and browser screenshots."""

import re

from playwright.sync_api import expect


def workspace_layout(page):
    return page.evaluate('''() => Object.fromEntries(
      ['.sidebar', '.workspace', '.workspace-switch'].map(selector => {
        const rect = document.querySelector(selector).getBoundingClientRect();
        return [selector, {x: rect.x, y: rect.y, width: rect.width, height: rect.height}];
      }))''')


def compare_layout(view, desktop, browser, tolerance=2):
    for selector, coordinates in desktop.items():
        for key, value in coordinates.items():
            actual = browser[selector][key]
            if abs(actual - value) > tolerance:
                raise AssertionError(f'{view} {selector} {key}: desktop={value}, browser={actual}')


def exercise_sidebar_collapse(page, output=None, prefix=''):
    initial_width = page.locator('.sidebar').bounding_box()['width']
    page.get_by_role('button', name='收起侧边栏', exact=True).click()
    expect(page.locator('.real-client')).to_have_class(re.compile(r'\bcompact-sidebar\b'))
    page.wait_for_function('''initial => {
      const shell = document.querySelector('.shell');
      const width = document.querySelector('.sidebar').getBoundingClientRect().width;
      return width < initial - 30 && !shell.getAnimations().some(a => a.playState === 'running');
    }''', arg=initial_width)
    compact_width = page.locator('.sidebar').bounding_box()['width']
    assert compact_width < initial_width, (initial_width, compact_width)
    collapsed_layout = workspace_layout(page)
    if output is not None:
        page.evaluate('document.activeElement.blur()')
        page.screenshot(path=str(output / f'{prefix}-ask-collapsed.png'), animations='disabled')
    page.get_by_role('button', name='展开侧边栏', exact=True).click()
    expect(page.locator('.real-client')).not_to_have_class(re.compile(r'\bcompact-sidebar\b'))
    page.wait_for_function("initial => Math.abs(document.querySelector('.sidebar').getBoundingClientRect().width - initial) <= 1", arg=initial_width)
    restored_width = page.locator('.sidebar').bounding_box()['width']
    assert abs(restored_width - initial_width) <= 1, (initial_width, restored_width)
    return collapsed_layout


def preference_layouts(page, output, prefix):
    """Exercise the same UI controls before comparing dark and English views."""
    page.get_by_role('button', name='问答', exact=True).click()
    expect(page.locator('.welcome h1')).to_have_text('向你的文件提问')
    page.get_by_role('button', name='切换明暗主题').click()
    expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
    expect(page.locator('#notice')).to_contain_text('设置已保存')
    page.get_by_role('button', name='关闭提示').click()
    expect(page.locator('#notice')).to_have_count(0)
    page.evaluate('document.activeElement.blur()')
    layouts = {'ask_dark': workspace_layout(page)}
    page.screenshot(path=str(output / f'{prefix}-ask-dark.png'), animations='disabled')

    page.get_by_role('button', name='设置', exact=True).click()
    page.get_by_role('button', name='界面语言').click()
    page.get_by_role('option', name='English', exact=True).click()
    expect(page.locator('html')).to_have_attribute('lang', 'en')
    page.get_by_role('button', name='Save settings', exact=True).click()
    expect(page.get_by_role('dialog')).to_have_count(0)
    expect(page.locator('.welcome h1')).to_have_text('Ask your files')
    expect(page.locator('#notice')).to_contain_text('Settings saved')
    page.get_by_role('button', name='Dismiss notification').click()
    expect(page.locator('#notice')).to_have_count(0)
    page.evaluate('document.activeElement.blur()')
    layouts['ask_en_dark'] = workspace_layout(page)
    page.screenshot(path=str(output / f'{prefix}-ask-en-dark.png'), animations='disabled')
    return layouts
