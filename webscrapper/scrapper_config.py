# Configuration
CONFIG = {
    "page_timeout_ms": 100000,  # Page load timeout
    "scroll_delay_range": (0.1, 1.1), # Delay range for scrolling
    "interaction_delay_range": (2, 6), # Delay range for interactions
    "new_request_delay_range": (3, 15),  # Delay range between requests
    "retry_attempts": 2,       # Retry attempts for failed requests
    "retry_delay_range": (4, 16),  # Delay range between retries
    "new_batch_delay_range": (60, 180),  # Delay range between batches
    "scroll_amount_range": (20, 400),  # Range for scroll amount
    "scroll_back_probability": 0.3,    # Probability of scrolling backward
    "min_batch_interval": 1,  # Minimum interval between requests
    "max_batch_interval": 8,  # Maximum interval between requests

    "mouse_move_range_x": (-300, 800),  # X-coordinate range for mouse movement
    "mouse_move_range_y": (-100, 700),  # Y-coordinate range for mouse movement
  
    "max_scroll_iterations": 39,     # Prevent infinite scroll loops
    "max_workers": 20,                    # Concurrent translation workers
    "batch_size": 6,                    # Sentences per context (proxy switch)    
    "sentences_per_request_range": (1, 1),         # Sentences per translation request
    "proxy_rotation": False,    
    
    # get_bible_versions.py specific
    "scroll_limit": 0.7,  # Scroll limit as a fraction of total height

    # scrapper_google_translate.py specific
    "safe_button_click_probability": 0.3,  # Probability of clicking safe buttons
    "unsafe_button_click_probability": 0.2,  # Probability of clicking unsafe buttons
    "double_button_click_probability": 0.12,  # Probability of double clicking buttons
    
    # translator_maitre.py specific   
    "button_click_probability": 0.7,  # Probability of clicking a button
    "button_delay_range": (0.5, 2), # Delay range for interactions
}