import requests
import random
import time
import urllib3
import re
import base64
from bs4 import BeautifulSoup
from extractor import extract_contact_and_field
from exporter import export_to_excel

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ══════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════
TARGET_LEADS = 50
MAX_RETRIES = 3
RETRY_DELAY = 3

QUERIES = [
    "software company vietnam",
    "it outsourcing vietnam",
    "web development company vietnam",
    "mobile app development vietnam",
    "digital agency vietnam",
    "tech startup vietnam",
    "saas company vietnam",
    "ai company vietnam",
    "it service company ho chi minh",
    "software outsourcing hanoi",
    "cong ty phan mem viet nam",
    "cong ty cong nghe ho chi minh",
    "outsourcing company vietnam",
    "software development firm vietnam",
    "app development company ho chi minh",
]

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]

BAD_DOMAINS = [
    "bing.com",
    "google.com",
    "yahoo.com",
    "linkedin",
    "facebook",
    "twitter",
    "youtube",
    "instagram",
    "tiktok",
    "techbehemoths",
    "goodfirms",
    "clutch",
    "sortlist",
    "upcity",
    "manifest",
    "designrush",
    "bark.com",
    "yelp",
    "yello",
    "zoominfo",
    "crunchbase",
    "wikipedia",
    "reddit",
    "quora",
    "medium.com",
    "blogspot",
    "wordpress.com",
    "microsoft",
    "amazon",
    "apple.com",
    "zhihu",
    "baidu",
    "mobile01",
    "recruit.net",
    "juraforum",
    "wirtschaftsforum",
    "digitalspy",
    "smergers",
    "hkbav",
    "vtudin",
    "ciovietnam",
]

BAD_PATHS = [
    "/blog",
    "/top-",
    "/list-",
    "/category",
    "/directory",
    "/profile",
    "/review",
    "/ranking",
    "/tag/",
    "/news/",
    "/press/",
    "/search/",
    "/question/",
    "/topic/",
    "/forum",
    "/answer/",
]


# ══════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════
def get_headers():
    return {
        "User-Agent": random.choice(UA_POOL),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Connection": "keep-alive",
        "DNT": "1",
    }


def resolve_bing_url(url: str) -> str:
    """Giải mã Bing redirect (bing.com/ck/a?...) → URL thật."""
    if "bing.com/ck/a" not in url:
        return url
    # Thử decode param u=a1<base64>
    match = re.search(r"[?&]u=([^&]+)", url)
    if match:
        encoded = match.group(1)
        if encoded.startswith("a1"):
            encoded = encoded[2:]
        # Thêm padding
        padding = 4 - len(encoded) % 4
        if padding != 4:
            encoded += "=" * padding
        try:
            decoded = base64.urlsafe_b64decode(encoded).decode("utf-8", errors="ignore")
            if decoded.startswith("http"):
                return decoded
        except Exception:
            pass
    # Fallback: follow HTTP redirect
    try:
        r = requests.head(
            url, headers=get_headers(), timeout=5, allow_redirects=True, verify=False
        )
        if r.url and "bing.com" not in r.url:
            return r.url
    except Exception:
        pass
    return ""  # trả "" nếu không giải được → sẽ bị lọc bởi is_clean_link


def is_clean_link(link: str) -> bool:
    if not link or not link.startswith("http"):
        return False
    low = link.lower()
    if any(b in low for b in BAD_DOMAINS):
        return False
    if any(k in low for k in BAD_PATHS):
        return False
    return True


def fetch_with_retry(
    url: str, method: str = "GET", data: dict = None
) -> requests.Response | None:
    """GET hoặc POST với retry + exponential backoff."""
    for attempt in range(MAX_RETRIES):
        try:
            if method == "POST":
                r = requests.post(
                    url, data=data, headers=get_headers(), timeout=10, verify=False
                )
            else:
                r = requests.get(
                    url,
                    headers=get_headers(),
                    timeout=10,
                    verify=False,
                    allow_redirects=True,
                )

            if r.status_code == 200:
                return r
            if r.status_code in (429, 503):
                wait = RETRY_DELAY * (2**attempt)
                print(f"    ⏳ HTTP {r.status_code} — retry sau {wait}s...")
                time.sleep(wait)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
        except Exception:
            pass
    return None


