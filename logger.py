import logging

logger = logging.getLogger("spiel")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
file_handler = logging.FileHandler("log.txt", mode="a")

console_handler.setLevel(logging.INFO)
file_handler.setLevel(logging.DEBUG)

# Create formatter and add to handlers
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to logger (avoid adding multiple times)
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
