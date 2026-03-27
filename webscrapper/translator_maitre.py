
import pandas as pd
import os
import random
import queue
import threading

from datasets import Dataset, load_dataset
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple, Optional, TypedDict

from constants.output import LOG_FILENAME, OUTPUT_FOLDER
from constants.languages import SL, TL, OL
from exceptions.not_found_exception import NotFoundException
from pw_context import get_new_context
from scrapper_config import CONFIG
from scrapper_google_translate import get_url, translate_sentence
# from scrapper_korpus_kernewek import get_url, translate_sentence
# from scrapper_korpus_kernewek import wordbank

from logger import translation_logger
from utils.batch_scheduler import BatchScheduler
from utils.csv_helper import save_batch_to_csv
from utils.json_helper import save_batch_to_json
from utils.list_helper import remove_duplicates_from_list
from utils.pw_helper import handle_cookies_request, take_screenshot, get_random_delay, perform_action
from utils.txt_helper import clean_text, get_last_directory_alphabetic
from utils.worker_helper import get_latest_iteration
'''
Translator using Google Translate via Playwright.
Translates sentences from a Parquet dataset and saves results in CSV and JSON formats.
'''


# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

BatchType = List[Tuple[str, str]]
TaskType = Tuple[int, BatchType]

class TaskResultType(TypedDict):  
    error_count: int
    worker_id: int
    task_id: int
    entries: List[Dict[str, any]]
    

logger = translation_logger.get_logger(
    output_folder=OUTPUT_FOLDER,
    log_filename=LOG_FILENAME
)

MERGE_SYMBOL = "<|||>"  # Symbol to merge multiple sentences


scheduler = BatchScheduler(max_workers=CONFIG["max_workers"])

def clean_corpus_entries(entries):
    """
    Remove invalid entries and duplicates from the corpus.
    Returns a new list.
    """
    cleaned = []
    seen = set()  # track unique keys
    for entry in entries:
        sl = entry.get(SL, "")
        tl = entry.get(TL, "")
        # Skip if SL equals TL
        if sl == tl:
            continue

        # Skip if TL contains "[ERROR]" (or is exactly that)
        if tl == "[ERROR]" or "[ERROR]" in tl:
            continue
        
        # Skip if SL contains "[ERROR]" (or is exactly that)
        if sl == "[ERROR]" or "[ERROR]" in sl:
            continue

        # Create a unique key – adjust as needed
        # Here we use (sl, tl) as the deduplication key.
        key = (sl, tl)

        if key not in seen:
            seen.add(key)
            cleaned.append(entry)

    return cleaned


