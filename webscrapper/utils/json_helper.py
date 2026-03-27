import json
from collections import OrderedDict

from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from constants.languages import OL, SL, TL
from constants.output import LOG_FILENAME, OUTPUT_FOLDER
from logger import translation_logger
from utils.list_helper import remove_duplicates_from_list
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
    
def _save_json_data(
    data: List[Dict],
    filepath: Path,
    indent: int = 2,
    msg_prefix: str = "Saving JSON |"
) -> bool:
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        if filepath.exists() and filepath.stat().st_size > 0:
            logger.info(f"{msg_prefix} Saved {len(data)} records to {filepath}")
            return True
        else:
            logger.error(f"{msg_prefix} File created but appears empty: {filepath}")
            return False
    except (OSError, json.JSONEncodeError) as e:
        logger.error(f"{msg_prefix} Failed to save {filepath}: {e}")
        return False
    except Exception as e:
        logger.error(f"{msg_prefix} Unexpected error: {e}")
        return False
def save_batch_to_json(
    batch_results: List[Dict],
    filename: str,
    output_folder: str = None,
    msg_prefix: str = 'Saving as json |',
    indent: int = 2,
    remove_duplicates: bool = False,
    columns: Optional[List[str]] = None,
    keys_to_remove: Optional[List[str]] = None,
    save_duplicates: bool = False,
    duplicate_filename: Optional[str] = None,
    add_timestamp: bool = False
) -> Optional[str]:
    """
    Save a list of dictionaries to a JSON file. Optionally remove duplicates
    based on one or more columns and save duplicates separately.
    """
    if remove_duplicates:
        if not columns:
            raise ValueError("columns list must be provided when remove_duplicates=True")
        if not isinstance(columns, list) or len(columns) == 0:
            raise ValueError("columns must be a non-empty list of column names")

    filename = sanitize_txt(filename)
    if add_timestamp:
        current_date = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{filename}_{current_date}"
    if not filename.lower().endswith('.json'):        
        filename = f"{Path(filename).stem}.json"

    base_path = Path(translation_logger.get_filepath())
    try:
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

        json_file_path = target_dir / filename
        json_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Validate input data
        if not batch_results:
            logger.warning(f"{msg_prefix} No data to save")
            return None

        # --- Optional duplicate removal ---
        if remove_duplicates:
            # Use the helper to deduplicate
            unique_data, duplicate_entries = remove_duplicates_from_list(
                batch_results,
                columns=columns,
                keys_to_remove=keys_to_remove,
                strip=True,
                preserve_order=True
            )

            logger.info(f"{msg_prefix} Duplicate removal: {len(batch_results)} total -> "
                        f"{len(unique_data)} unique, {len(duplicate_entries)} duplicates "
                        f"(based on columns: {columns})")

            # Replace batch_results with unique data
            batch_results = unique_data

            # Save duplicates if requested
            if save_duplicates and duplicate_entries:
                if duplicate_filename is None:
                    stem = Path(filename).stem
                    duplicate_filename = f"{stem}_duplicates.json"
                else:
                    duplicate_filename = sanitize_txt(duplicate_filename)
                    if not duplicate_filename.lower().endswith('.json'):
                        duplicate_filename = f"{Path(duplicate_filename).stem}.json"

                dup_file_path = target_dir / duplicate_filename
                success = _save_json_data(duplicate_entries, dup_file_path, indent,
                                          f"{msg_prefix} (duplicates) |")
                if success:
                    logger.info(f"{msg_prefix} Duplicates saved to {dup_file_path}")
                else:
                    logger.error(f"{msg_prefix} Failed to save duplicates to {dup_file_path}")

        # --- Save the (possibly deduplicated) main data ---
        success = _save_json_data(batch_results, json_file_path, indent, msg_prefix)
        if success:
            return str(json_file_path)
        else:
            return None

    except (OSError, json.JSONEncodeError) as e:
        logger.error(f"{msg_prefix} Failed to save {filename}: {e}")
        return None
    except Exception as e:
        logger.error(f"{msg_prefix} Unexpected error: {e}")
        return None