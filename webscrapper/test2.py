import re
from translate import tmxfile
import pandas as pd
from datasets import Dataset, DatasetDict
from datasets import load_metric

# Define a function to check for invalid characters
def has_invalid_characters(text):
    # Regular expression to detect non-standard characters (e.g., Æ, ±, etc.)
    invalid_pattern = r"[Æ±\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]"
    return bool(re.search(invalid_pattern, text))

# Input file name
input_file = "br-en.tmx"

# Lists to store the content of each output file
corrupted_content = []
curated_content = []

# Corrupted sentences (your list remains unchanged)
excluded_sentences = [
    "Efail-wen[1], pe Efailwen, zo ur gêriadenn e kornôg Sir Gaerfyrddin, e Kembre.",
    # ... (rest of your excluded sentences)
]

# Variables to track the current <tu> block
current_tu = []
in_tu = False

# Read the file as plain text
try:
    with open(input_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Detect the start of a <tu> block
            if "<tu>" in line:
                in_tu = True
                current_tu = [line]
                continue

            # Detect the end of a <tu> block
            if "</tu>" in line and in_tu:
                current_tu.append(line)
                in_tu = False

                # Join the current <tu> block into a single string for processing
                tu_block = "\n".join(current_tu)

                # Check if the Breton segment contains invalid characters
                br_seg_match = re.search(
                    r'<tuv xml:lang="br"><seg>(.*?)</seg></tuv>', tu_block, re.DOTALL
                )
                if br_seg_match:
                    br_text = br_seg_match.group(1)
                    if br_text in excluded_sentences:
                        current_tu = []
                        continue
                    if has_invalid_characters(br_text):
                        corrupted_content.append(tu_block)
                    else:
                        curated_content.append(tu_block)
                else:
                    curated_content.append(tu_block)

                current_tu = []
                continue

            # Add lines to the current <tu> block
            if in_tu:
                current_tu.append(line)
            else:
                # Preserve header/footer lines
                curated_content.append(line)
                corrupted_content.append(line)

except FileNotFoundError:
    print(f"Error: The file '{input_file}' was not found.")
    exit(1)
except UnicodeDecodeError:
    print(f"Error: The file '{input_file}' could not be decoded as UTF-8.")
    exit(1)

# Write to output files
with open("corrupted_translations.tmx", "w", encoding="utf-8") as f:
    f.write("\n".join(corrupted_content) + "\n")

with open("curated_translations.tmx", "w", encoding="utf-8") as f:
    f.write("\n".join(curated_content) + "\n")

print("Files generated: 'corrupted_translations.tmx' and 'curated_translations.tmx'")

# Function to convert TMX to DataFrame
def tmx_to_dataframe_translate_toolkit(tmx_path, source_lang, target_lang):
    data = []
    with open(tmx_path, "rb") as fin:
        tmx_file = tmxfile(fin, source_lang, target_lang)
        for node in tmx_file.unit_iter():
            # Use the lang attribute from the node's source language or fallback to provided source_lang
            source_lang_node = node.xmlelement.get("xml:lang") if node.xmlelement.get("xml:lang") else source_lang
            data.append({
                "source": node.source,
                "target": node.target,
                "source_language": source_lang_node,
                "target_language": target_lang,
            })
    return pd.DataFrame(data)

# Load and parse the TMX file
tmx_file_path = "curated_translations.tmx"
df = tmx_to_dataframe_translate_toolkit(tmx_file_path, "br", "en")

print("DataFrame head:")
print(df.head())

# Extract source and target texts
source_texts = df["source"].tolist()
target_texts = df["target"].tolist()

# Convert to a Hugging Face Dataset format for Breton-to-English
raw_datasets = DatasetDict({
    "train": Dataset.from_dict({
        "translation": [
            {"br": src, "en": tgt}
            for src, tgt in zip(source_texts, target_texts)
            if src is not None and tgt is not None  # Filter out None values
        ]
    })
})

# Load metric (for evaluating translations)
metric = load_metric("sacrebleu")

# Example: Inspect the first few entries
print("First 2 entries in the dataset:")
print(raw_datasets["train"][:2])