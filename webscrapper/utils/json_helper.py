import json
from collections import OrderedDict
import os
from pathlib import Path
from typing import Dict, List

from constants.languages import OL, SL, TL
from constants.output import LOG_FILENAME, OUTPUT_FOLDER
from logger import translation_logger
from utils.txt_helper import sanitize_txt

logger = translation_logger.get_logger(
    output_folder=OUTPUT_FOLDER,
    log_filename=LOG_FILENAME
)


# CURRENT_ITERACTION = '20251212_232342'
CURRENT_ITERACTION = '20251215_090122'
FOLDER = f'output/translation_{SL}2{TL}_{CURRENT_ITERACTION}'
FOLDER = './'
ORIGINAL_FILE = f"{FOLDER}/{SL}_{TL}_{OL}_parallel.json"
ORIGINAL_FILE = f"{FOLDER}/merged-1765838350936.json"
CLEANED_FILE = f"{FOLDER}/unique.json"
DUPLICATES_FILE = f"{FOLDER}/duplicates.json"
KEY_TO_REMOVE = 'english'

def remove_keys_json(    
    data: List[Dict],
    keys_to_remove: List[str] = [],
    filepath: str = '',
    msg: str = ''
):
    if filepath:
        with open(f'{filepath}', "r", encoding="utf-8") as f:
            data: List[Dict] = json.load(f)
    
    if len(data) == 0:
        logger.debug(f"{msg} The data is empty.")
        return data
    
    logger.debug(f'{msg} Removing keys: {data[0].keys()}')    
    for entry in data:
        for key in keys_to_remove:            
            if key in entry:
                del entry[key]
    logger.debug(f'{msg} Remaining keys: {data[0].keys()}')
    return data

def remove_duplicates_json(
    filename: str,
    folder: str,
    source_col: str,
    target_col: str,
    keys_to_remove: List[str] = [],
    msg: str = ''):
    
    if not filename or not folder or not source_col or not target_col:
        raise f"All parameters are required -> filename: {filename}, folder: {folder}, source_col: {source_col}, target_col: {target_col}"
    filename = filename.removeprefix(folder)


    # We use an OrderedDict to preserve the original order while tracking seen en values
    seen_en = OrderedDict()  # value → index in the list
    seen_br = OrderedDict()
    duplicates = []

    with open(f'{folder}/{filename}', "r", encoding="utf-8") as f:
        data = json.load(f)

    if keys_to_remove:
        remove_keys_json(data, keys_to_remove)
  

    # First pass: identify duplicates
    for idx, entry in enumerate(data):
        en_text = entry[source_col].strip()  # strip in case of hidden spaces
        br_text = entry[target_col].strip()  # strip in case of hidden spaces
       
        if en_text in seen_en and br_text in seen_br:
            duplicates.append((idx, entry))
        else:
            seen_en[en_text] = idx
            seen_br[br_text] = idx

    # Create the cleaned list (preserves original order)
    unique_data = [entry for idx, entry in enumerate(data) if idx not in {i for i, _ in duplicates}]


    # Extract only the duplicate entries (keep the first occurrence out)
    duplicate_entries = [entry for _, entry in duplicates]

        
    cleaned_file = f"{folder}/unique.json"
    duplicates_file = f"{folder}/duplicates.json"

    # Save results
    save_batch_to_json(unique_data, cleaned_file, "Saving cleaned file |")
    save_batch_to_json(duplicate_entries, duplicates_file, "Saving duplicate file |")
    
    logger.info(f"{msg} Original entries : {len(data)}")
    logger.info(f"{msg} Unique entries   : {len(unique_data)}")
    logger.info(f"{msg} Duplicates found : {len(duplicate_entries)}")
    logger.info(f"{msg} → Saved unique data → {CLEANED_FILE}")
    logger.info(f"{msg} → Saved duplicates  → {DUPLICATES_FILE}")
    


def save_batch_to_json(batch_results: List[Dict], filename: str, output_folder: str = None, msg_prefix: str = 'Saving as json |', indent: int = 2):
  
    filename = sanitize_txt(filename)
   
    filename = Path(filename).name
    
    if not filename.lower().endswith('.json'):
        filename = f"{Path(filename).stem}.json"
    
    base_path = Path(translation_logger.get_filepath())
    try:        
        if output_folder:
            output_folder = sanitize_txt(output_folder)
            
            target_dir = (base_path / output_folder).resolve()
            # Ensure it is still under the logger's base directory
            try:
                target_dir.relative_to(base_path.resolve())
            except ValueError:
                logger.warning(f"{msg_prefix} output_folder escapes base directory; falling back to base")
                target_dir = base_path
        else:
            target_dir = base_path

        json_file_path = target_dir / filename
        
        # Create directory if needed
        json_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Validate input
        if not batch_results:
            logger.warning(f"{msg_prefix} No data to save")
            return None
        
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(batch_results, f, ensure_ascii=False, indent=indent)
        
        # Verify file was created
        if json_file_path.exists() and json_file_path.stat().st_size > 0:
            logger.info(f"{msg_prefix} Saved {len(batch_results)} records to {json_file_path}")
            return str(json_file_path)
        else:
            logger.error(f"{msg_prefix} File was created but appears to be empty: {json_file_path}")
            return None 
         
    except (OSError, json.JSONEncodeError) as e:
        logger.error(f"{msg_prefix} Failed to save {filename}: {e}")
        return None

    except Exception as e:
        logger.error(f"{msg_prefix} Unexpected error: {e}")
        return None
