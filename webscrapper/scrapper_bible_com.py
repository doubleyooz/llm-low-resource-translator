from typing import Dict, List, Tuple
from playwright.sync_api import sync_playwright, Page



# Import the singleton logger
from logger import translation_logger
from utils.pw_helper import get_random_delay, perform_action, take_screenshot
from pw_user_sim import simulate_human

from scrapper_config import CONFIG
from constants.output import OUTPUT_FOLDER, LOG_FILENAME

logger = translation_logger.get_logger(
    output_folder=OUTPUT_FOLDER,
    log_filename=LOG_FILENAME
)

SAFE_CLICK_SELECTORS = [
    "button[aria-label='profile menu']",
    "button[id='headlessui-popover-button-:R1nlal9m:']",
    "button[id='headlessui-popover-button-:r2:']",
    "button[id='headlessui-popover-button-:r6:']",
    "input[aria-label=''Search]"    
]


def get_url(version_id: str, abbrev: str, chapter: int, suffix: str) -> str:
    if version_id == None or abbrev == None or chapter == None or suffix == None:
        raise f"Can't generate a link. version_id: {version_id}, abbrev: {abbrev}, chapter: {chapter}, suffix: {suffix}."
    return f"https://www.bible.com/bible/{version_id}/{abbrev}.{chapter}.{suffix}"



def fetch_chapter(page: Page, full_name: str, url: str, chapter: int, total_of_chapters: int, msg: str = "") -> List[str]:
    """Fetch and extract verses for a single chapter with retries."""

    logger.info(f"{msg} Fetching {chapter}/{total_of_chapters}: {url}")

    for attempt in range(CONFIG["retry_attempts"]):
        try:
            perform_action(action=lambda: page.goto(url, timeout=CONFIG["page_timeout_ms"]), description="page navigation", delay_range=CONFIG["interaction_delay_range"], msg=msg)
            simulate_human(page, selectors=SAFE_CLICK_SELECTORS, msg=msg)
            return extract_verses(page, msg=msg)
        except Exception as e:
            logger.error(f"{msg} Attempt {attempt + 1}/{CONFIG['retry_attempts']} failed for {full_name} {chapter}: {str(e)}")
            if attempt < CONFIG["retry_attempts"] - 1:
                get_random_delay(CONFIG["retry_delay_range"])
            else:
                error_msg = f"All retries failed for {full_name} {chapter}: {str(e)}"                
                logger.error(f'{msg} {error_msg}')
                raise error_msg
    return []

def extract_verses(page: Page, msg: str = '') -> List[str]:
    try:
        # Wait for verse containers to be attached to the DOM
        verse_locators = page.locator('[class*="ChapterContent_verse"]')
        verse_locators.first.wait_for(state="attached", timeout=CONFIG["page_timeout_ms"])

        logger.info(f"{msg} Found {verse_locators.count()} verse containers")

        extracted_verses = []
        for i in range(verse_locators.count()):
            try:     
                verse = verse_locators.nth(i)
                verse_num_locator = verse.locator('[class*="ChapterContent_label"]').first         
                verse_text_locator = verse.locator('[class*="ChapterContent_content"]')
                is_there_a_note = verse.locator('[class*="ChapterContent_note"]').first

                verse_num = verse_num_locator.inner_text().strip() if verse_num_locator.is_visible() and verse_num_locator.inner_text().strip().isdigit() else None
                     
                content_texts = verse_text_locator.all_inner_texts()          
                verse_text = " ".join([text.strip() for text in content_texts if text.strip()])
                              
                             
                # if no verse_text and verse_number and note: skip
                # if verse_text and verse_number and note: add
                # if verse_text and no verse_number and note: add
                # if verse_text and verse_number is greater than previous+1: skip and add
                              
                                                              
                if verse_text:
                    if verse_num:
                        if str.isnumeric(verse_num) and int(verse_num) > len(extracted_verses) + 1:                          
                            extracted_verses.append('')
                            logger.debug(f"{msg} Inserting missing verse placeholder.")
                        extracted_verses.append(verse_text)
                        logger.debug(f"{msg} Verse {verse_num}: {verse_text[:50]}...")
                                    
                    elif verse_num is None and extracted_verses:                            
                        # if is_there_a_note.is_visible():
                        #    extracted_verses.append('')
                        #    logger.debug(f"{msg} Skipping verse {verse_num} as it contains only a note.")
                        # else:
                            extracted_verses[-1] += " " + verse_text                        
                            logger.debug(f"{msg} Continued verse: {verse_text[:50]}...")
                    
                  
                elif is_there_a_note.is_visible():
                    extracted_verses.append('')
                    logger.debug(f"{msg} Skipping verse {verse_num} as it contains only a note.")
                     
                else:
                    logger.debug(f"{msg} No text found for verse {verse_num}")
            except Exception as e:
                err_msg = f"Error processing verse {verse_num}: {str(e)}"
                take_screenshot(page, filename=err_msg, msg_prefix=msg)

                logger.error(f"{msg} {err_msg}")
        logger.info(f"{msg} Extracted {len(extracted_verses)} verses")
        return extracted_verses
    except Exception as e:
        raise f"Error extracting verses: {str(e)}"