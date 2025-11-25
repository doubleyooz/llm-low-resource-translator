from datetime import datetime
import logging
import random

from typing import Any, Dict
from xml.sax.xmlreader import Locator
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
    
    set_input(page, sentence, msg=batch_msg, logger=logger)
   
    initial_query_params = get_current_query_params(page.url)
 
    # Optional: light scroll to trigger lazy load
    simulate_human(page=page, msg=batch_msg)
    
 
    if initial_query_params.get('sl')[0] != SL:
        logger.debug(f"{batch_msg} | Source language mismatch: {initial_query_params.get('sl')[0]} → {SL}. Resetting...")
        initial_query_params = _reset_languages(page=page, language=initial_query_params.get("sl")[0], is_source_language=True, batch_msg=batch_msg)
    if initial_query_params.get('tl')[0] != TL:
        logger.debug(f"{batch_msg} | Target language mismatch: {initial_query_params.get('tl')[0]} → {TL}. Resetting...")
        initial_query_params = _reset_languages(page=page, language=initial_query_params.get("tl")[0], is_source_language=False, batch_msg=batch_msg)
    
    logger.debug(f"{batch_msg} | Translating: [{initial_query_params.get('sl')[0]} → {initial_query_params.get('tl')[0]}] {sentence[:30]}...")
    
    result = page.locator("span[jsname='W297wb']").first
    
    output = result.inner_text().strip()
    
    while not output:
        logger.debug(f"{batch_msg} | Waiting for translation result...")
        perform_action(lambda: page.wait_for_timeout(500), f"{batch_msg} | wait for translation")
        output = result.inner_text().strip()
    
    if output != sentence:
        logger.debug(f"{batch_msg} | Translated: {sentence[:30]}... → {output[:30]}...")
        stealthInteractionRoutine(page, batch_idx, initial_query_params)
        return output
    else:
        logger.info(initial_query_params)
        logger.info(f"{batch_msg} | {SL} -> {TL}")
        if initial_query_params.get('sl')[0] == SL and initial_query_params.get('tl')[0] == TL:
            logger.warning(f"{batch_msg} | Clicking on swap languages for backtranslation...")
            _click_element(page.locator(DOUBLE_CLICK_SELECTORS[0]).first, msg=batch_msg)
            output = result.inner_text().strip()

            logger.warning(f"{batch_msg} | Translated back from {TL}: {sentence[:50]}...")
            stealthInteractionRoutine(page, batch_idx, initial_query_params)
            return f"[TRANSLATION BACK FROM {TL}] - {output}"
        raise ValueError(f"{batch_msg} | Can't perform backtranslation [{SL}] -> [{TL}] for sentence: {sentence[:50]}...")

