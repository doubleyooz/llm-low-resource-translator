import json
import os
from collections import defaultdict, Counter
import statistics
from constants.output import OUTPUT_FOLDER
from utils.txt_helper import get_last_directory_alphabetic

# Load the data
input_dir = f'{OUTPUT_FOLDER}/{get_last_directory_alphabetic(OUTPUT_FOLDER)}'
input_path = os.path.join(input_dir, 'parallel_corpus_inconsistent_chapters.json')

with open(input_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Auto-detect versions
versions = [key for key in data[0].keys() if key.endswith('_text')]
print(f"Detected versions: {versions}")

ACCEPTABLE_LENGTH_VARIATION = 1.37

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
good_prefix_data = []
suffix_with_merge_data = []

report_lines = ["INCONSISTENT CHAPTERS ANALYSIS REPORT\n" + "="*60 + "\n"]

for chapter_key, counts in chapter_verse_counts.items():
    count_values = list(counts.values())
    if len(set(count_values)) <= 1:
        good_prefix_data.extend(chapter_entries[chapter_key])
        continue
    
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
    
    # Find the EARLIEST suspicious merge
    first_suspicious_verse = None
    suspicious_info = None
    
    report_lines.append("Suspected merged verses (significantly longer text in outlier versions):")

    for vnum, version_texts in sorted(verse_groups.items()):
        if len(version_texts) < 2:
            continue  # Can't compare385
        
        lengths = {v: len(text) for v, text in version_texts.items()}
        non_zero_lengths = [l for l in lengths.values() if l > 0]
        if not non_zero_lengths:
            continue
        
        avg_len = statistics.mean(lengths.values())
        
        # Find versions that are >30% longer than average
        long_outliers = [
            v for v, length in lengths.items()
            if length > avg_len * ACCEPTABLE_LENGTH_VARIATION
            and v in minority_versions
        ]
        
        if long_outliers:
            first_suspicious_verse = vnum
            suspicious_info = (vnum, long_outliers, lengths)
            break
    
    report_lines.append(f"{chapter_key[0]} {chapter_key[1]}")
    report_lines.append(f"  Verse counts: {dict(counts)}")
    report_lines.append(f"  Minority versions: {minority_versions}")
    
    if first_suspicious_verse is None:
        # No clear merge found → treat whole chapter as potentially bad or move to good
        # (you can change this logic)
        report_lines.append("  → No suspicious merge detected — whole chapter to good prefix")
        good_prefix_data.extend(chapter_entries[chapter_key])
    else:
        good = [e for e in chapter_entries[chapter_key] if e['verse'] < first_suspicious_verse]
        suffix = [e for e in chapter_entries[chapter_key] if e['verse'] >= first_suspicious_verse]
        
        good_prefix_data.extend(good)
        suffix_with_merge_data.extend(suffix)
        
        vnum, suspects, lens = suspicious_info
        report_lines.append(
            f"  → Split at verse {vnum} (first suspicious merge)"
        )
        report_lines.append(f"     Good prefix: {len(good)} verses")
        report_lines.append(f"     Suffix incl. merge: {len(suffix)} verses")
        report_lines.append(f"     Suspect in: {suspects}")
        report_lines.append(f"     Lengths at v{vnum}: {lens}")

    report_lines.append("-" * 60 + "\n")

output_good_prefix = os.path.join(input_dir, 'parallel_corpus_salvaged.json')
output_suffix_merge = os.path.join(input_dir, 'parallel_corpus_suspected_merge.json')
report_path = os.path.join(input_dir, 'split_at_first_merge_report.txt')

with open(output_good_prefix, 'w', encoding='utf-8') as f:
    json.dump(good_prefix_data, f, ensure_ascii=False, indent=2)

with open(output_suffix_merge, 'w', encoding='utf-8') as f:
    json.dump(suffix_with_merge_data, f, ensure_ascii=False, indent=2)

with open(report_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report_lines))

print("\nDone.")
print(f"  Good prefix (verses before first suspicious merge): {len(good_prefix_data):,} verses")
print(f"  Suffix incl. merge (from suspicious onward): {len(suffix_with_merge_data):,} verses")
print(f"  Report with split points: {report_path}")
print("\nNow you can manually fix only the suffix file → much smaller scope.")