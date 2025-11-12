import csv
import json
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional

import pandas as pd
from playwright.sync_api import sync_playwright, Page, BrowserContext
from config import CONFIG
from user_agents import USER_AGENTS

'''
Translator for French to English using Google Translate via Playwright.
Translates sentences from a Parquet dataset and saves results in CSV and JSON formats.
'''


# Language codes
SL = "fr"   # Source language
TL = "en"   # Target language (English)
OL = "br"   # Original language (Breton)

# -------------------------------
# Logging
# -------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

SAFE_CLICK_SELECTORS = [
    "button[aria-label='Stop Listening']",
    "button[aria-label='Copy Translation']",
]

# -------------------------------
# Helpers
# -------------------------------
def get_random_delay(delay_range: Tuple[float, float]) -> None:
    time.sleep(random.uniform(*delay_range))

def perform_action(page: Page, action: callable, name: str, delay_range=None):
    delay_range = delay_range or CONFIG["interaction_delay_range"]
    try:
        action()
        get_random_delay(delay_range)
    except Exception as e:
        logger.warning(f"[{name}] failed: {e}")

def simulate_human(page: Page):
    """Light human simulation: scroll + mouse move."""
    try:
        height = page.evaluate("document.body.scrollHeight")
        target = height * 0.6
        pos = 0
        it = 0
        while pos < target and it < CONFIG["max_scroll_iterations"]:
            delta = random.randint(*CONFIG["scroll_amount_range"])
            if random.random() < CONFIG["scroll_back_probability"]:
                delta = -delta
            page.evaluate(f"window.scrollBy(0, {delta})")
            pos += abs(delta)
            it += 1

            perform_action(
                page,
                lambda: page.mouse.move(
                    random.randint(*CONFIG["mouse_move_range_x"]),
                    random.randint(*CONFIG["mouse_move_range_y"])
                ),
                "mouse move",
                CONFIG["scroll_delay_range"]
            )
     

        # Randomly decide whether to click (30% chance per page visit)
        if random.random() < 0.3:
            logger.debug("Simulating random button click...")
            # Filter only visible & enabled buttons
            clickable = []
            for sel in SAFE_CLICK_SELECTORS:
                try:
                    el = page.locator(sel).first
                    if el.is_visible() and el.is_enabled():
                        clickable.append(el)
                except:
                    continue

            if clickable:
                button = random.choice(clickable)
                perform_action(
                    page,
                    lambda: button.click(delay=random.uniform(80, 200)),
                    f"click random button: {button.get_attribute('aria-label') or 'unknown'}",
                    CONFIG["interaction_delay_range"]
                )
                logger.debug(f"Clicked random UI: {button.get_attribute('aria-label')}")
                # Small pause after click
                get_random_delay(CONFIG["button_delay_range"])
    except Exception as e:
        logger.debug(f"Human sim failed: {e}")

def get_proxy(batch_idx: int) -> Optional[Dict]:
    if not CONFIG["proxy_rotation"] or not PROXIES:
        return None
    return PROXIES[batch_idx % len(PROXIES)]

# -------------------------------
# Translation Core
# -------------------------------
def translate_sentence(page: Page, sentence: str) -> str:
    """Translate one sentence using Google Translate."""
    encoded = sentence.replace(" ", "%20")
    url = f"https://translate.google.com/?sl={SL}&tl={TL}&text={encoded}&op=translate"

    for attempt in range(CONFIG["retry_attempts"]):
        try:
            perform_action(page, lambda: page.goto(url, timeout=CONFIG["page_timeout_ms"]), "goto")
            perform_action(page, lambda: page.wait_for_selector("span[jsname='W297wb']", timeout=15000), "wait result")

            # Optional: light scroll to trigger lazy load
            simulate_human(page)

            result = page.locator("span[jsname='W297wb']").first
            text = result.inner_text().strip()

            if text and text != sentence:
                logger.debug(f"Translated: {sentence[:30]}... → {text[:30]}...")
                return text
            else:
                raise ValueError("Empty or same-as-input translation")

        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed for '{sentence[:40]}...': {e}")
            if attempt < CONFIG["retry_attempts"] - 1:
                get_random_delay(CONFIG["retry_delay_range"])
            else:
                return "[TRANSLATION FAILED]"

    return "[TRANSLATION FAILED]"