# ══════════════════════════════════════════════════════════════════════
#  SEARCH ENGINES
# ══════════════════════════════════════════════════════════════════════
def search_bing(query: str, pages: int = 2) -> list:
    links = []
    for page in range(pages):
        url = (
            f"https://www.bing.com/search"
            f"?q={requests.utils.quote(query)}&first={page*10+1}&count=10"
        )
        r = fetch_with_retry(url)
        if not r:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        for h2 in soup.select("li.b_algo h2 a"):
            href = h2.get("href", "")
            if "bing.com/ck" in href:
                href = resolve_bing_url(href)
            if href.startswith("http"):
                links.append(href)
        time.sleep(random.uniform(2.0, 3.5))
    return links


def search_ddg(query: str) -> list:
    links = []
    r = fetch_with_retry(
        "https://html.duckduckgo.com/html/", method="POST", data={"q": query}
    )
    if r:
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a.result__a"):
            href = a.get("href", "")
            if href.startswith("http"):
                links.append(href)
    time.sleep(random.uniform(3.0, 5.0))
    return links


def search_mojeek(query: str) -> list:
    links = []
    url = f"https://www.mojeek.com/search?q={requests.utils.quote(query)}"
    r = fetch_with_retry(url)
    if r:
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("ul.results-standard li a.ob"):
            href = a.get("href", "")
            if href.startswith("http"):
                links.append(href)
    time.sleep(random.uniform(2.0, 3.5))
    return links


def search_all_engines(query: str) -> list:
    all_links = []

    print(f"    🔎 Bing...", end=" ", flush=True)
    bing = search_bing(query, pages=2)
    print(f"{len(bing)} links")
    all_links.extend(bing)

    if len(bing) < 5:
        print(f"    🔎 DDG...", end=" ", flush=True)
        ddg = search_ddg(query)
        print(f"{len(ddg)} links")
        all_links.extend(ddg)

        print(f"    🔎 Mojeek...", end=" ", flush=True)
        moj = search_mojeek(query)
        print(f"{len(moj)} links")
        all_links.extend(moj)

    clean = [l for l in all_links if is_clean_link(l)]
    return list(set(clean))


# ══════════════════════════════════════════════════════════════════════
#  EMAIL SCORING
# ══════════════════════════════════════════════════════════════════════
EMAIL_SCORES = {
    "ceo": 10,
    "founder": 10,
    "director": 9,
    "cto": 9,
    "head": 8,
    "sales": 8,
    "bd": 8,
    "business": 7,
    "partner": 7,
    "hr": 6,
    "recruit": 6,
    "career": 6,
    "hiring": 6,
    "hello": 4,
    "hi": 4,
    "contact": 3,
    "info": 2,
    "admin": 2,
    "support": 2,
    "help": 1,
    "general": 1,
    "noreply": -99,
    "no-reply": -99,
    "bounce": -99,
    "donotreply": -99,
}


def score_email(email: str) -> int:
    prefix = email.split("@")[0].lower()
    for kw, sc in EMAIL_SCORES.items():
        if kw in prefix:
            return sc
    return 3


def rank_emails(emails: list) -> list:
    return sorted(emails, key=score_email, reverse=True)


def email_quality_label(email: str) -> str:
    s = score_email(email)
    if s >= 8:
        return "🔥 Decision Maker"
    if s >= 5:
        return "✅ Good"
    if s >= 2:
        return "🔵 Generic"
    return "⚫ Low"


# ══════════════════════════════════════════════════════════════════════
#  LEAD SCORING
# ══════════════════════════════════════════════════════════════════════
HIGH_VALUE_FIELDS = {
    "IT Software",
    "IT Outsourcing",
    "AI/ML",
    "Cloud/DevOps",
    "Mobile Dev",
}


