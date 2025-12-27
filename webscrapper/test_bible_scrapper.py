import json
import os
from pathlib import Path
import queue
import random
import threading

from typing import Dict, List, Tuple
from typing_extensions import TypedDict
from playwright.sync_api import sync_playwright

from constants.bibles import VERSIONS, KOAD21, BCNDA, ABK, NIV, BCC1923, BIBLE, BookInfo, VersionInfo, books, POSTFIX
from constants.output import LOG_FILENAME, OUTPUT_FOLDER
from exceptions.not_found_exception import NotFoundException
from pw_context import get_new_context
from scrapper_bible_com import fetch_chapter, get_url
from scrapper_config import CONFIG
from logger import translation_logger
from utils.batch_scheduler import BatchScheduler
from utils.json_helper import save_batch_to_json
from utils.pw_helper import take_screenshot
from utils.txt_helper import clean_text, get_last_directory_alphabetic

logger = translation_logger.get_logger(
    output_folder=OUTPUT_FOLDER,
    log_filename=LOG_FILENAME
)

class TaskResultType(TypedDict):
   
    book: BookInfo
    version: VersionInfo
    book_id: int
    entries: List[Dict[str, any]]
    

class EntryType(TypedDict, extra_items=str):
    chapter: int
    verse: int
    book_name: str
    book_id: int
    
   
    
    
TaskType = Tuple[int, BookInfo, VersionInfo, int, int]


scheduler = BatchScheduler(max_workers=CONFIG['max_workers'])
def sort_key(entry: EntryType):
    # You might want to use book index instead of name for proper biblical order
    book_index = next((idx for idx, b in enumerate(books) if b['id'] == entry['book_id']), -1)
    return (book_index, entry["chapter"], entry["verse"])
    
def save_to_txt(book_entries: List[EntryType], book_title: str, version: VersionInfo, msg_prefix: str = '') -> None:  
    # Get file path and ensure directory exists
    output_dir = translation_logger.get_filepath()
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, version["file"])
    
    version_name = version["name"]
    suffix_key = f"{version['suffix'].lower()}{POSTFIX}"
    
    logger.info(f"{msg_prefix} Saving {version_name} as text file: {output_file}")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"The Holy Bible - {version_name}\n\n")
        
        try:                      
            # Write to file
            book_verses = {}          
            
            # book_entries.sort(key=sort_key)           

            for entry in book_entries:
                chapter = entry["chapter"]
                book_id = entry["book_id"]
                if book_id not in book_verses:
                    book_verses[book_id] = {}
                    
                if chapter not in book_verses[book_id]:
                    book_verses[book_id][chapter] = []
                book_verses[book_id][chapter].append((entry["verse"], entry[suffix_key]))
                    # Sort books in order
            sorted_book_ids = sorted(book_verses.keys(), 
                key=lambda bid: next(idx for idx, b in enumerate(books) if b['id'] == bid))
           
            logger.debug(f"Writing book: {book_title}")
            for book_id in sorted_book_ids:
                book_name = next(b['name'] for b in books if b['id'] == book_id)
                chapters = book_verses[book_id]

                f.write(f"{book_name}\n{'=' * 50}\n\n")

                for chapter in sorted(chapters.keys()):
                    f.write(f"Chapter {chapter}\n{'-' * 20}\n")
                    verses = sorted(chapters[chapter])
                    f.write("\n".join(f"{num} {text}" for num, text in verses))
                    f.write("\n\n")

                f.write("\n")
           
           
            logger.info(f"Finished {version_name}! Check {output_file}")
        except Exception as e:
            logger.error(f"Error processing book {book_title} ({version_name}): {str(e)}")
        

