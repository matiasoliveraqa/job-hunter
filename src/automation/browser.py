"""
Stealth Playwright Browser Manager.
Configures browser context with anti-bot detection evasion while preserving
native OS/Platform consistency so hCaptcha and Cloudflare Turnstile pass cleanly.
"""

from pathlib import Path
from typing import Tuple, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from src.core.config import PROJECT_ROOT

PROFILE_DATA_DIR = PROJECT_ROOT / ".playwright_profile"

async def launch_stealth_browser(headless: bool = False) -> Tuple[Optional[Browser], BrowserContext, Page]:
    """
    Launch a browser configured with anti-detection properties.
    Important: Does NOT override User-Agent with a mismatched OS string (e.g. Linux UA on Windows),
    and avoids bot-flagged switches like --no-sandbox or --disable-infobars so ATS captchas
    (Lever hCaptcha, Greenhouse reCAPTCHA, Cloudflare) validate cleanly.
    """
    p = await async_playwright().start()

    args = [
        "--start-maximized",
        "--disable-blink-features=AutomationControlled",
    ]

    PROFILE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    context: Optional[BrowserContext] = None
    browser: Optional[Browser] = None

    # Prefer persistent context with installed Chrome if available (best captcha trust score),
    # falling back to bundled Playwright Chromium persistent context.
    for channel in ("chrome", None):
        try:
            launch_kwargs = {
                "user_data_dir": str(PROFILE_DATA_DIR),
                "headless": headless,
                "args": args,
                "no_viewport": True,
            }
            if channel:
                launch_kwargs["channel"] = channel
            context = await p.chromium.launch_persistent_context(**launch_kwargs)
            break
        except Exception:
            continue

    if context is None:
        browser = await p.chromium.launch(headless=headless, args=args)
        context = await browser.new_context(no_viewport=True)

    # Mask navigator.webdriver without spoofing OS platform
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)

    page = context.pages[0] if context.pages else await context.new_page()
    return browser, context, page
