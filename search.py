from ddgs import DDGS
import logging
import time
import re
from urllib.parse import urlparse
from config import PLATFORMS, TIME_FILTER_MAP
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Platform configs ───────────────────────────────────────────────────────────
# Each platform has multiple query strategies tried in order.
# "no_quotes"  → keyword without wrapping quotes (broader, works better for FB/IG)
# "with_reel"  → append platform-specific content type word
# DDG barely indexes Facebook/Instagram — so we cast a wider net.




def _extract_platform(url: str) -> str:
    url_lower = url.lower()
    for platform, cfg in PLATFORMS.items():
        if any(ind in url_lower for ind in cfg["indicators"]):
            return platform
    return "unknown"


def _is_valid_video_url(url: str, platform: str) -> bool:
    url_lower = url.lower()
    cfg = PLATFORMS.get(platform)
    if not cfg:
        return False
    return any(path in url_lower for path in cfg["paths"])


def _deduplicate(results: list[dict], seen_urls: set) -> list[dict]:
    unique = []
    for r in results:
        url = r["url"].rstrip("/").split("?")[0]
        if url not in seen_urls:
            seen_urls.add(url)
            r["url_normalized"] = url
            unique.append(r)
    return unique


def _ddg_search(query: str, max_results: int, timelimit: str = None) -> list[dict]:
    """
    Thin wrapper around DDGS.text().
    Returns raw list or [] on any error including 'No results found'.
    Treats 'No results found' as a normal empty result, not an error.
    """
    try:
        kwargs = {"max_results": max_results}
        if timelimit:
            kwargs["timelimit"] = timelimit

        with DDGS() as ddgs:
            return list(ddgs.text(query, **kwargs))

    except Exception as e:
        err = str(e).lower()
        # "No results found" is normal — log as info not error
        if "no results" in err or "ratelimit" in err.lower():
            logger.info(f"    ℹ️  DDG returned no results for query: {query[:80]}")
        else:
            logger.warning(f"    ⚠️  DDG error: {e} | query: {query[:80]}")
        return []


def search_platform(
    keyword: str,
    platform: str,
    max_results: int = 20,
    time_filter: str = "week",
    seen_urls: set = None,
) -> list[dict]:
    """
    Search a single platform using a waterfall of query strategies:
      1. Primary:  keyword (quoted or not) + site: filter + timelimit
      2. Fallback: no quotes, no timelimit, with extra_term appended
    This ensures Facebook/Instagram get results even when strict queries fail.
    """
    if seen_urls is None:
        seen_urls = set()

    cfg = PLATFORMS.get(platform)
    if not cfg:
        logger.warning(f"Unknown platform: {platform}")
        return []

    site       = cfg["site"]
    use_quotes = cfg.get("use_quotes", True)
    extra_term = cfg.get("extra_term", "")
    no_tl      = cfg.get("no_timelimit", False)
    timelimit  = None if no_tl else TIME_FILTER_MAP.get(time_filter, "w")

    # ── Query variants (tried in order until we get results) ──────────────────
    kw_quoted  = f'"{keyword}"'
    kw_plain   = keyword

    primary_kw = kw_quoted if use_quotes else kw_plain
    queries = [
        # 1. Primary strategy
        f"{primary_kw} {extra_term} {site}".strip(),
        # 2. Flip quote mode
        f"{kw_plain if use_quotes else kw_quoted} {extra_term} {site}".strip(),
        # 3. No extra_term, no timelimit
        f"{kw_plain} {site}".strip(),
        # 4. Drop site: filter entirely, search keyword + platform name
        f"{kw_plain} {platform} video",
    ]

    raw = []
    for i, query in enumerate(queries):
        tl = timelimit if i < 2 else None   # drop timelimit on fallback attempts
        logger.info(f"  🔍 [{platform}] attempt {i+1}: {query[:90]}")
        raw = _ddg_search(query, max_results=max_results, timelimit=tl)
        if raw:
            logger.info(f"  ✅ [{platform}] got {len(raw)} raw results on attempt {i+1}")
            break
        time.sleep(1.0)

    if not raw:
        logger.info(f"  ⬜ [{platform}] no results after all attempts — skipping")
        return []

    # ── Filter to valid video URLs for this platform ───────────────────────────
    results = []
    for r in raw:
        url = r.get("href", "")
        if not url:
            continue

        detected = _extract_platform(url)

        # For the "drop site:" fallback query, accept any platform's valid URL
        if detected != platform:
            continue

        if not _is_valid_video_url(url, platform):
            continue

        results.append({
            "url":      url,
            "title":    r.get("title", ""),
            "snippet":  r.get("body", ""),
            "platform": platform,
            "keyword":  keyword,
        })

    deduped = _deduplicate(results, seen_urls)
    logger.info(f"  📌 [{platform}] {len(deduped)} unique valid video URLs after filtering")
    time.sleep(1.2)
    return deduped


def search_all_platforms(
    keyword: str,
    platforms: list[str] = None,
    max_per_platform: int = 20,
    time_filter: str = "week",
    seen_urls: set = None,
) -> list[dict]:
    """
    Search across platforms separately and merge unique results.
    Pass a shared `seen_urls` set to deduplicate across keyword runs.
    """
    if seen_urls is None:
        seen_urls = set()
    if platforms is None:
        platforms = list(PLATFORMS.keys())

    all_results = []
    for platform in platforms:
        results = search_platform(
            keyword, platform, max_per_platform, time_filter, seen_urls
        )
        all_results.extend(results)

    logger.info(f"🎯 Total unique videos for '{keyword}': {len(all_results)}")
    return all_results


# ── Legacy compat ──────────────────────────────────────────────────────────────
def validate_video_url(url: str) -> bool:
    platform = _extract_platform(url)
    return _is_valid_video_url(url, platform)


def search_ddg(query: str, max_results: int = 50) -> list[dict]:
    """Legacy single-query search. Prefer search_all_platforms()."""
    raw = _ddg_search(query, max_results=max_results)
    return [{"url": r.get("href",""), "title": r.get("title",""), "snippet": r.get("body","")} for r in raw]