import random
import requests
from typing import Dict, List, Tuple, Optional

from constants.output import LOG_FILENAME, OUTPUT_FOLDER
from logger import translation_logger
from scrapper_config import CONFIG


logger = translation_logger.get_logger(
    output_folder=OUTPUT_FOLDER,
    log_filename=LOG_FILENAME
)

# AUTO-REFRESH PROXIES (always fresh!)
def load_fresh_proxies() -> List[Dict]:
    """Fetches fresh elite/anonymous HTTP proxies from ProxyScrape"""
    if CONFIG["proxy_rotation"] is False:
        return []
    url = (
        "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc"
    )
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()     
        proxies = []
        for line in resp.text.strip().splitlines():
            if line.strip():
                ip_port = line.strip()
                proxies.append({"server": f"http://{ip_port}"})
        logger.info(f"Loaded {len(proxies)} fresh proxies")
        return proxies
    except Exception as e:
        logger.error(f"Failed to load proxies: {e}. Running without proxies.")
        return []

# Load proxies once at startup
PROXIES = load_fresh_proxies()

def get_proxy() -> Optional[Dict]:
    if not CONFIG["proxy_rotation"] or not PROXIES:
        return None
    return PROXIES[random.randint(0, len(PROXIES))]
