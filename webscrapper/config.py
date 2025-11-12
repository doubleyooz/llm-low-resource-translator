# Configuration
CONFIG = {
    "max_workers_versions": 4,  # Concurrent versions
    "max_workers_books": 5,    # Concurrent books per version
    "page_timeout_ms": 60000,  # Page load timeout
    "scroll_delay_range": (0.1, 2), # Delay range for scrolling
    "interaction_delay_range": (3, 10), # Delay range for interactions
    "button_delay_range": (1, 4), # Delay range for interactions
    "retry_attempts": 3,       # Retry attempts for failed requests
    "retry_delay_range": (5, 15),  # Delay range between retries
    "scroll_amount_range": (20, 400),  # Range for scroll amount
    "scroll_back_probability": 0.2,    # Probability of scrolling backward
    "scroll_limit": 0.7,  # Scroll limit as a fraction of total height
    "mouse_move_range_x": (-300, 800),  # X-coordinate range for mouse movement
    "mouse_move_range_y": (-100, 700),  # Y-coordinate range for mouse movement
    "search_action_probability": 0.3,  # Probability of performing search
    "profile_menu_probability": 0.4,   # Probability of interacting with profile menu
    "max_scroll_iterations": 50,     # Prevent infinite scroll loops
    "max_workers": 6,                    # Concurrent translation workers
    "batch_size": 10,                    # Sentences per context (proxy switch)    
    "proxy_rotation": False,         
}