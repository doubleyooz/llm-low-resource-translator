import logging
import random
import time
from typing import Dict, List, Tuple, Optional
from playwright.sync_api import sync_playwright, Page, BrowserContext
from scrapper_config import CONFIG

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def get_random_delay(delay_range: Tuple[float, float], fatigue: float = 1) -> None:
    if fatigue < 1:
        fatigue = 1
    delay = random.uniform(*delay_range) * fatigue
    time.sleep(delay)
    if fatigue > 1:
        logger.info(f"Sleeping {delay:.1f}s (fatigue mode)") 

def perform_action(action: callable, name: str, delay_range: Tuple[float, float] = CONFIG["interaction_delay_range"]):
    try:
        action()
        get_random_delay(delay_range)
    except Exception as e:
        logger.warning(f"[{name}] failed: {e}")

def simulate_human(page: Page, selectors: list[str] = [], max_scroll_iterations: int = CONFIG["max_scroll_iterations"]) -> None:
    # Light human simulation: scroll + mouse move.
    try:
        height = page.evaluate("document.body.scrollHeight")
        target = height * 0.6
        pos = 0
        it = 0
        while pos < target and it < max_scroll_iterations:
            delta = random.randint(*CONFIG["scroll_amount_range"])
            if random.random() < CONFIG["scroll_back_probability"]:
                delta = -delta
            page.evaluate(f"window.scrollBy(0, {delta})")
            pos += abs(delta)
            it += 1

            perform_action(
                lambda: page.mouse.move(
                    random.randint(*CONFIG["mouse_move_range_x"]),
                    random.randint(*CONFIG["mouse_move_range_y"])
                ),
                "mouse move",
                CONFIG["scroll_delay_range"]
            )
     
        # Random mouse wandering (very important for anti-bot)
        if(random.random() < CONFIG["button_click_probability"] / 2):
            for _ in range(random.randint(*CONFIG["button_delay_range"])):
                perform_action(
                    lambda: page.mouse.move(
                        random.randint(*CONFIG["mouse_move_range_x"]),
                        random.randint(*CONFIG["mouse_move_range_y"]),
                        steps=random.randint(15, 30)
                    ),
                    "mouse wander"
                )
             
        # Randomly decide whether to click (20% chance per page visit)
        if random.random() < CONFIG["button_click_probability"]:
            logger.debug("Simulating random button click...")
            # Filter only visible & enabled buttons
            clickable = []
            for sel in selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible() and el.is_enabled():
                        clickable.append(el)
                except:
                    continue
            if clickable:
                target_button = random.choice(clickable)
                
                # Critical: hover before click (humans always hover)
                try:
                    box = target_button.bounding_box()
                    if box:
                        perform_action(        
                            lambda: page.mouse.move(
                                box["x"] + box["width"] / 2 + random.randint(-10, 10),
                                box["y"] + box["height"] / 2 + random.randint(-10, 10),
                                steps=random.randint(12, 22)
                            ),
                            "hover before click",
                            CONFIG["scroll_delay_range"]
                        )
                    
                except:
                    pass
                
                perform_action(
                    lambda: target_button.click(delay=random.uniform(**CONFIG["button_delay_range"])),
                    f"click random button: {target_button.get_attribute('aria-label') or 'unknown'}",
                    CONFIG["button_delay_range"]
                )
                logger.debug(f"Clicked random UI: {target_button.get_attribute('aria-label')}")
               
              
    except Exception as e:
        logger.debug(f"Human sim failed: {e}")
    finally:
        # Small pause after interaction
        get_random_delay(CONFIG["interaction_delay_range"])


