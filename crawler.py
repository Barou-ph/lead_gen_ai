"""
crawler.py — async multi-thread version
- ThreadPoolExecutor: crawl N sites song song
- asyncio-style search: gom tất cả engine không cần chờ tuần tự
- Sleep giảm tối đa (chỉ giữ ở search để tránh ban IP)
- Mỗi lần chạy tạo file Excel MỚI có timestamp, KHÔNG overwrite
- Append vào visited.txt để không crawl lại
"""

import requests
import random
import time
import urllib3
import re
import base64
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from extractor import extract_contact_and_field
from exporter import export_to_excel

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ══════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════
TARGET_LEADS = 100
MAX_WORKERS = 8  # số thread crawl song song
SEARCH_DELAY = (1.5, 3.0)  # delay giữa các search query
CRAWL_DELAY = (0.3, 0.8)  # delay giữa các thread (nhỏ thôi)
MAX_RETRIES = 2
SESSION_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

QUERIES = [
    # English — core
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
    "blockchain company vietnam",
    "fintech company vietnam",
    "edtech company vietnam",
    "healthtech company vietnam",
    "game development company vietnam",
    # Vietnamese không dấu
    "cong ty phan mem viet nam",
    "cong ty cong nghe ho chi minh",
    "cong ty lap trinh ha noi",
    "cong ty thiet ke web viet nam",
    "cong ty phat trien ung dung di dong",
    "cong ty outsourcing viet nam",
    "cong ty digital marketing viet nam",
    "cong ty ai viet nam",
    "startup cong nghe viet nam",
    "cong ty blockchain viet nam",
]

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
]

BAD_DOMAINS = [
    "bing.com",
    "google.com",
    "yahoo.com",
    "duckduckgo.com",
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
    "bocasay.com",
    "pixelake.com",
    "outsourced.co",
    "joomlavi.com",
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
    "vietnamoutsource.com",
    "outsourced.co",
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
    "/software-development-companies",
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
    if "bing.com" not in url:
        return url
    match = re.search(r"[?&]u=([^&]+)", url)
    if match:
        encoded = match.group(1)
        if encoded.startswith("a1"):
            encoded = encoded[2:]
        pad = 4 - len(encoded) % 4
        if pad != 4:
            encoded += "=" * pad
        try:
            decoded = base64.urlsafe_b64decode(encoded).decode("utf-8", errors="ignore")
            if decoded.startswith("http") and "bing.com" not in decoded:
                return decoded
        except Exception:
            pass
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
    try:
        parts = url.split("//")[-1].split("/")[0].split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else url
    except Exception:
        return url


def is_clean_link(link: str, domain_counter: dict) -> bool:
    if not link or not link.startswith("http"):
        return False
    low = link.lower()
    if "bing.com/ck/a" in low or "bing.com" in low.split("/")[2]:
        return False
    if any(b in low for b in BAD_DOMAINS):
        return False
    if any(k in low for k in BAD_PATHS):
        return False
    root = get_root_domain(link)
    if domain_counter.get(root, 0) >= 2:  # max 2 URL/domain
        return False
    domain_counter[root] = domain_counter.get(root, 0) + 1
    return True


def fetch_url(url: str, method: str = "GET", data: dict = None):
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
                time.sleep(5 * (attempt + 1))
        except Exception:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
    return None


# ══════════════════════════════════════════════════════════════════════
#  SEARCH — chạy 3 engine SONG SONG cho mỗi query
# ══════════════════════════════════════════════════════════════════════
def _bing_worker(query: str, pages: int = 3) -> list:
    links = []
    for page in range(pages):
        url = (
            f"https://www.bing.com/search"
            f"?q={requests.utils.quote(query)}&first={page*10+1}&count=10"
        )
        r = fetch_url(url)
        if not r:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        for h2 in soup.select("li.b_algo h2 a"):
            href = h2.get("href", "")
            if "bing.com" in href:
                href = resolve_bing_url(href)
            if href and href.startswith("http") and "bing.com" not in href:
                links.append(href)
        time.sleep(random.uniform(1.0, 2.0))
    return links


def _ddg_worker(query: str) -> list:
    links = []
    r = fetch_url("https://html.duckduckgo.com/html/", method="POST", data={"q": query})
    if r:
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a.result__a"):
            href = a.get("href", "")
            if href.startswith("http"):
                links.append(href)
    return links


def _mojeek_worker(query: str, pages: int = 2) -> list:
    links = []
    for page in range(pages):
        url = (
            f"https://www.mojeek.com/search"
            f"?q={requests.utils.quote(query)}&s={page*10}"
        )
        r = fetch_url(url)
        if r:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select("ul.results-standard li a.ob"):
                href = a.get("href", "")
                if href.startswith("http"):
                    links.append(href)
        time.sleep(random.uniform(1.0, 1.5))
    return links


def search_query_parallel(query: str, domain_counter: dict) -> list:
    """Chạy Bing + DDG + Mojeek SONG SONG (3 thread) cho 1 query."""
    raw = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_bing_worker, query, 3): "Bing",
            pool.submit(_ddg_worker, query): "DDG",
            pool.submit(_mojeek_worker, query, 2): "Mojeek",
        }
        counts = {}
        for fut in as_completed(futures):
            engine = futures[fut]
            try:
                result = fut.result()
                counts[engine] = len(result)
                raw.extend(result)
            except Exception as e:
                counts[engine] = 0

    parts = " | ".join(f"{e}:{counts.get(e,0)}" for e in ["Bing", "DDG", "Mojeek"])
    print(f"    [{parts}]", end=" ")

    clean = []
    for l in raw:
        if is_clean_link(l, domain_counter):
            clean.append(l)
    return list(set(clean))