def merge_corpus(corpus_entries: List[EntryType], msg_prefix: str = "") -> List[Dict]:
    """Merge corpus entries into a parallel corpus."""
    merged_corpus = {}
    logger.info(f'{msg_prefix} Merging {len(corpus_entries)} corpus entries')
    
    version_text_keys = {f"{version['text']}{POSTFIX}" for version in VERSIONS}
    
    # Track statistics
    total_entries = len(corpus_entries)
    unique_verses = set()
    
    for entry in corpus_entries:
        print(entry)
        key = (entry["book_name"], entry["chapter"], entry["verse"])
        unique_verses.add(key)
        
        # Initialize entry if not exists
        if key not in merged_corpus:
            merged_corpus[key] = {
                "book_name": entry["book_name"],
                "book_id": entry["book_id"],
                "chapter": entry["chapter"],
                "verse": entry["verse"],
            }
            # Initialize all version fields with empty string
            for version_key in version_text_keys:
                merged_corpus[key][version_key] = ""
        
        # Find which version this entry belongs to
        # More efficient than using next() with generator
        for version_key in version_text_keys:
            if version_key in entry and entry[version_key]:
                merged_corpus[key][version_key] = entry[version_key]
                break
    
     # Convert to list and sort for consistent output
    result = list(merged_corpus.values())
    
    result.sort(key=sort_key)
    
    # Log detailed statistics
    logger.info(f'{msg_prefix} Merge complete: '
                f'{len(unique_verses)} unique verses, '
                f'{total_entries} total entries, '
                f'{len(result)} merged entries')
    
    # Log any potential data issues
    incomplete_entries = 0
    for entry in result:
        empty_versions = sum(1 for key in version_text_keys if not entry.get(key))
        if empty_versions > 0:
            incomplete_entries += 1
    
    if incomplete_entries > 0:
        logger.warning(f'{msg_prefix} Found {incomplete_entries} entries with missing translations')
    
    return result

def get_latest_iteration(suffix: str, abbrev: str, start_chapter: int, end_chapter: int, batch_msg: str) -> Tuple[List[EntryType], int]:
    last_iteration = get_last_directory_alphabetic("output/bibles")
    logger.warning(f"{batch_msg} Checking for previous iteration: {last_iteration}")
    corpus_entries = []
    error_count = 0
    if last_iteration:
        prev_partial_dir = Path("output/bibles") / last_iteration / "partial_results"
        logger.warning(f"{batch_msg} Looking for previous partial results in: {prev_partial_dir}")
        if prev_partial_dir.exists():
            # Expected filename pattern:
            # Something like: Worker_X_Batch_..._{suffix}_{abbrev}_chapters_{start}-{end}.json
            # We'll build the expected pattern from current batch info
            expected_pattern = f"*{suffix.upper()}*{abbrev.upper()}*chapters_{start_chapter}-{end_chapter}*.json"
            
            matching_files = list(prev_partial_dir.glob(expected_pattern))
            
            if matching_files:
                # Found one or more matching files — assume the work is already done
                latest_match = max(matching_files, key=lambda p: p.stat().st_mtime)  # most recent if multiple
                logger.info(f"{batch_msg} Found existing complete results: {latest_match.name}")
                logger.info(f"{batch_msg} Skipping processing — reusing existing data.")
                
                try:
                    with open(latest_match, "r", encoding="utf-8") as f:
                        corpus_entries = json.load(f)
                    logger.info(f"{batch_msg} Loaded {len(corpus_entries)} existing entries from previous run.")

                except Exception as e:
                    logger.error(f"{batch_msg} Failed to load existing JSON {latest_match}: {e}")
                    error_count += 1
                    # Fall through to normal processing
            else:
                logger.info(f"{batch_msg} No matching completed batch found in previous iteration {expected_pattern}. Starting fresh.")
        else:
            logger.info(f"{batch_msg} No partial_results folder in previous iteration.")
    else:
        logger.info(f"{batch_msg} No previous iteration found. Starting fresh.")
        
    return corpus_entries, error_count
    


