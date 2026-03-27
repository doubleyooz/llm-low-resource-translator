import csv
import os
import pandas as pd

from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from constants.output import LOG_FILENAME, OUTPUT_FOLDER
from logger import translation_logger
from utils.txt_helper import clean_text, sanitize_txt

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

def save_batch_to_csv(
    batch_results: List[Dict],
    filename: str,
    columns: List[str],    
    output_folder: str = None,
    dedup_columns: Optional[List[str]] = [], # if None → dedup on all columns, if [] → no dedup
    msg_prefix: str = 'Saving as csv | ',
    add_timestamp: bool = False
) -> Optional[Path]:    

    filename = sanitize_txt(filename)
    if add_timestamp:
        current_date = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{filename}_{current_date}"

    csv_filename = f"{filename}.csv" 
    
    try:        
        base_path = Path(translation_logger.get_filepath())       
        
        if output_folder:
            output_folder = sanitize_txt(output_folder)
            target_dir = (base_path / output_folder).resolve()
            # Ensure it stays under the logger base directory
            try:
                target_dir.relative_to(base_path.resolve())
            except ValueError:
                logger.warning(f"{msg_prefix} output_folder escapes base directory; falling back to base")
                target_dir = base_path
        else:
            target_dir = base_path
        
        # Ensure output folder exists        
        os.makedirs(target_dir, exist_ok=True)
        
        
        csv_file_path = target_dir / csv_filename
        csv_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not batch_results:
            logger.warning(f"{msg_prefix} Empty batch")
            return None
        
        df = pd.DataFrame(batch_results)

        # Ensure all expected columns exist
        for col in columns:
            if col not in df.columns:
                df[col] = None
        
       
        with open(csv_file_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(batch_results)
        
        # Deduplication
        if dedup_columns is None:
            # Default: all columns
            df_unique = df.drop_duplicates(keep='first')
        elif dedup_columns:
            # Subset of columns
            valid_subset = [c for c in dedup_columns if c in df.columns]
            if valid_subset:
                df_unique = df.drop_duplicates(subset=valid_subset, keep='first')
            else:
                logger.warning(f"{msg_prefix} No valid dedup columns → saving all")
                df_unique = df
        else:
            # dedup_columns = [] → no dedup
            df_unique = df

        if df_unique.empty:
            logger.warning(f"{msg_prefix} No rows after deduplication")
            return None
        
        df_unique = df_unique.apply(clean_text, axis=1)
        df_unique[columns].to_csv(csv_file_path, index=False, encoding="utf-8")

        removed = len(df) - len(df_unique)
        logger.info(
            f"{msg_prefix} CSV saved to {csv_file_path} "
            f"({len(df_unique):,} unique rows"
            f"{f', removed {removed:,} duplicates' if removed > 0 else ''})"
        )
        
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
