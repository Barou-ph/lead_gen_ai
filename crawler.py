import requests
import random
import time
import urllib3
from bs4 import BeautifulSoup
from extractor import extract_contact_and_field
from exporter import export_to_excel

# ── Tắt SSL warning hoàn toàn ─────────────────────────────────────────
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Queries ────────────────────────────────────────────────────────────
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
    "công ty phần mềm việt nam",
    "công ty công nghệ hồ chí minh",
    "outsourcing company vietnam",
    "software development firm vietnam",
    "app development company ho chi minh",
]

# ── User-Agent pool để rotate ──────────────────────────────────────────
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
]

# ── Domain/path blacklist ──────────────────────────────────────────────
BAD_DOMAINS = [
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
    "topon.tech",
    "ensun.io",
    "globalsoftwarecompanies",
    "softwarecompanynetwork",
    "bestarion.com/software-development",  # directory page
    "microsoft",
    "google.com",
    "amazon",
    "apple.com",
]

BAD_PATH_KEYWORDS = [
    "/blog",
    "/top-",
    "/list-",
    "/category",
    "/directory",
    "/profile",
    "/companies/",
    "/review",
    "/ranking",
    "/tag/",
    "/news/",
    "/press/",
    "/search/",
]


def get_headers():
    return {
        "User-Agent": random.choice(UA_POOL),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "DNT": "1",
    }


def is_clean_link(link: str) -> bool:
    low = link.lower()
    if not low.startswith("http"):
        return False
    if any(b in low for b in BAD_DOMAINS):
        return False
    if any(k in low for k in BAD_PATH_KEYWORDS):
        return False
    return True


# ══════════════════════════════════════════════════════════════════════
#  ENGINE 1: Bing scraping (chính)
# ══════════════════════════════════════════════════════════════════════
def search_bing(query: str, pages: int = 3) -> list[str]:
    links = []
    session = requests.Session()

    for page in range(pages):
        offset = page * 10
        url = f"https://www.bing.com/search?q={requests.utils.quote(query)}&first={offset + 1}&count=10"

        try:
            res = session.get(url, headers=get_headers(), timeout=10, verify=False)
            soup = BeautifulSoup(res.text, "html.parser")

            # Bing result links nằm trong <li class="b_algo"> → <h2> → <a>
            for h2 in soup.select("li.b_algo h2 a"):
                href = h2.get("href", "")
                if href.startswith("http"):
                    links.append(href)

            # Fallback: bắt tất cả <a> có cite (URL hiển thị)
            if not links:
                for cite in soup.select("li.b_algo cite"):
                    text = cite.get_text()
                    if text.startswith("http"):
                        links.append(text)

        except Exception as e:
            print(f"    ⚠️ Bing error (page {page}): {e}")

        time.sleep(random.uniform(2.0, 4.0))

    return links


# ══════════════════════════════════════════════════════════════════════
#  ENGINE 2: DuckDuckGo HTML (fallback, nếu Bing trả ít)
# ══════════════════════════════════════════════════════════════════════
def search_ddg(query: str) -> list[str]:
    links = []
    try:
        res = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers=get_headers(),
            timeout=10,
            verify=False,
        )
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.select("a.result__a"):
            href = a.get("href", "")
            if href.startswith("http"):
                links.append(href)
    except Exception as e:
        print(f"    ⚠️ DDG error: {e}")

    time.sleep(random.uniform(3.0, 5.0))
    return links


# ══════════════════════════════════════════════════════════════════════
#  ENGINE 3: Mojeek (không cần API, ít block hơn)
# ══════════════════════════════════════════════════════════════════════
def search_mojeek(query: str) -> list[str]:
    links = []
    try:
        url = f"https://www.mojeek.com/search?q={requests.utils.quote(query)}"
        res = requests.get(url, headers=get_headers(), timeout=10, verify=False)
        soup = BeautifulSoup(res.text, "html.parser")
        for a in soup.select("ul.results-standard li a.ob"):
            href = a.get("href", "")
            if href.startswith("http"):
                links.append(href)
    except Exception as e:
        print(f"    ⚠️ Mojeek error: {e}")

    time.sleep(random.uniform(2.0, 3.5))
    return links


# ══════════════════════════════════════════════════════════════════════
#  MULTI-ENGINE SEARCH với dedup
# ══════════════════════════════════════════════════════════════════════
def search_all_engines(query: str) -> list[str]:
    all_links = []

    print(f"    🔎 Bing...", end=" ", flush=True)
    bing_links = search_bing(query, pages=2)
    print(f"{len(bing_links)} links")
    all_links.extend(bing_links)

    # Chỉ dùng DDG/Mojeek nếu Bing trả ít
    if len(bing_links) < 5:
        print(f"    🔎 DDG fallback...", end=" ", flush=True)
        ddg_links = search_ddg(query)
        print(f"{len(ddg_links)} links")
        all_links.extend(ddg_links)

        print(f"    🔎 Mojeek fallback...", end=" ", flush=True)
        mojeek_links = search_mojeek(query)
        print(f"{len(mojeek_links)} links")
        all_links.extend(mojeek_links)

    clean = [l for l in all_links if is_clean_link(l)]
    return list(set(clean))


# ══════════════════════════════════════════════════════════════════════
#  VISITED FILE
# ══════════════════════════════════════════════════════════════════════
def load_visited() -> set:
    try:
        with open("visited.txt", "r", encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        return set()


def save_visited(link: str):
    with open("visited.txt", "a", encoding="utf-8") as f:
        f.write(link + "\n")


# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    TARGET_LEADS = 50
    visited = load_visited()
    all_links: list[str] = []

    print(f"🔍 Chạy {len(QUERIES)} queries trên multi-engine...\n")
    print("=" * 60)

    for i, query in enumerate(QUERIES):
        print(f'\n[{i+1}/{len(QUERIES)}] Query: "{query}"')
        results = search_all_engines(query)
        new = [l for l in results if l not in visited and l not in all_links]
        all_links.extend(new)
        print(f"  → +{len(new)} links mới | Tổng pool: {len(all_links)}")

        # Nghỉ giữa các query để tránh bị ban
        time.sleep(random.uniform(3.0, 6.0))

    all_links = list(set(all_links))
    print(f"\n{'=' * 60}")
    print(f"📦 Tổng link sạch cần crawl: {len(all_links)}")
    print(f"{'=' * 60}\n")

    data = []

    for i, link in enumerate(all_links):
        if len(data) >= TARGET_LEADS:
            print(f"\n🎯 Đã đủ {TARGET_LEADS} leads, dừng.")
            break

        progress = f"[{i+1}/{len(all_links)} | Lead: {len(data)}/{TARGET_LEADS}]"
        print(f"\n{progress} {link}")

        emails, phones, field = extract_contact_and_field(link)

        if emails or phones:
            data.append(
                {
                    "website": link,
                    "emails": ", ".join(emails[:3]),
                    "phones": ", ".join(phones[:3]),
                    "field": field,
                }
            )
            save_visited(link)
            print(f"  ✅ LEAD #{len(data)} | {field} | {emails[:1]} | {phones[:1]}")
        else:
            print(f"  ❌ No contact")

        time.sleep(random.uniform(1.5, 3.0))

    print(f"\n{'=' * 60}")
    print(f"🎯 Tổng lead thu được: {len(data)}/{TARGET_LEADS}")

    if data:
        export_to_excel(data)
        print("✅ Export xong → leads.xlsx")
    else:
        print("⚠️  Không có lead nào, chưa export.")
