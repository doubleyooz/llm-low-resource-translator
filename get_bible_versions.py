from typing import Dict, List, Tuple
from playwright.sync_api import sync_playwright, Page
import time
import json
import random
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from bibles import VERSIONS, KOAD21, BCNDA, ABK, NIV, BIBLE, BookInfo, VersionInfo, books, POSTFIX, get_random_version
from user_agents import USER_AGENTS

# Configuration
CONFIG = {
    "max_workers_versions": 4,  # Concurrent versions
    "max_workers_books": 2,    # Concurrent books per version
    "page_timeout_ms": 60000,  # Page load timeout
    "scroll_delay_range": (0.1, 1.1),
    "interaction_delay_range": (3, 11),
    "retry_attempts": 3,       # Retry attempts for failed requests
    "retry_delay_range": (5, 15),  # Delay range between retries
    "scroll_amount_range": (50, 500),  # Range for scroll amount
    "scroll_back_probability": 0.2,    # Probability of scrolling backward
    "mouse_move_range_x": (-300, 800),  # X-coordinate range for mouse movement
    "mouse_move_range_y": (50, 700),  # Y-coordinate range for mouse movement
    "search_action_probability": 0.3,  # Probability of performing search
    "profile_menu_probability": 0.4,   # Probability of interacting with profile menu
    "max_scroll_iterations": 1000,     # Prevent infinite scroll loops

}


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def get_random_delay(delay_range: Tuple[float, float] = CONFIG["scroll_delay_range"]) -> float:
    """Generate a random delay within the specified range."""
    time.sleep(random.uniform(*delay_range))

def perform_action_with_delay(page: Page, action: callable, action_name: str, delay_range: Tuple[float, float] = CONFIG["scroll_delay_range"]) -> None:
    """Execute an action with a random delay and error handling."""
    try:
        action()
        get_random_delay(delay_range)
    except Exception as e:
        logger.warning(f"Failed to perform {action_name}: {str(e)}")

def simulate_human_behavior(page: Page, scroll_limit: float = 0.9) -> None:
    """Simulate human-like scrolling, mouse movements, and interactions on a webpage."""
    try:
        total_scroll_height = page.evaluate("document.body.scrollHeight")
        scroll_target = total_scroll_height * scroll_limit
        current_scroll = 0
        iteration_count = 0

        # Scroll loop with randomized behavior
        while current_scroll < scroll_target and iteration_count < CONFIG["max_scroll_iterations"]:
            scroll_amount = random.randint(*CONFIG["scroll_amount_range"])
            if random.random() < CONFIG["scroll_back_probability"]:
                scroll_amount = -scroll_amount  # Occasionally scroll backward
            page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            perform_action_with_delay(
                page,
                lambda: page.mouse.move(
                    random.randint(*CONFIG["mouse_move_range_x"]),
                    random.randint(*CONFIG["mouse_move_range_y"])
                ),
                "mouse movement"
            ) 
         
            current_scroll += scroll_amount
            iteration_count += 1

        
        # Simulate search action
        if random.random() < CONFIG["search_action_probability"]:
            random_version = get_random_version()
            perform_action_with_delay(
                page,
                lambda: page.locator('[name="Search"]').type(
                    random_version["name"], delay=random.uniform(50, 150)
                ),
                "search action"
            )

        # Simulate profile menu interaction
        if random.random() < CONFIG["profile_menu_probability"]:
            profile_locator = page.locator('button[aria-label="profile menu"]')
            perform_action_with_delay(page, lambda: profile_locator.hover(), "profile menu hover")
            perform_action_with_delay(page, lambda: profile_locator.click(), "profile menu click")

    except Exception as e:
        logger.error(f"Error in simulate_human_behavior: {str(e)}")

