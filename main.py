import requests
import logging
from datetime import datetime
from search import search_all_platforms
from ai_filter import filter_results
from config import (
    API_ENDPOINT, USER_API_KEY, PLATFORMS,
    SEARCH_PROFILES, BATCH_SIZE, MIN_SCORE,
    REQUEST_TIMEOUT, TIME_FILTER, MAX_PER_PLATFORM
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from services.trend_video_picker import fetch_metadata, pick_top_and_viral
    TREND_PICKER_AVAILABLE = True
except ImportError as e:
    TREND_PICKER_AVAILABLE = False
    logger.warning(f"⚠️  video_trend_picker not available: {e}")


def send_batch_to_api(items: list[dict], keyword: str):
    if not items or not USER_API_KEY or not API_ENDPOINT:
        logger.warning("⚠️  Missing API config or empty batch — skipping")
        return
    try:
        payload = {
            "keyword": keyword,
            "videos": [
                {
                    "externalId":  item.get("externalId", ""),
                    "platform":    item.get("platform", "unknown"),
                    "title":       item["title"],
                    "description": item.get("snippet", ""),
                    "videoUrl":    item["url"],
                    "score":       item["score"],
                }
                for item in items
            ],
        }
        resp = requests.post(
            API_ENDPOINT,
            json=payload,
            headers={"Authorization": f"Bearer {USER_API_KEY}", "Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        logger.info(f"✅ API response: {resp.status_code}")
    except Exception as e:
        logger.error(f"❌ API send failed: {e}")


def analyse_trends(all_video_items: list[dict]) -> dict:
    if not TREND_PICKER_AVAILABLE:
        return {}
    if not all_video_items:
        logger.error("❌ analyse_trends: no items to analyse")
        return {}

    urls = [item["url"] for item in all_video_items]
    logger.info(f"\n📊 Running trend analysis on {len(urls)} URLs...")

    videos = fetch_metadata(urls, fallback_items=all_video_items)
    if not videos:
        logger.error("❌ fetch_metadata returned 0 results (auth-walled platforms?)")
        return {}

    results = pick_top_and_viral(videos)
    if not results:
        return {}

    top   = results.get("top_video", {})
    viral = results.get("viral_video", {})
    logger.info(f"\n🏆  TOP   → {top.get('url')}  (views={top.get('views',0):,})")
    logger.info(f"🔥  VIRAL → {viral.get('url')}  (eng={viral.get('engagement_rate_%',0)}%)")
    return results


def run():
    logger.info("🚀 Starting video discovery service")
    logger.info(f"  User key  : {USER_API_KEY[:8]}...{USER_API_KEY[-4:] if USER_API_KEY else 'NOT SET'}")
    logger.info(f"  Profiles  : {len(SEARCH_PROFILES)}")
    logger.info(f"  Platforms : {list(PLATFORMS.keys())}")
    logger.info(f"  Min score : {MIN_SCORE}")
    logger.info(f"  Time filter: {TIME_FILTER}")

    if not USER_API_KEY:
        logger.error("❌ FATAL: USER_API_KEY not set!")
        return {"success": False, "error": "USER_API_KEY not configured"}

    seen_urls: set[str]    = set()
    all_top_items: list[dict] = []
    total_found = 0

    for profile in SEARCH_PROFILES:
        keyword      = profile["query"]
        profile_type = profile["type"]

        logger.info(f"\n{'='*60}")
        logger.info(f"🔎 [{profile_type}] {keyword}")
        logger.info(f"{'='*60}")

        raw_results = search_all_platforms(
            keyword=keyword,
            platforms=list(PLATFORMS.keys()),   # ← from user config
            max_per_platform=MAX_PER_PLATFORM,
            time_filter=TIME_FILTER,
            seen_urls=seen_urls,
        )

        logger.info(f"📹 Raw results: {len(raw_results)}")
        if not raw_results:
            logger.warning(f"⚠️  No results for: {keyword}")
            continue

        filtered = filter_results(raw_results, keyword, min_score=MIN_SCORE)
        logger.info(f"✨ After filter (min={MIN_SCORE}): {len(filtered)}")
        if not filtered:
            logger.warning("⚠️  All filtered out — try lowering MIN_SCORE")
            continue

        for i, v in enumerate(filtered[:3]):
            logger.info(f"  [{i+1}] {v['score']} [{v['platform']}] {v['title'][:60]}")

        top_videos = filtered[:BATCH_SIZE]
        total_found += len(top_videos)
        all_top_items.extend(top_videos)

        with open("discovered_videos.txt", "a") as f:
            f.write(f"\n# [{datetime.now().isoformat()}] keyword={keyword}\n")
            for v in top_videos:
                f.write(f"{v['url']}\n")

        send_batch_to_api(top_videos, keyword)

    # ── Trend analysis ─────────────────────────────────────────────────────────
    trend_results = {}
    if all_top_items:
        trend_results = analyse_trends(all_top_items)

    logger.info(f"\n{'='*60}")
    logger.info(f"📊 DONE — {total_found} videos discovered")
    if trend_results:
        logger.info(f"📌 Top   → {trend_results.get('top_video', {}).get('url', 'N/A')}")
        logger.info(f"📌 Viral → {trend_results.get('viral_video', {}).get('url', 'N/A')}")
    logger.info(f"{'='*60}")

    return {
        "success":     True,
        "total_found": total_found,
        "top_video":   trend_results.get("top_video"),
        "viral_video": trend_results.get("viral_video"),
    }


if __name__ == "__main__":
    run()