import datetime
import logging
import random
from typing import Any, Dict
from playwright.sync_api import sync_playwright, Page, BrowserContext
from urllib.parse import urlparse, parse_qs

from constants.languages import SL, TL
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
    "button[aria-label='Swap languages (Cmd+Shift+S)']",
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

    set_input(page, sentence, batch_idx)
   
    initial_query_params = get_current_query_params(page.url)
    
    # Optional: light scroll to trigger lazy load
    logger.debug(f"Batch {batch_idx} | Simulating human behavior...")
    simulate_human(page)
    
    result = page.locator("span[jsname='W297wb']").first
    output = result.inner_text().strip()

    if output and output != sentence:
        logger.debug(f"Batch {batch_idx} | Translated: {sentence[:30]}... → {output[:30]}...")
        stealthInteractionRoutine(page, logger, batch_idx, initial_query_params)
        return output
    else:
        logger.info(initial_query_params)
        logger.info(f"Batch {batch_idx} | {SL} -> {TL}")
        if initial_query_params['sl'] == SL and initial_query_params['tl'] == TL:
            _click_element(page.locator(DOUBLE_CLICK_SELECTORS[0]))
            text = result.inner_text().strip()

            logger.warning(f"Batch {batch_idx} | Translated back from {TL}: {sentence[:50]}...")
            stealthInteractionRoutine(page, logger, batch_idx, initial_query_params)
            return f"[TRANSLATION BACK FROM {TL}] - {sentence}"
        raise ValueError(f"Batch {batch_idx} | Empty or same-as-input translation")

def _reset_languages(page: Page, sl: str, tl: str):
    if type(sl) is list:
        sl = sl[0]
    if type(tl) is list:
        tl = tl[0]
        
    _click_element(page.locator(DOUBLE_CLICK_SELECTORS[1],).first)
    _click_element(page.locator(f'xpath=//div[@data-language-code="{sl}" and .//span[contains(text(), "recently used language")]]').first)
    _click_element(page.locator(DOUBLE_CLICK_SELECTORS[1],).first)
    _click_element(page.locator(DOUBLE_CLICK_SELECTORS[2],).first)
    _click_element(page.locator(f'xpath=//div[@data-language-code="{tl}" and .//span[contains(text(), "recently used language")]]').first)
    _click_element(page.locator(DOUBLE_CLICK_SELECTORS[2],).first)
    return get_current_query_params(page.url)
            
            
def set_input(page: Page, sentence: str, batch_idx: int):
    perform_action(lambda: page.wait_for_selector(INPUT_TEXTAREA_SELECTOR, timeout=20000), f"Batch {batch_idx} | wait result")
    perform_action(lambda:  page.fill(INPUT_TEXTAREA_SELECTOR, sentence), f"Batch {batch_idx} | type in text to be translated")
       
    textbox = page.wait_for_selector(INPUT_TEXTAREA_SELECTOR)
  
    final_text = textbox.input_value()
    attempts = 0
    while final_text != sentence and attempts < 3:
        # clear textbox
        _click_element(page.locator(UNSAFE_CLICK_SELECTORS[0],).first)
        perform_action(lambda:  page.fill(INPUT_TEXTAREA_SELECTOR, sentence), f"Batch {batch_idx} | type in text to be translated")
        final_text = textbox.input_value()
        attempts += 1
    if final_text != sentence:
        raise ValueError(f"Batch {batch_idx} | Failed to set input text after {attempts} attempts.")
    
  
def stealthInteractionRoutine(page: Page, logger: logging.Logger, batch_idx: int, initial_query_params):
    # light scroll to trigger lazy load
    if random.random() < 0.2:
        simulate_human(page, DOUBLE_CLICK_SELECTORS, number_of_clicks=2, button_click_probability=1)
        simulate_human(page, UNSAFE_CLICK_SELECTORS)
    final_query_params = get_current_query_params(page.url)
        
    while initial_query_params["sl"] != final_query_params['sl']:
        logger.warning(f"Batch {batch_idx} | URL sl value changed during translation: {initial_query_params['sl']} → {final_query_params['sl']}")
        final_query_params = _reset_languages(page, initial_query_params["sl"], final_query_params['tl'])
    while initial_query_params["tl"] != final_query_params['tl']:
        logger.warning(f"Batch {batch_idx} | URL tl value changed during translation: {initial_query_params['tl']} → {final_query_params['tl']}")
        final_query_params = _reset_languages(page, initial_query_params["sl"], final_query_params['tl'])
    
def get_current_query_params(url: str) -> Dict[str, Any]:
    return parse_qs(urlparse(url).query)