from ddgs import DDGS
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def search_ddg(query, max_results=50):
    """
    Search using DuckDuckGo with official Python library
    Returns list of {url, title, snippet}
    """
    try:
        logger.info(f"🔍 Querying DuckDuckGo for: {query}")
        results = []
        
        with DDGS() as ddgs:
            # Use text search for better results
            search_results = list(ddgs.text(query, max_results=max_results))
            
            for result in search_results:
                results.append({
                    "url": result.get("href", ""),
                    "title": result.get("title", ""),
                    "snippet": result.get("body", "")
                })
        
        logger.info(f"✅ Found {len(results)} results for: {query}")
        time.sleep(1)  # Rate limiting between requests
        return results

    except Exception as e:
        logger.error(f"❌ Search error for '{query}': {str(e)}")
        return []


def validate_video_url(url):
    """Quick check if URL looks like a valid video link"""
    video_indicators = [
        "watch", "video", "v=", "shorts", "reel", "tiktok.com",
        "instagram.com", "youtube.com", "facebook.com", "twitter.com"
    ]
    return any(ind in url.lower() for ind in video_indicators)