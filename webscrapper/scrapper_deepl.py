import logging
import random
from playwright.sync_api import sync_playwright, Page, BrowserContext

from scrapper_config import CONFIG
from pw_user_sim import simulate_human
from utils.pw_helper import get_random_delay, perform_action
# -------------------------------
# DeepL-specific Selectors (updated Nov 2025)
# -------------------------------
SAFE_CLICK_SELECTORS = [
    # Listen buttons
    "button[dl-test='translator-source-speech-button']",
    "button[dl-test='translator-target-speech-button']",
    # Copy button
    "button[dl-test='translator-target-copy-button']",
    # Fullscreen, keyboard shortcuts, etc.
    "button[dl-test='translator-fullscreen-button']",
    "button[dl-test='translator-keyboard-shortcuts-button']",
]

UNSAFE_CLICK_SELECTORS = [
    # These change content or clear input → avoid unless intentional
    "button[dl-test='translator-source-clear-button']",
    "button[dl-test='translator-lang-select-source']",   # language dropdown
    "button[dl-test='translator-lang-select-target']",
    "button[dl-test='translator-swap-button']",
]

INPUT_SELECTOR = "div[aria-labelledby='translation-source-heading'][contenteditable='true']"
OUTPUT_SELECTOR = "div[aria-labelledby='translation-target-heading'][contenteditable='true']"
RESULT_TOOLBAR_SELECTOR = "div[dl-test='translator-target-toolbar']"  # appears when translation is ready

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def get_url(sl: str, tl: str) -> str:
    """
    DeepL URL format: https://www.deepl.com/translator#source_lang/target_lang/text
    Note: We encode the text later in the script to avoid URL length issues.
    """
    return f"https://www.deepl.com/en/translator"


# -------------------------------
# Translation Core
# -------------------------------
def translate_sentence(page: Page, sentence: str, batch_idx: int) -> str:
    """
    Translate one sentence using DeepL.
    """
    # Clean and trim input
    sentence = sentence.strip()
    if not sentence:
        return ""

    # Navigate to DeepL with correct languages (only once per batch ideally)
    # page.goto(get_url(sl, tl), wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")

    for attempt in range(CONFIG["retry_attempts"]):
        try:
            # Clear previous input if needed (only on retries or if field is not empty)
            if attempt > 0 or page.locator(INPUT_SELECTOR).input_value():
                perform_action(
                    lambda: page.click("button[dl-test='translator-source-clear-button']", timeout=5000),
                    "clear previous input",
                    optional=True
                )

            # Type the sentence naturally
            perform_action(
                lambda: page.fill(INPUT_SELECTOR, ""),
                "clear textarea"
            )
            perform_action(
                lambda: page.type(INPUT_SELECTOR, sentence, delay=random.randint(50, 150)),
                f"type sentence (attempt {attempt+1})"
            )

            logger.debug(f"Batch {batch_idx} | Waiting for translation of: {sentence[:40]}...")

            # Wait for result toolbar (most reliable indicator that translation is done)
            page.wait_for_selector(RESULT_TOOLBAR_SELECTOR, timeout=15000)

            # Additional small delay to ensure final text is rendered
            get_random_delay((0.8, 2.0))

            # Extract all result spans and join (DeepL splits into multiple <span>)
            result_elements = page.locator(OUTPUT_SELECTOR).all()
            translated_text = "".join(el.inner_text() for el in result_elements).strip()

            # Post-translation human simulation
            simulate_human(page, extra_safe_selectors=SAFE_CLICK_SELECTORS)

            if translated_text and translated_text.lower() != sentence.lower():
                logger.debug(f"Translated: {sentence[:30]}... → {translated_text[:30]}...")
                
                # Occasionally interact lightly (20% chance)
                if random.random() < 0.2:
                    simulate_human(page, UNSAFE_CLICK_SELECTORS)

                return translated_text

            else:
                raise ValueError("Empty or identical translation")

        except Exception as e:
            logger.warning(f"Attempt {attempt+1}/{CONFIG['retry_attempts']} failed: {e}")
            get_random_delay(CONFIG["retry_delay_range"])

            if attempt == CONFIG["retry_attempts"] - 1:
                return "[TRANSLATION FAILED] " + sentence

            # Optional: reload page on severe failure
            if "timeout" in str(e).lower() or "detached" in str(e).lower():
                logger.info("Page issue detected, reloading...")
                page.reload(wait_until="domcontentloaded")
                page.wait_for_load_state("networkidle")

    return "[TRANSLATION FAILED] " + sentence
