import csv
import json
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional

import pandas as pd
from playwright.sync_api import sync_playwright, Page, BrowserContext
from scrapper_config import CONFIG
from scrapper_google_translate import get_url, translate_sentence
from pw_proxies import get_proxy
from pw_user_agents import USER_AGENTS
from pw_user_sim import get_random_delay, perform_action

'''
Translator for French to English using Google Translate via Playwright.
Translates sentences from a Parquet dataset and saves results in CSV and JSON formats.
'''

OUTPUT_FOLDER = "output"

# Language codes
SL = "fr"   # Source language (French)
TL = "en"   # Target language (English)
OL = "br"   # Original language (Breton)


# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Worker: Process One Batch
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
        perform_action(lambda: page.goto(get_url(SL, TL), timeout=CONFIG["page_timeout_ms"]), "goto")
        
        for i, pair in enumerate(sentence_pairs):
            try:
                logger.info(f"Batch {batch_idx + 1} | Translating {i + 1}/{len(sentence_pairs)}: {pair[0][:50]}...")
                translation = translate_sentence(page, pair[0], batch_idx + 1)
                results.append({    
                    f"{SL}": pair[0],
                    f"{TL}": translation,
                    f"{OL}": pair[1]
                })

            except Exception as e:
                logger.error(f"Batch {batch_idx + 1} | Unexpected error: {e}")
                results.append({f"{SL}": pair[0], f"{TL}": "[ERROR]", f"{OL}": pair[1]})
            finally:
                # Random delay between requests
                get_random_delay(CONFIG["new_request_delay_range"])
        context.close()
        browser.close()

    return results

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
   
    sl_sentences = df[SL].dropna().tolist()
    ol_sentences = df[OL].dropna().tolist()
    if not sl_sentences:
        logger.error(f"No {SL.upper()} sentences found.")
        return
    logger.info(f"{SL.upper()} sentences length: {len(sl_sentences)}")
    print(sl_sentences[0])
    logger.info(f"Loaded {len(sl_sentences):,} {SL.upper()} sentences. Starting translation...")
    # Optional: test with subset
    # sl_sentences = sl_sentences[:50]
    # ol_sentences = ol_sentences[:50]
    
    # Merge the lists using zip()
    merged_iterator = zip(sl_sentences, ol_sentences)

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
            completed = batch_idx + 1
            try:
                batch_results = future.result()
                all_results.extend(batch_results)
                logger.info(f"Batch {completed}/{len(batches)} completed.")
            except Exception as e:
                logger.error(f"Batch {completed} failed: {e}")
                
            # Random delay between batches
            if completed < len(batches):
                logger.info(f"{completed}/{len(batches)} Sleeping before next batch...")          
                
                get_random_delay(*CONFIG["new_batch_delay_range"], fatigue=1 + (completed / len(batches)) * 3)         

    # Save CSV
    csv_file = f"{OUTPUT_FOLDER}/{SL}_{TL}_{OL}_parallel.csv"
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[SL, TL, OL])
        writer.writeheader()
        writer.writerows(all_results)

    # Save JSON
    json_file = f"{OUTPUT_FOLDER}/{SL}_{TL}_{OL}_parallel.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    logger.info(f"Translation complete! Saved to {csv_file} and {json_file}")
    logger.info(f"Success rate: {sum(1 for r in all_results if not r[TL].startswith('[')) / len(all_results):.1%}")

if __name__ == "__main__":
    main()