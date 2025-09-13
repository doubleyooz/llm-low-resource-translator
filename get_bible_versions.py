from playwright.sync_api import sync_playwright
import time
import json
import random

# Hardcoded book data: (full_name, abbrev, num_chapters, book_id)
# Book IDs are sequential starting from 1 (Genesis=1, etc.)
books = [
    ("Genesis", "GEN", 50, 1),
    ("Exodus", "EXO", 40, 2),

]

BIBLE = "bible"
ABK = "abk"
BCNDA = "bcnda"
CPDV = "cpdv"
KOAD21 = "koad21"
POSTFIX = "_text"  

VERSIONS = [
    {"id": "42", "suffix": CPDV.upper(), "name": "Catholic Public Domain Version", "file": f'{BIBLE}_{CPDV}.txt', "apocrypha": True},
    {"id": "1231", "suffix": KOAD21.upper(), "name": "Bibl Koad 21", "file": f'{BIBLE}_{KOAD21}.txt', "apocrypha": True},
    {"id": "4114", "suffix": BCNDA.upper(), "name": "Beibl Cymraeg Newydd Diwygiedig yn cynnwys yr Apocryffa 2008", "file": f'{BIBLE}_{BCNDA}.txt', "apocrypha": False},
    {"id": "1079", "suffix": ABK.upper(), "name": "An Bibel Kernewek 20234 (Kernewek Kemmyn)", "file": f'{BIBLE}_{ABK}.txt', "apocrypha": True}
]


def extract_verses(page):
    """Extract verses from the current chapter page by processing verse containers."""
    try:
        # Wait for verse containers to be attached to the DOM
        page.wait_for_selector('[class*="ChapterContent_verse"]', state="attached", timeout=30000)
        # Wait for network to be idle to ensure content is loaded
        page.wait_for_load_state("networkidle", timeout=30000)
        
        # Find all verse containers
        verses = page.locator('[class*="ChapterContent_verse"]').all()
        print(f"    Found {len(verses)} verse containers")
        
        extracted_verses = []
        for i, verse in enumerate(verses):
            try:
                # Get the verse number from ChapterContent_label
                label = verse.locator('[class*="ChapterContent_label"]').first
                verse_num = label.inner_text().strip() if label.count() > 0 else f"unknown_{i+1}"
                
                # Get all content spans within this verse (including those in ChapterContent_add)
                content_spans = verse.locator('[class*="ChapterContent_content"]').all()
                verse_text = ""
                for span in content_spans:
                    text = span.inner_text().strip()
                    if text:
                        verse_text += text + " "
                
                verse_text = verse_text.strip()
                if verse_text:
                    extracted_verses.append(verse_text)
                    print(f"    Verse {verse_num}: {verse_text[:50]}...")
                else:
                    print(f"    No text found for verse {verse_num}")
            except Exception as e:
                print(f"    Error processing verse {verse_num}: {str(e)}")
        
        return extracted_verses
    except Exception as e:
        print(f"    Error extracting verses: {str(e)}")
        return []

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to True for headless mode
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36")
        
        # Initialize parallel corpus
        parallel_corpus = []
        
        for version in VERSIONS:
            version_id = version["id"]
            suffix = version["suffix"]
            version_name = version["name"]
            output_file = version["file"]
            
            # Output file for individual version
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"The Holy Bible - {version_name}\n\n")
                
                for full_name, abbrev, num_chapters, book_id in books:
                    print(f"Processing {full_name} ({version_name})...")
                    f.write(f"{full_name}\n{'='*50}\n\n")
                    
                    for chapter in range(1, 2):
                        url = f"https://www.bible.com/bible/{version_id}/{abbrev}.{chapter}.{suffix}"
                        print(f"  Chapter {chapter}: {url}")
                        
                        try:
                            page.goto(url, timeout=60000)
                            time.sleep(random.uniform(5, 15))  # Random delay for stability
                            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            time.sleep(2)
                            
                            verses = extract_verses(page)
                            # 
                            if verses:
                                f.write(f"Chapter {chapter}\n{'-'*20}\n")
                                f.write("\n".join(f"{num} {text}" for num, text in enumerate(verses, start=1)))
                                f.write("\n\n")
                                # print(verses)
                                # Add to parallel corpus
                                for verse_num, verse_text in enumerate(verses, start=1):
                                    print(verse_num, verse_text)
                                    parallel_corpus.append({
                                        "book": full_name,
                                        "chapter": chapter,
                                        "verse": verse_num,
                                        f"{suffix.lower()}{POSTFIX}": verse_text
                                    })
                            else:
                                print(f"    No verses found for {full_name} {chapter} ({version_name})")
                        except Exception as e:
                            print(f"    Error processing {full_name} {chapter} ({version_name}): {str(e)}")
                    
                    f.write("\n")  # Space between books
            
            print(f"Finished {version_name}! Check {output_file}")
        
        # Merge parallel corpus entries by book, chapter, and verse
        merged_corpus = {}
        for entry in parallel_corpus:
            key = (entry["book"], entry["chapter"], entry["verse"])
            if key not in merged_corpus:
                merged_corpus[key] = {
                    "book": entry["book"],
                    "chapter": entry["chapter"],
                    "verse": entry["verse"],
                    f"{CPDV}{POSTFIX}": "",
                    f"{KOAD21}{POSTFIX}": "",
                    f"{BCNDA}{POSTFIX}": "",
                    f"{ABK}{POSTFIX}": ""
                }
                
                 # Update the appropriate text field based on the suffix
            for version in VERSIONS:
                suffix = version["suffix"].lower()
                if f"{suffix}{POSTFIX}" in entry:
                    merged_corpus[key][f"{suffix}{POSTFIX}"] = entry[f"{suffix}{POSTFIX}"]
                    
        # Save parallel corpus to JSON
        with open("parallel_corpus.json", "w", encoding="utf-8") as f:
            json.dump(list(merged_corpus.values()), f, ensure_ascii=False, indent=2)
        
        browser.close()
        print(f"Download complete! Check {ABK}.txt, {BCNDA}.txt, {CPDV}.txt, {KOAD21}.txt and parallel_corpus.json")
if __name__ == "__main__":
    main()