def fetch_chapter(page: Page, version_id: str, suffix: str, full_name: str, abbrev: str, chapter: int) -> List[str]:
    """Fetch and extract verses for a single chapter with retries."""
    url = f"https://www.bible.com/bible/{version_id}/{abbrev}.{chapter}.{suffix}"
    logger.info(f"Fetching chapter {chapter}: {url}")

    for attempt in range(CONFIG["retry_attempts"]):
        try:
            perform_action_with_delay(page, lambda: page.goto(url, timeout=CONFIG["page_timeout_ms"]), "page navigation", CONFIG["interaction_delay_range"])           
            perform_action_with_delay(page, lambda: page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {random.uniform(0.2, 0.8)})"), "page navigation", CONFIG["interaction_delay_range"])
            simulate_human_behavior(page, scroll_limit=0.9)
            return extract_verses(page)
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{CONFIG['retry_attempts']} failed for {full_name} {chapter}: {str(e)}")
            if attempt < CONFIG["retry_attempts"] - 1:
                get_random_delay(CONFIG["retry_delay_range"])
            else:
                logger.error(f"All retries failed for {full_name} {chapter}")
                return []
    return []

def extract_verses(page: Page) -> List[str]:
    try:
        # Wait for verse containers to be attached to the DOM
        verse_locators = page.locator('[class*="ChapterContent_verse"]')
        verse_locators.first.wait_for(state="attached", timeout=CONFIG["page_timeout_ms"])

        logger.info(f"Found {verse_locators.count()} verse containers")

        extracted_verses = []
        for i in range(verse_locators.count()):
            try:
               
                verse = verse_locators.nth(i)
                verse_num_locator = verse.locator('[class*="ChapterContent_label"]').first         
                verse_text_locator = verse.locator('[class*="ChapterContent_content"]')

                verse_num = verse_num_locator.inner_text().strip() if verse_num_locator.is_visible() and verse_num_locator.inner_text().strip().isdigit() else None
                     
                content_texts = verse_text_locator.all_inner_texts()          
                verse_text = " ".join([text.strip() for text in content_texts if text.strip()])
             
                if verse_text:
                    if verse_num is None and extracted_verses:
                        extracted_verses[-1] += " " + verse_text                        
                        logger.debug(f"Continued verse: {verse_text[:50]}...")
                    else:
                        extracted_verses.append(verse_text)
                        logger.debug(f"Verse {verse_num}: {verse_text[:50]}...")
              #  else:
              #      logger.warning(f"No text found for verse {verse_num}")
            except Exception as e:
                logger.error(f"Error processing verse {verse_num}: {str(e)}")
        logger.info(f"Extracted {len(extracted_verses)} verses")
        return extracted_verses
    except Exception as e:
        logger.error(f"Error extracting verses: {str(e)}")
        return []

def process_version(version: VersionInfo, books: List[BookInfo]) -> List[Dict]:
    """Process a single Bible version and return its corpus entries."""
    version_id = version["id"]
    suffix = version["suffix"]
    version_name = version["name"]
    output_file = version["file"]
    corpus_entries = []
    
    logger.info(f"Processing version: {version_name}")
    # Output file for individual version
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"The Holy Bible - {version_name}\n\n")
        with ThreadPoolExecutor(max_workers=CONFIG["max_workers_books"]) as executor:  # Limit to 2 books per version
            future_to_book = {executor.submit(process_book, book, version): book for book in books}
            for future in as_completed(future_to_book):
                try:
                    book_entries, full_name = future.result()
                    
                    corpus_entries.extend(book_entries)
                    # Write to file
                    book_verses = {}
                    
                    for entry in book_entries:
                        chapter = entry["chapter"]
                        if chapter not in book_verses:
                            book_verses[chapter] = []
                        book_verses[chapter].append((entry["verse"], entry[f"{suffix.lower()}{POSTFIX}"]))
                    
                    f.write(f"{full_name}\n{'='*50}\n\n")
                
                    for chapter in sorted(book_verses.keys()):
                        f.write(f"Chapter {chapter}\n{'-'*20}\n")
                        f.write("\n".join(f"{num} {text}" for num, text in sorted(book_verses[chapter])))
                        f.write("\n\n")
                    
                    f.write("\n")
                except Exception as e:
                    book = future_to_book[future]
                    print(f"Error processing book {book[0]} ({version_name}): {str(e)}")
    
    
    logger.info(f"Finished {version_name}! Check {output_file}")
    return corpus_entries

