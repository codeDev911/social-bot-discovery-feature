import os
from dotenv import load_dotenv

load_dotenv()

# API Integration
API_ENDPOINT = "https://social-bot-nine.vercel.app/dashboard/api/videos/ingest-discovered"
USER_API_KEY = "s5ikqMfTlsuy10ehz2O8qG-4neFWKIeof37jfFKg0UA"  # User's API key from dashboard

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
    {"query": "#fifa #gta6 #gta6gameplay #fifa2026  #ishowspeed #mrbeast worldcup", "type": "hashtag"},
]

# Filtering
MIN_SCORE = 0.2  # Lower threshold to accept more videos (video discovery is broad)
BATCH_SIZE = 10
REQUEST_TIMEOUT = 10
