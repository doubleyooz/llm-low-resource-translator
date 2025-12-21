from datetime import datetime
from typing import Dict, List, Tuple
from playwright.sync_api import sync_playwright, Page
from constants.output import OUTPUT_FOLDER, LOG_FILENAME
from pw_user_sim import get_random_delay, perform_action, simulate_human
from scrapper_config import CONFIG

# Import the singleton logger
from logger import translation_logger

logger = translation_logger.get_logger(
    output_folder=OUTPUT_FOLDER,
    log_filename=LOG_FILENAME
)

SAFE_CLICK_SELECTORS = [
    "button[aria-label='profile menu']",
    "button[id='headlessui-popover-button-:R1nlal9m:']"
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
        '''HEREEEEEE'''
        logger.info(f"{msg} Found {verse_locators.count()} verse containers")

        extracted_verses = []
        for i in range(verse_locators.count()):
            try:
               
                verse = verse_locators.nth(i)
                verse_num_locator = verse.locator('[class*="ChapterContent_label"]').first         
                verse_text_locator = verse.locator('[class*="ChapterContent_content"]')

                verse_num = verse_num_locator.inner_text().strip() if verse_num_locator.is_visible() and verse_num_locator.inner_text().strip().isdigit() else None
                     
                content_texts = verse_text_locator.all_inner_texts()          
                verse_text = " ".join([text.strip() for text in content_texts if text.strip()])
             

                if verse_text:
                    if verse_num is None and extracted_verses:
                        extracted_verses[-1] += " " + verse_text                        
                        logger.debug(f"{msg} Continued verse: {verse_text[:50]}...")
                    else:
                        extracted_verses.append(verse_text)
                        logger.debug(f"{msg} Verse {verse_num}: {verse_text[:50]}...")
              #  else:
              #      logger.warning(f"No text found for verse {verse_num}")
            except Exception as e:
                page.screenshot(path=f"{translation_logger.get_filepath()}/{msg} Error processing verse {verse_num}: {str(e)} {datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                logger.error(f"{msg} Error processing verse {verse_num}: {str(e)}")
        logger.info(f"{msg} Extracted {len(extracted_verses)} verses")
        return extracted_verses
    except Exception as e:
        page.screenshot(path=f"{translation_logger.get_filepath()}/{msg} Error extracting verses: {str(e)} {datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        logger.error(f"{msg} Error extracting verses: {str(e)}")
        raise f"{msg} Error extracting verses: {str(e)}"
    
