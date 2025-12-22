from typing import Any, Dict, List, Tuple
from playwright.sync_api import sync_playwright, Page

from exceptions.not_found_exception import NotFoundException
from constants.languages import SL, TL
from constants.output import LOG_FILENAME, OUTPUT_FOLDER
from scrapper_config import CONFIG

from utils.pw_helper import click_element, perform_action, get_random_delay
from pw_user_sim import simulate_human

# Import the singleton logger
from logger import translation_logger

logger = translation_logger.get_logger(
    output_folder=OUTPUT_FOLDER,
    log_filename=LOG_FILENAME
)


wordbank =   [
    "accept", "refuse", "offer", "decline", "choose", "pick", "select", "avoid", "ignore", "notice",
    "observe", "examine", "check", "inspect", "measure", "count", "calculate", "estimate", "guess", "predict",
    "plan", "organize", "prepare", "arrange", "schedule", "cancel", "postpone", "delay", "advance", "move",
    "transfer", "shift", "replace", "remove", "add", "subtract", "multiply", "divide", "share", "split",
    "join", "connect", "attach", "detach", "fasten", "tie", "untie", "wrap", "unwrap", "pack",
    "unpack", "load", "unload", "ship", "deliver", "order", "request", "demand", "beg", "plead",
    "persuade", "convince", "encourage", "discourage", "motivate", "inspire", "comfort", "console", "cheer", "celebrate",
    "mourn", "grieve", "regret", "elder", "blame", "accuse", "defend", "protect", "attack", "fight", "surrender",
    "win", "lose", "compete", "race", "bet", "gamble", "risk", "dare", "challenge", "provoke",
    "calm", "relax", "tense", "excite", "bore", "amuse", "entertain", "surprise", "shock", "disappoint",
    "impress", "attract", "repel", "charm", "flirt", "date", "marry", "divorce", "separate", "reunite",
    "gather", "scatter", "collect", "jet", "distribute", "spread", "cover", "uncover", "reveal", "hide", "seek",
    "discover", "invent", "create", "destroy", "repair", "damage", "hurt", "heal", "cure", "treat",
    "diagnose", "operate", "inject", "prescribe", "swallow", "chew", "bite", "taste", "sip", "gulp",
    "pour", "fill", "empty", "mix", "stir", "bake", "fry", "boil", "grill", "roast",
    "slice", "chop", "peel", "grate", "blend", "freeze", "thaw", "preserve", "spoil", "waste",
    "recycle", "reuse", "reduce", "consume", "produce", "manufacture", "assemble", "disassemble", "test", "experiment",
    "research", "analyze", "compare", "contrast", "evaluate", "judge", "decide", "vote", "elect", "appoint",
    "resign", "retire", "promote", "demote", "hire", "fire", "train", "coach", "guide", "direct",
    "instruct", "demonstrate", "perform", "act", "rehearse", "record", "edit", "publish", "broadcast", "stream",
    "download", "upload", "click", "type", "scroll", "zoom", "refresh", "save", "delete", "block",
    "report", "complain", "praise", "criticize", "review", "rate", "comment", "reply", "forward", "quote",
    "ask", "tell", "say", "talk", "call", "answer", "explain", "describe", "discuss", "argue",
    "agree", "disagree", "promise", "lie", "jew", "admit", "deny", "suggest", "recommend", "advise",
    "warn", "remind", "invite", "tank", "thank", "apologize", "forgive", "compliment", "insult", "joke", "tease",
    "buy", "sell", "pay", "spend", "save", "borrow", "lend", "steal", "find", "lose",
    "give", "take", "receive", "send", "bring", "carry", "hold", "drop", "throw", "catch",
    "push", "pull", "lift", "turn", "twist", "bend", "stretch", "shake", "wave", "clap",
    "kick", "hit", "punch", "bite", "scratch", "hug", "kiss", "stroke", "pat", "rub",
    "wait", "hurry", "rush", "arrive", "leave", "enter", "exit", "follow", "lead", "chase",
    "hide", "search", "look", "stare", "glance", "blink", "nod", "shake", "point", "gesture",
    "sit", "stand", "lie", "kneel", "crouch", "lean", "climb", "fall", "rise", "hang",
    "start", "stop", "begin", "end", "continue", "pause", "repeat", "try", "succeed", "fail"



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

# Translation Core
def translate_sentence(page: Page, sentence: str, batch_idx: int) -> str:
    """Translate one sentence using Google Translate."""
    batch_msg = f"Batch {batch_idx}" 
    
    # Replace double quotes with single quotes to avoid issues
    sentence = sentence.replace('"', "'")

    # Optional: light scroll to trigger lazy load
    simulate_human(page=page, msg=batch_msg)
    
    set_input(page, sentence, msg=batch_msg, logger=logger)
   
    logger.debug(f"{batch_msg} | Searching: {sentence}...")
    
    return get_output(logger=logger, page=page, msg=batch_msg)
    
def set_input(page: Page, sentence: str, msg: str = '') -> None:
 
   
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
    
def get_output(page: Page, msg: str = '') -> Tuple[List[str], List[str]]:
    buttons = page.locator(SAFE_CLICK_SELECTORS[0])
    attempts = 0
    max_attempts = 2
    while(attempts < max_attempts):
        logger.debug(f"{msg} | Attempt {attempts+1}/{max_attempts} {buttons.last.inner_text()}")
        click_element(buttons.last, msg)
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

'''
    "television", "screen", "remote", "channel", "movie", "actor", "actress", "director", "scene", "script",
    "radio", "news", "reporter", "camera", "lens", "flash", "film", "roll", "studio", "stage",
    "ticket", "seat", "audience", "crowd", "applause", "curtain", "costume", "mask", "mirror", "shadow",
    "river", "lake", "ocean", "island", "forest", "desert", "valley", "peak", "cliff", "cave",
    "farm", "field", "crop", "harvest", "barn", "tractor", "tool", "hammer", "nail", "screw",
    "building", "tower", "bridge", "tunnel", "station", "platform", "track", "signal", "bell", "whistle"
'''
