import csv
from datetime import datetime
import json
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional
from threading import Lock

import pandas as pd

from playwright.sync_api import sync_playwright, Page, BrowserContext
from constants.output import OUTPUT_FOLDER
from constants.languages import SL, TL, OL
from scrapper_config import CONFIG
from scrapper_google_translate import get_url, translate_sentence
from pw_proxies import get_proxy
from pw_user_agents import USER_AGENTS
from pw_user_sim import get_random_delay, perform_action

# Import the singleton logger
from logger import translation_logger
'''
Translator for French to English using Google Translate via Playwright.
Translates sentences from a Parquet dataset and saves results in CSV and JSON formats.
'''


# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


logger = translation_logger.get_logger()

# Add global timing variables
last_batch_start_time = 0
batch_timing_lock = Lock()

MERGE_SYMBOL = "|||"  # Symbol to merge multiple sentences

def ensure_batch_interval(batch_idx: int):
    """Ensure minimum interval between batch starts"""
    global last_batch_start_time
    
    with batch_timing_lock:
        current_time = time.time()
        time_since_last_batch = current_time - last_batch_start_time
        
        if time_since_last_batch < CONFIG["min_batch_interval"]:
            wait_time = CONFIG["min_batch_interval"] - time_since_last_batch
            logger.info(f"Batch {batch_idx + 1} | Waiting {wait_time:.2f}s to maintain batch interval")
            time.sleep(wait_time)
        
        last_batch_start_time = time.time()


