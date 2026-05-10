"""
enricher.py — Enrich lead với thêm signals:
- Có tuyển dụng không (hiring)
- Có blog không
- Có English content không
- Estimate company size
- Có LinkedIn page không
Chạy sau khi crawl xong, trước khi AI phân tích.
"""

import requests
import re
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
}

# Keywords chỉ hiring page
HIRING_KEYWORDS = [
    "job",
    "career",
    "hiring",
    "tuyen dung",
    "tuyển dụng",
    "we're hiring",
    "join us",
    "join our team",
    "open position",
    "vacancy",
    "recruitment",
]

# Keywords chỉ company có English content (global reach)
ENGLISH_KEYWORDS = [
    "our services",
    "about us",
    "contact us",
    "our team",
    "our clients",
    "case study",
    "portfolio",
]

# Size signals từ text
SIZE_SIGNALS = {
    "enterprise": ["1000+", "over 1000", "5000", "10000", "multinational", "global"],
    "large": ["500+", "over 500", "300+", "500 employees", "300 staff"],
    "medium": ["100+", "over 100", "200+", "150+", "100 employees"],
    "small": ["50+", "30+", "20+", "small team", "startup"],
    "micro": ["10+", "under 20", "small", "boutique", "independent"],
}


def _fetch(url: str, timeout: int = 6) -> str:
    try:
        r = requests.get(
            url, headers=HEADERS, timeout=timeout, verify=False, allow_redirects=True
        )
        if r.status_code == 200:
            return r.text
    except Exception:
        pass
    return ""


def _check_hiring(html: str, base_url: str) -> bool:
    """Kiểm tra xem site có tuyển dụng không."""
    low = html.lower()
    # Check keywords trong nội dung
    if any(k in low for k in HIRING_KEYWORDS):
        return True
    # Check /careers hoặc /jobs page tồn tại
    for path in ["/careers", "/jobs", "/tuyen-dung", "/work-with-us"]:
        try:
            r = requests.head(
                base_url.rstrip("/") + path,
                headers=HEADERS,
                timeout=4,
                verify=False,
                allow_redirects=True,
            )
            if r.status_code == 200:
                return True
        except Exception:
            pass
    return False


def _check_english(html: str) -> bool:
    low = html.lower()
    count = sum(1 for k in ENGLISH_KEYWORDS if k in low)
    return count >= 3  # có ít nhất 3 dấu hiệu English


def _check_blog(html: str, base_url: str) -> bool:
    low = html.lower()
    if any(k in low for k in ["/blog", "/news", "/insight", "/resource"]):
        return True
    for path in ["/blog", "/news", "/insights"]:
        try:
            r = requests.head(
                base_url.rstrip("/") + path,
                headers=HEADERS,
                timeout=4,
                verify=False,
                allow_redirects=True,
            )
            if r.status_code == 200:
                return True
        except Exception:
            pass
    return False


def _estimate_size(html: str) -> str:
    low = html.lower()
    for size, signals in SIZE_SIGNALS.items():
        if any(s in low for s in signals):
            return size
    # Fallback: đếm số lần mention "team" và "employee"
    team_count = low.count("team") + low.count("staff") + low.count("employee")
    if team_count > 10:
        return "medium"
    if team_count > 3:
        return "small"
    return "unknown"


def _check_linkedin(html: str) -> str:
    """Tìm LinkedIn URL trong homepage."""
    match = re.search(r"https?://(?:www\.)?linkedin\.com/company/([^\"'\s/]+)", html)
    if match:
        return f"https://linkedin.com/company/{match.group(1)}"
    return ""


def _extract_description(html: str, max_chars: int = 300) -> str:
    """Lấy meta description hoặc đoạn text đầu tiên của site."""
    soup = BeautifulSoup(html, "html.parser")
    # Meta description
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"][:max_chars].strip()
    # OG description
    og = soup.find("meta", property="og:description")
    if og and og.get("content"):
        return og["content"][:max_chars].strip()
    # Fallback: first <p>
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) > 50:
            return text[:max_chars]
    return ""


def enrich_lead(lead: dict) -> dict:
    """
    Nhận 1 lead dict, trả về lead dict đã enrich thêm:
    - is_hiring (bool)
    - has_blog (bool)
    - has_english (bool)
    - size_estimate (str)
    - linkedin_url (str)
    - description (str)
    """
    url = lead.get("website", "")
    if not url:
        return {
            **lead,
            "is_hiring": False,
            "has_blog": False,
            "has_english": False,
            "size_estimate": "unknown",
            "linkedin_url": "",
            "description": "",
        }

    html = _fetch(url)
    if not html:
        return {
            **lead,
            "is_hiring": False,
            "has_blog": False,
            "has_english": False,
            "size_estimate": "unknown",
            "linkedin_url": "",
            "description": "",
        }

    enriched = {
        **lead,
        "is_hiring": _check_hiring(html, url),
        "has_blog": _check_blog(html, url),
        "has_english": _check_english(html),
        "size_estimate": _estimate_size(html),
        "linkedin_url": _check_linkedin(html),
        "description": _extract_description(html),
    }

    # Cập nhật score: thêm điểm nếu có hiring hoặc English
    bonus = 0
    tags = enriched.get("tags", "")
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    if enriched["is_hiring"]:
        bonus += 4
        tag_list.append("Hiring")
    if enriched["has_english"]:
        bonus += 2
        tag_list.append("English Site")
    if enriched["linkedin_url"]:
        bonus += 2
        tag_list.append("Has LinkedIn")

    new_score = enriched.get("score", 0) + bonus
    enriched["score"] = new_score
    enriched["tags"] = ", ".join(tag_list)

    # Recompute grade
    enriched["grade"] = (
        "A"
        if new_score >= 18
        else "B" if new_score >= 12 else "C" if new_score >= 6 else "D"
    )

    return enriched


def enrich_all(leads: list, max_workers: int = 6) -> list:
    """Enrich toàn bộ leads song song."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    results = [None] * len(leads)
    lock = threading.Lock()
    completed = [0]

    def worker(idx: int, lead: dict):
        enriched = enrich_lead(lead)
        with lock:
            results[idx] = enriched
            completed[0] += 1
            pct = completed[0] / len(leads) * 100
            print(
                f"\r  🔍 Enriching... {completed[0]}/{len(leads)} ({pct:.0f}%)", end=""
            )
        return enriched

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(worker, i, lead): i for i, lead in enumerate(leads)}
        for _ in as_completed(futures):
            pass

    print()  # newline sau progress
    return [r for r in results if r is not None]
