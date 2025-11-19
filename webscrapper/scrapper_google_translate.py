import logging
import random
from playwright.sync_api import sync_playwright, Page, BrowserContext

from scrapper_config import CONFIG
from pw_user_sim import get_random_delay, perform_action, simulate_human


SAFE_CLICK_SELECTORS = [
    "button[aria-label='Listen to source text']",
    "button[aria-label='Listen to translation']",
    "button[aria-label='Copy translation']",
    "button[aria-label='Rate this translation']",
    "button[aria-label='Share translation']",
    "button[aria-label='Settings']",
]

UNSAFE_CLICK_SELECTORS = [
    "button[aria-label='Clear source text']",
    "button[aria-label='Swap languages (Ctrl+Shift+S)']",
    "button[aria-label='More source languages']",
]

INPUT_TEXTAREA_SELECTOR = "textarea[aria-label='Source text']"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)



def get_url (sl, tl):
    return f"https://translate.google.com/?sl={sl}&tl={tl}&op=translate"

# -------------------------------
# Translation Core
# -------------------------------
def translate_sentence(page: Page, sentence: str, batch_idx: int) -> str:
    """Translate one sentence using Google Translate."""

    for attempt in range(CONFIG["retry_attempts"]):
        try:
            perform_action(lambda: page.wait_for_selector(INPUT_TEXTAREA_SELECTOR, timeout=20000), "wait result")
            perform_action(lambda:  page.fill(INPUT_TEXTAREA_SELECTOR, sentence), "type in text to be translated")

           
            # Optional: light scroll to trigger lazy load
            logger.debug(f"Batch {batch_idx} | Simulating human behavior...")
            simulate_human(page)

            result = page.locator("span[jsname='W297wb']").first
            text = result.inner_text().strip()

            if text and text != sentence:
                logger.debug(f"Translated: {sentence[:30]}... → {text[:30]}...")
                if random.random() < 0.2:
                    simulate_human(page, UNSAFE_CLICK_SELECTORS, max_scroll_iterations=5)
                return text
            else:
                if (attempt < CONFIG["retry_attempts"] / 2):
                    raise ValueError("Empty or same-as-input translation")
                
                return text + "- [Empty or same-as-input translation]"

        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed for '{sentence[:40]}...': {e}")
            get_random_delay(CONFIG["retry_delay_range"])
            
            # checks if it's the last attempt
            if attempt == CONFIG["retry_attempts"] - 1:
                return "[TRANSLATION FAILED]"

    return "[TRANSLATION FAILED]"
