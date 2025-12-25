# logger.py
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Optional

from constants.output import OUTPUT_FOLDER
from utils.txt_helper import sanitize_txt

class SingletonLogger:
    _instance: Optional['SingletonLogger'] = None
    _initialized: bool = False
    
    _filepath: Optional[str] = None
    _log_filename: Optional[str] = None
    _ext = ".log"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.logger: Optional[logging.Logger] = None
            self._initialized = True

    def get_filepath(self) -> Optional[str]:
        return self._filepath

    def setup_logger(self, output_folder: str = None, log_filename: str = None, level= logging.INFO) -> logging.Logger:
        """
        Setup the logger with file and console handlers.
        
        Args:
            output_folder: Path to the output directory
            source_lang: Source language code (e.g., 'fr')
            target_lang: Target language code (e.g., 'en')
            
        Returns:
            Configured logger instance
        """
        if self.logger is not None:
            return self.logger

        # If no output folder specified, use current script directory
        if output_folder is None:
            script_dir = Path(__file__).parent
            folder_name = OUTPUT_FOLDER or "output"
            output_folder = script_dir / folder_name
        else:
            output_folder = Path(output_folder)

        # Ensure output folder exists        
        os.makedirs(output_folder, exist_ok=True)
        
        current_date = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if log_filename:
            log_filename = log_filename.split('.')
            self._log_filename = f"{sanitize_txt(log_filename[0])}_{current_date}"
        else:
            self._log_filename =  f"{hash(f'{current_date}_{output_folder}')}_{current_date}"
              

        # Create log filename with timestamp
        self._filepath = os.path.join(
            output_folder,
            self._log_filename
        )
        
        # Create folder within the output folder
        os.makedirs(self._filepath, exist_ok=True)
        
        self._log_filename = os.path.join(
            output_folder,
            self._log_filename,
            f"{self._log_filename}.{self._ext}"
        )


        # Create logger
        self.logger = logging.getLogger("TranslationLogger")
        self.logger.setLevel(level)

        # Prevent duplicate logs from propagation
        self.logger.propagate = False

        # Create formatter
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

        # File handler
        file_handler = logging.FileHandler(self._log_filename, mode='w', encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)

        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Log initialization
        self.logger.info(f"Logger initialized. Log file: {self._log_filename}")
        self.logger.info(f"Output folder: {output_folder}")

        return self.logger

    def get_logger(self, output_folder: str = None, log_filename: str = None) -> logging.Logger:
        """
        Get the logger instance. Must call setup_logger() first.
        
        Returns:
            The logger instance
            
        Raises:
            RuntimeError: If logger is not initialized
        """
        if self.logger is None:
            self.setup_logger(level=logging.INFO, log_filename=log_filename, output_folder=output_folder)
        return self.logger

    def shutdown(self):
        """Properly shutdown the logger and close all handlers."""
        if self.logger:
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
            logging.shutdown()
            self.logger = None
            self._initialized = False
            
    def filter_log(
        self,
        filter_func: Callable[[str], bool],
        new_filename: str = None,
        suffix: str = "_filtered",
        prefix: str = "",
        output_folder: str = None,
        encoding: str = "utf-8",
        msg: str = "",
    ) -> str:
        """
        Reads the current log file, applies a filter function to each line,
        and writes matching lines to a new log file.

        Args:
            filter_func: Callable that takes a log line (str) and returns True if it should be kept
            new_filename: Optional full name for the new file (without path). If None, auto-generates.
            suffix: Suffix to add to original filename (e.g. '_errors', '_warnings')
            prefix: Prefix to add before the original filename
            encoding: File encoding (default utf-8)

        Returns:
            str: Path to the newly created filtered log file

        Raises:
            FileNotFoundError: If no log file has been created yet
            RuntimeError: If logger was not initialized
        """
        if not self._filepath or not self.logger:
            raise RuntimeError("Logger has not been initialized yet. Call setup_logger() first.")

        # Auto-generate new filena output_folder = self._filepathme if not provided
        if new_filename is None:
            base_path = Path(current_log_path)
            stem = base_path.stem
            new_stem = f"{prefix}{stem}{suffix}"
            new_log_path = base_path.with_name(f"{new_stem}{base_path.suffix}")
        else:            
            new_filename = new_filename.split('.')[0]
            new_filename = sanitize_txt(new_filename)
            new_filename += suffix if suffix and not new_filename.endswith(suffix) else ""
            new_filename += f"{self._ext}" if not new_filename.endswith(f"{self._ext}") else ""
            
            if output_folder is None:
                output_folder = self._filepath

            new_log_path =  new_filename
            
        if output_folder is None:
            output_folder = self._filepath

        else:
            output_folder = os.path.join(
                self._filepath,
                output_folder,
            )

        # Ensure output folder exists        
        os.makedirs(output_folder, exist_ok=True)
        
        new_log_path = os.path.join(
                output_folder,
                new_log_path,
        )
        
        filtered_lines: List[str] = []
        total_lines = 0
    
        with open(self._log_filename, 'r', encoding=encoding) as src:
            for line in src:
                total_lines += 1
                if filter_func(line):
                    filtered_lines.append(line)

        with open(new_log_path, 'w', encoding=encoding) as dst:
            dst.writelines(filtered_lines)

        # Log the action
        logger = self.get_logger()
        logger.info(f"{msg} Filtered log created: {new_log_path}")
        logger.info(f"{msg} Original: {total_lines} lines → Filtered: {len(filtered_lines)} lines "
                    f"({len(filtered_lines)/total_lines*100:.1f}% kept)")

        return str(new_log_path)

# Create global instance
translation_logger = SingletonLogger()