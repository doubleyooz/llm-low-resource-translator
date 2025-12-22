import random
from playwright.sync_api import sync_playwright, Page, BrowserContext, Locator
from constants.output import OUTPUT_FOLDER, LOG_FILENAME
from scrapper_config import CONFIG

from logger import translation_logger
from utils.pw_helper import get_random_delay, random_mouse_movement, perform_action, click_element


logger = translation_logger.get_logger(
    output_folder=OUTPUT_FOLDER,
    log_filename=LOG_FILENAME
)

    
def _simulate_scrolling(page: Page, msg: str = "") -> None:
    """Simulate realistic scrolling behavior."""
    try:
        # Get page dimensions
        scroll_height = page.evaluate("document.documentElement.scrollHeight")
        viewport_height = page.evaluate("window.innerHeight")
        max_scroll = max(0, scroll_height - viewport_height)
        
        if max_scroll < 100:
            logger.debug(f"{msg} No scrollable content")
            return
        
        # Determine target scroll position (as percentage of max scroll)
        scroll_percentage_range = CONFIG.get("scroll_percentage_range", (0.3, 0.7))
        target_percentage = random.uniform(*scroll_percentage_range)
        target_scroll = target_percentage * max_scroll
                    
        current_scroll = page.evaluate("window.pageYOffset")
        iterations = 0
        max_iterations = CONFIG.get("max_scroll_iterations", 50)
        
        logger.debug(f"{msg} Entering scrolling loop")
        
        while (abs(current_scroll - target_scroll) > 100 and iterations < max_iterations):
                 
            # Calculate remaining distance
            remaining = target_scroll - current_scroll       
                 
            upper_bound = int(max(300, remaining / 3))
            
            # Determine scroll amount (don't overshoot)
            scroll_amount = random.randint(100, upper_bound)
            
          
         
            logger.debug(f"{msg} Remaining scroll: {remaining:.0f}px, initial scroll amount: {scroll_amount}px")
            # If we're close to target, reduce scroll amount
            if abs(remaining) < scroll_amount:
                scroll_amount = int((abs(remaining) * 0.8) * (1 if remaining > 0 else -1))
            else:
                scroll_amount = scroll_amount if remaining > 0 else -scroll_amount
           
            # Occasionally scroll back on the opposite direction
            if (random.random() < CONFIG["scroll_back_probability"] and 
                current_scroll > scroll_amount) or current_scroll > target_scroll:
                scroll_amount = -scroll_amount
            
            # If the target_scroll is negative and scroll_amount is positive, let's invert the scroll_amount sign to shorten the distance
            elif scroll_amount > 0 and 0 > target_scroll:
                scroll_amount = -scroll_amount
                
            perform_action(
                    action=lambda: page.evaluate(f"window.scrollBy(0, {scroll_amount})"),
                    description=f"scrolling by {scroll_amount}px. {current_scroll:.0f}px → {target_scroll:.0f}px",
                    delay_range=CONFIG["scroll_delay_range"],
                    msg=msg
                )
            current_scroll += scroll_amount

            iterations += 1
            
            logger.debug(f"{msg} Scroll iteration {iterations}: {current_scroll:.0f}px")
            
            # Random mouse movements during scrolling
            random_mouse_movement(page, msg)
        logger.debug(f"{msg} Finishing simulating scrolling...")        
    except Exception as e:
        logger.debug(f"{msg} Scrolling simulation failed: {e}")

    
def simulate_human(page: Page, selectors: list[str] = [], number_of_clicks: int = 1, button_click_probability: float = CONFIG["button_click_probability"], msg: str = "") -> None:
    # Light human simulation: scroll + mouse move.
    try:
        logger.info(f"{msg} Simulating human behaviour...")
        _simulate_scrolling(page, msg)
              
        for _ in range(number_of_clicks):
            
            # Random mouse wandering (very important for anti-bot)
            if(random.random() < button_click_probability / 2):
                logger.debug(f"{msg} Preparing wandering before click...")
                for _ in range(random.randint(1,3)):
                    perform_action(
                        action=lambda: page.mouse.move(
                            random.randint(*CONFIG["mouse_move_range_x"]),
                            random.randint(*CONFIG["mouse_move_range_y"]),
                            steps=random.randint(15, 30)
                        ),
                        description="mouse wander",
                        msg=msg
                    )
                
            # Randomly decide whether to click (20% chance per page visit)
            if random.random() <= button_click_probability:
                logger.debug(f"{msg} Simulating random button click...")
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
                                action=lambda: page.mouse.move(
                                    box["x"] + box["width"] / 2 + random.randint(-10, 10),
                                    box["y"] + box["height"] / 2 + random.randint(-10, 10),
                                    steps=random.randint(12, 22)
                                ),
                                description="hover before click",
                                delay_range=CONFIG["scroll_delay_range"],
                                msg=msg
                            )
                        
                    except:
                        pass
                    
                    click_element(target_button, msg)      
                else:
                    logger.debug(f"{msg} No clickable elements found for selectors: {selectors}")        

              
    except Exception as e:
        logger.debug(f"{msg} Human sim failed: {e}")
    finally:
        # Small pause after interaction
        get_random_delay(CONFIG["interaction_delay_range"])


