"""
Stealth Playwright Browser Manager.
Configures browser context with anti-bot detection evasion while preserving
native OS/Platform consistency across Windows, Linux, and macOS.
"""

import sys
from typing import Tuple, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

async def launch_stealth_browser(headless: bool = False) -> Tuple[Browser, BrowserContext, Page]:
    """
    Launch a browser configured with anti-detection properties across Windows, Linux, and macOS.
    - Preserves native OS User-Agent and navigator.platform (Win32 on Windows, MacIntel on macOS,
      Linux x86_64 on Linux) so Lever hCaptcha, Greenhouse reCAPTCHA, and Cloudflare pass cleanly.
    - Avoids bot-flagged flags (--no-sandbox, --disable-infobars).
    - Uses isolated browser instances per invocation so multiple application windows can stay
      open simultaneously without profile lock ('ProcessSingleton') errors on Windows/macOS/Linux.
    """
    p = await async_playwright().start()

    args = [
        "--disable-blink-features=AutomationControlled",
    ]
    # On Windows and Linux, --start-maximized maximizes the window cleanly
    if sys.platform in ("win32", "linux"):
        args.insert(0, "--start-maximized")

    browser: Optional[Browser] = None

    # Prefer system Chrome (or Edge on Windows) for authentic TLS/fingerprint score,
    # falling back seamlessly to Playwright's bundled Chromium.
    channels_to_try = ["chrome", "msedge", None] if sys.platform == "win32" else ["chrome", None]
    for channel in channels_to_try:
        try:
            launch_kwargs = {"headless": headless, "args": args}
            if channel:
                launch_kwargs["channel"] = channel
            browser = await p.chromium.launch(**launch_kwargs)
            break
        except Exception:
            continue

    if browser is None:
        browser = await p.chromium.launch(headless=headless, args=args)

    # On macOS, no_viewport=True can sometimes open a small default window if not maximized;
    # setting a generous viewport on macOS while using no_viewport=True on Windows/Linux works best.
    if sys.platform == "darwin" and not headless:
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
    else:
        context = await browser.new_context(no_viewport=True)

    # Mask navigator.webdriver without spoofing OS platform
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    page = await context.new_page()
    return browser, context, page