# ══════════════════════════════════════════════════════════════════════
#  EMAIL / LEAD SCORING
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


HIGH_VALUE = {"IT Software", "IT Outsourcing", "AI/ML", "Cloud/DevOps", "Mobile Dev"}


def score_lead(data: dict) -> dict:
    score, tags = 0, []
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
    if field in HIGH_VALUE:
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
#  CRAWL — chạy MAX_WORKERS sites SONG SONG
# ══════════════════════════════════════════════════════════════════════
def crawl_one(link: str) -> dict | None:
    """Crawl 1 link, trả dict lead hoặc None."""
    time.sleep(random.uniform(*CRAWL_DELAY))  # nhỏ thôi, chạy song song rồi
    try:
        emails, phones, field = extract_contact_and_field(link)
        if not emails and not phones:
            return None
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
        return score_lead(lead)
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════
#  VISITED
# ══════════════════════════════════════════════════════════════════════
def load_visited() -> set:
    try:
        with open("visited.txt", "r", encoding="utf-8") as f:
            return set(l.strip() for l in f if l.strip())
    except FileNotFoundError:
        return set()


def save_visited(links: list):
    with open("visited.txt", "a", encoding="utf-8") as f:
        for l in links:
            f.write(l + "\n")


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    visited = load_visited()
    all_links = []
    domain_counter = {}

    print(
        f"🚀 Target: {TARGET_LEADS} leads | {len(QUERIES)} queries | {MAX_WORKERS} threads"
    )
    print(f"📅 Session: {SESSION_TIMESTAMP}\n" + "=" * 65)

    # ── Phase 1: Search song song theo query (tuần tự query, song song engine) ──
    for i, query in enumerate(QUERIES):
        print(f'\n[{i+1}/{len(QUERIES)}] "{query}"')
        results = search_query_parallel(query, domain_counter)
        new = [l for l in results if l not in visited and l not in all_links]
        all_links.extend(new)
        print(f"+{len(new)} | Pool: {len(all_links)}")
        time.sleep(random.uniform(*SEARCH_DELAY))

    all_links = list(set(all_links))
    random.shuffle(all_links)

    print(f"\n{'='*65}")
    print(
        f"📦 Pool sạch: {len(all_links)} links → bắt đầu crawl {MAX_WORKERS} threads\n"
    )

    # ── Phase 2: Crawl song song MAX_WORKERS threads ──────────────────
    data = []
    newly_visited = []
    total = len(all_links)
    done = 0
    lock_print = __import__("threading").Lock()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_to_link = {pool.submit(crawl_one, link): link for link in all_links}

        for fut in as_completed(future_to_link):
            if len(data) >= TARGET_LEADS:
                pool.shutdown(wait=False, cancel_futures=True)
                break

            link = future_to_link[fut]
            done += 1

            try:
                result = fut.result()
            except Exception:
                result = None

            with lock_print:
                bar = f"[{done}/{total} | Lead {len(data)}/{TARGET_LEADS}]"
                if result:
                    data.append(result)
                    newly_visited.append(link)
                    print(
                        f"✅ {bar} Grade={result['grade']} (+{result['score']}pts) "
                        f"| {result['field']}"
                    )
                    print(f"   📧 {result['emails'][:60]}")
                    print(f"   📞 {result['phones']}")
                    if result["tags"]:
                        print(f"   🏷  {result['tags']}")
                else:
                    print(f"❌ {bar} {link[:70]}")

    # ── Save visited + export ─────────────────────────────────────────
    save_visited(newly_visited)

    grade_order = {"A": 0, "B": 1, "C": 2, "D": 3}
    data.sort(
        key=lambda x: (grade_order.get(x.get("grade", "D"), 3), -x.get("score", 0))
    )

    print(f"\n{'='*65}")
    print(f"🎯 Leads thu được: {len(data)}/{TARGET_LEADS}")
    gc = {}
    for d in data:
        g = d.get("grade", "?")
        gc[g] = gc.get(g, 0) + 1
    for g, c in sorted(gc.items()):
        print(f"  Grade {g}: {c} leads")

    if data:
        export_to_excel(data, session=SESSION_TIMESTAMP)
        print("✅ Done!")
    else:
        print("⚠️  Không có lead nào.")
