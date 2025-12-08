import json
import hashlib
from collections import OrderedDict
from pathlib import Path

from constants.languages import OL, SL, TL

CURRENT_ITERACTION = '20251207_224427'
# CURRENT_ITERACTION = '20251208_112939'
FOLDER = f'output/translation_{SL}2{TL}_{CURRENT_ITERACTION}'

ORIGINAL_FILE = f"{FOLDER}/{SL}_{TL}_{OL}_parallel.json"
CLEANED_FILE = f"{FOLDER}/unique.json"
DUPLICATES_FILE = f"{FOLDER}/duplicates.json"

# We use an OrderedDict to preserve the original order while tracking seen en values
seen_en = OrderedDict()  # value → index in the list
seen_br = OrderedDict()
duplicates = []

with open(ORIGINAL_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# First pass: identify duplicates
for idx, entry in enumerate(data):
    en_text = entry["en"].strip()  # strip in case of hidden spaces
    br_text = entry["br"].strip()  # strip in case of hidden spaces
    if en_text in seen_en and br_text in seen_br:
        duplicates.append((idx, entry))
    else:
        seen_en[en_text] = idx
        seen_br[br_text] = idx

# Create the cleaned list (preserves original order)
unique_data = [entry for idx, entry in enumerate(data) if idx not in {i for i, _ in duplicates}]

# Extract only the duplicate entries (keep the first occurrence out)
duplicate_entries = [entry for _, entry in duplicates]

# Save results
with open(CLEANED_FILE, "w", encoding="utf-8") as f:
    json.dump(unique_data, f, ensure_ascii=False, indent=2)

with open(DUPLICATES_FILE, "w", encoding="utf-8") as f:
    json.dump(duplicate_entries, f, ensure_ascii=False, indent=2)

print(f"Original entries : {len(data)}")
print(f"Unique entries   : {len(unique_data)}")
print(f"Duplicates found : {len(duplicate_entries)}")
print(f"→ Saved unique data → {CLEANED_FILE}")
print(f"→ Saved duplicates  → {DUPLICATES_FILE}")