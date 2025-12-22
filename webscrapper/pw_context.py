import random
from typing import Tuple
from playwright.sync_api import Playwright, Browser, BrowserContext
from constants.output import LOG_FILENAME, OUTPUT_FOLDER
from pw_proxies import get_proxy
from pw_user_agents import USER_AGENTS
from logger import translation_logger

logger = translation_logger.get_logger(
    output_folder=OUTPUT_FOLDER,
    log_filename=LOG_FILENAME
)

def get_new_context(playwright: Playwright, headless: bool = False, useProxy: bool = False, msg_prefix: str = '') -> Tuple[Browser, BrowserContext]:
    browser = playwright.chromium.launch(headless=headless)  # Set to True for headless mode
      
    proxy = get_proxy() if useProxy else None
    logger.info(f"{msg_prefix} Proxy: {proxy['server'] if proxy else 'None'}")
    return browser, browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "DNT": "1",  # Do Not Track
            "Upgrade-Insecure-Requests": "1",
            
        },
        proxy=proxy,
        locale="en-US",
        java_script_enabled=True,
        viewport={
            'width': random.randint(1366, 1920),
            'height': random.randint(768, 1080)
        },
    )
    