def puppeter_browser(
    batch: BatchType,
    current_batch: int,
    total_of_batches: int,
    batch_msg: str,
    results_list: List[Dict] = [],
    headless: bool = True):
    
    scheduler.ensure_batch_interval(batch_msg)  
    with sync_playwright() as p:
        browser, context = get_new_context(playwright=p, headless=headless, msg_prefix=batch_msg)
        page = context.new_page()
        
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            window.chrome = { runtime: {}, app: {}, LoadTimes: function(){} };
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        """)        
        
     
        logger.info(f"{batch_msg} {len(batch)} sentences")
        perform_action(lambda: page.goto(get_url(SL, TL), timeout=CONFIG["page_timeout_ms"]), f"{batch_msg} goto")
        handle_cookies_request(page=page, batch_msg=batch_msg)
        
        sentences_per_request = random.randint(*CONFIG["sentences_per_request_range"])
        chunked_sentences = [batch[i:i + sentences_per_request] for i in range(0, len(batch), sentences_per_request)]
        logger.debug(f"{batch_msg} Chunked_sentences: {len(batch)} elements")
       
        for i, chunk in enumerate(chunked_sentences):  
            try:
                scheduler.ensure_batch_interval(batch_msg) 
                if scheduler.check_errors_limit():
                    error_msg = "Too many errors, adding pause..."
                    logger.error(f"{batch_msg} {error_msg}")
                    take_screenshot(page, filename=error_msg, msg_prefix=batch_msg)                   
                   
                    get_random_delay(CONFIG["new_request_delay_range"], fatigue=2, msg=f"{batch_msg}: Cooling down after errors")
                    scheduler.reset_errors_count()
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
                            scheduler.increment_errors_count()
                logger.debug(f"{batch_msg} translation type: {type(translation)}")
                if isinstance(translation, tuple):
                    logger.debug(f"{batch_msg} Translation {translation}")
                    source_texts, target_texts = translation[0], translation[1]
                    
                    for i, (sl, tl) in enumerate(zip(source_texts, target_texts)):
                        results_list.append({    
                            SL: sl.strip() if sl else "",
                            TL: tl.strip() if tl else "",
                            OL: merged_text.strip()
                        })
                else: 
                    split_translations = split_translation(translation, len(chunk), msg=batch_msg)

                    for i, translation in enumerate(split_translations):
                        
                        results_list.append({    
                            SL: " ".join(chunk[i][0].split()),
                            TL: clean_text(translation),
                            OL: " ".join(chunk[i][1].split())
                        })

            except Exception as e:
                error_msg = f"Unexpected error: {e}"
                logger.error(f"{batch_msg} {error_msg}")
                take_screenshot(page, filename=error_msg, msg_prefix=batch_msg   )
                scheduler.increment_errors_count()
                results_list.append({f"{SL}": chunk[i][0], f"{TL}": "[ERROR]", f"{OL}": chunk[i][1]})
            finally:
                # Random delay between requests
                get_random_delay(CONFIG["new_request_delay_range"])
        

        logger.debug(f"{batch_msg} Filtering logs.")
        batch_msg = batch_msg.split('|')[0]

                            
        translation_logger.filter_log(
            filter_func=lambda line: batch_msg in line,
            new_filename=batch_msg if scheduler.get_errors_count() < 1 else f"{batch_msg}_err",
            output_folder="filtered_logs",
            msg=batch_msg
        )
              
        context.close()
        browser.close()
        scheduler.ensure_interval_before_next_batch(total_of_batches, batch_msg)
              
        return results_list


# Worker: Process One Batch
#def process_task(sentence_pairs: List[Tuple[str, str]], batch_idx: int, total_of_batches: int) -> List[Dict]:
def process_task(
    worker_id: int,
    task_queue: queue.Queue[TaskType],
    result_queue: queue.Queue[TaskResultType],
    total_of_batches: int
    ) -> None:

    while True:       
        try:
            task = task_queue.get(timeout=10)  # Wait for task
            if task is None:  # Poison pill to stop worker
                task_queue.task_done()
                break
            
            task_id, batch = task
            
            batch_msg = (
                f"Worker {worker_id} | "
                f"Batch {task_id}/{total_of_batches} | "
            )              
            

            entries = puppeter_browser(
                batch=batch,
                current_batch=task_id,
                total_of_batches=total_of_batches,
                batch_msg=batch_msg,
                headless=True
            )
            
            result_queue.put({
                "worker_id": worker_id,
                "task_id": task_id,
                "entries": entries
            })
                    
            task_queue.task_done()
        except queue.Empty as e:
            logger.warning(f"Worker {worker_id} Batch is empty: {str(e)}")
            break
        except Exception as e:
            logger.error(f"Worker {worker_id} error: {str(e)}")
            task_queue.task_done()
        finally:
            scheduler.ensure_batch_interval(batch_msg)
            



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
    
def is_valid(row: dict, source_col: str, target_col: str) -> bool:
    s = row.get(source_col)  # or row[source_col]
    t = row.get(target_col)
    return (s is not None and isinstance(s, str) and s.strip() and
            t is not None and isinstance(t, str) and t.strip())

def load_dataset_hugging_face(
    dataset_path: str,
    source_col: str = SL,      # e.g. "br"
    target_col: str = OL       # e.g. "fr"
) -> Tuple[List[str], List[str]]: 
    try:                
        logger.info(f"Loading dataset: {dataset_path} (columns: {source_col!r}, {target_col!r})")

        # Try to load only the two columns we care about
        ds: Dataset = load_dataset(
            dataset_path,
            columns=[source_col, target_col],  # only download these columns
            split="train"
        )

        logger.info(
            f"Dataset loaded | rows: {len(ds):,} | "
            f"columns: {ds.column_names} | "
            f"features: {ds.features}"
        )
          
        if len(ds) == 0:
            raise ValueError(f"Dataset {dataset_path} is empty after loading")
        

        missing = {source_col, target_col} - set(ds.column_names)
        if missing:
            raise ValueError(
                f"Requested columns {source_col!r} and/or {target_col!r} "
                f"not found in {dataset_path}. Available: {ds.column_names}"
            )
 
        ds = ds.filter(lambda row: is_valid(row, source_col, target_col))
        if len(ds) == 0:
            raise ValueError(
                f"No valid non‑empty {source_col.upper()} → {target_col.upper()} pairs found "
                f"in {dataset_path} (after filtering null/empty)"
            )

        # 2. Remove duplicates using Pandas
        df = ds.to_pandas()
        df = df.drop_duplicates(subset=[source_col, target_col])
        ds = Dataset.from_pandas(df)
        
        # 3. Shuffle (reproducible)
        ds = ds.shuffle(seed=random.randint(1, 43))
       
        # Convert tuples back to lists (usually very cheap)
        source_sentences = list(ds[source_col])
        target_sentences = list(ds[target_col])
                
        logger.info(f"{SL.upper()} sentences after filtering & shuffling: {len(source_sentences):,}")
        if source_sentences:
            print("Example source sentence:", source_sentences[0][:200])  # limit length for log
            logger.info(f"Loaded {len(source_sentences):,} valid {SL.upper()} sentences from {dataset_path}")

        return source_sentences, target_sentences

    except Exception as e:
        logger.error(f"Failed to load {dataset_path}: {type(e).__name__}: {str(e)}", exc_info=True)
        return [], []


def main():
    
    dataset_path = "./scrapper_korpus_kernewek"
    dataset_paths = [
    #    "Bretagne/Banque_Sonore_Dialectes_Bretons",
        "Bretagne/Autogramm_Breton_translation",
        "Bretagne/UD_Breton-KEB_translation",
        "Bretagne/Korpus-divyezhek-brezhoneg-galleg"
        
    ]

    data = {SL: [], OL: []}

    for path in dataset_paths:
        # Load dataset   
        sl_sentences, ol_sentences = load_dataset_hugging_face(path)
        data[SL].extend(sl_sentences)
        data[OL].extend(ol_sentences)
        
    # Merge the lists using zip()
    logger.info(f"Merged datasets: {len(data[SL]):,} sentences total")
    
    expected_pattern = f"*_*_*_*.json"
    
    corpus_entries, error_count = get_latest_iteration(
        expected_pattern=expected_pattern,
        return_all_matches=True
    )
    
    filtered_sl = []
    filtered_ol = []
    
    corpus_entries = clean_corpus_entries(corpus_entries)
    
    for sl_sent, ol_sent in zip(data[SL], data[OL]):
        if (sl_sent, ol_sent) not in corpus_entries:
            filtered_sl.append(sl_sent)
            filtered_ol.append(ol_sent)
    
    data[SL] = filtered_sl
    data[OL] = filtered_ol
    
    # Merge the lists using zip()
    logger.info(f"After removing existing entries from previous runs: {len(data[SL]):,}/{len(data[OL]):,} sentences total")
    
    merged_list = []
    for sl, ol in zip(data[SL], data[OL]):
        merged_list.append({SL: sl, OL: ol})
    
    random.shuffle(merged_list) 
    
    merged_list_of_tuples = [(item[SL], item[OL]) for item in merged_list]
    
    # Split into batches
    batch_size = CONFIG["batch_size"]
    batches: BatchType = [merged_list_of_tuples[i:i + batch_size] for i in range(0, len(merged_list_of_tuples), batch_size)]
    all_results = []

    columns = [SL, TL, OL]
    
    # shuffle the batches so the request will be randomised

    
    task_queue = queue.Queue[TaskType]()
    result_queue = queue.Queue[TaskResultType]()

    for task_id, item in enumerate(batches, 1):
        task_queue.put((task_id, item))
    
    workers = []
    task_queue_size = task_queue.qsize() + 1
    
    scheduler.set_max_workers(min(CONFIG['max_workers'], task_queue_size))
    
    for worker_id in range(1, scheduler.max_workers + 1):
        worker_thread = threading.Thread(target=process_task, args=(worker_id, task_queue, result_queue, task_queue_size))
        worker_thread.start()
        workers.append(worker_thread)
    
    
    # Wait for all tasks to complete
    task_queue.join()
    
        
    # Send poison pills to stop workers
    for _ in workers:
        task_queue.put(None)
    
    # Wait for workers to finish
    for worker_thread in workers:
        worker_thread.join()
        
    while not result_queue.empty():        
        try:
            result = result_queue.get()
            all_results.extend(result["entries"])
            logger.warning(f"Batch {result.get('task_id')}/{task_queue_size}.")
            
           
            # Save batch immediately to individual files
            filename = f"worker_{result.get('worker_id')}_batch_{result.get('task_id')}_{task_queue_size}"
            
            filtered_results = [entry for entry in result['entries'] if entry[TL] != entry[SL]]
            
            save_batch_to_csv(
                batch_results=filtered_results,
                filename=filename,
                columns=columns,
                output_folder="partial_results",
            )
                            
            save_batch_to_json(
                batch_results=filtered_results,
                filename=filename,
                output_folder="partial_results",
            )
            
            logger.info(f"Batch {result.get('task_id')}/{task_queue_size} completed.")
        except Exception as e:
            logger.error(f"Batch {result.get('task_id')} failed: {e}")
        
    
    
    output_filename = f"{SL}_{TL}_{OL}_parallel"  
    
    save_batch_to_csv(
        batch_results=corpus_entries,
        filename=f"{output_filename}_previous_runs",
        columns=columns,
        add_timestamp=True
    )
    
    save_batch_to_json(
        batch_results=corpus_entries,
        filename=f"{output_filename}_previous_runs",
        remove_duplicates=True,
        columns=columns,
        save_duplicates=True, 
        add_timestamp=True
    )   
            
    all_results.extend(corpus_entries)   
    # Save CSV
    save_batch_to_csv(
        batch_results=all_results,
        filename=output_filename,
        columns=columns,
        add_timestamp=True
    )

    # Save JSON
    save_batch_to_json(
        batch_results=all_results,
        filename=output_filename,
        remove_duplicates=True,
        columns=columns,
        save_duplicates=True, 
        duplicate_filename=f"{output_filename}_duplicates",
        add_timestamp=True
    )
    
     
    if(len(all_results) == 0):
        logger.warning("Catastrophic failure! No results were obtained.")
        logger.warning(f"Whatever results were saved to {output_filename} and {output_filename}")
        
    else:
        logger.info(f"Translation complete! Saved to {output_filename}.csv and {output_filename}.json")
        
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