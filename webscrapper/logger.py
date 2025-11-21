# logger.py
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from constants.languages import SL, TL
from constants.output import OUTPUT_FOLDER

class SingletonLogger:
    _instance: Optional['SingletonLogger'] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonLogger, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.logger: Optional[logging.Logger] = None
            self._initialized = True

    def setup_logger(self, output_folder: str = None, source_lang: str = SL, target_lang: str = TL, level= logging.INFO) -> logging.Logger:
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
            output_folder = script_dir / "output"
        else:
            output_folder = Path(output_folder)

        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)

        # Create log filename with timestamp
        log_filename = os.path.join(
            output_folder,
            f"translation_{source_lang}2{target_lang}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )

        # Create logger
        self.logger = logging.getLogger("TranslationLogger")
        self.logger.setLevel(level)

        # Prevent duplicate logs from propagation
        self.logger.propagate = False

        # Create formatter
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

        # File handler
        file_handler = logging.FileHandler(log_filename, mode='w', encoding='utf-8')
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
        self.logger.info(f"Logger initialized. Log file: {log_filename}")
        self.logger.info(f"Output folder: {output_folder}")

        return self.logger

    def get_logger(self) -> logging.Logger:
        """
        Get the logger instance. Must call setup_logger() first.
        
        Returns:
            The logger instance
            
        Raises:
            RuntimeError: If logger is not initialized
        """
        if self.logger is None:
            self.setup_logger(level=logging.DEBUG)
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

# Create global instance
translation_logger = SingletonLogger()