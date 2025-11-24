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
# Import the singleton logger
from logger import translation_logger

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
    batch_msg = f"Batch {batch_idx}" 
    
    set_input(page, sentence, msg=batch_msg)
   
    initial_query_params = get_current_query_params(page.url)
 
    # Optional: light scroll to trigger lazy load
    simulate_human(page=page, msg=batch_msg)
    
 
    if initial_query_params.get('sl')[0] != SL:
        logger.debug(f"{batch_msg} | Source language mismatch: {initial_query_params.get('sl')[0]} → {SL}. Resetting...")
        initial_query_params = _reset_languages(page= page, language=initial_query_params.get("sl")[0], is_source_language=True, batch_msg=batch_msg)
    if initial_query_params.get('tl')[0] != TL:
        logger.debug(f"{batch_msg} | Target language mismatch: {initial_query_params.get('tl')[0]} → {TL}. Resetting...")
        initial_query_params = _reset_languages(page= page, language=initial_query_params.get("tl")[0], is_source_language=False, batch_msg=batch_msg)
    
    logger.debug(f"{batch_msg} | Translating: [{initial_query_params.get('sl')[0]} → {initial_query_params.get('tl')[0]}] {sentence[:30]}...")
    
    result = page.locator("span[jsname='W297wb']").first
    output = result.inner_text().strip()
    
    if output and output != sentence:
        logger.debug(f"{batch_msg} | Translated: {sentence[:30]}... → {output[:30]}...")
        stealthInteractionRoutine(page, batch_idx, initial_query_params)
        return output
    else:
        logger.info(initial_query_params)
        logger.info(f"{batch_msg} | {SL} -> {TL}")
        if initial_query_params.get('sl')[0] == SL and initial_query_params.get('tl')[0] == TL:
            _click_element(page.locator(DOUBLE_CLICK_SELECTORS[0]), msg=batch_msg)
            output = result.inner_text().strip()

            logger.warning(f"{batch_msg} | Translated back from {TL}: {sentence[:50]}...")
            stealthInteractionRoutine(page, batch_idx, initial_query_params)
            return f"[TRANSLATION BACK FROM {TL}] - {output}"
        raise ValueError(f"{batch_msg} | Can't perform backtranslation [{SL}] -> [{TL}] for sentence: {sentence[:50]}...")

def _click_language_option(page: Page, language_code: str, batch_msg: str = ''):
    """Helper function to click language option with fallback"""
    recent_lang_locator = page.locator(f'xpath=//div[@data-language-code="{language_code}" and .//span[contains(text(), "recently used language")]]')
    _logger = translation_logger.get_logger()
    try:
        if recent_lang_locator.count() > 0:
            _logger.debug(f"{batch_msg} | Clicking recently used language option: {language_code}")   
            is_menu_open = _click_element(recent_lang_locator.first, msg=batch_msg, hover=True)
            if not is_menu_open:
                _logger.debug(f"{batch_msg} | Fallback: Clicking language option: {language_code}")
                
                is_menu_open = _click_element(page.locator(f'div[data-language-code="{language_code}"]').first, msg=batch_msg, hover=True)
                if not is_menu_open:
                    _logger.debug(f"{batch_msg} | Fallback failed: Clicking language option without waiting: {language_code}")
                    raise Exception("Failed to click recently used language option")
        else:
            _logger.debug(f"{batch_msg} | Clicking language option: {language_code}")
            is_menu_open = _click_element(page.locator(f'div[data-language-code="{language_code}"]').first, msg=batch_msg, hover=True)
            if not is_menu_open:
                _logger.debug(f"{batch_msg} | Fallback failed: Clicking language option without waiting: {language_code}")
                raise Exception("Failed to click language option")
            
            
    except Exception as e:
        _logger.error(f"{batch_msg} | Failed to click language option {language_code}: {e}")
        _click_element(page.locator(f'div[data-language-code="{language_code}"]').first, msg=batch_msg)
        

def _reset_languages(page: Page, language: str, is_source_language: bool = True, batch_msg: str = '') -> Dict[str, Any]:
    if type(language) is list:
        language = language[0]
    _logger = translation_logger.get_logger()
    selector = DOUBLE_CLICK_SELECTORS[1] if is_source_language else DOUBLE_CLICK_SELECTORS[2]
  
    _logger.debug(f"{batch_msg} | Clicking selector: {selector}")
    _click_element(page.locator(selector).first, msg=batch_msg, hover=True)
    _logger.debug(f"{batch_msg} | Resetting {'source' if is_source_language else 'target'} language to {language}...")
    _click_language_option(page, language, batch_msg=batch_msg)
    _logger.debug(f"{batch_msg} | Closing selector: {selector}")
    _click_element(page.locator(selector).first, msg=batch_msg, hover=True)
    
    return get_current_query_params(page.url)
            
def set_input(page: Page, sentence: str, msg: str = ''):
    perform_action(lambda: page.wait_for_selector(INPUT_TEXTAREA_SELECTOR, timeout=20000), f"{msg} | wait result")
    perform_action(lambda:  page.fill(INPUT_TEXTAREA_SELECTOR, sentence), f"{msg} | type in text to be translated")
       
    textbox = page.wait_for_selector(INPUT_TEXTAREA_SELECTOR)
  
    final_text = textbox.input_value()
    attempts = 0
    while final_text != sentence and attempts < 3:
        # clear textbox
        _click_element(page.locator(UNSAFE_CLICK_SELECTORS[0],).first, msg=msg)
        perform_action(lambda:  page.fill(INPUT_TEXTAREA_SELECTOR, sentence), f"{msg} | type in text to be translated")
        final_text = textbox.input_value()
        attempts += 1
    if final_text != sentence:
        raise ValueError(f"{msg} | Failed to set input text after {attempts} attempts.")
    
  
def stealthInteractionRoutine(page: Page, batch_idx: int, initial_query_params: Dict[str, Any]) -> None:
    batch_msg = f"Batch {batch_idx}"
    _logger = translation_logger.get_logger()
    # light scroll to trigger lazy load
    if random.random() < 0.2:
        simulate_human(page=page, selectors=DOUBLE_CLICK_SELECTORS, number_of_clicks=2, button_click_probability=1, msg=batch_msg)
        simulate_human(page=page, selectors=UNSAFE_CLICK_SELECTORS, msg=batch_msg)
    final_query_params = get_current_query_params(page.url)
        
    while initial_query_params.get('sl')[0] != final_query_params.get('sl')[0]:
        _logger.warning(f"{batch_msg} | URL sl value changed during translation: {initial_query_params.get('sl')} → {final_query_params.get('sl')}")
        final_query_params = _reset_languages(page= page, language=initial_query_params.get("sl")[0], is_source_language=True, batch_msg=batch_msg)
    while initial_query_params.get("tl")[0] != final_query_params.get('tl')[0]:
        _logger.warning(f"{batch_msg} | URL tl value changed during translation: {initial_query_params.get('tl')} → {final_query_params.get('tl')}")
        final_query_params = _reset_languages(page=page, language=initial_query_params.get("tl"), is_source_language=False, batch_msg=batch_msg)
    
def get_current_query_params(url: str) -> Dict[str, Any]:
    return parse_qs(urlparse(url).query)