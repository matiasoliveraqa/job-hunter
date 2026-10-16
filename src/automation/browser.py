"""
Stealth Playwright Browser Manager.
Configures browser context with anti-bot detection evasion flags.
"""

from typing import Tuple, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

async def launch_stealth_browser(headless: bool = False) -> Tuple[Browser, BrowserContext, Page]:
    """Launch a Chromium browser configured with anti-detection properties."""
    p = await async_playwright().start()
    
    args = [
        "--start-maximized",
        "--no-sandbox",
        "--disable-blink-features=AutomationControlled",
        "--disable-infobars",
    ]
    
    browser = await p.chromium.launch(
        headless=headless,
        args=args
    )
    
    context = await browser.new_context(
        no_viewport=True,
        user_agent=DEFAULT_USER_AGENT
    )
    
    # Mask navigator.webdriver
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    page = await context.new_page()
    return browser, context, page