def process_book(
    book: BookInfo,
    version: VersionInfo,
    start_chapter: int,
    end_chapter: int,
    batch_idx: int,
    total_of_batches: int,
    batch_msg: str
    ) -> List[EntryType]:

    full_name = book["name"]
    abbrev = book["abbr"]
    book_id = book["id"]
    
    version_id = version["id"]
    suffix = version["suffix"]
      
    corpus_entries, error_count = get_latest_iteration(suffix, abbrev, start_chapter, end_chapter, batch_msg)
    
    if not corpus_entries:        
        with sync_playwright() as p:  # Create a new Playwright instance per thread        
            browser, context = get_new_context(playwright=p, headless=True, msg_prefix=batch_msg)          
            page = context.new_page()
        
            for chapter in range(start_chapter, end_chapter + 1):  # Process all chapters
                
                try:           
                    logger.info(f"{batch_msg} Processing version: {version['name']} {chapter}/{end_chapter}")
                    scheduler.ensure_batch_interval(batch_msg)       
                
                    url = get_url(version_id=version_id, abbrev=abbrev, chapter=chapter, suffix=suffix)
                    verses = fetch_chapter(page=page, url=url, full_name=full_name, chapter=chapter, total_of_chapters=end_chapter, batches_asleep=scheduler.get_sleeping_batches_count(), msg=batch_msg)
                    if verses:
                        logger.debug(f"{batch_msg} Chapter {chapter}: {len(verses)} verses extracted.")
                        bible_suffix_key = f"{suffix.lower()}{POSTFIX}"
                        for verse_num, verse_text in enumerate(verses, 1):
                            # logger.debug(f"{batch_msg} Verse {verse_num}: {verse_text[:50]}...")
                            corpus_entries.append({     
                                "chapter": chapter,
                                "verse": verse_num,
                                "book_name": full_name,
                                "book_id": book_id,
                                bible_suffix_key: clean_text(verse_text)
                            })                        
                    else:
                        raise NotFoundException(f"No verses extracted for {full_name} {chapter}.")  
                        
                except Exception as e:
                    error_msg = f'{batch_msg} {str(e)}'
                    error_count += 1
                    logger.error(error_msg)
                    take_screenshot(page, filename=error_msg, msg_prefix=batch_msg)  
            
            context.close()
            browser.close()        
    if error_count == 0:
        scheduler.ensure_interval_before_next_batch(total_of_batches, batch_msg)
        save_batch_to_json(
            batch_results=corpus_entries,
            filename=batch_msg,
            output_folder="partial_results"
        )
    logger.debug(f"{batch_msg} Filtering logs.")
    batch_msg = batch_msg.split('|')[0]
    translation_logger.filter_log(
        filter_func=lambda line: batch_msg in line,
        new_filename=batch_msg if error_count < 1 else f"{batch_msg}_err",
        output_folder="filtered_logs",
        msg=batch_msg
    )
             
    return corpus_entries


def process_task(worker_id: int, task_queue: queue.Queue[TaskType], result_queue: queue.Queue, total_of_batches: int ):
    batch_msg = ""
    
    while True:       
        try:
            task = task_queue.get(timeout=10)  # Wait for task
            if task is None:  # Poison pill to stop worker
                task_queue.task_done()
                break
           
            task_id, book, version, start_chapter, end_chapter = task
            
            batch_msg = (
                f"Worker {worker_id} | "
                f"Batch {task_id}/{total_of_batches} | "
                f"{version['suffix']} {book['abbr']} "
                f"chapters {start_chapter}-{end_chapter} |"
            )
                                 
            book_entries = process_book(
                book=book,
                version=version,
                start_chapter=start_chapter,
                end_chapter=end_chapter,
                batch_idx=task_id,
                total_of_batches=total_of_batches,
                batch_msg=batch_msg
            )           
                        
            result_queue.put({
                'book_id': book['id'],
                'version': version,
                'book': book,
                'entries': book_entries,
                'book_name': book['name']
            })
            
            task_queue.task_done()
        except queue.Empty as e:
            logger.warning(f"Worker {worker_id} Batch is empty: {str(e)}")
            break
        except Exception as e:
            logger.error(f"Worker {worker_id} error: {str(e)}")
            task_queue.task_done()
  