def _click_language_option(page: Page, language_code: str, _language_list: Locator, batch_msg: str = ''):
    """Helper function to click language option with fallback"""

    _logger = translation_logger.get_logger()
    
    # Selector priorities

    try:
        menu_state = _language_list.get_attribute('aria-expanded')
        if menu_state != 'true':
            _logger.debug(f"{batch_msg} | Opening language menu")
            _click_element(_language_list, msg=batch_msg, hover=True)
        
        
        _logger.debug(f"{batch_msg} | Searching for language options...")
        groups = page.locator('div[role="group"]')
        options = groups.locator('div[role="option"]')

                  
        # Try each selector until one works
        success = False
     
        found_element = None
        for i in range(options.count()):
            option = options.nth(i)
            option_lang_code = option.get_attribute('data-language-code')
            
            if option_lang_code == language_code and option.is_visible():
                found_element = option
                _logger.debug(f"{batch_msg} | Attempting with selector: {found_element.get_attribute('data-language-code')} at index {i}...")
                try:     
                    if success:
                        break    
                    menu_state = _language_list.get_attribute('aria-expanded')
                    if menu_state != 'true':
                        page.screenshot(path=f"output/screenshoot_{batch_msg}_closed_{_language_list.get_attribute('aria-label')}_menu_{language_code}_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                        _logger.warning(f"{batch_msg} | Taking screenshot before trying to open the {_language_list.get_attribute('aria-label')} menu {language_code} at index {i}...")
                        _logger.debug(f"{batch_msg} | Opening language menu")
                        _click_element(_language_list, msg=batch_msg, hover=True)
                    # page.screenshot(path=f"output/screenshoot_{batch_msg}_opened_{_language_list.get_attribute('aria-label')}_menu_{language_code}_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    # _logger.warning(f"{batch_msg} | Taking screenshot before clicking language option {language_code} at index {i}...")
                    _logger.debug(f"{batch_msg} | {_language_list.get_attribute('aria-label')} Menu is visible: {_language_list.is_visible()}, Option is visible: {found_element.is_visible()}")
                    success = _click_element(element=found_element, msg=batch_msg, hover=True, raise_exception=True)
                except Exception as e:
                    _logger.debug(f"{batch_msg} | Selector failed: {e}")
                    continue
                break       
     
        if not success:
            raise Exception(f"No working selector found for {language_code}")      
              
        # Verify menu closed
        page.wait_for_timeout(500)
        final_state = _language_list.get_attribute('aria-expanded')
        if final_state == 'true':
            _logger.warning(f"{batch_msg} | Menu didn't close automatically, closing manually")
            _click_element(_language_list, msg=batch_msg, hover=True)
    
    except Exception as e:
        _logger.error(f"{batch_msg} | Language selection failed for {language_code}: {e}")
        
        # Last resort attempt
        _logger.error(f"{batch_msg} | Complete failure for {language_code}")
        raise 

def _reset_languages(page: Page, language: str, is_source_language: bool = True, batch_msg: str = '') -> Dict[str, Any]:
    if type(language) is list:
        language = language[0]
    _logger = translation_logger.get_logger()
    selector = DOUBLE_CLICK_SELECTORS[1] if is_source_language else DOUBLE_CLICK_SELECTORS[2]
  
    _logger.debug(f"{batch_msg} | {selector} Resetting {'source' if is_source_language else 'target'} language to {language}...")
    _click_language_option(page, language, page.locator(selector).first, batch_msg=batch_msg)

    
    return get_current_query_params(page.url)
            
def set_input(page: Page, sentence: str, msg: str = '', logger: logging.Logger = None) -> None:
    # ensure menus are closed
    for selector in DOUBLE_CLICK_SELECTORS[1:]:          
        menu = page.locator(selector).first
        menu_state = menu.get_attribute('aria-expanded')
        if menu_state == 'true':
            logger.debug(f"{msg} | Ensuring menu {menu.get_attribute('aria-label')} is closed...")
            _click_element(menu, msg=msg, hover=True)
        
   
    perform_action(lambda: page.wait_for_selector(INPUT_TEXTAREA_SELECTOR, timeout=20000), f"{msg} | wait result")
    perform_action(lambda:  page.fill(INPUT_TEXTAREA_SELECTOR, sentence), f"{msg} | type in text to be translated")
       
    textbox = page.wait_for_selector(INPUT_TEXTAREA_SELECTOR)
  
    final_text = textbox.input_value()
    attempts = 0
    while final_text != sentence and attempts < 3:
        # clear textbox
        _click_element(page.locator(UNSAFE_CLICK_SELECTORS[0]).first, msg=msg)
        perform_action(lambda:  page.fill(INPUT_TEXTAREA_SELECTOR, sentence), f"{msg} | type in text to be translated")
        final_text = textbox.input_value()
        attempts += 1
    if final_text != sentence:
        raise ValueError(f"{msg} | Failed to set input text after {attempts} attempts.")
    
  
def stealthInteractionRoutine(page: Page, batch_idx: int, initial_query_params: Dict[str, Any]) -> None:
    batch_msg = f"Batch {batch_idx}"
    _logger = translation_logger.get_logger()
    # light scroll to trigger lazy load
    #if random.random() < 0.5:
    #    simulate_human(page=page, selectors=SAFE_CLICK_SELECTORS, msg=batch_msg)
        
    if random.random() < 0.7:
            _logger.warning(f"{batch_msg} | Using unsafe selectors...")
            simulate_human(page=page, selectors=DOUBLE_CLICK_SELECTORS, number_of_clicks=2, button_click_probability=1, msg=batch_msg)
            simulate_human(page=page, selectors=UNSAFE_CLICK_SELECTORS, msg=batch_msg)
            _logger.warning(f"{batch_msg} | Finished using unsafe selectors...")
    final_query_params = get_current_query_params(page.url)
        
    while initial_query_params.get('sl')[0] != final_query_params.get('sl')[0]:
        _logger.warning(f"{batch_msg} | URL sl value changed during translation: {initial_query_params.get('sl')} → {final_query_params.get('sl')}")
        final_query_params = _reset_languages(page= page, language=initial_query_params.get("sl")[0], is_source_language=True, batch_msg=batch_msg)
    while initial_query_params.get("tl")[0] != final_query_params.get('tl')[0]:
        _logger.warning(f"{batch_msg} | URL tl value changed during translation: {initial_query_params.get('tl')} → {final_query_params.get('tl')}")
        final_query_params = _reset_languages(page=page, language=initial_query_params.get("tl"), is_source_language=False, batch_msg=batch_msg)
    
def get_current_query_params(url: str) -> Dict[str, Any]:
    return parse_qs(urlparse(url).query)

# update language name mapping when needed
def _get_language_name(language_code: str) -> str:
    """Map language code to English name for selectors"""
    language_names = {
        'fr': 'French', 'en': 'English', 'es': 'Spanish', 'de': 'German',
        'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'zh': 'Chinese',
        'ja': 'Japanese', 'ko': 'Korean', 'ar': 'Arabic', 'hi': 'Hindi',
        'nl': 'Dutch', 'pl': 'Polish', 'sv': 'Swedish', 'tr': 'Turkish'
    }
    return language_names.get(language_code, language_code)