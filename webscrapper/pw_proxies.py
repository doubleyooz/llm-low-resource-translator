import logging
import requests
from typing import Dict, List, Tuple, Optional


from scrapper_config import CONFIG


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# AUTO-REFRESH PROXIES (always fresh!)
# -------------------------------
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

def get_proxy(batch_idx: int) -> Optional[Dict]:
    if not CONFIG["proxy_rotation"] or not PROXIES:
        return None
    return PROXIES[batch_idx % len(PROXIES)]
