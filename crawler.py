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
TARGET_LEADS = 100
MAX_RETRIES = 3
RETRY_DELAY = 3

# ── 30 queries đa dạng để đủ pool ─────────────────────────────────────
QUERIES = [
    # English
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
    "outsourcing company vietnam",
    "software development firm vietnam",
    "app development company ho chi minh",
    "software house vietnam",
    "it consulting firm vietnam",
    "ecommerce development vietnam",
    "react developer company vietnam",
    "nodejs company vietnam",
    "python development company vietnam",
    "cloud services company vietnam",
    # Vietnamese (không dấu)
    "cong ty phan mem viet nam",
    "cong ty cong nghe ho chi minh",
    "cong ty lap trinh ha noi",
    "cong ty thiet ke web viet nam",
    "cong ty phat trien ung dung di dong",
    "cong ty outsourcing viet nam",
    "cong ty digital marketing viet nam",
    "cong ty ai viet nam",
    "cong ty saas viet nam",
    "startup cong nghe viet nam",
]

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
]

# Domain rác hoàn toàn loại bỏ
BAD_DOMAINS = [
    # Search engines → redirect link
    "bing.com",
    "google.com",
    "yahoo.com",
    "duckduckgo.com",
    # Social / job
    "linkedin",
    "facebook",
    "twitter",
    "youtube",
    "instagram",
    "tiktok",
    "itviec",
    "vietnamworks",
    "topcv",
    "jobstreet",
    "recruit.net",
    "wellfound.com",
    "thesaasjobs",
    "10times.com",
    # Directories (không phải company thật)
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
    "appdevelopmentcompanies.co",
    "topsoftwarecompanies.co",
    "softwarecompanynetwork",
    "globalsoftwarecompanies",
    "bestarion.com",
    "topon.tech",
    "ensun.io",
    "techvify.com",
    # Info / news / blog
    "zoominfo",
    "crunchbase",
    "wikipedia",
    "reddit",
    "quora",
    "medium.com",
    "blogspot",
    "wordpress.com",
    "vietcetera",
    "forbes.com",
    "techcollectivesea",
    "thegradient.pub",
    "investasian",
    "hkbav",
    "bizasean",
    "aseantechsec",
    "theinfostride",
    "vietnamdoneright",
    "vietnamoutsource.com",
    "bocasay.com",
    "pixelake.com",
    "outsourced.co",
    "joomlavi.com",
    # Irrelevant
    "zhihu",
    "baidu",
    "mobile01",
    "juraforum",
    "wirtschaftsforum",
    "digitalspy",
    "smergers",
    "vtudin",
    "ciovietnam",
    "stackexchange",
    "stackoverflow",
    "math.stackexchange",
    "microsoft",
    "amazon.com",
    "apple.com",
    "ibm.com",
    "52wmb",
    "soopage",
    "tradebrio.com",
    "jcsearch",
    "qblends.com",
    "offshoredevelopmentteam.com",
    "golftipsandvideos",
    "vastvietnam.org",
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
    "/jobs/",
    "/company/",
    "/companies/",
    "/agencies/",
    "/developers/",
    "/location/",
    "/local-agencies/",
    "/software-development-companies",  # directory page của techvify etc.
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
    """Decode Bing redirect URL (bing.com/ck/a?) → URL thật."""
    if "bing.com" not in url:
        return url
    match = re.search(r"[?&]u=([^&]+)", url)
    if match:
        encoded = match.group(1)
        if encoded.startswith("a1"):
            encoded = encoded[2:]
        padding = 4 - len(encoded) % 4
        if padding != 4:
            encoded += "=" * padding
        try:
            decoded = base64.urlsafe_b64decode(encoded).decode("utf-8", errors="ignore")
            if decoded.startswith("http") and "bing.com" not in decoded:
                return decoded
        except Exception:
            pass
    # fallback: follow redirect
    try:
        r = requests.head(
            url, headers=get_headers(), timeout=5, allow_redirects=True, verify=False
        )
        if r.url and "bing.com" not in r.url:
            return r.url
    except Exception:
        pass
    return ""


def get_root_domain(url: str) -> str:
    """Lấy root domain (ví dụ: https://sub.example.com/page → example.com)."""
    try:
        parts = url.split("//")[-1].split("/")[0].split(".")
        if len(parts) >= 2:
            return ".".join(parts[-2:])
    except Exception:
        pass
    return url


def is_clean_link(link: str, seen_domains: set) -> bool:
    """Lọc link rác + giới hạn 3 link/domain."""
    if not link or not link.startswith("http"):
        return False
    low = link.lower()

    # Bing redirect chưa được decode
    if "bing.com/ck/a" in low:
        return False

    if any(b in low for b in BAD_DOMAINS):
        return False
    if any(k in low for k in BAD_PATHS):
        return False

    # Giới hạn 3 URL cùng domain (tránh crawl 10 page của cùng 1 site)
    root = get_root_domain(link)
    count = sum(1 for d in seen_domains if d == root)
    if count >= 3:
        return False

    return True


def fetch_with_retry(url: str, method: str = "GET", data: dict = None):
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
                print(f"    ⏳ HTTP {r.status_code} — chờ {wait}s...")
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
def search_bing(query: str, pages: int = 3) -> list:
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
            if "bing.com" in href:
                href = resolve_bing_url(href)
            if href and href.startswith("http") and "bing.com" not in href:
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


def search_mojeek(query: str, pages: int = 2) -> list:
    links = []
    for page in range(pages):
        url = (
            f"https://www.mojeek.com/search"
            f"?q={requests.utils.quote(query)}&s={page*10}"
        )
        r = fetch_with_retry(url)
        if r:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select("ul.results-standard li a.ob"):
                href = a.get("href", "")
                if href.startswith("http"):
                    links.append(href)
        time.sleep(random.uniform(2.0, 3.0))
    return links


def search_all_engines(query: str, seen_domains: set) -> list:
    all_links = []

    print(f"    🔎 Bing...", end=" ", flush=True)
    bing = search_bing(query, pages=3)
    print(f"{len(bing)} links", end=" | ", flush=True)
    all_links.extend(bing)

    if len(bing) < 5:
        print(f"DDG...", end=" ", flush=True)
        ddg = search_ddg(query)
        print(f"{len(ddg)}", end=" | ", flush=True)
        all_links.extend(ddg)

        print(f"Mojeek...", end=" ", flush=True)
        moj = search_mojeek(query, pages=2)
        print(f"{len(moj)}", end="", flush=True)
        all_links.extend(moj)
    print()

    clean = []
    for l in all_links:
        if is_clean_link(l, seen_domains):
            root = get_root_domain(l)
            seen_domains.add(root)
            clean.append(l)

    return list(set(clean))


# ══════════════════════════════════════════════════════════════════════
#  EMAIL SCORING
# ══════════════════════════════════════════════════════════════════════
EMAIL_SCORES = {
    "ceo": 10,
    "founder": 10,
    "director": 9,
    "cto": 9,
    "coo": 9,
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
        return "Decision Maker"
    if s >= 5:
        return "Good"
    if s >= 2:
        return "Generic"
    return "Low"


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
    phones = data.get("phones", "")
    website = data.get("website", "").lower()
    field = data.get("field", "")

    if emails:
        best = max(score_email(e) for e in emails)
        score += max(best, 0)
        if best >= 8:
            tags.append("Decision Maker")

    if phones:
        score += 5
        tags.append("Has Phone")

    if field in HIGH_VALUE_FIELDS:
        score += 5
        tags.append(field)

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
    seen_domains = set()

    print(f"🚀 Target: {TARGET_LEADS} leads | {len(QUERIES)} queries\n" + "=" * 60)

    for i, query in enumerate(QUERIES):
        print(f'\n[{i+1}/{len(QUERIES)}] "{query}"')
        results = search_all_engines(query, seen_domains)
        new = [l for l in results if l not in visited and l not in all_links]
        all_links.extend(new)
        print(f"  → +{len(new)} mới | Pool: {len(all_links)}")
        time.sleep(random.uniform(3.0, 5.0))

    all_links = list(set(all_links))
    random.shuffle(all_links)  # shuffle để không bị cluster theo query

    print(f"\n{'='*60}")
    print(f"📦 Tổng link sạch: {len(all_links)}")
    print(f"{'='*60}\n")

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
                f"  ✅ Lead #{len(data)} | Grade={scored['grade']} "
                f"(+{scored['score']}pts) | {field}"
            )
            print(f"     📧 {ranked[:2]}")
            print(f"     📞 {phones[:2]}")
            if scored["tags"]:
                print(f"     🏷  {scored['tags']}")
        else:
            print("  ❌ No contact")

        time.sleep(random.uniform(1.5, 2.5))

    # Sort A → D
    grade_order = {"A": 0, "B": 1, "C": 2, "D": 3}
    data.sort(
        key=lambda x: (grade_order.get(x.get("grade", "D"), 3), -x.get("score", 0))
    )

    print(f"\n{'='*60}")
    print(f"🎯 Tổng lead: {len(data)}/{TARGET_LEADS}")
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
