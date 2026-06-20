import re
from difflib import SequenceMatcher
from urllib.parse import urlparse, parse_qs

BAD_KEYWORDS = [
    "ad", "sponsored", "promo", "giveaway", "crypto",
    "earn money", "click here", "bitcoin", "work from home",
    "mlm", "dropship", "tag"
]

QUALITY_KEYWORDS = [
    "vlog", "travel", "lifestyle", "nature", "adventure",
    "music", "dance", "challenge", "gaming", "football",
    "food", "recipe", "comedy", "funny", "animals", "pets",
    "art", "fashion", "highlights", "goals", "match", "clips",
    "fifa", "world cup", "soccer", "replay", "skills", "trick"
]

BLOCKED_PATTERNS = [
    "/discover/", "/tag/", "/hashtag/", "/place/",
    "/explore/", "/search/", "/topics/",
]


def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()


def is_spam(title):
    title = title.lower()
    return sum(1 for b in BAD_KEYWORDS if b in title) > 0


def has_quality_markers(title):
    title = title.lower()
    return sum(1 for q in QUALITY_KEYWORDS if q in title) > 0


def normalize_url(url):
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc:
        video_id = parse_qs(parsed.query).get("v")
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id[0]}"
    return url.split("&")[0]


def is_valid_video_url(url):
    url = url.lower()
    if any(pattern in url for pattern in BLOCKED_PATTERNS):
        return False
    if re.search(r"tiktok\.com/@[^/]+/video/\d+", url):
        return True
    if re.search(r"instagram\.com/reel/[a-zA-Z0-9_-]+", url):
        return True
    if "/reel/" in url:
        return True
    if re.search(r"facebook\.com/.*/videos/\d+", url):
        return True
    if re.search(r"youtube\.com/shorts/[a-zA-Z0-9_-]+", url):
        return True
    if re.search(r"youtube\.com/watch\?v=", url):
        return True
    return False


def direct_video_bonus(url):
    url = url.lower()
    if "/shorts/" in url:   return 0.30
    if "/reel/" in url:     return 0.30
    if re.search(r"tiktok\.com/@[^/]+/video/\d+", url): return 0.30
    if "/videos/" in url:   return 0.20
    if "watch?v=" in url:   return 0.10
    return 0


def clean_keyword(keyword: str) -> str:
    """
    Strip hashtags and normalise keyword for matching.
    '#fifa2026 #football' → 'fifa2026 football'
    """
    return re.sub(r"#", "", keyword).strip()


def score_content(title, keyword, url=None):
    """
    Score a result against the search keyword.

    Key fix: hashtags are stripped before splitting so
    '#fifa2026' correctly matches a title containing 'fifa2026'.
    Also: snippet/description now contributes to the score.
    """
    title_l  = title.lower()
    # ── FIX: strip # before splitting ────────────────────────────────────────
    clean_kw = clean_keyword(keyword).lower()
    keywords = [w for w in clean_kw.split() if len(w) > 2]  # ignore tiny words

    score = 0.0

    # Keyword match in title (up to 0.50)
    matched = sum(1 for kw in keywords if kw in title_l)
    if matched:
        score += min(0.50, matched * 0.15)

    # Fuzzy similarity between title and cleaned keyword (up to 0.20)
    score += similarity(title_l, clean_kw) * 0.20

    # Quality marker bonus (up to 0.20)
    if has_quality_markers(title):
        score += 0.20

    # Direct video URL bonus (up to 0.30)
    if url:
        score += direct_video_bonus(url)

    # Spam penalty
    if is_spam(title):
        score -= 0.90

    return max(0.0, min(score, 1.0))


def extract_platform(url):
    if "tiktok.com"   in url: return "tiktok"
    if "instagram.com" in url: return "instagram"
    if "facebook.com" in url: return "facebook"
    if "youtube.com"  in url: return "youtube"
    if "twitter.com"  in url or "x.com" in url: return "twitter"
    return "unknown"


def extract_video_id(url):
    if "youtube.com/watch" in url:
        parsed = urlparse(url)
        return parse_qs(parsed.query).get("v", [None])[0]
    for pattern in [
        r"/shorts/([A-Za-z0-9_-]+)",
        r"/video/(\d+)",
        r"/reel/([A-Za-z0-9_-]+)",
        r"/videos/(\d+)",
    ]:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return url.rstrip("/").split("/")[-1]


def filter_results(results, keyword, min_score=0.20):
    """
    Score and filter results.
    Now also accepts a 'snippet' field to score against when title is weak.
    """
    filtered = []
    seen = set()

    for r in results:
        raw_url = r.get("url", "")
        title   = r.get("title", "")
        snippet = r.get("snippet", "")    # DDG body text — bonus signal

        if not raw_url:
            continue

        url = normalize_url(raw_url)

        if url in seen:
            continue

        if not is_valid_video_url(url):
            continue

        seen.add(url)

        # Score title first
        score = score_content(title=title, keyword=keyword, url=url)

        # ── FIX: if title scored 0, try scoring the snippet too ───────────────
        # This catches reels/shorts with generic titles like "Watch this 🔥"
        if score < min_score and snippet:
            snippet_score = score_content(title=snippet, keyword=keyword, url=url)
            score = max(score, snippet_score)

        if score < min_score:
            continue

        filtered.append({
            "url":        url,
            "title":      title,
            "snippet":    snippet,
            "score":      round(score, 2),
            "platform":   extract_platform(url),
            "externalId": extract_video_id(url),
        })

    filtered.sort(key=lambda x: x["score"], reverse=True)
    return filtered