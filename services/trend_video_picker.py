"""
video_trend_picker.py
─────────────────────
Fetches yt-dlp metadata for a list of URLs and picks:
  • TOP video    → highest view count
  • VIRAL video  → best engagement rate (likes+comments / views)

Platform reality:
  ✅ Full metadata  : YouTube, TikTok (public), Dailymotion, Twitch clips
  ⚠️  Partial/needs cookies : Instagram, Facebook, Twitter/X
  → Fallback scoring uses DDG snippet data when yt-dlp returns nothing
"""

import yt_dlp
import json
import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# ─── Data Model ───────────────────────────────────────────────────────────────

@dataclass
class VideoMeta:
    url: str
    title: str = "Unknown"
    uploader: str = "Unknown"
    platform: str = "Unknown"
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    upload_date: Optional[str] = None
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    description: Optional[str] = None
    engagement_rate: float = 0.0
    metadata_source: str = "yt-dlp"   # "yt-dlp" | "fallback"
    raw: dict = field(default_factory=dict, repr=False)

    def compute_engagement(self):
        interactions = (self.like_count or 0) + (self.comment_count or 0)
        views = self.view_count or 1
        self.engagement_rate = round((interactions / views) * 100, 4)

    def formatted_date(self) -> str:
        if not self.upload_date:
            return "Unknown"
        try:
            return datetime.strptime(self.upload_date, "%Y%m%d").strftime("%d %b %Y")
        except ValueError:
            return self.upload_date

    def summary(self) -> dict:
        return {
            "url":               self.url,
            "title":             self.title,
            "platform":          self.platform,
            "uploader":          self.uploader,
            "views":             self.view_count,
            "likes":             self.like_count,
            "comments":          self.comment_count,
            "engagement_rate_%": self.engagement_rate,
            "upload_date":       self.formatted_date(),
            "duration_sec":      self.duration,
            "thumbnail":         self.thumbnail,
            "metadata_source":   self.metadata_source,
        }


# ─── Platform support map ─────────────────────────────────────────────────────

# Platforms yt-dlp can fetch WITHOUT cookies
SUPPORTED_PLATFORMS = {
    "youtube.com", "youtu.be",
    "tiktok.com",
    "dailymotion.com",
    "twitch.tv",
    "reddit.com",
    "vimeo.com",
}

def _platform_from_url(url: str) -> str:
    url = url.lower()
    for p in SUPPORTED_PLATFORMS:
        if p in url:
            return p
    if "instagram.com" in url:   return "instagram"
    if "facebook.com" in url:    return "facebook"
    if "twitter.com" in url or "x.com" in url: return "twitter"
    return "unknown"

def _yt_dlp_likely_works(url: str) -> bool:
    """Return True if yt-dlp can fetch this URL without cookies."""
    return _platform_from_url(url) in SUPPORTED_PLATFORMS


# ─── yt-dlp fetcher ───────────────────────────────────────────────────────────

YDL_OPTS = {
    "quiet":         False,       # show errors so we can debug
    "verbose":       False,
    "skip_download": True,
    "no_warnings":   False,       # show warnings
    "ignoreerrors":  False,       # DON'T swallow errors silently
    "extract_flat":  False,
    "socket_timeout": 20,
}


def _fetch_single(ydl: yt_dlp.YoutubeDL, url: str) -> Optional[dict]:
    """
    Attempt to extract info for one URL.
    Returns raw info dict or None on any failure.
    """
    try:
        info = ydl.extract_info(url, download=False)
        return info
    except yt_dlp.utils.DownloadError as e:
        logger.warning(f"    yt-dlp DownloadError [{url}]: {e}")
        return None
    except yt_dlp.utils.ExtractorError as e:
        logger.warning(f"    yt-dlp ExtractorError [{url}]: {e}")
        return None
    except Exception as e:
        logger.warning(f"    yt-dlp unexpected error [{url}]: {type(e).__name__}: {e}")
        return None


