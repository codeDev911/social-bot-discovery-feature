import re
from difflib import SequenceMatcher
from urllib.parse import urlparse, parse_qs

BAD_KEYWORDS = [
"ad",
"sponsored",
"promo",
"giveaway",
"crypto",
"earn money",
"click here",
"bitcoin",
"work from home",
"mlm",
"dropship",
"tag"
]

QUALITY_KEYWORDS = [
"vlog",
"travel",
"lifestyle",
"nature",
"adventure",
"music",
"dance",
"challenge",
"gaming",
"football",
"food",
"recipe",
"comedy",
"funny",
"animals",
"pets",
"art",
"fashion"
]

BLOCKED_PATTERNS = [
"/discover/",
"/tag/",
"/hashtag/",
"/place/",
"/explore/",
"/search/",
"/topics/",
]

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def is_spam(title):
    title = title.lower()
    spam_score = sum(1 for b in BAD_KEYWORDS if b in title)
    return spam_score > 0

def has_quality_markers(title):
    title = title.lower()
    quality_score = sum(1 for q in QUALITY_KEYWORDS if q in title)
    return quality_score > 0

def normalize_url(url):
    """
    Keep important IDs while removing tracking params.
    """

    parsed = urlparse(url)

    # YouTube watch URLs
    if "youtube.com" in parsed.netloc:
        video_id = parse_qs(parsed.query).get("v")

        if video_id:
            return f"https://www.youtube.com/watch?v={video_id[0]}"

    # Remove common tracking params
    return url.split("&")[0]

def is_valid_video_url(url):
    url = url.lower()

    # Reject discover/tag pages
    if any(pattern in url for pattern in BLOCKED_PATTERNS):
        return False

    # TikTok direct video
    if re.search(r"tiktok\.com/@[^/]+/video/\d+", url):
        return True

    # Instagram Reel
    if re.search(r"instagram\.com/reel/[a-zA-Z0-9_-]+", url):
        return True

    # Facebook Reel
    if "/reel/" in url:
        return True

    # Facebook Videos
    if re.search(r"facebook\.com/.*/videos/\d+", url):
        return True

    # YouTube Shorts
    if re.search(r"youtube\.com/shorts/[a-zA-Z0-9_-]+", url):
        return True

    # YouTube Watch
    if re.search(r"youtube\.com/watch\?v=", url):
        return True

    return False

def direct_video_bonus(url):
    url = url.lower()

    if "/shorts/" in url:
        return 0.30

    if "/reel/" in url:
        return 0.30

    if re.search(r"tiktok\.com/@[^/]+/video/\d+", url):
        return 0.30

    if "/videos/" in url:
        return 0.20

    if "watch?v=" in url:
        return 0.10

    return 0

def score_content(title, keyword, url=None):
    title_l = title.lower()
    keyword_l = keyword.lower()
    score = 0.0

    keywords = keyword_l.replace("#", "").split()

    matched_keywords = sum(
        1 for kw in keywords
        if kw in title_l
    )

    if matched_keywords:
        score += min(0.5, matched_keywords * 0.15)

    score += similarity(title_l, keyword_l) * 0.20

    if has_quality_markers(title):
        score += 0.20

    if url:
        score += direct_video_bonus(url)

    if is_spam(title):
        score -= 0.90

    return max(0, min(score, 1))

def extract_platform(url):
    if "tiktok.com" in url:
        return "tiktok"

    
    if "instagram.com" in url:
        return "instagram"

    if "facebook.com" in url:
        return "facebook"

    if "youtube.com" in url:
        return "youtube"

    if "twitter.com" in url or "x.com" in url:
        return "twitter"

    return "unknown"


def extract_video_id(url):
    if "youtube.com/watch" in url:
        parsed = urlparse(url)
        return parse_qs(parsed.query).get("v", [None])[0]


    match = re.search(r"/shorts/([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)

    match = re.search(r"/video/(\d+)", url)
    if match:
        return match.group(1)

    match = re.search(r"/reel/([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)

    match = re.search(r"/videos/(\d+)", url)
    if match:
        return match.group(1)

    return url.rstrip("/").split("/")[-1]


def filter_results(results, keyword, min_score=0.40):
    filtered = []
    seen = set()


    for r in results:

        raw_url = r.get("url", "")
        title = r.get("title", "")

        if not raw_url:
            continue

        url = normalize_url(raw_url)

        if url in seen:
            continue

        if not is_valid_video_url(url):
            continue

        seen.add(url)

        score = score_content(
            title=title,
            keyword=keyword,
            url=url
        )

        if score < min_score:
            continue

        filtered.append({
            "url": url,
            "title": title,
            "score": round(score, 2),
            "platform": extract_platform(url),
            "externalId": extract_video_id(url)
        })

    filtered.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return filtered

