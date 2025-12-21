import csv
import os
from pathlib import Path
from typing import Dict, List
import pandas as pd
from constants.output import LOG_FILENAME, OUTPUT_FOLDER
from logger import translation_logger

FOLDER = './'

# Adjust these column names based on your actual CSV headers!
# Common guesses for a Celtic (e.g., Welsh/Breton/Cornish) ↔ English parallel dataset:

logger = translation_logger.get_logger(
    output_folder=OUTPUT_FOLDER,
    log_filename=LOG_FILENAME
)

def remove_columns_csv(
    filename: str,
    folder: str,
    source_col: str,
    target_col: str,
    columns_to_remove: List[str] = [],
    batch_msg: str = ''):
    
    if not filename or not folder or not source_col or not target_col:
        raise f"All parameters are required -> filename: {filename}, folder: {folder}, source_col: {source_col}, target_col: {target_col}"
    filename = filename.removeprefix(folder)

    # Load the CSV
    df = pd.read_csv(f"{folder}/{filename}")
    
    cleaned_file = f"{folder}/unique.csv"
    duplicates_file = f"{folder}/duplicates.csv"

    logger.debug(f"{batch_msg} Original entries: {len(df)}")
    logger.debug(f"{batch_msg} Columns: {list(df.columns)}", )
    logger.debug(f"{batch_msg} First few rows:")
    logger.debug(df.head())

    # Optional: Remove column(s) – you can list multiple

    df = df.drop(columns=columns_to_remove)
    logger.debug(f"{batch_msg} Removed columns: {columns_to_remove}")

    # Detect duplicates based on the parallel pair (source + target)
    # This marks ALL occurrences of duplicates (including the first)
    duplicate_mask = df.duplicated(subset=[source_col, target_col], keep=False)


    # If you want to keep ONLY ONE occurrence of each duplicate:
    unique_df = df.drop_duplicates(subset=[source_col, target_col], keep='first')
    duplicates_df = df[df.duplicated(subset=[source_col, target_col], keep=False)]

    # Save
    df.to_csv(duplicates_file, index=False)

    logger.info(f"{batch_msg} Df entries   : {len(df)}")
    logger.info(f"{batch_msg} → Saved unique data → {cleaned_file}")
    logger.info(f"{batch_msg} → Saved duplicates  → {duplicates_file}")

def save_batch_to_csv(batch_results: List[Dict], filename: str, columns: List[str], msg_prefix: str = 'Saving as csv | '):    
    filename = Path(filename).stem  # Remove any existing extension
    csv_filename = f"{filename}.csv"
 
    
    try:        
        base_path = Path(translation_logger.get_filepath())
        csv_file_path = base_path / csv_filename

        csv_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure all dictionaries have all columns (fill missing with None)
        sanitized_results = []
        for row in batch_results:
            sanitized_row = {col: row.get(col) for col in columns}
            sanitized_results.append(sanitized_row)
            
        with open(csv_file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(batch_results)
            
        logger.info(f"{msg_prefix} csv saved to {csv_file_path}")
        
        # Verify file was created
        if csv_file_path.exists() and csv_file_path.stat().st_size > 0:
            logger.info(f"{msg_prefix} Successfully saved {len(batch_results)} rows to {csv_file_path}")
            return csv_file_path
        else:
            logger.error(f"{msg_prefix} File was created but appears to be empty: {csv_file_path}")
            return None
        
    except Exception as e:
        logger.error(f"{msg_prefix} Failed to save {filename} to CSV: {e}")
        return None
