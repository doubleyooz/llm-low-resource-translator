import json
import os
from collections import defaultdict, Counter
import statistics
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

# Step 1: Count verses + collect entries per chapter
chapter_verse_counts = defaultdict(lambda: defaultdict(int))
chapter_entries = defaultdict(list)

for entry in data:
    key = (entry['book_name'], entry['chapter'])
    chapter_entries[key].append(entry)
    
    for v in versions:
        text = entry.get(v, '').strip()
        if text:
            chapter_verse_counts[key][v] += 1

# Step 2: Analyze only inconsistent chapters
inconsistent_chapters = []
report_lines = ["INCONSISTENT CHAPTERS ANALYSIS REPORT\n" + "="*60 + "\n"]

for chapter_key, counts in chapter_verse_counts.items():
    count_values = list(counts.values())
    if len(set(count_values)) <= 1:
        continue  # Consistent → skip
    
    inconsistent_chapters.append(chapter_key)
    
    report_lines.append(f"{chapter_key[0]} {chapter_key[1]}")
    report_lines.append(f"Verse counts per version: {dict(sorted(counts.items(), key=lambda x: x[1]))}")
    
    majority_count = Counter(count_values).most_common(1)[0][0]
    minority_versions = [v for v, c in counts.items() if c != majority_count]
    
    report_lines.append(f"Majority has {majority_count} verses")
    report_lines.append(f"Outlier versions (wrong count): {minority_versions}\n")
    
    # Group texts by verse number
    verse_groups = defaultdict(dict)  # verse_num -> version -> text
    for entry in chapter_entries[chapter_key]:
        vnum = entry['verse']
        for v in versions:
            text = entry.get(v, '').strip()
            if text:
                verse_groups[vnum][v] = text
    
    report_lines.append("Suspected merged verses (significantly longer text in outlier versions):")
    found_merge = False
    
    for vnum, version_texts in sorted(verse_groups.items()):
        if len(version_texts) < 2:
            continue  # Can't compare
        
        lengths = {v: len(text) for v, text in version_texts.items()}
        avg_len = statistics.mean(lengths.values())
        
        # Find versions that are >30% longer than average
        long_versions = [v for v, l in lengths.items() if l > avg_len * 1.3]
        
        # Only flag if the long version is one of the structural outliers
        suspected = [v for v in long_versions if v in minority_versions]
        
        if suspected:
            found_merge = True
            for v in suspected:
                text = version_texts[v]
                snippet = text.replace('\n', ' ')[:300]
                report_lines.append(
                    f"  → Verse {vnum} in {v}: likely merged (len={lengths[v]}, avg={avg_len:.0f})"
                )
                report_lines.append(f"    Text: \"{snippet}{'...' if len(text) > 300 else ''}\"")
                report_lines.append("")  # blank line
    
    if not found_merge:
        report_lines.append("  (No clear merged verse detected by length — may be missing verse or complex misalignment)\n")
    
    report_lines.append("-" * 60 + "\n")

print(f"Found {len(inconsistent_chapters)} inconsistent chapters.")
print("Full detailed report generated and saved.\n")

# Save report
report_path = os.path.join(input_dir, 'inconsistent_chapters_report.txt')
with open(report_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report_lines))

# Save inconsistent chapters JSON again (for easy loading later)
inconsistent_data = []
for entry in data:
    if (entry['book_name'], entry['chapter']) in inconsistent_chapters:
        inconsistent_data.append(entry)

inconsistent_json_path = os.path.join(input_dir, 'parallel_corpus_inconsistent_chapters.json')
with open(inconsistent_json_path, 'w', encoding='utf-8') as f:
    json.dump(inconsistent_data, f, ensure_ascii=False, indent=2)

print(f"Report saved to: {report_path}")
print(f"Inconsistent chapters JSON saved to: {inconsistent_json_path}")
print("\nOpen the .txt report — it will show you exactly which versions have merged text,")
print("and give you the full text snippet so you can manually split/fix it.")