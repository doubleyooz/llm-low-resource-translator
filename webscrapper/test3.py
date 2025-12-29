import json
import os
from collections import defaultdict
from constants.output import OUTPUT_FOLDER
from utils.txt_helper import get_last_directory_alphabetic

# Load the data
input_dir = f'{OUTPUT_FOLDER}/{get_last_directory_alphabetic(OUTPUT_FOLDER)}'
input_path = os.path.join(input_dir, 'parallel_corpus.json')

with open(input_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Auto-detect versions
versions = [key for key in data[0].keys() if key.endswith('_text')]
print(f"Detected versions: {versions}")

# Step 1: Count verses per version per chapter
chapter_verse_counts = defaultdict(lambda: defaultdict(int))  # (book, chapter) -> version -> count

for entry in data:
    key = (entry['book_name'], entry['chapter'])
    for v in versions:
        text = entry.get(v, '').strip()
        if text:
            chapter_verse_counts[key][v] += 1

# Step 2: Determine which chapters are perfectly consistent
consistent_chapters = set()
inconsistent_chapters = set()

for chapter_key, counts in chapter_verse_counts.items():
    # Get all verse counts for this chapter across versions that have any text
    verse_counts = list(counts.values())
    
    if not verse_counts:
        inconsistent_chapters.add(chapter_key)
        continue
    
    # All versions must have exactly the same number of verses
    if len(set(verse_counts)) == 1:
        consistent_chapters.add(chapter_key)
    else:
        inconsistent_chapters.add(chapter_key)
        print(f"Inconsistent chapter: {chapter_key[0]} {chapter_key[1]} "
              f"— verse counts: {dict(counts)}")

print(f"\nConsistent chapters: {len(consistent_chapters)}")
print(f"Inconsistent chapters (will be separated): {len(inconsistent_chapters)}")

# Step 3: Split the data
consistent_data = []
inconsistent_data = []

for entry in data:
    chapter_key = (entry['book_name'], entry['chapter'])
    
    if chapter_key in consistent_chapters:
        consistent_data.append(entry)
    else:
        inconsistent_data.append(entry)

# Step 4: Save both files
output_dir = input_dir
consistent_path = os.path.join(output_dir, 'parallel_corpus_perfect.json')
inconsistent_path = os.path.join(output_dir, 'parallel_corpus_inconsistent_chapters.json')

with open(consistent_path, 'w', encoding='utf-8') as f:
    json.dump(consistent_data, f, ensure_ascii=False, indent=2)

with open(inconsistent_path, 'w', encoding='utf-8') as f:
    json.dump(inconsistent_data, f, ensure_ascii=False, indent=2)

print(f"\nSaved:")
print(f"  • Perfectly aligned corpus ({len(consistent_chapters)} chapters):")
print(f"    {consistent_path}")
print(f"    → {len(consistent_data)} verses")
print(f"  • Inconsistent chapters saved separately ({len(inconsistent_chapters)} chapters):")
print(f"    {inconsistent_path}")
print(f"    → {len(inconsistent_data)} verses")