# Worker: Process One Batch
def process_batch(sentence_pairs: List[Tuple[str, str]], batch_idx: int) -> List[Dict]:
    ensure_batch_interval(batch_idx)
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
        current_batch = batch_idx + 1
        batch_msg = f"Batch {current_batch}"
        logger.info(f"{batch_msg} | Proxy: {proxy['server'] if proxy else 'None'} | {len(sentence_pairs)} sentences")
        perform_action(lambda: page.goto(get_url(SL, TL), timeout=CONFIG["page_timeout_ms"]), f"{batch_msg} | goto")
        
        extracted_list = [tup[0] for tup in sentence_pairs]
        logger.debug(f"{batch_msg} | Extracted_list: {len(extracted_list)} elements")
        chunked_sentences = [sentence_pairs[i:i + CONFIG["sentences_per_request"]] for i in range(0, len(sentence_pairs), CONFIG["sentences_per_request"])]
        logger.debug(f"{batch_msg} | Chunked_sentences: {len(sentence_pairs)} elements")
        
        error_count = 0

        for i, chunk in enumerate(chunked_sentences):            
            
            try:
                if error_count >= 5:
                    logger.error(f"{batch_msg} | Too many errors, adding pause.")
                    page.screenshot(path=f"{translation_logger.get_filepath()}/{batch_msg} | Too many errors, adding pause {datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    get_random_delay(CONFIG["new_request_delay_range"], fatigue=2, msg=f"{batch_msg}: Cooling down after errors")
                    error_count = 0
                logger.debug(f"{batch_msg} | Translating {len(chunk)} sentences per request")

                merged_text = merge_sentences([pair[0] for pair in chunk])
                logger.info(f"{batch_msg} | Translating {i + 1}/{len(chunked_sentences)}: {merged_text[:50]}...")
            
                for attempt in range(CONFIG["retry_attempts"]):
                    try:
                        translation = translate_sentence(page=page, sentence=merged_text, batch_idx=current_batch, logger=logger)
                        break
                    except Exception as e:
                        logger.warning(f"{batch_msg} | Attempt {attempt+1} failed for '{merged_text[:40]}...': {e}")
                        get_random_delay(CONFIG["retry_delay_range"])
                        page.reload()
                        get_random_delay(CONFIG["retry_delay_range"])
                        # checks if it's the last attempt
                        if attempt == CONFIG["retry_attempts"] - 1:
                            translation = f"[TRANSLATION FAILED] - {merged_text}"
                            error_count += 1
                            
                split_translations = split_translation(translation, len(chunk), msg=batch_msg)

                for i, translation in enumerate(split_translations):
                    
                    results.append({    
                        f"{SL}": chunk[i][0],
                        f"{TL}": translation.strip(),
                        f"{OL}": chunk[i][1]
                    })

            except Exception as e:
                logger.error(f"{batch_msg} | Unexpected error: {e}")
                page.screenshot(path=f"{translation_logger.get_filepath()}/{batch_msg} | Unexpected error: {e} {datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                error_count += 1
                results.append({f"{SL}": chunk[i][0], f"{TL}": "[ERROR]", f"{OL}": chunk[i][1]})
            finally:
                # Random delay between requests
                get_random_delay(CONFIG["new_request_delay_range"])
        
        # Random delay between batches

        logger.info(f"{batch_msg} | Sleeping before next batch...")          
        translation_logger.filter_log(
            filter_func=lambda line: batch_msg in line,
            new_filename=batch_msg,
            msg=batch_msg
        )
        get_random_delay(delay_range=CONFIG["new_batch_delay_range"], fatigue=1 + (batch_idx / (CONFIG['batch_size'] * CONFIG['max_workers'])) * 3, msg=batch_msg)
        logger.info(f"{batch_msg} | Next batch is ready to start...")           
        context.close()
        browser.close()

    return results


def merge_sentences(sentences: List[str]) -> str:
    """Merge multiple sentences with the separator symbol"""

    return f" {MERGE_SYMBOL} ".join(sentences)

def split_translation(translated_text: str, expected_count: int, msg: str = '') -> List[str]:
    """
    Split translated text back into individual sentences using the merge symbol.
    Handles cases where the symbol might be preserved in translation.
    """
    logger.debug(f"{msg} | Translated text: {translated_text}")
    logger.debug(f"{msg} | Splitting translated text into {expected_count} parts on the symbol {MERGE_SYMBOL}...")
    # Try to split by the original merge symbol
    parts = translated_text.split(MERGE_SYMBOL)
    
    # If we got the expected number of parts, return them
    logger.debug(f"{msg} | Gathered parts {(len(parts))} {parts}")
    if len(parts) != expected_count:   
        logger.warning(f"{msg} | Expected {expected_count} parts but got {len(parts)} after splitting. Attempting recovery...")
        raise Exception(f"{msg} | Split count mismatch Expected {expected_count} but got {len(parts)}")

    return parts
    


def save_batch_to_csv(batch_results: List[Dict], msg: str):
    """Save a single batch to CSV file"""
    batch_csv_file = f"{translation_logger.get_filepath()}/{msg}.csv"
    try:
        with open(batch_csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[SL, TL, OL])
            writer.writeheader()
            writer.writerows(batch_results)
        logger.info(f"{msg} saved to {batch_csv_file}")
        return batch_csv_file
    except Exception as e:
        logger.error(f"Failed to save {msg} to CSV: {e}")
        return None

def save_batch_to_json(batch_results: List[Dict], msg: str):
    """Save a single batch to JSON file"""
    batch_json_file = f"{translation_logger.get_filepath()}/{msg}.json"
    try:
        with open(batch_json_file, "w", encoding="utf-8") as f:
            json.dump(batch_results, f, ensure_ascii=False, indent=2)
        logger.info(f"{msg} saved to {batch_json_file}")
        return batch_json_file
    except Exception as e:
        logger.error(f"Failed to save {msg} to JSON: {e}")
        return None


def main():
    # Load dataset
    try:
        dataset_path = "hf://datasets/Bretagne/Autogramm_Breton_translation/data/train-00000-of-00001.parquet"
        df = pd.read_parquet(dataset_path)
        logger.info(df.info())
        logger.info(dataset_path)
        df = df.sample(frac=1, random_state=random.randint(1, 43)).reset_index(drop=True)

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
    # sl_sentences = sl_sentences[:260]
    # ol_sentences = ol_sentences[:260]
    
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
                # Save batch immediately to individual files
                save_batch_to_csv(batch_results, f"batch_{completed}")
                                
                save_batch_to_json(batch_results, f"batch_{completed}")
                
                logger.info(f"Batch {completed}/{len(batches)} completed.")
            except Exception as e:
                logger.error(f"Batch {completed} failed: {e}")
                
            
            
    # Save CSV
    csv_file = f"{SL}_{TL}_{OL}_parallel"
    save_batch_to_csv(all_results, csv_file)

    # Save JSON
    json_file = f"{SL}_{TL}_{OL}_parallel"
    save_batch_to_json(all_results, json_file)
    
     
    if(len(all_results) == 0):
        logger.warning("Catastrophic failure! No results were obtained.")
        logger.warning(f"Whatever results were saved to {csv_file} and {json_file}")
        
    else:
        logger.info(f"Translation complete! Saved to {csv_file} and {json_file}")
        logger.info(f"Success rate: {sum(1 for r in all_results if not r[TL].startswith('[')) / len(all_results):.1%}")



if __name__ == "__main__":
    main()