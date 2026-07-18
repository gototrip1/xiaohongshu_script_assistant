
import os
from dotenv import load_dotenv


load_dotenv(override=True)
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL")

QWEN3_API_KEY = os.getenv("QWEN3_API_KEY")
QWEN3_BASE_URL = os.getenv("QWEN3_BASE_URL")

APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
YOUR_EMAIL = os.getenv("YOUR_EMAIL")
DOC_TOKEN = os.getenv("DOC_TOKEN")
YOUR_PHONE = os.getenv("YOUR_PHONE")
YOUR_OPEN_ID = os.getenv("YOUR_OPEN_ID")
