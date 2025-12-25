
import pandas as pd
import os
import random

from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional

from constants.output import LOG_FILENAME, OUTPUT_FOLDER
from constants.languages import SL, TL, OL
from exceptions.not_found_exception import NotFoundException
from pw_context import get_new_context
from scrapper_config import CONFIG
from scrapper_korpus_kernewek import get_url, translate_sentence
from scrapper_korpus_kernewek import wordbank

from logger import translation_logger
from utils.batch_handling import BatchScheduler
from utils.csv_helper import save_batch_to_csv
from utils.json_helper import save_batch_to_json
from utils.pw_helper import take_screenshot, get_random_delay, perform_action
from utils.txt_helper import clean_text
'''
Translator using Google Translate via Playwright.
Translates sentences from a Parquet dataset and saves results in CSV and JSON formats.
'''


# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


logger = translation_logger.get_logger(
    output_folder=OUTPUT_FOLDER,
    log_filename=LOG_FILENAME
)

MERGE_SYMBOL = "<|||>"  # Symbol to merge multiple sentences


scheduler = BatchScheduler(max_workers=CONFIG["max_workers"])

# Worker: Process One Batch
def process_batch(sentence_pairs: List[Tuple[str, str]], batch_idx: int, total_of_batches: int) -> List[Dict]:
    current_batch = batch_idx + 1
    batch_msg = f"Batch {current_batch} |"
    scheduler.ensure_batch_interval(batch_msg)
    results = []
   

    with sync_playwright() as p:
        browser, context = get_new_context(playwright=p, headless=True, msg_prefix=batch_msg)
        page = context.new_page()
        
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            window.chrome = { runtime: {}, app: {}, LoadTimes: function(){} };
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        """)        
        
     
        logger.info(f"{batch_msg} {len(sentence_pairs)} sentences")
        perform_action(lambda: page.goto(get_url(SL, TL), timeout=CONFIG["page_timeout_ms"]), f"{batch_msg} goto")
        
        sentences_per_request = random.randint(*CONFIG["sentences_per_request_range"])
        chunked_sentences = [sentence_pairs[i:i + sentences_per_request] for i in range(0, len(sentence_pairs), sentences_per_request)]
        logger.debug(f"{batch_msg} Chunked_sentences: {len(sentence_pairs)} elements")
        
        error_count = 0

        for i, chunk in enumerate(chunked_sentences):            
            
            try:
                if error_count >= 5:
                    error_msg = "Too many errors, adding pause..."
                    logger.error(f"{batch_msg} {error_msg}")
                    take_screenshot(page, filename=error_msg, msg_prefix=batch_msg)                   
                   
                    get_random_delay(CONFIG["new_request_delay_range"], fatigue=2, msg=f"{batch_msg}: Cooling down after errors")
                    error_count = 0
                logger.debug(f"{batch_msg} Translating {len(chunk)} sentences per request")

                merged_text = merge_sentences([pair[0] for pair in chunk], msg=batch_msg)
                logger.info(f"{batch_msg} Translating {i + 1}/{len(chunked_sentences)}: {merged_text}...")
            
                for attempt in range(CONFIG["retry_attempts"]):
                    try:
                        translation = translate_sentence(page=page, sentence=merged_text, batch_idx=current_batch)
                        break
                    except Exception as e:
                        if(isinstance(e, NotFoundException)):
                            logger.warning(e.message + f" - {merged_text}")
                            translation = f"[NOT FOUND] - {merged_text}"
                            take_screenshot(page, filename=f"{e.message}", msg_prefix=batch_msg)
                            break
                        logger.warning(f"{batch_msg} Attempt {attempt+1} failed for '{merged_text[:40]}...': {e}")
                        get_random_delay(CONFIG["retry_delay_range"])
                        page.reload()
                        get_random_delay(CONFIG["retry_delay_range"])
                        # checks if it's the last attempt
                        if attempt == CONFIG["retry_attempts"] - 1:
                            translation = f"[TRANSLATION FAILED] - {merged_text}"
                            error_count += 1
                logger.debug(f"{batch_msg} translation type: {type(translation)}")
                if isinstance(translation, tuple):
                    logger.debug(f"{batch_msg} Translation {translation}")
                    source_texts, target_texts = translation[0], translation[1]
                    
                    for i, (sl, tl) in enumerate(zip(source_texts, target_texts)):
                        results.append({    
                            SL: sl.strip() if sl else "",
                            TL: tl.strip() if tl else "",
                            OL: merged_text.strip()
                        })
                else: 
                    split_translations = split_translation(translation, len(chunk), msg=batch_msg)

                    for i, translation in enumerate(split_translations):
                        
                        results.append({    
                            SL: " ".join(chunk[i][0].split()),
                            TL: clean_text(translation),
                            OL: " ".join(chunk[i][1].split())
                        })

            except Exception as e:
                error_msg = f"Unexpected error: {e}"
                logger.error(f"{batch_msg} {error_msg}")
                take_screenshot(page, filename=error_msg, msg_prefix=batch_msg   )
                error_count += 1
                results.append({f"{SL}": chunk[i][0], f"{TL}": "[ERROR]", f"{OL}": chunk[i][1]})
            finally:
                # Random delay between requests
                get_random_delay(CONFIG["new_request_delay_range"])
        
        scheduler.ensure_interval_before_next_batch(total_of_batches, batch_msg)
                          
        translation_logger.filter_log(
            filter_func=lambda line: batch_msg in line,
            new_filename=batch_msg if error_count < 1 else f"{batch_msg}_err",
            msg=batch_msg
        )
              
        context.close()
        browser.close()

    return results


def merge_sentences(sentences: List[str], msg: str = '') -> str:
    """Merge multiple sentences with the separator symbol"""
    logger.debug(f"{msg} Sentences to merge: {sentences}")
    logger.debug(f"{msg} Merging {len(sentences)} sentences with symbol {MERGE_SYMBOL}...")
    return f" {MERGE_SYMBOL} ".join(sentences)

def split_translation(translated_text: str, expected_count: int, msg: str = '') -> List[str]:
    if not isinstance(translated_text, str):
        logger.debug(f"{msg} Translated text is not a string: {translated_text}")
        return translated_text
   
    logger.debug(f"{msg} Translated text: {translated_text}")
    logger.debug(f"{msg} Splitting translated text into {expected_count} parts on the symbol {MERGE_SYMBOL}...")
    # Try to split by the original merge symbol
    parts = translated_text.split(MERGE_SYMBOL)
    
    # If we got the expected number of parts, return them
    logger.debug(f"{msg} Gathered parts {(len(parts))} {parts}")
    if len(parts) != expected_count:   
        logger.warning(f"{msg} Expected {expected_count} parts but got {len(parts)} after splitting. Attempting recovery...")
        raise Exception(f"{msg} Split count mismatch Expected {expected_count} but got {len(parts)}")

    return parts
    



def load_dataset() -> Tuple[List[str], List[str]]:  
    try:
        dataset_path = "./scrapper_korpus_kernewek"
        # dataset_path = "hf://datasets/Bretagne/Banque_Sonore_Dialectes_Bretons"
        # dataset_path = "hf://datasets/Bretagne/Autogramm_Breton_translation/data/train-00000-of-00001.parquet"
        # dataset_path = "hf://datasets/Bretagne/UD_Breton-KEB_translation/data/train-00000-of-00001.parquet"
        # df = pd.read_parquet(dataset_path)
        df = pd.DataFrame({SL: wordbank, OL: wordbank})
        logger.info("DataFrame loaded. Shape: %s, Columns: %s, Data Types:\n%s", 
            df.shape, df.columns.tolist(), df.dtypes)
        logger.info(dataset_path)
        df = df.sample(frac=1, random_state=random.randint(1, 43)).reset_index(drop=True)
        sl_sentences = df[SL].dropna().tolist()
        ol_sentences = df[OL].dropna().tolist()
        if not sl_sentences:
            raise ValueError(f"No {SL.upper()} sentences found in dataset.")
        
            
        logger.info(f"{SL.upper()} sentences length: {len(sl_sentences)}")
        print(sl_sentences[0])
        logger.info(f"Loaded {len(sl_sentences):,} {SL.upper()} sentences. Starting translation...")
        
            
        return sl_sentences, ol_sentences
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        return


def main():
    # Load dataset   
    sl_sentences, ol_sentences = load_dataset()

    # Merge the lists using zip()
    merged_iterator = zip(sl_sentences, ol_sentences)

    # Convert the iterator to a list of tuples
    merged_list_of_tuples = list(merged_iterator)
    
    # Split into batches
    batch_size = CONFIG["batch_size"]
    batches = [merged_list_of_tuples[i:i + batch_size] for i in range(0, len(merged_list_of_tuples), batch_size)]
    total_of_batches = len(batches)
    all_results = []

    columns = [SL, TL, OL]

    with ThreadPoolExecutor(max_workers=CONFIG["max_workers"]) as executor:
        futures = {
            executor.submit(process_batch, batch, idx, total_of_batches): idx
            for idx, batch in enumerate(batches)
        }

        for future in as_completed(futures):
            batch_idx = futures[future]
            completed = batch_idx + 1
            try:
                batch_results = future.result()
                all_results.extend(batch_results)
                # Save batch immediately to individual files
                save_batch_to_csv(batch_results, f"batch_{completed}", columns)
                                
                save_batch_to_json(batch_results, f"batch_{completed}")
                
                logger.info(f"Batch {completed}/{len(batches)} completed.")
            except Exception as e:
                logger.error(f"Batch {completed} failed: {e}")
                
            
            
    # Save CSV
    csv_file = f"{SL}_{TL}_{OL}_parallel"
    save_batch_to_csv(all_results, csv_file, columns)

    # Save JSON
    json_file = f"{SL}_{TL}_{OL}_parallel"
    save_batch_to_json(all_results, json_file)
    
     
    if(len(all_results) == 0):
        logger.warning("Catastrophic failure! No results were obtained.")
        logger.warning(f"Whatever results were saved to {csv_file} and {json_file}")
        
    else:
        logger.info(f"Translation complete! Saved to {csv_file}.csv and {json_file}.json")
        
        # 1. Overall success rate
        successful = sum(1 for r in all_results if not r[TL].startswith('['))
        failed = len(all_results) - successful
        logger.info(f"Total sentences processed: {len(all_results):,}")
        logger.info(f"Successful translations : {successful:,} ({successful/len(all_results):.1%})")
        logger.info(f"Failed / errored        : {failed:,} ({failed/len(all_results):.1%})")

        # 2. Print ALL errors with source + original + failed translation
        if failed > 0:
            logger.warning(f"\n{'='*60}")
            logger.warning(f"  DETAILED ERROR REPORT ({failed} failed translations)")
            logger.warning(f"{'='*60}")

            for idx, row in enumerate(all_results, 1):
                translation = row[TL]
                if translation.startswith('['):  # [ERROR], [TRANSLATION FAILED], etc.
                    src = row[SL]
                    orig = row.get(OL, "N/A")
                    logger.error(f"FAIL #{idx:04d} | {SL} → {TL}")
                    logger.error(f"   Source ({SL}):     {src}")
                    logger.error(f"   Original ({OL}):  {orig}")
                    logger.error(f"   Result:           {translation}")
                    logger.error(f"   {'-'*50}")

            logger.warning(f"END OF ERROR REPORT")
            logger.warning(f"{'='*60}\n")
        else:
            logger.info("Perfect run! No errors detected.")


if __name__ == "__main__":
    main()