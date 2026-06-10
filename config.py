import os
from dotenv import load_dotenv

load_dotenv()

# API Integration
API_ENDPOINT = os.getenv("API_ENDPOINT")
USER_API_KEY = os.getenv("USER_API_KEY")  # User's API key from dashboard

# Search Config
PLATFORMS = [
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "youtube.com",
    "twitter.com"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
}

# Search Topics (can be managed from dashboard later)
SEARCH_PROFILES = [
    # {"query": "travel pakistan", "type": "keyword"},
    # {"query": "#hunza valley", "type": "hashtag"},
    {"query": "#fifa #football #fifa worldcup", "type": "hashtag"},
]

# Filtering
MIN_SCORE = 0.2  # Lower threshold to accept more videos (video discovery is broad)
BATCH_SIZE = 10
REQUEST_TIMEOUT = 10