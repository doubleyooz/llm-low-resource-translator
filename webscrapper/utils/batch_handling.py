import random
import threading
import time


from constants.output import LOG_FILENAME, OUTPUT_FOLDER
from utils.pw_helper import get_random_delay
from scrapper_config import CONFIG
from logger import translation_logger

class BatchScheduler:

    __logger = translation_logger.get_logger(
        output_folder=OUTPUT_FOLDER,
        log_filename=LOG_FILENAME
    )

    def __init__(self, max_workers: int):
        self.last_batch_start_time = 0
        self.batch_timing_lock = threading.Lock()
        self.completed_batches = 0
        self.completed_batches_lock = threading.Lock()
        self.max_workers = max_workers
        

    def ensure_interval_before_next_batch(self, batch_idx: int, total_of_batches: int, msg: str = ""):
        """
        Applies a random delay before allowing the next batch if there are enough remaining batches.
        """
        self.__logger.debug(f"{msg} Ensuring interval before next batch...")
        with self.completed_batches_lock:
            self.completed_batches += 1
            remaining_batches = total_of_batches - self.completed_batches
            if self.max_workers <= remaining_batches:
                self.__logger.info(f"{msg} Sleeping before next batch...")
                get_random_delay(
                    delay_range=CONFIG["new_batch_delay_range"],
                    fatigue=1 + (batch_idx / (CONFIG['batch_size'] * self.max_workers)) * 3,
                    msg=msg
                )
                self.__logger.info(f"{msg} Next batch is ready to start...")

    def ensure_batch_interval(self, msg: str):
        """
        Ensures a minimum time interval between the start of consecutive requests.
        """
        with self.batch_timing_lock:
            current_time = time.time()
            time_since_last_batch = current_time - self.last_batch_start_time
            
            batch_interval = random.randint(CONFIG["min_batch_interval"], CONFIG["max_batch_interval"])
            if time_since_last_batch < batch_interval:
                wait_time = batch_interval - time_since_last_batch
                self.__logger.info(f"{msg} Waiting {wait_time:.2f}s to maintain batch interval")
                time.sleep(wait_time)
            
            self.last_batch_start_time = time.time()