from datetime import datetime
import logging
import random

from typing import Any, Dict, List, Tuple
from xml.sax.xmlreader import Locator
from playwright.sync_api import sync_playwright, Page, BrowserContext
from urllib.parse import urlparse, parse_qs

from exceptions.not_found_exception import NotFoundException
from constants.languages import SL, TL
from constants.output import OUTPUT_FOLDER
from scrapper_config import CONFIG
from pw_user_sim import _click_element, get_random_delay, perform_action, simulate_human
# Import the singleton logger
from logger import translation_logger

wordbank =   [
"television", "screen", "remote", "channel", "movie", "actor", "actress", "director", "scene", "script",
"radio", "news", "reporter", "camera", "lens", "flash", "film", "roll", "studio", "stage",
"ticket", "seat", "audience", "crowd", "applause", "curtain", "costume", "mask", "mirror", "shadow",
"river", "lake", "ocean", "island", "forest", "desert", "valley", "peak", "cliff", "cave",
"farm", "field", "crop", "harvest", "barn", "tractor", "tool", "hammer", "nail", "screw",
"building", "tower", "bridge", "tunnel", "station", "platform", "track", "signal", "bell", "whistle",

"computer", "keyboard", "mouse", "monitor", "printer", "internet", "website", "email", "password", "account",
"phone", "call", "text", "app", "battery", "charger", "cable", "headphones", "speaker", "microphone",
"calendar", "date", "event", "reminder", "note", "list", "task", "project", "deadline", "meeting",
"email", "folder", "file", "document", "spreadsheet", "presentation", "slide", "chart", "graph", "data",
"network", "server", "cloud", "storage", "backup", "virus", "software", "program", "code", "bug",
"window", "door", "key", "lock", "handle", "knob", "switch", "button", "lever", "dial",
"fan", "air", "heat", "thermostat", "fridge", "oven", "microwave", "toaster", "kettle", "pan",
"pot", "lid", "sink", "tap", "soap", "towel", "brush", "comb", "mirror", "razor",
"toothbrush", "paste", "shower", "bath", "tub", "curtain", "mat", "rug", "carpet", "tile",
"pillow", "blanket", "sheet", "mattress", "frame", "drawer", "shelf", "closet", "hanger", "laundry",
"basket", "iron", "board", "detergent", "fabric", "thread", "needle", "button", "zipper", "belt",
"umbrella", "raincoat", "boots", "socks", "gloves", "scarf", "cap", "sunglasses", "backpack", "suitcase",
"luggage", "passport", "visa", "flight", "hotel", "room", "keycard", "lobby", "elevator", "stairs",
"pool", "gym", "exercise", "weight", "machine", "treadmill", "bicycle", "helmet", "gloves", "pad",

"run", "walk", "jump", "swim", "fly", "drive", "ride", "cook", "eat", "drink", "death", "sadness",
"read", "write", "speak", "listen", "watch", "see", "hear", "touch", "feel", "smell",
"think", "know", "believe", "understand", "remember", "forget", "learn", "teach", "study", "work",
"play", "dance", "sing", "laugh", "cry", "shout", "whisper", "sleep", "wake", "dream",
"build", "break", "fix", "clean", "wash", "paint", "draw", "cut", "open", "close"





]

    
SAFE_CLICK_SELECTORS = [   
    "button[class='gwt-Button searchButton']",
 
]

UNSAFE_CLICK_SELECTORS = [

]

# they're unsafe and given the currently logic they must be clicked twice
DOUBLE_CLICK_SELECTORS = [

]

INPUT_TEXTAREA_SELECTOR = "input[class='gwt-TextBox searchBox']"

def get_url (sl, tl):
    return 'https://www.akademikernewek.org.uk/corpus/?locale=en'

# -------------------------------
# Translation Core
# -------------------------------
def translate_sentence(page: Page, sentence: str, batch_idx: int, logger: logging.Logger) -> str:
    """Translate one sentence using Google Translate."""
    batch_msg = f"Batch {batch_idx}" 
    
    # Replace double quotes with single quotes to avoid issues
    sentence = sentence.replace('"', "'")

    # Optional: light scroll to trigger lazy load
    simulate_human(page=page, msg=batch_msg)
    
    set_input(page, sentence, msg=batch_msg, logger=logger)
   
    logger.debug(f"{batch_msg} | Searching: {sentence}...")
    
    return get_output(logger=logger, page=page, msg=batch_msg)
    
def set_input(page: Page, sentence: str, msg: str = '', logger: logging.Logger = None) -> None:
 
   
    perform_action(lambda: page.wait_for_selector(INPUT_TEXTAREA_SELECTOR, timeout=20000), f"{msg} | wait result")
    perform_action(lambda:  page.fill(INPUT_TEXTAREA_SELECTOR, sentence), f"{msg} | type in text to be translated")
       
    textbox = page.wait_for_selector(INPUT_TEXTAREA_SELECTOR)
  
    final_text = textbox.input_value()
    attempts = 0
    while final_text != sentence and attempts < 3:
        perform_action(lambda:  page.fill(INPUT_TEXTAREA_SELECTOR, sentence), f"{msg} | type in text to be translated")
        final_text = textbox.input_value()
        logger.debug(f"{msg} | current input: {final_text}")
        attempts += 1
    if final_text != sentence:
        raise ValueError(f"{msg} | Failed to set input text after {attempts} attempts.")
    
def get_output(page: Page, logger: logging.Logger, msg: str = '') -> Tuple[List[str], List[str]]:
    buttons = page.locator(SAFE_CLICK_SELECTORS[0])
    attempts = 0
    max_attempts = 2
    while(attempts < max_attempts):
        logger.debug(f"{msg} | Attempt {attempts+1}/{max_attempts} {buttons.last.inner_text()}")
        _click_element(buttons.last, msg)
        first_half = page.locator("tr[class='even']")
        second_half = page.locator("tr[class='odd']")
        even_elements = first_half.element_handles()
        odd_elements = second_half.element_handles()
        if len(even_elements) == 0 and len(odd_elements) == 0:
            if attempts > 0:
                raise NotFoundException(f"{msg} | No translation output found.")
            get_random_delay()
        else:
            break
        attempts += 1
    
    logger.debug(f"{msg} | First half ({len(even_elements)}): {first_half}")
    logger.debug(f"{msg} | Second half ({len(odd_elements)}): {second_half}")
    all_elements = even_elements + odd_elements
    
    en_output = []
    kw_output = []
    
    for e in all_elements:
        text = e.inner_text().strip()
        # logger.debug(f"{msg} | First half element text: {text}")
        result = text.replace("\"", '\'').split('	')
        en_output.append(result[0].strip())
        kw_output.append(result[1].strip())
        
    return en_output, kw_output
    "television", "screen", "remote", "channel", "movie", "actor", "actress", "director", "scene", "script",
"radio", "news", "reporter", "camera", "lens", "flash", "film", "roll", "studio", "stage",
"ticket", "seat", "audience", "crowd", "applause", "curtain", "costume", "mask", "mirror", "shadow",
"river", "lake", "ocean", "island", "forest", "desert", "valley", "peak", "cliff", "cave",
"farm", "field", "crop", "harvest", "barn", "tractor", "tool", "hammer", "nail", "screw",
"building", "tower", "bridge", "tunnel", "station", "platform", "track", "signal", "bell", "whistle"