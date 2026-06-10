import time
import requests
import logging
import threading
from datetime import datetime
from search import search_ddg, validate_video_url
from ai_filter import filter_results
from config import API_ENDPOINT, USER_API_KEY, SEARCH_PROFILES, BATCH_SIZE, MIN_SCORE, REQUEST_TIMEOUT

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def send_batch_to_api(items, keyword):
    """Send batch of videos to API (fire and forget)"""
    if not items or not USER_API_KEY or not API_ENDPOINT:
        print("⚠️  Missing API configuration or no items to send")
        return
    
    print("🚀 Sending batch to API...")
    try:
        payload = {
            "keyword": keyword,
            "videos": [
                {
                    "externalId": item.get("externalId", ""),
                    "platform": item.get("platform", "unknown"),
                    "title": item["title"],
                    "description": item.get("snippet", ""),
                    "videoUrl": item["url"],
                    "score": item["score"]
                }
                for item in items
            ]
        }
        requests.post(
            "https://social-bot-nine.vercel.app/dashboard/api/videos/ingest-discovered",
            json=payload,
            headers={"Authorization": f"Bearer {USER_API_KEY}", "Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT
        )
        print("done")
    except:
        pass
    



def run():
    """Main discovery loop"""
    logger.info("🚀 Starting video discovery service")
    logger.info(f"API Endpoint: {API_ENDPOINT}")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    if not USER_API_KEY:
        logger.error("❌ FATAL: USER_API_KEY not set!")
        return {"success": False, "error": "USER_API_KEY not configured"}
    
    total_found = 0

    for profile in SEARCH_PROFILES:
        keyword = profile["query"]
        profile_type = profile["type"]
        
        logger.info(f"\n🔎 Searching [{profile_type}]: {keyword}")

        # Build search query - search for TikTok videos with keyword
        search_query = f'"{keyword}" site:tiktok.com/video OR site:instagram.com/reel OR site:instagram.com/video '
         
        raw_results = search_ddg(search_query, max_results=50)
        
        if not raw_results:
            logger.warning(f"⚠️  No results for: {keyword}")
            continue

        # Filter valid video URLs
        video_urls = [r for r in raw_results if validate_video_url(r["url"])]

                
        logger.info(f"📹 {len(video_urls)} valid video URLs found")

        # Apply AI filtering
        filtered = filter_results(video_urls, keyword, min_score=MIN_SCORE)
        logger.info(f"✨ {len(filtered)} high-quality results after filtering (threshold: {MIN_SCORE})")
        
        # Show top results for debugging
        if filtered:
            for i, video in enumerate(filtered[:3]):
                logger.info(f"  [{i+1}] Score: {video['score']} - {video['title'][:60]}")

        # Send in batches (fire and forget)
        # for i in range(0, len(filtered), BATCH_SIZE):
        #     batch = filtered[i:i + BATCH_SIZE]
        #     print(i)
        #     # send_batch_to_api(batch, keyword)
        #     total_found += len(batch)

        # with open("discovered_videos.txt", "w+") as f:
        #     for video in filtered[:10]:
        #         f.write(video["url"] + "\n")

        top_videos = filtered[:10]
        # send top 10 vidoes
        # print("Top videos:",top_videos)
        send_batch_to_api(top_videos, keyword)

    logger.info(f"\n📊 Summary: Discovered {total_found}")
    return {"success": True, "total_found": total_found}


if __name__ == "__main__":
    run()   