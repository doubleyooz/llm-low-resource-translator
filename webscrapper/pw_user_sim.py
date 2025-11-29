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
        logger.debug(f"Action '{description}' performed successfully.")
        get_random_delay(delay_range)
        return True
    except Exception as e:
        logger.warning(f"Action '{description}' failed: {e}")
        if raise_exception:
            raise
        return False
    
def _simulate_scrolling(page: Page, msg: str = "") -> None:
    """Simulate realistic scrolling behavior."""
    try:
        # Get page dimensions
        scroll_height = page.evaluate("document.documentElement.scrollHeight")
        viewport_height = page.evaluate("window.innerHeight")
        max_scroll = max(0, scroll_height - viewport_height)
        
        if max_scroll < 100:
            logger.debug(f"{msg} | No scrollable content")
            return
        
        # Determine target scroll position (as percentage of max scroll)
        scroll_percentage_range = CONFIG.get("scroll_percentage_range", (0.3, 0.7))
        target_percentage = random.uniform(*scroll_percentage_range)
        target_scroll = target_percentage * max_scroll
                    
        current_scroll = page.evaluate("window.pageYOffset")
        iterations = 0
        max_iterations = CONFIG.get("max_scroll_iterations", 50)
        
        logger.debug(f"{msg} | Entering scrolling loop")
        
        while (abs(current_scroll - target_scroll) > 100 and iterations < max_iterations):
                 
            # Determine scroll amount (don't overshoot)
            scroll_pixel_range = CONFIG.get("scroll_pixel_range", (100, 300))
            scroll_amount = random.randint(*scroll_pixel_range)
            
          
            # Calculate remaining distance
            remaining = target_scroll - current_scroll
       
            logger.debug(f"{msg} | Remaining scroll: {remaining:.0f}px, initial scroll amount: {scroll_amount}px")
            # If we're close to target, reduce scroll amount
            if abs(remaining) < scroll_amount:
                scroll_amount = int((abs(remaining) * 0.8) * (1 if remaining > 0 else -1))
            else:
                scroll_amount = scroll_amount if remaining > 0 else -scroll_amount
           
            # Occasionally scroll back up
            if ((random.random() < CONFIG["scroll_back_probability"] and 
                current_scroll > scroll_amount) or current_scroll > target_scroll):
                scroll_amount = -scroll_amount
            
            perform_action(
                    lambda: page.evaluate(f"window.scrollBy(0, {scroll_amount})"),
                    f"{msg} | scrolling by {scroll_amount}px. {current_scroll:.0f}px → {target_scroll:.0f}px",
                    CONFIG["scroll_delay_range"]
                )
            current_scroll += scroll_amount

            iterations += 1
            
            logger.debug(f"{msg} | Scroll iteration {iterations}: {current_scroll:.0f}px")
            
            # Random mouse movements during scrolling
            _random_mouse_movement(page, msg)
        logger.debug(f"{msg} | Finishing simulating scrolling...")        
    except Exception as e:
        logger.debug(f"{msg} Scrolling simulation failed: {e}")

def _random_mouse_movement(page: Page, msg: str = "") -> None:
    """Perform random mouse movement within viewport."""
    perform_action(
        lambda: page.mouse.move(
            random.randint(*CONFIG["mouse_move_range_x"]),
            random.randint(*CONFIG["mouse_move_range_y"]),
            steps=random.randint(5, 15)
        ),
        f"{msg} | random mouse movement",
        CONFIG["scroll_delay_range"]
    )
    

def _click_element(element: Locator, msg: str = "", hover: bool = False, raise_exception: bool = False) -> bool:
        """Click an element with realistic delay."""
        try:
            if isinstance(element, list):
                if len(element) == 0:
                    logger.warning(f"{msg} | Empty element list provided")
                    raise ValueError("Empty element list")
                element = element[0]  # Use first element from list
                logger.debug(f"{msg} | Using first element from list ({len(element)} elements total)")

                
            element_description = (
                element.get_attribute('aria-label') or 
                element.get_attribute('title') or 
                element.text_content()[:50] or 'unknown element'
            )
            
            if hover:
                perform_action(
                    lambda: element.hover(),
                    f"{msg} | hover: {element_description}",
                    CONFIG["scroll_delay_range"],
                    raise_exception
                )
            
            return perform_action(
                lambda: element.click(delay=random.uniform(100, 300)),
                f"{msg} | click: {element_description}",
                CONFIG["button_delay_range"],
                raise_exception
            )
        except Exception as e:
            logger.warning(f"{msg} | Click failed: {e}")
            if raise_exception:
                raise e
            return False


def simulate_human(page: Page, selectors: list[str] = [], number_of_clicks: int = 1, button_click_probability: float = CONFIG["button_click_probability"], msg: str = "") -> None:
    # Light human simulation: scroll + mouse move.
    try:
        logger.debug(f"{msg} | Simulating human behaviour...")
        _simulate_scrolling(page, msg)
              
        for _ in range(number_of_clicks):
            
            # Random mouse wandering (very important for anti-bot)
            if(random.random() < button_click_probability / 2):
                logger.debug(f"{msg} | Preparing wandering before click...")
                for _ in range(random.randint(1,3)):
                    perform_action(
                        lambda: page.mouse.move(
                            random.randint(*CONFIG["mouse_move_range_x"]),
                            random.randint(*CONFIG["mouse_move_range_y"]),
                            steps=random.randint(15, 30)
                        ),
                        f"{msg} | mouse wander"
                    )
                
            # Randomly decide whether to click (20% chance per page visit)
            if random.random() <= button_click_probability:
                logger.debug(f"{msg} | Simulating random button click...")
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
                                f"{msg} | hover before click",
                                CONFIG["scroll_delay_range"]
                            )
                        
                    except:
                        pass
                    
                    _click_element(target_button, msg)      
                else:
                    logger.debug(f"{msg} | No clickable elements found for selectors: {selectors}")        

              
    except Exception as e:
        logger.debug(f"{msg} | Human sim failed: {e}")
    finally:
        # Small pause after interaction
        get_random_delay(CONFIG["interaction_delay_range"])