def split_chapters_evenly(total_chapters: int, max_chapters_per_task: int = 20) -> List[Tuple[int, int]]:
    """
    Split total chapters into ranges where each range has at most max_chapters_per_task.
    
    Args:
        total_chapters: Total number of chapters in the book
        max_chapters_per_task: Maximum chapters each task can handle
        
    Returns:
        List of (start_chapter, end_chapter) tuples (1-based inclusive)
    """
    if total_chapters <= max_chapters_per_task:
        return [(1, total_chapters)]
    
    # Calculate number of tasks needed
    num_tasks = (total_chapters + max_chapters_per_task - 1) // max_chapters_per_task
    # Calculate chapters per task (as evenly as possible)
    base_chapters = total_chapters // num_tasks
    remainder = total_chapters % num_tasks
    
    ranges = []
    start_chapter = 1
    
    for i in range(num_tasks):
        # Distribute remainder chapters among first few tasks
        chapters_in_this_task = base_chapters + (1 if i < remainder else 0)
        end_chapter = start_chapter + chapters_in_this_task - 1
        ranges.append((start_chapter, end_chapter))
        start_chapter = end_chapter + 1
    
    return ranges


def main():
    # Process versions concurrently using ThreadPoolExecutor
    # Define the names of the four gospels
    gospel_names = ["Romans", "Mark", "Luke" "1 Maccabees", "2 Maccabees", "Matthew", "John"]

    # Use a list comprehension to filter the original list
    # The BookInfo tuples are structured as: (Name, Abbreviation, Chapters, Index)
       
    
    gospels = [book for book in books if book['name'] in gospel_names]


    task_queue = queue.Queue[TaskType]()
    result_queue = queue.Queue[TaskResultType]()
   
    temp_list = []
    # Example usage in your loop
    for version in VERSIONS:
        for book in gospels:
            book_name = book["name"]
            book_abbrev = book["abbr"]
            total_chapters = book["chapters"]
            book_id = book["id"]
        
            # Get chapter ranges for this book
            chapter_ranges = split_chapters_evenly(total_chapters, max_chapters_per_task=CONFIG['batch_size'])
            
            # Create tasks for each range
            for start_chapter, end_chapter in chapter_ranges:
                temp_list.append((book, version, start_chapter, end_chapter))
               
    # shuffle them first so you wont repeat the requests in the same order all the time             
    random.shuffle(temp_list) 
  
    for task_id, item in enumerate(temp_list, 1):
        task_queue.put((task_id, ) + item)
       
    
    workers = []
    task_queue_size = task_queue.qsize() + 1
    
    scheduler.set_max_workers(min(CONFIG['max_workers'], task_queue_size))
    logger.info(f"Starting download with {scheduler.max_workers} workers and {task_queue_size} tasks.")
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
    
    # Collect results
    version_data = {}
    while not result_queue.empty():
        result = result_queue.get()
        version_key = result['version']['name']
        if version_key not in version_data:
            version_data[version_key] = {
                'version': result['version'],
                'entries': [],
                'books': set()
            }
        version_data[version_key]['entries'].extend(result['entries'])
        version_data[version_key]['books'].add(result['book_name'])

    # Save results
    parallel_corpus = []
    for version_info in version_data.values():
        # Save individual version files
        save_to_txt(version_info['entries'], list(version_info['books'])[0], version_info['version'])
        parallel_corpus.extend(version_info['entries'])

    # Merge parallel corpus entries by book, chapter, and verse
    merged_corpus = merge_corpus(parallel_corpus)
    save_batch_to_json(merged_corpus, "parallel_corpus.json")

    output_files = ", ".join(f"{translation_logger.get_filepath()}/{BIBLE}_{v['text']}.txt" for v in VERSIONS) + ", and parallel_corpus.json"
    logger.info(f"Download complete! Check {output_files}")


if __name__ == "__main__":
    main()
