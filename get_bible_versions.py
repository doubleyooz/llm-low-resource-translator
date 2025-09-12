from playwright.sync_api import sync_playwright
import time

# Hardcoded book data: (full_name, abbrev, num_chapters, book_id)
# Book IDs are sequential starting from 1 (Genesis=1, etc.)
books = [
    ("Genesis", "GEN", 50, 1),
    ("Exodus", "EXO", 40, 2),
    ("Leviticus", "LEV", 27, 3),
    ("Numbers", "NUM", 36, 4),
    ("Deuteronomy", "DEU", 34, 5),
    ("Joshua", "JOS", 24, 6),
    ("Judges", "JDG", 21, 7),
    ("Ruth", "RUT", 4, 8),
    ("1 Samuel", "1SA", 31, 9),
    ("2 Samuel", "2SA", 24, 10),
    ("1 Kings", "1KI", 22, 11),
    ("2 Kings", "2KI", 25, 12),
    ("1 Chronicles", "1CH", 29, 13),
    ("2 Chronicles", "2CH", 36, 14),
    ("Ezra", "EZR", 10, 15),
    ("Nehemiah", "NEH", 13, 16),
    ("Esther", "EST", 10, 17),
    ("Job", "JOB", 42, 18),
    ("Psalms", "PSA", 150, 19),
    ("Proverbs", "PRO", 31, 20),
    ("Ecclesiastes", "ECC", 12, 21),
    ("Song of Solomon", "SNG", 8, 22),
    ("Isaiah", "ISA", 66, 23),
    ("Jeremiah", "JER", 52, 24),
    ("Lamentations", "LAM", 5, 25),
    ("Ezekiel", "EZK", 48, 26),
    ("Daniel", "DAN", 12, 27),
    ("Hosea", "HOS", 14, 28),
    ("Joel", "JOL", 3, 29),
    ("Amos", "AMO", 9, 30),
    ("Obadiah", "OBA", 1, 31),
    ("Jonah", "JON", 3, 32),
    ("Micah", "MIC", 7, 33),
    ("Nahum", "NAH", 3, 34),
    ("Habakkuk", "HAB", 3, 35),
    ("Zephaniah", "ZEP", 3, 36),
    ("Haggai", "HAG", 2, 37),
    ("Zechariah", "ZEC", 14, 38),
    ("Malachi", "MAL", 4, 39),
    ("Matthew", "MAT", 28, 40),
    ("Mark", "MRK", 16, 41),
    ("Luke", "LUK", 24, 42),
    ("John", "JHN", 21, 43),
    ("Acts", "ACT", 28, 44),
    ("Romans", "ROM", 16, 45),
    ("1 Corinthians", "1CO", 16, 46),
    ("2 Corinthians", "2CO", 13, 47),
    ("Galatians", "GAL", 6, 48),
    ("Ephesians", "EPH", 6, 49),
    ("Philippians", "PHP", 4, 50),
    ("Colossians", "COL", 4, 51),
    ("1 Thessalonians", "1TH", 5, 52),
    ("2 Thessalonians", "2TH", 3, 53),
    ("1 Timothy", "1TI", 6, 54),
    ("2 Timothy", "2TI", 4, 55),
    ("Titus", "TIT", 3, 56),
    ("Philemon", "PHM", 1, 57),
    ("Hebrews", "HEB", 13, 58),
    ("James", "JAS", 5, 59),
    ("1 Peter", "1PE", 5, 60),
    ("2 Peter", "2PE", 3, 61),
    ("1 John", "1JN", 5, 62),
    ("2 John", "2JN", 1, 63),
    ("3 John", "3JN", 1, 64),
    ("Jude", "JUD", 1, 65),
    ("Revelation", "REV", 22, 66),
]

VERSION_ID = "1"  # KJV

def extract_verses(page):
    """Extract verses from the current chapter page using flexible class matching."""
    try:
        # Wait for verse labels to be attached to the DOM
        page.wait_for_selector('[class*="ChapterContent_label"]', state="attached", timeout=30000)
        
        # Wait for network to be idle to ensure content is loaded
        page.wait_for_load_state("networkidle", timeout=30000)
        
        # Find all verse labels and content elements
        labels = page.locator('[class*="ChapterContent_label"]').all()
        contents = page.locator('[class*="ChapterContent_content"]').all()
        print(f"    Found {len(labels)} verse labels and {len(contents)} content elements")
        
        extracted_verses = []
        for i, label in enumerate(labels):
            verse_num = label.inner_text().strip()
            # Get the i-th content element, assuming they align with labels
            content = page.locator('[class*="ChapterContent_content"]').nth(i)
            print(f"Content: {content}")
            if content.count() > 0:
                try:
                    verse_text = content.inner_text().strip()
                    if verse_text:
                        extracted_verses.append(f"{verse_num} {verse_text}")
                        print(f"    Verse {verse_num}: {verse_text[:50]}...")  # Log first 50 chars
                    else:
                        print(f"    No text found for verse {verse_num}")
                except Exception as e:
                    print(f"    Error extracting text for verse {verse_num}: {str(e)}")
            else:
                print(f"    No content element found for verse {verse_num}")
        
        return extracted_verses
    except Exception as e:
        print(f"    Error extracting verses: {str(e)}")
        return []
    
    
def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to True for no UI
        page = browser.new_page()
        
        # Output file
        with open("bible_kjv.txt", "w", encoding="utf-8") as f:
            f.write("The Holy Bible - King James Version\n\n")
            
            for full_name, abbrev, num_chapters, book_id in books:
                print(f"Processing {full_name}...")
                f.write(f"{full_name}\n{'='*50}\n\n")
                
                for chapter in range(1, num_chapters + 1):
                    url = f"https://www.bible.com/bible/{book_id}/{abbrev}.{chapter}.kjv"
                    print(f"  Chapter {chapter}: {url}")
                    
                    page.goto(url)
                    time.sleep(2)  # Wait for load (adjust if needed)
                    
                    verses = extract_verses(page)
                    if verses:
                        f.write(f"Chapter {chapter}\n{'-'*20}\n")
                        f.write("\n".join(verses))
                        f.write("\n\n")
                    else:
                        print(f"    No verses found for {full_name} {chapter}")
                
                f.write("\n")  # Space between books
        
        browser.close()
        print("Download complete! Check bible_kjv.txt")

if __name__ == "__main__":
    main()