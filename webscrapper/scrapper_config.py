# Configuration
CONFIG = {

    "page_timeout_ms": 100000,  # Page load timeout
    "scroll_delay_range": (0.1, 2), # Delay range for scrolling
    "interaction_delay_range": (3, 8), # Delay range for interactions
    "new_request_delay_range": (2, 10),  # Delay range between requests
    "retry_attempts": 10,       # Retry attempts for failed requests
    "retry_delay_range": (5, 15),  # Delay range between retries
    "new_batch_delay_range": (80, 150),  # Delay range between batches
    "scroll_amount_range": (20, 400),  # Range for scroll amount
    "scroll_back_probability": 0.2,    # Probability of scrolling backward
    
   
    "mouse_move_range_x": (-300, 800),  # X-coordinate range for mouse movement
    "mouse_move_range_y": (-100, 700),  # Y-coordinate range for mouse movement
  
    "max_scroll_iterations": 30,     # Prevent infinite scroll loops
    "max_workers": 2,                    # Concurrent translation workers
    "batch_size": 15,                    # Sentences per context (proxy switch)    
    "proxy_rotation": False,    
    
    # get_bible_versions.py specific
    "scroll_limit": 0.7,  # Scroll limit as a fraction of total height
    "search_action_probability": 0.3,  # Probability of performing search
    "profile_menu_probability": 0.4,   # Probability of interacting with profile menu
    "max_workers_versions": 4,  # Concurrent versions
    "max_workers_books": 5,    # Concurrent books per version
    
    
    # translator_maitre.py specific   
    "button_click_probability": 0.25,  # Probability of clicking a button
    "button_delay_range": (1, 4), # Delay range for interactions
}