"""Shared geometry probe for installed desktop and browser screenshots."""


def workspace_layout(page):
    return page.evaluate('''() => Object.fromEntries(
      ['.sidebar', '.workspace', '.workspace-switch'].map(selector => {
        const rect = document.querySelector(selector).getBoundingClientRect();
        return [selector, {x: rect.x, y: rect.y, width: rect.width, height: rect.height}];
      }))''')
