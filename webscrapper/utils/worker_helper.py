import json
from pathlib import Path
from typing import Dict, List, Tuple

from constants.output import LOG_FILENAME, OUTPUT_FOLDER
from utils.txt_helper import get_last_directory_alphabetic

from logger import translation_logger

logger = translation_logger.get_logger(
    output_folder=OUTPUT_FOLDER,
    log_filename=LOG_FILENAME
)

def get_latest_iteration(
    expected_pattern: str,
    output_folder = OUTPUT_FOLDER,
    subfolder = "partial_results",
    batch_msg = '',
    return_all_matches = False
    ) -> Tuple[List[Dict], int]:
    last_iteration = get_last_directory_alphabetic(output_folder, second_last=True)
    logger.warning(f"{batch_msg} Checking for previous iteration: {last_iteration}")
    corpus_entries = []
    error_count = 0
    if last_iteration:
        prev_partial_dir = Path(output_folder) / last_iteration / subfolder
        logger.warning(f"{batch_msg} Looking for previous partial results in: {prev_partial_dir}")
        if prev_partial_dir.exists():
            # Expected filename pattern:
            # Something like: Worker_X_Batch_..._{suffix}_{abbrev}_chapters_{start}-{end}.json
            # We'll build the expected pattern from current batch info
        
            matching_files = list(prev_partial_dir.glob(expected_pattern))
            
            if matching_files:
                # Found one or more matching files — assume the work is already done
                
                if return_all_matches:
                    for file_path in matching_files:
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                data = json.load(f)
                                if isinstance(data, list):
                                    corpus_entries.extend(data)
                                else:
                                    corpus_entries.append(data)
                               
                        except Exception as e:
                            logger.error(f"{batch_msg} Failed to load existing JSON {latest_match}: {e}")
                            error_count += 1
                    
                    # corpus_entries = [item for sublist in corpus_entries for item in sublist]
                    
                    logger.info(f"{batch_msg} Loaded {len(corpus_entries)} existing entries from previous run.")

                else:           
                    latest_match = max(matching_files, key=lambda p: p.stat().st_mtime)  # most recent if multiple
                    logger.info(f"{batch_msg} Found existing complete results: {latest_match.name}")
                    logger.info(f"{batch_msg} Skipping processing — reusing existing data.")
                    
                    try:
                        with open(latest_match, "r", encoding="utf-8") as f:
                            corpus_entries = json.load(f)
                        logger.info(f"{batch_msg} Loaded {len(corpus_entries)} existing entries from previous run.")

                    except Exception as e:
                        logger.error(f"{batch_msg} Failed to load existing JSON {latest_match}: {e}")
                        error_count += 1
                        # Fall through to normal processing
            else:
                logger.info(f"{batch_msg} No matching completed batch found in previous iteration {expected_pattern}. Starting fresh.")
        else:
            logger.info(f"{batch_msg} No partial_results folder in previous iteration.")
    else:
        logger.info(f"{batch_msg} No previous iteration found. Starting fresh.")
        
    return corpus_entries, error_count
   