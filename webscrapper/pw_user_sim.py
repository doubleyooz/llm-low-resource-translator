import logging
import random
import time
from typing import Dict, List, Tuple, Optional
from playwright.sync_api import sync_playwright, Page, BrowserContext, Locator
from scrapper_config import CONFIG

from logger import translation_logger

logger = translation_logger.get_logger()

def set_fatigue(fatigue: float = 1):
    return max(1.0, fatigue)
    

def get_random_delay(delay_range: Tuple[float, float], fatigue: float = 1, msg: str = "") -> None:
    if not delay_range or len(delay_range) != 2:
        delay_range = CONFIG["interaction_delay_range"]

    delay = random.uniform(*delay_range) * set_fatigue(fatigue)
    time.sleep(delay)
    
    if fatigue > 1:
        logger.info(f"{msg} | Sleeping {delay:.1f}s (fatigue mode)") 

def perform_action(action: callable, description: str, delay_range: Tuple[float, float] = CONFIG["interaction_delay_range"], 
        raise_exception: bool = False) -> bool:
    try:
        action()
        get_random_delay(delay_range)
        return True
    except Exception as e:
        logger.warning(f"Action '{description}' failed: {e}")
        if raise_exception:
            raise
        return False
    
def _simulate_scrolling(page: Page) -> None:
    """Simulate realistic scrolling behavior."""
    try:
        scroll_height = page.evaluate("document.body.scrollHeight")
        viewport_height = page.evaluate("window.innerHeight")
        max_scroll = max(0, scroll_height - viewport_height)
        
        if max_scroll == 0:
            return
            
        # Scroll to a random position (60-80% down the page)
        target_scroll = random.uniform(*CONFIG["scroll_amount_range"] or (0.6, 0.8)) * max_scroll
        current_scroll = 0
        iterations = 0
        
        while (current_scroll < target_scroll and 
                iterations < CONFIG["max_scroll_iterations"]):
            
            scroll_amount = random.randint(*CONFIG["scroll_amount_range"])
            
            # Occasionally scroll back up
            if (random.random() < CONFIG["scroll_back_probability"] and 
                current_scroll > scroll_amount):
                scroll_amount = -scroll_amount
            
            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            current_scroll = max(0, page.evaluate("window.pageYOffset"))
            iterations += 1
            
            # Random mouse movements during scrolling
            _random_mouse_movement(page)
            
    except Exception as e:
        logger.debug(f"Scrolling simulation failed: {e}")

def _random_mouse_movement(page: Page) -> None:
    """Perform random mouse movement within viewport."""
    perform_action(
        lambda: page.mouse.move(
            random.randint(*CONFIG["mouse_move_range_x"]),
            random.randint(*CONFIG["mouse_move_range_y"]),
            steps=random.randint(5, 15)
        ),
        "random mouse movement",
        CONFIG["scroll_delay_range"]
    )

def _click_element(element: Locator) -> bool:
        """Click an element with realistic delay."""
        try:
            element_description = (
                element.get_attribute('aria-label') or 
                element.get_attribute('title') or 
                element.text_content()[:50] or 'unknown element'
            )
            
            return perform_action(
                lambda: element.click(delay=random.uniform(100, 300)),
                f"click: {element_description}",
                CONFIG["button_delay_range"]
            )
        except Exception as e:
            logger.debug(f"Click failed: {e}")
            return False


def simulate_human(page: Page, selectors: list[str] = [], number_of_clicks: int = 1, button_click_probability: float = CONFIG["button_click_probability"]) -> None:
    # Light human simulation: scroll + mouse move.
    try:
        _simulate_scrolling(page)
                        
        for _ in range(number_of_clicks):
            # Random mouse wandering (very important for anti-bot)
            if(random.random() < button_click_probability / 2):
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
            if random.random() < button_click_probability:
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
                    
                    _click_element(target_button)              

              
    except Exception as e:
        logger.debug(f"Human sim failed: {e}")
    finally:
        # Small pause after interaction
        get_random_delay(CONFIG["interaction_delay_range"])