def process_book(book: BookInfo, version: VersionInfo):
    """Process a single book for a version and return corpus entries."""
    full_name, abbrev, num_chapters, _ = book
    version_id = version["id"]
    suffix = version["suffix"]
    corpus_entries = []
    
    with sync_playwright() as p:  # Create a new Playwright instance per thread
        browser = p.chromium.launch(headless=False)  # Set to True for headless mode
        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "DNT": "1",  # Do Not Track
                "Upgrade-Insecure-Requests": "1",
            },
            viewport={'width': random.randint(1366, 1920), 'height': random.randint(768, 1080)},  # Random viewport
        )
        
        page = context.new_page()
        
        logger.info(f"Processing {full_name} ({version['name']})...")
        for chapter in range(1, num_chapters + 1):  # Process all chapters
            verses = fetch_chapter(page, version_id, suffix, full_name, abbrev, chapter)
            if verses:
                logger.debug(f"  Chapter {chapter}")
                for verse_num, verse_text in enumerate(verses, 1):
                    logger.debug(f"Verse {verse_num}: {verse_text[:50]}...")
                    corpus_entries.append({
                        "book": full_name,
                        "chapter": chapter,
                        "verse": verse_num,
                        f"{suffix.lower()}{POSTFIX}": verse_text
                    })
            else:
                logger.warning(f"No verses found for {full_name} {chapter} ({version['name']})")
        context.close()
        browser.close()
    return corpus_entries, full_name

def merge_corpus(corpus_entries: List[Dict]) -> List[Dict]:
    """Merge corpus entries into a parallel corpus."""
    merged_corpus = {}
    for entry in corpus_entries:
        key = (entry["book"], entry["chapter"], entry["verse"])
        if key not in merged_corpus:
            merged_corpus[key] = {
                "book": entry["book"],
                "chapter": entry["chapter"],
                "verse": entry["verse"],
            }
            for version in VERSIONS:
                merged_corpus[key][f"{version['text']}{POSTFIX}"] = ""
        suffix = next(v["suffix"].lower() for v in VERSIONS if f"{v['suffix'].lower()}{POSTFIX}" in entry)
        merged_corpus[key][f"{suffix}{POSTFIX}"] = entry[f"{suffix}{POSTFIX}"]

    return list(merged_corpus.values())


def main():
    # Initialize parallel corpus
    parallel_corpus = []
    
    # Process versions concurrently using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=CONFIG["max_workers_versions"]) as executor:
        # Submit tasks for each version
        future_to_version = {executor.submit(process_version, version, books): version for version in VERSIONS}
        
        # Collect results as they complete
        for future in as_completed(future_to_version):
            version = future_to_version[future]
            try:
                corpus_entries = future.result()
                parallel_corpus.extend(corpus_entries)
            except Exception as e:
                logger.error(f"Error processing version {version['name']}: {str(e)}")
    
    # Merge parallel corpus entries by book, chapter, and verse
    merged_corpus = merge_corpus(parallel_corpus)

    # Save parallel corpus to JSON
    with open("parallel_corpus.json", "w", encoding="utf-8") as f:
        json.dump(merged_corpus, f, ensure_ascii=False, indent=2)

    output_files = ", ".join(f"{BIBLE}_{v['text']}.txt" for v in VERSIONS) + ", and parallel_corpus.json"
    logger.info(f"Download complete! Check {output_files}")

if __name__ == "__main__":
    main()