from datetime import datetime
import random
import time
from typing import Tuple
from playwright.sync_api import sync_playwright, Page, BrowserContext, Locator

from constants.output import LOG_FILENAME, OUTPUT_FOLDER
from logger import translation_logger
from scrapper_config import CONFIG
from utils.txt_helper import sanitize_txt


logger = translation_logger.get_logger(
    output_folder=OUTPUT_FOLDER,
    log_filename=LOG_FILENAME
)


def set_fatigue(fatigue: float = 1):
    return max(1.0, fatigue)
    
def take_screenshot(page: Page, filename: str, msg_prefix: str = "") -> None:
    logger.warning(f"{msg_prefix} Taking screenshot in order to sort out an issue {filename}...")
    
    msg_prefix = sanitize_txt(msg_prefix)
    filename = sanitize_txt(filename).removeprefix(msg_prefix)
    page.screenshot(path=f"{translation_logger.get_filepath()}/screenshots/{msg_prefix}_{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

def get_random_delay(delay_range: Tuple[float, float] = None, fatigue: float = 1, msg: str = "") -> None:
    if delay_range is None or len(delay_range) != 2:
        delay_range = CONFIG["interaction_delay_range"]
    delay = random.uniform(*delay_range) * set_fatigue(fatigue)
    if fatigue > 1:
        logger.info(f"{msg} Sleeping {delay:.1f}s (fatigue mode)") 

    time.sleep(delay)
    


def perform_action(action: callable, description: str, delay_range: Tuple[float, float] = CONFIG["interaction_delay_range"], 
        raise_exception: bool = False, msg: str = '') -> bool:
    if msg:        
        description = description.removeprefix(msg)
    try:
        action()
        logger.debug(f"{msg} Action '{description}' performed successfully.")
        get_random_delay(delay_range)
        return True
    except Exception as e:
        logger.warning(f"{msg} Action '{description}' failed: {e}")
        if raise_exception:
            raise
        return False
    

def random_mouse_movement(page: Page, msg: str = "") -> None:
    """Perform random mouse movement within viewport."""
    perform_action(
        action=lambda: page.mouse.move(
            random.randint(*CONFIG["mouse_move_range_x"]),
            random.randint(*CONFIG["mouse_move_range_y"]),
            steps=random.randint(5, 15)
        ),
        description=f"random mouse movement",
        delay_range=CONFIG["scroll_delay_range"],
        msg=msg
    )    

def click_element(element: Locator, msg_prefix: str = "", hover: bool = False, raise_exception: bool = False) -> bool:
        """Click an element with realistic delay."""
        try:
            if isinstance(element, list):
                if len(element) == 0:
                    logger.warning(f"{msg_prefix} Empty element list provided")
                    raise ValueError("Empty element list")
                element = element[0]  # Use first element from list
                logger.debug(f"{msg_prefix} Using first element from list ({len(element)} elements total)")

                
            element_description = (
                element.get_attribute('aria-label') or 
                element.get_attribute('title') or 
                element.text_content()[:50] or 'unknown element'
            )
            
            if hover:
                perform_action(
                    action=lambda: element.hover(),
                    description=f"hover: {element_description}",
                    delay_range=CONFIG["scroll_delay_range"],
                    raise_exception=raise_exception,
                    msg=msg_prefix
                )
            
            return perform_action(
                action=lambda: element.click(delay=random.uniform(100, 300)),
                description=f"click: {element_description}",
                delay_range=CONFIG["button_delay_range"],
                raise_exception=raise_exception,
                msg=msg_prefix
            )
        except Exception as e:
            logger.warning(f"{msg_prefix} Click failed: {e}")
            if raise_exception:
                raise e
            return False
