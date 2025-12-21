import os
import queue
import threading

from datetime import datetime
from typing import Dict, List, Tuple
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor, as_completed

from constants.bibles import VERSIONS, KOAD21, BCNDA, ABK, NIV, BCC1923, BIBLE, BookInfo, VersionInfo, books, POSTFIX
from constants.output import LOG_FILENAME, OUTPUT_FOLDER
from pw_context import get_new_context
from scrapper_bible_com import fetch_chapter, get_url
from scrapper_config import CONFIG
from logger import translation_logger
from utils.batch_handling import BatchScheduler
from utils.json_helper import save_batch_to_json

logger = translation_logger.get_logger(
    output_folder=OUTPUT_FOLDER,
    log_filename=LOG_FILENAME
)

scheduler = BatchScheduler()

    
def save_to_txt(book_entries: List[str], book: BookInfo, version: VersionInfo, msg_prefix: str = '') -> None:  
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
            
            for entry in book_entries:
                chapter = entry["chapter"]
                if chapter not in book_verses:
                    book_verses[chapter] = []
                book_verses[chapter].append((entry["verse"], entry[suffix_key]))
            
            f.write(f"{book[0]}\n{'='*50}\n\n")
        
            for chapter in sorted(book_verses.keys()):
                f.write(f"Chapter {chapter}\n{'-'*20}\n")
                f.write("\n".join(f"{num} {text}" for num, text in sorted(book_verses[chapter])))
                f.write("\n\n")
            
            f.write("\n")
            logger.info(f"Finished {version_name}! Check {output_file}")
        except Exception as e:
            logger.error(f"Error processing book {book[0]} ({version_name}): {str(e)}")
        

def merge_corpus(corpus_entries: List[Dict], msg_prefix: str = "") -> List[Dict]:
    """Merge corpus entries into a parallel corpus."""
    merged_corpus = {}
    logger.info(f'{msg_prefix} Merging {len(corpus_entries)} corpus entries')
    
    version_text_keys = {f"{version['text']}{POSTFIX}" for version in VERSIONS}
    
    # Track statistics
    total_entries = len(corpus_entries)
    unique_verses = set()
    
    for entry in corpus_entries:
        key = (entry["book"], entry["chapter"], entry["verse"])
        unique_verses.add(key)
        
        # Initialize entry if not exists
        if not merged_corpus[key]:
            merged_corpus[key] = {
                "book": entry["book"],
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
    
    # Sort by book, chapter, verse for consistent output
    def sort_key(entry):
        # You might want to use book index instead of name for proper biblical order
        book_index = next((idx for idx, b in enumerate(books) if b[0] == entry["book"]), -1)
        return (book_index, entry["chapter"], entry["verse"])
    
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


def process_book(book: BookInfo, version: VersionInfo, batch_idx: int, total_of_batches: int, batch_msg: str):
    """Process a single book for a version and return corpus entries."""
    full_name, abbrev, num_chapters, _ = book
    version_id = version["id"]
    suffix = version["suffix"]
    corpus_entries = []
    error_count = 0   
    
    with sync_playwright() as p:  # Create a new Playwright instance per thread        
        browser, context = get_new_context(playwright=p, headless=True, msg_prefix=batch_msg)        
        page = context.new_page()
       
        for chapter in range(1, num_chapters + 1):  # Process all chapters
            try:     
                logger.info(f"{batch_msg} Processing version: {version['name']} {batch_idx}/{total_of_batches}")
                scheduler.ensure_batch_interval(batch_msg)       
               
                url = get_url(version_id=version_id, abbrev=abbrev, chapter=chapter, suffix=suffix)
                verses = fetch_chapter(page=page, url=url, full_name=full_name, chapter=chapter, total_of_chapters=num_chapters, msg=batch_msg)
                if verses:
                    logger.debug(f"{batch_msg} Chapter {chapter}")
                    for verse_num, verse_text in enumerate(verses, 1):
                        # logger.debug(f"{batch_msg} Verse {verse_num}: {verse_text[:50]}...")
                        corpus_entries.append({
                            "book": full_name,
                            "chapter": chapter,
                            "verse": verse_num,
                            f"{suffix.lower()}{POSTFIX}": verse_text
                        })
                else:
                    warning_msg = f"{batch_msg} No verses found for {full_name} {chapter} ({version['name']})"
                    page.screenshot(path=f"{translation_logger.get_filepath()}/{warning_msg}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
                    logger.warning(f"{warning_msg}")
            except Exception as e:
                error_msg = f'{batch_msg}_{str(e)}'
                error_count += 1
                logger.warning(error_msg)
                page.screenshot(path=f"{translation_logger.get_filepath()}/{error_msg}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        
        scheduler.ensure_interval_before_next_batch(batch_idx, total_of_batches, batch_msg)
        logger.debug(f"{batch_msg} Filtering logs.")
        translation_logger.filter_log(
            filter_func=lambda line: batch_msg in line,
            new_filename=batch_msg if error_count < 1 else f"{batch_msg}_err",
            msg=batch_msg
        )
             
        context.close()
        browser.close()
    return corpus_entries, full_name


def process_task(task_queue: queue.Queue[Tuple[int, BookInfo, VersionInfo]], result_queue: queue.Queue):
    corpus_entries = []
    batch_msg = ""
    
    while True:       
        try:
            task = task_queue.get(timeout=10)  # Wait for task
            if task is None:  # Poison pill to stop worker
                task_queue.task_done()
                break
           
            book_idx, book, version = task
            batch_msg = f'Batch {book_idx} {version["suffix"]} {book[1]} |'
           
            
            book_entries, book_name = process_book(book, version, book_idx, task_queue.qsize(), batch_msg)
            scheduler.ensure_interval_before_next_batch(book_idx * len(VERSIONS), task_queue.qsize(), batch_msg)
    
           
            save_to_txt(book_entries, book, version, batch_msg)
            corpus_entries.extend(book_entries)
            
            result_queue.put({
                'version': version,
                'book': book,
                'entries': book_entries,
                'book_name': book_name
            })
            
            task_queue.task_done()
        except queue.Empty:
            break
        except Exception as e:
            logger.error(f"{batch_msg} Worker error: {str(e)}")
            task_queue.task_done()
        

def main():
    # Process versions concurrently using ThreadPoolExecutor
    # Define the names of the four gospels
    gospel_names = ["Luke", "John"]

    # Use a list comprehension to filter the original list
    # The BookInfo tuples are structured as: (Name, Abbreviation, Chapters, Index)
       
    
    gospels = [book for book in books if book[0] in gospel_names]
    
    
    task_queue = queue.Queue()
    result_queue = queue.Queue()
    task_id = 1
    for version in VERSIONS:
        for book in (gospels):
            task_queue.put((task_id, book, version))
            task_id += 1
    
    workers = []
    for _ in range(min(CONFIG['max_workers'], task_queue.qsize())):
        worker_thread = threading.Thread(target=process_task, args=(task_queue, result_queue))
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
