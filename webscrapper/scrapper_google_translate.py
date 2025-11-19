import datetime
import logging
import random
from playwright.sync_api import sync_playwright, Page, BrowserContext
from urllib.parse import urlparse, parse_qs

from constants.output import OUTPUT_FOLDER
from scrapper_config import CONFIG
from pw_user_sim import _click_element, get_random_delay, perform_action, simulate_human


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

]

# they're unsafe and given the currently logic they must be clicked twice
DOUBLE_CLICK_SELECTORS = [
    "button[aria-label='Swap languages (Ctrl+Shift+S)']",
    "button[aria-label='More source languages']",
    "button[aria-label='More target languages']",
]

INPUT_TEXTAREA_SELECTOR = "textarea[aria-label='Source text']"


def get_url (sl, tl):
    return f"https://translate.google.com/?sl={sl}&tl={tl}&op=translate"

# -------------------------------
# Translation Core
# -------------------------------
def translate_sentence(page: Page, sentence: str, batch_idx: int, logger: logging.Logger) -> str:
    """Translate one sentence using Google Translate."""

    perform_action(lambda: page.wait_for_selector(INPUT_TEXTAREA_SELECTOR, timeout=20000), "wait result")
    perform_action(lambda:  page.fill(INPUT_TEXTAREA_SELECTOR, sentence), "type in text to be translated")
    initial_query_params = parse_qs(urlparse(page.url).query)
    
    # Optional: light scroll to trigger lazy load
    logger.debug(f"Batch {batch_idx} | Simulating human behavior...")
    simulate_human(page)
    
    result = page.locator("span[jsname='W297wb']").first
    text = result.inner_text().strip()

    if text and text != sentence:
        logger.debug(f"Translated: {sentence[:30]}... → {text[:30]}...")
        if random.random() < 0.2:
            simulate_human(page, DOUBLE_CLICK_SELECTORS, number_of_clicks=2, button_click_probability=1)
            simulate_human(page, UNSAFE_CLICK_SELECTORS)
            
        final_query_params = parse_qs(urlparse(page.url).query)
        while initial_query_params["sl"] != final_query_params['sl']:
            logger.warning(f"Batch {batch_idx} | URL sl value changed during translation: {initial_query_params['sl']} → {final_query_params['sl']}")
            final_query_params = _reset_languages(page, initial_query_params["sl"], final_query_params['tl'])
        while initial_query_params["tl"] != final_query_params['tl']:
            logger.warning(f"Batch {batch_idx} | URL tl value changed during translation: {initial_query_params['tl']} → {final_query_params['tl']}")
            final_query_params = _reset_languages(page, initial_query_params["sl"], final_query_params['tl'])
        return text
    else:

        raise ValueError("Empty or same-as-input translation")
'''   
<div class="qSb8Pe RCaXn KKjvXb"
    jsname="sgblj"
    role="option" 
    aria-selected="true" 
    data-language-code="fr" 
    tabindex="0" 
    jscontroller="e2jnoe" 
    jsslot="" 
    jsaction="mouseenter:tfO1Yc; focus:AHmuwe; blur:O22p3e; mouseleave:JywGue; touchstart:p6p2H; touchend:yfqBxc;mlnRJb:fLiPzd;" data-tooltip-
    id="ucj-7-fr-tooltip" 
    data-tooltip-x-position="6"
    data-tooltip-y-position="4" 
    data-tooltip-show-delay-ms="500"
    data-tooltip-anchor-boundary-type="1">

    <div class="l7O9Dc">
        <i class="material-icons-extended notranslate VfPpkd-kBDsod hsfpcd" 
            aria-hidden="true" lang="">
            check
        </i>
        <i class="material-icons-extended notranslate VfPpkd-kBDsod S3Dwie"
        aria-hidden="true" lang="">
            history
        </i>
    </div>
    <div class="Llmcnf">French</div>
    <span class="oBOnKe">(recently used language)</span>
</div>
'''
def _reset_languages(page: Page, sl: str, tl: str):
    if type(sl) is list:
        sl = sl[0]
    if type(tl) is list:
        tl = tl[0]
    _click_element(page.locator(DOUBLE_CLICK_SELECTORS[1],).first)
    _click_element(page.locator(f'div[data-language-code="{sl} role=option"]'))
    _click_element(page.locator(DOUBLE_CLICK_SELECTORS[2],).first)
    _click_element(page.locator(f'div[data-language-code="{tl} role=option"]')) 
    return parse_qs(urlparse(page.url).query)
            