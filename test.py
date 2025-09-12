from playwright.sync_api import sync_playwright
import re
import random
import time
import csv
from tqdm import tqdm

# Proxy list (example: replace with your own proxies)
proxies = [
    {"server": "http://proxy1.example.com:8080"},  # No auth
    {"server": "http://proxy2.example.com:8080"},
    {"server": "http://user:pass@proxy3.example.com:8080"},  # With auth
    # Add more proxies as needed
]

# Function to extract English segments from corrupted TMX text file
def extract_english_segments(txt_path):
    english_segments = []
    with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
        matches = re.findall(r'<tuv lang="en".*?>(.*?)</tuv>', content, re.DOTALL)
        for match in matches:
            text = re.sub(r'<[^>]+>', '', match).strip()
            if text:
                english_segments.append(text)
    return english_segments

# Function to translate a single sentence
def translate_sentence(page, sentence):
    url = "https://translate.google.com/?sl=en&tl=br&text=" + sentence.replace(" ", "%20")
    page.goto(url)
    page.wait_for_selector("span[jsname='W297wb']", timeout=10000)
    translation = page.query_selector("span[jsname='W297wb']").inner_text()
    return translation.strip()

# Main process
txt_file_path = "corrupted_target_translations.tmx"
output_file = "translated_corrupted_target.csv"

# Extract English segments
print(f"Extracting English sentences from {txt_file_path}...")
english_sentences = extract_english_segments(txt_file_path)

if not english_sentences:
    print("No English segments found.")
    exit(1)

print(f"Found {len(english_sentences)} sentences. Starting translation...")

# Limit to a subset for testing (remove or adjust for full run)
# english_sentences = english_sentences[:10]  # Uncomment to test with 10 sentences

# Start Playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    translations = []
    batch_size = 20  # Change IP every 20 translations

    # Process sentences in batches
    for i in range(0, len(english_sentences), batch_size):
        # Select proxy for this batch (cycle through proxies list)
        proxy = proxies[i // batch_size % len(proxies)]
        print(f"Using proxy: {proxy['server']} for batch {i // batch_size + 1}")

        # Create a new context with the current proxy
        context = browser.new_context(
            proxy=proxy,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        page = context.new_page()

        # Process this batch of sentences
        batch_sentences = english_sentences[i:i + batch_size]
        for sentence in tqdm(batch_sentences, desc=f"Translating batch {i // batch_size + 1} to Breton"):
            try:
                breton_translation = translate_sentence(page, sentence)
                translations.append({"en": sentence, "br": breton_translation})
                print(f"\nTranslated: {sentence} -> {breton_translation}")
            except Exception as e:
                print(f"\nError translating '{sentence}': {e}")
                translations.append({"en": sentence, "br": "Translation failed"})

            # Random delay between translations
            time.sleep(random.uniform(1, 3))

        # Close context after batch is done
        context.close()

        # Optional: Add a longer delay between batches to avoid rate limiting
        if i + batch_size < len(english_sentences):
            print("Waiting before switching IP...")
            time.sleep(random.uniform(5, 10))

    # Close browser
    browser.close()

# Save to CSV
with open(output_file, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["en", "br"])
    writer.writeheader()
    writer.writerows(translations)

print(f"Translations saved to {output_file}")