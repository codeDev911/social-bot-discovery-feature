
import os
import logging
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Core API ───────────────────────────────────────────────────────────────────
API_ENDPOINT    = os.getenv("API_ENDPOINT", "https://social-bot-nine.vercel.app/dashboard/api/videos/ingest-discovered")
CONFIG_ENDPOINT = os.getenv("CONFIG_ENDPOINT", "https://social-bot-nine.vercel.app/dashboard/api/user/bot-config")
USER_API_KEY    = os.getenv("USER_API_KEY", "")   # MUST be set via env / GH secret

# ── Platform definitions (canonical — not user-editable) ──────────────────────
ALL_PLATFORMS = {
    "instagram": {
        "site":         "site:instagram.com",
        "paths":        ["/reel/", "/p/", "/tv/"],
        "indicators":   ["instagram.com/reel", "instagram.com/p/", "instagram.com/tv"],
        "use_quotes":   False,
        "extra_term":   "reel",
    },
    "facebook": {
        "site":         "site:facebook.com",
        "paths":        ["/reel", "/videos/", "/watch"],
        "indicators":   ["facebook.com/reel", "facebook.com/videos", "facebook.com/watch"],
        "use_quotes":   False,
        "extra_term":   "reel video",
        "no_timelimit": True,
    },
    "youtube": {
        "site":         "site:youtube.com",
        "paths":        ["/watch", "/shorts/"],
        "indicators":   ["youtube.com/watch", "youtube.com/shorts"],
        "use_quotes":   True,
        "extra_term":   "",
    },
    "tiktok": {
        "site":         "site:tiktok.com",
        "paths":        ["/video/"],
        "indicators":   ["tiktok.com/@"],
        "use_quotes":   False,
        "extra_term":   "",
    },
    "twitter": {
        "site":         "site:twitter.com OR site:x.com",
        "paths":        ["/status/"],
        "indicators":   ["twitter.com/", "x.com/"],
        "use_quotes":   False,
        "extra_term":   "",
    },
}

TIME_FILTER_MAP = {"day": "d", "week": "w", "month": "m", "year": "y"}

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

# ── Default config (used when API fetch fails or in local dev) ─────────────────
DEFAULT_CONFIG = {
    "search_profiles": [
        {"query": "football match highlights 2026", "type": "keyword"},
    ],
    "enabled_platforms": ["instagram", "facebook", "tiktok"],
    "min_score":         0.20,
    "batch_size":        10,
    "time_filter":       "week",
    "request_timeout":   10,
    "max_per_platform":  20,
}


def fetch_user_config(api_key: str) -> dict:
    """
    GET /api/user/bot-config  →  returns the user's saved config from your DB.

    Expected response shape:
    {
      "search_profiles":   [{"query": "...", "type": "keyword"}, ...],
      "enabled_platforms": ["instagram", "facebook", "tiktok"],
      "min_score":         0.20,
      "batch_size":        10,
      "time_filter":       "week",
      "max_per_platform":  20,
      "request_timeout":   10
    }
    """
    if not api_key:
        logger.warning("⚠️  No USER_API_KEY — using default config")
        return DEFAULT_CONFIG

    print("API_KEY_UDER",api_key.strip())
    
    try:
        logger.info(f"📡 Fetching user config from API...")
        resp = requests.get(
            CONFIG_ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type":  "application/json",
            },
            timeout=10,
        )

        if resp.status_code == 200:
            data = resp.json()
            logger.info(f"✅ User config loaded: {len(data.get('search_profiles', []))} profiles, "
                        f"platforms={data.get('enabled_platforms', [])}")
            return data

        elif resp.status_code == 404:
            logger.warning("⚠️  No config found for this user — using defaults")
            return DEFAULT_CONFIG

        else:
            logger.error(f"❌ Config API returned {resp.status_code}: {resp.text[:200]}")
            return DEFAULT_CONFIG

    except requests.exceptions.ConnectionError:
        logger.error("❌ Cannot reach config API — using defaults (offline/firewall?)")
        return DEFAULT_CONFIG
    except Exception as e:
        logger.error(f"❌ Config fetch failed: {e} — using defaults")
        return DEFAULT_CONFIG


def load_config() -> dict:
    """
    Main entry point. Returns resolved config dict with PLATFORMS filtered
    to only the ones the user has enabled.
    """
    raw = fetch_user_config(USER_API_KEY)

    # Merge with defaults for any missing keys
    cfg = {**DEFAULT_CONFIG, **raw}

    # Resolve enabled platforms → filter ALL_PLATFORMS
    enabled = cfg.get("enabled_platforms") or list(ALL_PLATFORMS.keys())
    platforms = {k: v for k, v in ALL_PLATFORMS.items() if k in enabled}

    if not platforms:
        logger.warning("⚠️  No valid platforms in user config — enabling all")
        platforms = ALL_PLATFORMS

    return {
        "API_ENDPOINT":      API_ENDPOINT,
        "USER_API_KEY":      USER_API_KEY,
        "PLATFORMS":         platforms,
        "SEARCH_PROFILES":   cfg["search_profiles"],
        "MIN_SCORE":         float(cfg["min_score"]),
        "BATCH_SIZE":        int(cfg["batch_size"]),
        "TIME_FILTER":       cfg["time_filter"],
        "MAX_PER_PLATFORM":  int(cfg["max_per_platform"]),
        "REQUEST_TIMEOUT":   int(cfg["request_timeout"]),
    }


# ── Resolve at import time ─────────────────────────────────────────────────────
_cfg = load_config()

PLATFORMS        = _cfg["PLATFORMS"]
SEARCH_PROFILES  = _cfg["SEARCH_PROFILES"]
MIN_SCORE        = _cfg["MIN_SCORE"]
BATCH_SIZE       = _cfg["BATCH_SIZE"]
REQUEST_TIMEOUT  = _cfg["REQUEST_TIMEOUT"]
TIME_FILTER      = _cfg["TIME_FILTER"]
MAX_PER_PLATFORM = _cfg["MAX_PER_PLATFORM"]