def fetch_metadata(
    urls: list[str],
    fallback_items: Optional[list[dict]] = None,
) -> list[VideoMeta]:
    """
    Fetch yt-dlp metadata.

    Args:
        urls:           List of video URLs
        fallback_items: Optional list of dicts with keys url/title/snippet/score
                        from your DDG results — used when yt-dlp can't fetch a URL.

    Returns:
        List of VideoMeta (may be partial if some platforms blocked yt-dlp).
    """
    fallback_map: dict[str, dict] = {}
    if fallback_items:
        for item in fallback_items:
            fallback_map[item["url"]] = item

    results: list[VideoMeta] = []
    skipped_urls: list[str] = []

    logger.info(f"📡 Fetching metadata for {len(urls)} URLs via yt-dlp...")

    with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
        for url in urls:
            platform = _platform_from_url(url)
            likely_works = _yt_dlp_likely_works(url)

            if not likely_works:
                logger.info(f"  ⏭  Skipping {platform} URL (needs cookies): {url[:80]}")
                skipped_urls.append(url)
                # Immediately try fallback so we don't lose this URL
                fb = fallback_map.get(url)
                if fb:
                    meta = VideoMeta(
                        url=url,
                        title=fb.get("title", "Unknown"),
                        platform=platform,
                        description=(fb.get("snippet", ""))[:300],
                        # No view/like counts from DDG — score used as proxy
                        view_count=int(fb.get("score", 0) * 1000),
                        metadata_source="fallback",
                    )
                    meta.compute_engagement()
                    results.append(meta)
                    logger.info(f"    ↩ Fallback used for: {meta.title[:60]}")
                continue

            logger.info(f"  ↳ [{platform}] {url[:80]}")
            info = _fetch_single(ydl, url)

            if not info:
                logger.warning(f"    ⚠  No info returned for: {url}")
                skipped_urls.append(url)
                continue

            # yt-dlp sometimes returns a playlist wrapper — unwrap it
            if info.get("_type") == "playlist":
                entries = info.get("entries") or []
                info = entries[0] if entries else None
                if not info:
                    logger.warning(f"    ⚠  Playlist with no entries: {url}")
                    continue

            raw_views = info.get("view_count") or 0

            # ── FIX: Facebook/Instagram return info but view_count=0 ──────────
            # Fall back to score-based proxy so ranking still works.
            # score (0.0–1.0) × 100_000 gives a relative proxy view count.
            if raw_views == 0:
                fb = fallback_map.get(url, {})
                fb_score = fb.get("score", 0)
                if fb_score:
                    raw_views = int(fb_score * 100_000)
                    logger.info(f"    ℹ️  view_count=0 for {platform}, using score proxy: {raw_views:,}")

            meta = VideoMeta(
                url=url,
                title=info.get("title", "Unknown"),
                uploader=info.get("uploader") or info.get("channel") or "Unknown",
                platform=info.get("extractor_key", platform),
                view_count=raw_views,
                like_count=info.get("like_count") or 0,
                comment_count=info.get("comment_count") or 0,
                upload_date=info.get("upload_date"),
                duration=info.get("duration"),
                thumbnail=info.get("thumbnail"),
                description=(info.get("description") or "")[:300],
                metadata_source="yt-dlp" if info.get("view_count") else "yt-dlp+score-proxy",
                raw=info,
            )
            meta.compute_engagement()
            results.append(meta)
            logger.info(
                f"    ✓  {meta.title[:55]}  "
                f"views={meta.view_count:,}  "
                f"eng={meta.engagement_rate}%"
            )

    logger.info(
        f"\n📊 Metadata summary: "
        f"{len(results)} fetched | "
        f"{len(skipped_urls)} skipped (auth-walled)"
    )

    if skipped_urls:
        logger.info(f"  ℹ️  Skipped URLs (add cookies.txt to unlock):")
        for u in skipped_urls:
            logger.info(f"    - {u}")

    return results


# ─── Picker ───────────────────────────────────────────────────────────────────

def pick_top_and_viral(videos: list[VideoMeta]) -> dict:
    """
    TOP    → highest view_count
    VIRAL  → highest engagement_rate, tiebreak by view_count
    """
    if not videos:
        logger.error("pick_top_and_viral called with empty list!")
        return {}

    top   = max(videos, key=lambda v: v.view_count)
    viral = max(videos, key=lambda v: (v.engagement_rate, v.view_count))

    return {
        "top_video":          top.summary(),
        "viral_video":        viral.summary(),
        "all_videos_by_views": [
            v.summary()
            for v in sorted(videos, key=lambda x: x.view_count, reverse=True)
        ],
    }


# ─── Full pipeline ────────────────────────────────────────────────────────────

def analyse_links(
    urls: list[str],
    fallback_items: Optional[list[dict]] = None,
    output_json: Optional[str] = None,
) -> dict:
    if not urls:
        logger.error("analyse_links: received empty URL list!")
        return {}

    logger.info(f"\n🔍 Starting trend analysis for {len(urls)} URL(s)...")
    videos = fetch_metadata(urls, fallback_items=fallback_items)

    if not videos:
        logger.error(
            "❌ fetch_metadata returned 0 videos.\n"
            "   Likely causes:\n"
            "   1. All URLs are Instagram/Facebook/Twitter (need cookies)\n"
            "   2. URLs are private/deleted\n"
            "   3. Network/firewall blocking yt-dlp\n"
            "   → Pass fallback_items= with your DDG results as a workaround."
        )
        return {}

    results = pick_top_and_viral(videos)

    _print_video(results["top_video"],   label="🏆  TOP VIDEO (most views)")
    _print_video(results["viral_video"], label="🔥  VIRAL VIDEO (best engagement)")

    if output_json:
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"💾  Results saved → {output_json}")

    return results


def _print_video(v: dict, label: str = ""):
    logger.info(f"\n{'='*60}")
    if label:
        logger.info(label)
    logger.info(f"  Title     : {v['title']}")
    logger.info(f"  URL       : {v['url']}")
    logger.info(f"  Platform  : {v['platform']}")
    logger.info(f"  Views     : {v.get('views', 0):,}")
    logger.info(f"  Engagement: {v.get('engagement_rate_%', 0)}%")
    logger.info(f"  Source    : {v.get('metadata_source', '?')}")


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ]
    results = analyse_links(test_urls, output_json="trend_results.json")
    if results:
        print(f"\n📌 Top   → {results['top_video']['url']}")
        print(f"📌 Viral → {results['viral_video']['url']}")