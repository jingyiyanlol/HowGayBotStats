# encoding: utf-8
import logging

## Reference Source: https://github.com/alesanmed/python-telegram-bot-seed/blob/master/utils/logger.py
def init_logger(logfile: str):
    """Initialize the root logger and standard log handlers."""
    
    ## e.g. [2025-06-14 12:34:56,789] - [root] - [INFO] - Application started.
    log_formatter = logging.Formatter(
        "[%(asctime)s] - [%(name)s] - [%(levelname)s] - %(message)s"
    )
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(logfile)
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)
    

# def init_logger(logfile: str):
#     log_formatter = logging.Formatter(
#         "[%(asctime)s] - [%(name)s] - [%(levelname)s] - %(message)s"
#     )
#     root_logger = logging.getLogger()
#     root_logger.setLevel(logging.DEBUG)  # You can keep DEBUG if you want for your own logs

#     file_handler = logging.FileHandler(logfile)
#     file_handler.setLevel(logging.DEBUG)
#     file_handler.setFormatter(log_formatter)
#     root_logger.addHandler(file_handler)

#     console_handler = logging.StreamHandler()
#     console_handler.setLevel(logging.WARNING)
#     console_handler.setFormatter(log_formatter)
#     root_logger.addHandler(console_handler)

#     # Suppress noisy loggers from dependencies
#     logging.getLogger("httpcore").setLevel(logging.WARNING)
#     logging.getLogger("httpx").setLevel(logging.WARNING)
#     logging.getLogger("telegram").setLevel(logging.INFO)  # or WARNING
#     logging.getLogger("telegram.ext.ExtBot").setLevel(logging.WARNING)