def score_lead(data: dict) -> dict:
    score = 0
    tags = []

    emails = [e for e in data.get("emails", "").split(", ") if e]
    phones = [p for p in data.get("phones", "").split(", ") if p]
    website = data.get("website", "").lower()
    field = data.get("field", "")

    if emails:
        best = max(score_email(e) for e in emails)
        score += best
        if best >= 8:
            tags.append("Decision Maker Email")

    if phones:
        score += 5
        tags.append("Has Phone")

    if field in HIGH_VALUE_FIELDS:
        score += 5
        tags.append(f"High-Value: {field}")

    if ".vn" in website:
        score += 3
        tags.append("VN Domain")

    if len(emails) > 1:
        score += 2
        tags.append("Multi-Email")

    grade = "A" if score >= 18 else "B" if score >= 12 else "C" if score >= 6 else "D"
    return {**data, "score": score, "grade": grade, "tags": ", ".join(tags)}


# ══════════════════════════════════════════════════════════════════════
#  VISITED
# ══════════════════════════════════════════════════════════════════════
def load_visited() -> set:
    try:
        with open("visited.txt", "r", encoding="utf-8") as f:
            return set(l.strip() for l in f if l.strip())
    except FileNotFoundError:
        return set()


def save_visited(link: str):
    with open("visited.txt", "a", encoding="utf-8") as f:
        f.write(link + "\n")


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    visited = load_visited()
    all_links = []

    print(f"🔍 Chạy {len(QUERIES)} queries...\n" + "=" * 60)

    for i, query in enumerate(QUERIES):
        print(f'\n[{i+1}/{len(QUERIES)}] "{query}"')
        results = search_all_engines(query)
        new = [l for l in results if l not in visited and l not in all_links]
        all_links.extend(new)
        print(f"  → +{len(new)} mới | Pool: {len(all_links)}")
        time.sleep(random.uniform(3.0, 6.0))

    all_links = list(set(all_links))
    print(f"\n{'='*60}\n📦 Tổng link sạch: {len(all_links)}\n{'='*60}\n")

    data = []

    for i, link in enumerate(all_links):
        if len(data) >= TARGET_LEADS:
            print(f"\n🎯 Đủ {TARGET_LEADS} leads, dừng.")
            break

        bar = f"[{i+1}/{len(all_links)} | Lead {len(data)}/{TARGET_LEADS}]"
        print(f"\n{bar} {link}")

        emails, phones, field = extract_contact_and_field(link)

        if emails or phones:
            ranked = rank_emails(emails)
            best = ranked[0] if ranked else ""

            lead = {
                "website": link,
                "emails": ", ".join(ranked[:3]),
                "phones": ", ".join(phones[:3]),
                "field": field,
                "best_email": best,
                "email_quality": email_quality_label(best) if best else "",
            }
            scored = score_lead(lead)
            data.append(scored)
            save_visited(link)

            print(
                f"  ✅ Lead #{len(data)} | Grade={scored['grade']} (+{scored['score']}pts) | {field}"
            )
            print(f"     📧 {ranked[:2]}")
            print(f"     📞 {phones[:2]}")
            if scored["tags"]:
                print(f"     🏷  {scored['tags']}")
        else:
            print("  ❌ No contact")

        time.sleep(random.uniform(1.5, 3.0))

    # Sort grade A → D trước khi export
    grade_order = {"A": 0, "B": 1, "C": 2, "D": 3}
    data.sort(
        key=lambda x: (grade_order.get(x.get("grade", "D"), 3), -x.get("score", 0))
    )

    print(f"\n{'='*60}")
    print(f"🎯 Tổng lead: {len(data)}")
    grade_counts = {}
    for d in data:
        g = d.get("grade", "?")
        grade_counts[g] = grade_counts.get(g, 0) + 1
    for g, c in sorted(grade_counts.items()):
        print(f"  Grade {g}: {c} leads")

    if data:
        export_to_excel(data)
        print("✅ Export xong → leads.xlsx")
    else:
        print("⚠️  Không có lead nào.")
