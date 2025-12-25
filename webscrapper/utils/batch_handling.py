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
        
        self.sleeping_batches = 0
        self.sleeping_batches_lock = threading.Lock()
        

    def ensure_interval_before_next_batch(self, total_of_batches: int, msg: str = ""):
        """
        Applies a random delay before allowing the next batch if there are enough remaining batches.
        """
        if self.get_sleeping_batches_count() > self.max_workers/2:
                return None
        
        if self.completed_batches >= total_of_batches:
            return None
        
        self.__logger.debug(f"{msg} Ensuring interval before next batch...")
        with self.completed_batches_lock:
            self.completed_batches += 1
            remaining_batches = total_of_batches - self.completed_batches
                
            completed_ratio = self.completed_batches / total_of_batches
            
            if self.max_workers <= remaining_batches:
                self.__logger.info(f"{msg} Sleeping before next batch...")
                
                # Simple fatigue calculation: starts at 1, approaches 2.5 near completion
                # Using a simple linear approach: fatigue = 1 + 2 * completion_ratio
                fatigue = 0.5 + (2.0 * completed_ratio)
                
                with self.sleeping_batches_lock:
                    self.sleeping_batches += 1
                
                                  
                new_batch_delay_range = CONFIG.get("new_batch_delay_range", (60, 180))

                if self.get_sleeping_batches_count() >= self.max_workers/4:
                    new_batch_delay_range = tuple(item * 0.5 for item in new_batch_delay_range)
                
                get_random_delay(
                    delay_range=new_batch_delay_range,
                    fatigue=fatigue,
                    msg=msg,
                    verbose=True
                )
                
                with self.sleeping_batches_lock:
                    self.sleeping_batches -= 1
                
                self.__logger.info(f"{msg} Next batch is ready to start...")
            else:
                self.__logger.info(f"{msg} Not enough remaining batches ({remaining_batches}) to enforce delay.")

    def ensure_batch_interval(self, msg: str):
        """
        Ensures a minimum time interval between the start of consecutive requests.
        """
      
        with self.batch_timing_lock:
            current_time = time.time()
            time_since_last_batch = current_time - self.last_batch_start_time
            
            batch_interval = random.randint(CONFIG["min_batch_interval"], CONFIG["max_batch_interval"])
                       
            if self.get_sleeping_batches_count() >= self.max_workers/4:
                    batch_interval = batch_interval * 0.5
                    
            with self.sleeping_batches_lock:
                    self.sleeping_batches += 1
                
            if time_since_last_batch < batch_interval:
                wait_time = batch_interval - time_since_last_batch
                self.__logger.info(f"{msg} Waiting {wait_time:.2f}s to maintain batch interval")
                time.sleep(wait_time)
                
            with self.sleeping_batches_lock:
                self.sleeping_batches -= 1
                
            self.last_batch_start_time = time.time()
            
    def get_sleeping_batches_count(self):
        """Get the number of batches currently sleeping."""
        with self.sleeping_batches_lock:
            return self.sleeping_batches
        
    def set_max_workers(self, max_workers: int):
        if max_workers < 1:
            raise ValueError("max_workers must be at least 1")
        self.max_workers = max_workers