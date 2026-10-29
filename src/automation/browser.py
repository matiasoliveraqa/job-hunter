"""
Stealth Playwright Browser Manager.
Configures browser context with anti-bot detection evasion while preserving
native OS/Platform consistency across Windows, Linux, and macOS.
"""

import sys
from typing import Tuple, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from pathlib import Path
from src.core.config import OUTPUT_DIR

USER_DATA_DIR = OUTPUT_DIR / "browser_profile"

class _PersistentBrowserWrapper:
    def __init__(self, context: BrowserContext):
        self._context = context

    async def close(self):
        await self._context.close()

async def launch_stealth_browser(headless: bool = False) -> Tuple[Optional[Browser], BrowserContext, Page]:
    """
    Launch a browser configured with anti-detection properties across Windows, Linux, and macOS.
    - Preserves native OS User-Agent and navigator.platform.
    - Avoids bot-flagged flags (--no-sandbox, --disable-infobars).
    - Uses persistent browser context in output/browser_profile to maintain trust score and cookies.
    - Falls back to isolated browser if profile lock occurs.
    """
    p = await async_playwright().start()

    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if sys.platform in ("win32", "linux"):
        args.insert(0, "--start-maximized")

    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    stealth_script = """
        try {
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true
            });
        } catch (e) {}

        if (!window.chrome) {
            window.chrome = {
                app: {
                    isInstalled: false,
                    InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
                    RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }
                },
                csi: function() {},
                loadTimes: function() {}
            };
        }

        if (!navigator.plugins || navigator.plugins.length === 0) {
            const makePlugin = (name, filename, description) => ({ name, filename, description, length: 0 });
            const plugins = [
                makePlugin('PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
                makePlugin('Chrome PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
                makePlugin('Chromium PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
                makePlugin('Microsoft Edge PDF Viewer', 'internal-pdf-viewer', 'Portable Document Format'),
                makePlugin('WebKit built-in PDF', 'internal-pdf-viewer', 'Portable Document Format')
            ];
            plugins.item = (i) => plugins[i] || null;
            plugins.namedItem = (name) => plugins.find(p => p.name === name) || null;
            plugins.refresh = () => {};
            Object.defineProperty(navigator, 'plugins', {
                get: () => plugins,
                configurable: true,
                enumerable: true
            });
        }

        if (window.navigator.permissions) {
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters && parameters.name === 'notifications'
                    ? Promise.resolve({ state: Notification.permission })
                    : originalQuery(parameters)
            );
        }
    """

    channels_to_try = ["chrome", "msedge", None] if sys.platform == "win32" else ["chrome", None]
    ignore_default_args = ["--enable-automation"]

    context: Optional[BrowserContext] = None
    browser: Optional[Browser] = None

    # Try persistent context first for authentic cookies and token persistence
    for channel in channels_to_try:
        try:
            kwargs = {
                "user_data_dir": USER_DATA_DIR,
                "headless": headless,
                "args": args,
                "ignore_default_args": ignore_default_args,
            }
            if channel:
                kwargs["channel"] = channel
            if sys.platform == "darwin" and not headless:
                kwargs["viewport"] = {"width": 1440, "height": 900}
            else:
                kwargs["no_viewport"] = True

            context = await p.chromium.launch_persistent_context(**kwargs)
            browser = _PersistentBrowserWrapper(context)
            break
        except Exception:
            continue

    # Fallback to standard launch if persistent context is locked by another window
    if context is None:
        for channel in channels_to_try:
            try:
                launch_kwargs = {
                    "headless": headless,
                    "args": args,
                    "ignore_default_args": ignore_default_args,
                }
                if channel:
                    launch_kwargs["channel"] = channel
                browser = await p.chromium.launch(**launch_kwargs)
                break
            except Exception:
                continue

        if browser is None:
            browser = await p.chromium.launch(
                headless=headless,
                args=args,
                ignore_default_args=ignore_default_args,
            )

        if sys.platform == "darwin" and not headless:
            context = await browser.new_context(viewport={"width": 1440, "height": 900})
        else:
            context = await browser.new_context(no_viewport=True)

    await context.add_init_script(stealth_script)

    page = context.pages[0] if context.pages else await context.new_page()
    try:
        await page.evaluate(stealth_script)
    except Exception:
        pass
    return browser, context, page

