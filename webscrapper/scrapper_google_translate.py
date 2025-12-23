import random

from typing import Any, Dict
from xml.sax.xmlreader import Locator
from playwright.sync_api import sync_playwright, Page, BrowserContext
from urllib.parse import urlparse, parse_qs

from constants.languages import SL, TL
from constants.output import LOG_FILENAME, OUTPUT_FOLDER
from scrapper_config import CONFIG
from utils.pw_helper import click_element, perform_action, take_screenshot
from pw_user_sim import simulate_human

# Import the singleton logger
from logger import translation_logger

SAFE_CLICK_SELECTORS = [
    "button[aria-label='Listen to source text']",
    "button[aria-label='Listen to translation']",
    "div[aria-label='Main menu']",
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


logger = translation_logger.get_logger(
    output_folder=OUTPUT_FOLDER,
    log_filename=LOG_FILENAME
)


def get_url (sl, tl):
    n = random.randint(1, 3)
    if n == 1:
        return f"https://translate.google.com/?sl={sl}&tl={tl}&op=translate"
    elif n == 2:
        return f"https://translate.google.ca/?sl={sl}&tl={tl}&op=translate"
    else:
        return f"https://translate.google.co.uk/?sl={sl}&tl={tl}&op=translate"


# Translation Core
def translate_sentence(page: Page, sentence: str, batch_idx: int) -> str:
    """Translate one sentence using Google Translate."""
    batch_msg = f"Batch {batch_idx}" 
    
    # Replace double quotes with single quotes to avoid issues
    sentence = sentence.replace('"', "'")

    current_query_params = get_current_query_params(page.url)
 
    # Optional: light scroll to trigger lazy load
    simulate_human(page=page, msg=batch_msg)
    
 
    ensure_language_parameters_stability(page=page,
        current_sl=current_query_params.get('sl'),
        current_tl=current_query_params.get('tl'),
        final_sl=SL,
        final_tl=TL,
        batch_msg=batch_msg,
    )
    
    set_input(page, sentence, msg=batch_msg)
   
    logger.debug(f"{batch_msg} Translating: [{current_query_params.get('sl')[0]} → {current_query_params.get('tl')[0]}] {sentence}...")
    
    output = get_output(page=page, msg=batch_msg)
    
    if output != sentence:
        logger.debug(f"{batch_msg} Translated: {sentence[:30]}... → {output}...")
        stealthInteractionRoutine(page, batch_msg)
        return output
    else:
        logger.info(f"{batch_msg} {current_query_params}")
        logger.info(f"{batch_msg} {SL} -> {TL}")
        if current_query_params.get('sl')[0] == SL and current_query_params.get('tl')[0] == TL:
            logger.warning(f"{batch_msg} Clicking on swap languages {DOUBLE_CLICK_SELECTORS[0]} for backtranslation...")
            try:                
                click_element(page.locator(DOUBLE_CLICK_SELECTORS[0]).first, msg_prefix=batch_msg, raise_exception=True)
            except Exception as e:
                try:
                    new_locator = DOUBLE_CLICK_SELECTORS[0].replace("Cmd", "Ctrl")
                    logger.debug(f"{batch_msg} Retry clicking swap languages button with {new_locator}...")
                    click_element(page.locator(new_locator).first, msg_prefix=batch_msg, raise_exception=True)
                   
                except Exception as e2:
                    err_msg = f"Failed to click swap languages button. {str(e)}"
                    logger.error(f"{batch_msg} {err_msg}")
                    take_screenshot(page, filename=err_msg, msg_prefix=batch_msg)
                    raise e
                
            output = get_output(page=page, msg=batch_msg)

            if output == sentence:
                  
                current_query_params = get_current_query_params(page.url)
                if current_query_params.get('sl')[0]== TL and current_query_params.get('tl')[0] == SL:
                    err_msg = "Backtranslation failed, output matches input"
                    take_screenshot(page, filename=err_msg, msg_prefix=batch_msg)

                    logger.error(f"{batch_msg} {err_msg}")
                    logger.debug(f"{batch_msg} Attempting to reload in order to get the translation...")
                    page.reload()
                    output = get_output(page=page, msg=batch_msg)

                    if output == sentence:
                        logger.error(f"{batch_msg} {err_msg} after reload.")
                        take_screenshot(page, filename=f"{err_msg} after reload", msg_prefix=batch_msg)
                      
                    else:
                        logger.warning(f"{batch_msg} Backtranslation succeeded after reload. Output: {output[:50]}...")
                        stealthInteractionRoutine(page, batch_msg)
                        return f"[TRANSLATION BACK FROM {TL}] - {output}"
                else:
                    error_msg = "Backtranslation failed, failed to properly swap languages."
                    logger.error(f"{batch_msg} {error_msg}")
                    take_screenshot(page, filename=error_msg, msg_prefix=batch_msg)
                    
                    raise ValueError(f"{batch_msg} {error_msg}")
             
               
            logger.warning(f"{batch_msg} Translated back from {TL}: {sentence[:50]}...")
            stealthInteractionRoutine(page, batch_msg)
            return f"[TRANSLATION BACK FROM {TL}] - {output}"
        raise ValueError(f"{batch_msg} Can't perform backtranslation [{SL}] -> [{TL}] for sentence: {sentence[:50]}...")

def _click_language_option(page: Page, language_code: str, _language_list: Locator, batch_msg: str = ''):
    """Helper function to click language option with fallback"""  
    # Selector priorities
    try:
        menu_state = _language_list.get_attribute('aria-expanded')
        if menu_state != 'true':
            logger.debug(f"{batch_msg} Opening language menu")
            click_element(_language_list, msg_prefix=batch_msg, hover=True)
        
        
        logger.debug(f"{batch_msg} Searching for language options...")
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
                logger.debug(f"{batch_msg} Attempting with selector: {found_element.get_attribute('data-language-code')} at index {i}...")
                try:     
                    if success:
                        break    
                    menu_state = _language_list.get_attribute('aria-expanded')
                    if menu_state != 'true':
                        take_screenshot(page, filename=f"Menu not expanded for {_language_list.get_attribute('aria-label')}_menu{language_code} at index {i}", msg_prefix=batch_msg)
                        logger.debug(f"{batch_msg} Opening language menu")
                        click_element(_language_list, msg_prefix=batch_msg, hover=True)
                    # take_screenshot(page, filename=f"Menu expanded for {_language_list.get_attribute('aria-label')}_menu{language_code} at index {i}", msg_prefix=batch_msg)
                    logger.debug(f"{batch_msg} {_language_list.get_attribute('aria-label')} Menu is visible: {_language_list.is_visible()}, Option is visible: {found_element.is_visible()}")
                    success = click_element(element=found_element, msg_prefix=batch_msg, hover=True, raise_exception=True)
                except Exception as e:
                    logger.debug(f"{batch_msg} Selector failed: {e}")
                    continue
                break       
            
        if found_element is None:
            logger.debug(f"{batch_msg} No selector found for {language_code}")
            raise Exception(f"No selector found for {language_code}. Language list failed to open: {_language_list.get_attribute('aria-label')} Menu is visible: {_language_list.is_visible()}")    
     
        if not success:
            logger.debug(f"{batch_msg} No working selector found for {language_code}")
            raise Exception(f"No working selector found for {language_code}")      
              
        # Verify menu closed
        page.wait_for_timeout(500)
        final_state = _language_list.get_attribute('aria-expanded')
        if final_state == 'true':
            logger.warning(f"{batch_msg} Menu didn't close automatically, closing manually")
            click_element(_language_list, msg_prefix=batch_msg, hover=True)
    
    except Exception as e:
        error_msg = f"Language selection failed for {language_code}: {str(e)}"
        logger.error(f"{batch_msg} {error_msg}")
        take_screenshot(page, filename=error_msg, msg_prefix=batch_msg)        
        raise e

def _reset_languages(page: Page, language: str, is_source_language: bool = True, batch_msg: str = '') -> Dict[str, Any]:
    if type(language) is list:
        language = language[0]
    selector = DOUBLE_CLICK_SELECTORS[1] if is_source_language else DOUBLE_CLICK_SELECTORS[2]
  
    logger.debug(f"{batch_msg} {selector} Resetting {'source' if is_source_language else 'target'} language to {language}...")
    _click_language_option(page, language, page.locator(selector).first, batch_msg=batch_msg)

    
    return get_current_query_params(page.url)
            
def set_input(page: Page, sentence: str, msg: str = '') -> None:
    # ensure menus are closed
    for selector in DOUBLE_CLICK_SELECTORS[1:]:          
        menu = page.locator(selector).first
        menu_state = menu.get_attribute('aria-expanded')
        if menu_state == 'true':
            logger.debug(f"{msg} Ensuring menu {menu.get_attribute('aria-label')} is closed...")
            click_element(menu, msg_prefix=msg, hover=True)
        
   
    perform_action(lambda: page.wait_for_selector(INPUT_TEXTAREA_SELECTOR, timeout=20000), f"{msg} wait result")
    perform_action(lambda:  page.fill(INPUT_TEXTAREA_SELECTOR, sentence), f"{msg} type in text to be translated")
       
    textbox = page.wait_for_selector(INPUT_TEXTAREA_SELECTOR)
  
    final_text = textbox.input_value()
    attempts = 0
    while final_text != sentence and attempts < 3:
        # clear textbox
        click_element(page.locator(UNSAFE_CLICK_SELECTORS[0]).first, msg_prefix=msg)
        perform_action(lambda:  page.fill(INPUT_TEXTAREA_SELECTOR, sentence), f"{msg} type in text to be translated")
        final_text = textbox.input_value()
        attempts += 1
    if final_text != sentence:
        raise ValueError(f"{msg} Failed to set input text after {attempts} attempts.")
    
def get_output(page: Page, msg: str = '') -> str:
    result = page.locator("span[jsname='jqKxS']").first
    
    output = result.inner_text()
    
    while not output:
        logger.debug(f"{msg} Waiting for translation result...")
        perform_action(lambda: page.wait_for_timeout(500), f"{msg} wait for translation")
        output = result.inner_text()
    logger.debug(f"{msg} Obtained translation output: {output}...")
    return output
    
  
def stealthInteractionRoutine(page: Page, msg: str = "") -> None:
    # light scroll to trigger lazy load
    if random.random() < CONFIG["safe_button_click_probability"]:
        simulate_human(page=page, selectors=SAFE_CLICK_SELECTORS, msg=msg)
        
    if random.random() < CONFIG["double_button_click_probability"]:          
            logger.warning(f"{msg} Using unsafe double click selectors...")
            simulate_human(page=page, selectors=DOUBLE_CLICK_SELECTORS, number_of_clicks=2, button_click_probability=1, msg=msg)
            logger.warning(f"{msg} Finished using unsafe double click selectors...")
    elif random.random() < CONFIG["unsafe_button_click_probability"]:
            logger.warning(f"{msg} Using unsafe selectors...")
            simulate_human(page=page, selectors=UNSAFE_CLICK_SELECTORS, msg=msg)
            logger.warning(f"{msg} Finished using unsafe selectors...")
    final_query_params = get_current_query_params(page.url)
        
    ensure_language_parameters_stability(
        page=page,
        current_sl=final_query_params.get('sl'),
        current_tl=final_query_params.get('tl'),
        final_sl=SL,
        final_tl=TL,
        batch_msg=msg,
    )
    logger.debug(f"{msg} Stealth routine completed...")

def get_current_query_params(url: str) -> Dict[str, Any]:
    return parse_qs(urlparse(url).query)

def ensure_language_parameters_stability(
    page: Page,
    current_sl: str,
    current_tl: str,
    final_sl: str, # this must be the correct source language
    final_tl: str,  # this must be the correct target language
    batch_msg: str,
) -> dict:
    if type(current_sl) is list:
        current_sl = current_sl[0]
    if type(current_tl) is list:
        current_tl = current_tl[0]
    if type(final_sl) is list:
        final_sl = final_sl[0]
    if type(final_tl) is list:
        final_tl = final_tl[0]


    while current_sl != final_sl:
        final_query_params = _reset_languages(page= page, language=final_sl, is_source_language=True, batch_msg=batch_msg)
        logger.warning(f"{batch_msg} Source language mismatch: {current_sl} → {final_sl}. Resetting...")
        current_sl = final_query_params['sl'][0]
    while current_tl != final_tl:        
        logger.warning(f"{batch_msg} Target language mismatch: {current_tl} → {final_tl}. Resetting...")
        final_query_params = _reset_languages(page=page, language=final_tl, is_source_language=False, batch_msg=batch_msg)
        current_tl = final_query_params['tl'][0]
    return {
        "sl": current_sl,
        "tl": current_tl
    }
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