# -------------------------------
# Worker: Process One Batch
# -------------------------------
def process_batch(sentence_pairs: Tuple[List[str], List[str]], batch_idx: int) -> List[Dict]:
    results = []
    proxy = get_proxy(batch_idx)

    with sync_playwright() as p:
        browser_args = {
            "headless": False,
          # "args": ["--no-sandbox", "--disable-setuid-sandbox"]
        }
        if proxy:
            browser_args["proxy"] = proxy

        browser = p.chromium.launch(**browser_args)
        context: BrowserContext = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={
                "width": random.randint(1366, 1920),
                "height": random.randint(768, 1080)
            },
            locale="en-US",
            java_script_enabled=True,
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "DNT": "1",  # Do Not Track
                "Upgrade-Insecure-Requests": "1",
            },
        )

        page = context.new_page()

        logger.info(f"Batch {batch_idx + 1} | Proxy: {proxy['server'] if proxy else 'None'} | {len(sentence_pairs)} sentences")

        for pair in sentence_pairs:
            try:
                logger.info(f"Batch {batch_idx + 1} | Translating: {pair[0][:50]}...")
                translation = translate_sentence(page, pair[0])
                results.append({    
                    f"{SL}": pair[0],
                    f"{TL}": translation,
                    f"{OL}": pair[1]
                })
                # Random delay between requests
                get_random_delay(CONFIG["interaction_delay_range"])
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                results.append({f"{SL}": pair[0], f"{TL}": "[ERROR]", f"{OL}": pair[1]})

        context.close()
        browser.close()

    return results

# -------------------------------
# Main
# -------------------------------
def main():
    # Load dataset
    try:
        df = pd.read_parquet("hf://datasets/Bretagne/UD_Breton-KEB_translation/data/train-00000-of-00001.parquet")
        logger.info(df.info())
        logger.info(df.head(2))
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        return
    list_of_rows = df.values.tolist()
   
    french_sentences = df[SL].dropna().tolist()
    breton_sentences = df[OL].dropna().tolist()
    if not french_sentences:
        logger.error("No French sentences found.")
        return
    logger.info(f"French sentences length: {len(french_sentences)}")
    print(french_sentences[0])
    logger.info(f"Loaded {len(french_sentences):,} French sentences. Starting translation...")

    # Optional: test with subset
    french_sentences = french_sentences[:50]
    breton_sentences = breton_sentences[:50]
    
    # Merge the lists using zip()
    merged_iterator = zip(french_sentences, breton_sentences)

    # Convert the iterator to a list of tuples
    merged_list_of_tuples = list(merged_iterator)
    
    # Split into batches
    batch_size = CONFIG["batch_size"]
    batches = [merged_list_of_tuples[i:i + batch_size] for i in range(0, len(merged_list_of_tuples), batch_size)]

    all_results = []

    with ThreadPoolExecutor(max_workers=CONFIG["max_workers"]) as executor:
        futures = {
            executor.submit(process_batch, batch, idx): idx
            for idx, batch in enumerate(batches)
        }

        for future in as_completed(futures):
            batch_idx = futures[future]
            try:
                batch_results = future.result()
                all_results.extend(batch_results)
                logger.info(f"Batch {batch_idx + 1}/{len(batches)} completed.")
            except Exception as e:
                logger.error(f"Batch {batch_idx + 1} failed: {e}")

    # Save CSV
    csv_file = f"{SL}_{TL}_{OL}_parallel.csv"
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[SL, TL, OL])
        writer.writeheader()
        writer.writerows(all_results)

    # Save JSON
    json_file = f"{SL}_{TL}_{OL}_parallel.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    logger.info(f"Translation complete! Saved to {csv_file} and {json_file}")
    logger.info(f"Success rate: {sum(1 for r in all_results if not r[TL].startswith('[')) / len(all_results):.1%}")

if __name__ == "__main__":
    main()