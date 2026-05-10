"""
main.py — Lead Intelligence Tool v4
Pipeline: Search → URL Filter → Crawl (parallel) → Classify → Score → Enrich → AI → Export

Usage:
  python main.py                                    # IT, 100 leads
  python main.py --industry=logistics               # đổi ngành
  python main.py --industry=it --target=50          # đổi target
  python main.py --industry=it --skip-ai            # không dùng OpenAI
  python main.py --list-industries                  # xem danh sách ngành
"""

import argparse
import sys
import os
import random
import time
import urllib3
import re
import base64
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Local modules ──────────────────────────────────────────────────────
from industries import INDUSTRY_QUERIES, AVAILABLE_INDUSTRIES
from extractor import extract_contact_and_field
from enricher import enrich_all
from exporter import export_to_excel
from url_filter import filter_urls, filter_url
from company_classifier import classify_from_content, is_accepted_company
from lead_scorer import score_lead, rank_emails, email_quality_label

# ══════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════
DEFAULT_INDUSTRY = "it"
DEFAULT_TARGET   = 100
MAX_WORKERS      = 8
SEARCH_DELAY     = (2.0, 4.0)
CRAWL_DELAY      = (0.3, 0.8)
MAX_RETRIES      = 2
SESSION_TS       = datetime.now().strftime("%Y%m%d_%H%M%S")

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
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
    }


def get_root_domain(url: str) -> str:
    try:
        parts = url.split("//")[-1].split("/")[0].split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else url
    except Exception:
        return url


def resolve_bing_url(url: str) -> str:
    if "bing.com" not in url:
        return url
    m = re.search(r"[?&]u=([^&]+)", url)
    if m:
        enc = m.group(1)
        if enc.startswith("a1"):
            enc = enc[2:]
        pad = 4 - len(enc) % 4
        if pad != 4:
            enc += "=" * pad
        try:
            dec = base64.urlsafe_b64decode(enc).decode("utf-8", errors="ignore")
            if dec.startswith("http") and "bing.com" not in dec:
                return dec
        except Exception:
            pass
    try:
        r = requests.head(url, headers=get_headers(), timeout=5,
                          allow_redirects=True, verify=False)
        if r.url and "bing.com" not in r.url:
            return r.url
    except Exception:
        pass
    return ""


def fetch_url(url: str, method: str = "GET", data: dict = None):
    for attempt in range(MAX_RETRIES):
        try:
            if method == "POST":
                r = requests.post(url, data=data, headers=get_headers(),
                                  timeout=10, verify=False)
            else:
                r = requests.get(url, headers=get_headers(), timeout=10,
                                 verify=False, allow_redirects=True)
            if r.status_code == 200:
                return r
            if r.status_code in (429, 503):
                time.sleep(5 * (attempt + 1))
        except Exception:
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
    return None


# ══════════════════════════════════════════════════════════════════════
#  SEARCH — 3 engines parallel per query
# ══════════════════════════════════════════════════════════════════════
def _bing(query: str, pages: int = 3) -> list:
    links = []
    for page in range(pages):
        url = (f"https://www.bing.com/search"
               f"?q={requests.utils.quote(query)}&first={page*10+1}&count=10")
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


def _ddg(query: str) -> list:
    links = []
    r = fetch_url("https://html.duckduckgo.com/html/",
                  method="POST", data={"q": query})
    if r:
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a.result__a"):
            href = a.get("href", "")
            if href.startswith("http"):
                links.append(href)
    return links


def _mojeek(query: str, pages: int = 2) -> list:
    links = []
    for page in range(pages):
        url = (f"https://www.mojeek.com/search"
               f"?q={requests.utils.quote(query)}&s={page*10}")
        r = fetch_url(url)
        if r:
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select("ul.results-standard li a.ob"):
                href = a.get("href", "")
                if href.startswith("http"):
                    links.append(href)
        time.sleep(random.uniform(1.0, 1.5))
    return links


def search_parallel(query: str) -> list:
    """Chạy 3 engines đồng thời, gộp kết quả."""
    raw = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_bing,   query, 3): "Bing",
            pool.submit(_ddg,    query):    "DDG",
            pool.submit(_mojeek, query, 2): "Mojeek",
        }
        counts = {}
        for fut in as_completed(futures):
            engine = futures[fut]
            try:
                res = fut.result()
                counts[engine] = len(res)
                raw.extend(res)
            except Exception:
                counts[engine] = 0

    parts = " | ".join(f"{e}:{counts.get(e,0)}" for e in ["Bing","DDG","Mojeek"])
    print(f"    [{parts}] → raw:{len(raw)}", end=" ")
    return raw


# ══════════════════════════════════════════════════════════════════════
#  CRAWL WORKER — crawl + classify trong 1 bước
# ══════════════════════════════════════════════════════════════════════
def crawl_and_classify(link: str) -> dict | None:
    """
    Crawl 1 URL:
    1. Extract contact
    2. Classify entity từ HTML
    3. Reject nếu không phải company
    4. Return raw lead dict (chưa score)
    """
    time.sleep(random.uniform(*CRAWL_DELAY))
    try:
        emails, phones, field = extract_contact_and_field(link)

        # Không có contact gì → skip
        if not emails and not phones:
            return None

        # Fetch homepage để classify
        r = fetch_url(link)
        html_text = r.text if r else ""
        soup = BeautifulSoup(html_text, "html.parser") if html_text else None

        # Lấy description từ meta
        description = ""
        if soup:
            meta = soup.find("meta", attrs={"name": "description"})
            if meta and meta.get("content"):
                description = meta["content"][:300]
            if not description:
                og = soup.find("meta", property="og:description")
                if og and og.get("content"):
                    description = og["content"][:300]

        # Classify entity
        classification = classify_from_content(html_text, link, description)

        # Reject non-company
        if not is_accepted_company(classification):
            return None

        return {
            "website":       link,
            "emails":        ", ".join(emails[:5]),
            "phones":        ", ".join(phones[:3]),
            "field":         field,
            "description":   description,
            "entity_type":   classification["entity_type"],
            "confidence":    classification["confidence"],
            "commercial_signals": classification["commercial_signals"],
            "negative_signals":   classification["negative_signals"],
        }

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
#  MAIN PIPELINE
# ══════════════════════════════════════════════════════════════════════
def run(industry: str, target: int, skip_ai: bool, skip_enrich: bool):
    queries = INDUSTRY_QUERIES.get(industry, INDUSTRY_QUERIES["it"])

    print(f"\n{'='*65}")
    print(f"🏭 Industry : {industry.upper()}")
    print(f"🎯 Target   : {target} leads")
    print(f"🔍 Queries  : {len(queries)}")
    print(f"🤖 AI       : {'SKIP' if skip_ai else 'ON'}")
    print(f"📅 Session  : {SESSION_TS}")
    print(f"{'='*65}\n")

    visited        = load_visited()
    all_links      = []
    domain_counter = {}

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 1: SEARCH + URL FILTER
    # ══════════════════════════════════════════════════════════════════
    print("🔍 PHASE 1: SEARCH + URL FILTER\n")

    for i, query in enumerate(queries):
        print(f"[{i+1}/{len(queries)}] \"{query}\"")
        raw = search_parallel(query)

        # --- Layer 1: URL filter ngay tại đây ---
        clean, reject_stats = filter_urls(raw)

        # Dedup domain (max 2 URL/domain)
        new = []
        for url in clean:
            if url in visited or url in all_links:
                continue
            root = get_root_domain(url)
            if domain_counter.get(root, 0) >= 2:
                continue
            domain_counter[root] = domain_counter.get(root, 0) + 1
            new.append(url)

        all_links.extend(new)
        reject_summary = " ".join(f"{k}:{v}" for k, v in reject_stats.items())
        print(f"    pass:{len(clean)} | reject:[{reject_summary}] | +{len(new)} new | pool:{len(all_links)}")
        time.sleep(random.uniform(*SEARCH_DELAY))

    all_links = list(set(all_links))
    random.shuffle(all_links)
    print(f"\n✅ Pool sau URL filter: {len(all_links)} links\n")

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 2: CRAWL + CLASSIFY (parallel)
    # ══════════════════════════════════════════════════════════════════
    print(f"🕷️  PHASE 2: CRAWL + CLASSIFY ({MAX_WORKERS} threads)\n")

    raw_leads     = []
    newly_visited = []
    total         = len(all_links)
    done          = [0]
    lock          = threading.Lock()

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        future_to_link = {pool.submit(crawl_and_classify, link): link
                          for link in all_links}

        for fut in as_completed(future_to_link):
            link = future_to_link[fut]
            with lock:
                done[0] += 1
                bar = f"[{done[0]}/{total} | raw:{len(raw_leads)}]"

            try:
                result = fut.result()
            except Exception:
                result = None

            with lock:
                if result:
                    raw_leads.append(result)
                    newly_visited.append(link)
                    etype = result.get("entity_type", "?")
                    conf  = result.get("confidence", 0)
                    print(f"  ✅ {bar} {etype}(conf:{conf:.1f}) | {link[:55]}")
                else:
                    print(f"  ❌ {bar} {link[:60]}")

    save_visited(newly_visited)
    print(f"\n📊 Crawl + Classify: {len(raw_leads)} company leads (từ {total} URLs)\n")

    if not raw_leads:
        print("⚠️  Không có lead nào pass classify. Kết thúc.")
        return

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 3: SCORE
    # ══════════════════════════════════════════════════════════════════
    print("📊 PHASE 3: SCORE\n")
    scored_leads = []
    for lead in raw_leads:
        scored = score_lead(lead)
        scored_leads.append(scored)
        grade = scored.get("grade", "?")
        score = scored.get("score", 0)
        site  = scored.get("website", "")[:50]
        print(f"  Grade={grade}(+{score}) | {site}")

    # Reject Grade D (không đủ chất lượng)
    before_d = len(scored_leads)
    scored_leads = [l for l in scored_leads if l.get("grade", "D") != "D"]
    print(f"\n  → {len(scored_leads)} leads (loại {before_d - len(scored_leads)} Grade D)\n")

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 4: ENRICH
    # ══════════════════════════════════════════════════════════════════
    if not skip_enrich and scored_leads:
        print(f"🔍 PHASE 4: ENRICH ({len(scored_leads)} leads)\n")
        scored_leads = enrich_all(scored_leads, max_workers=6)
        # Re-score sau enrich (có thêm signals)
        scored_leads = [score_lead(l) for l in scored_leads]

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 5: AI ANALYZE
    # ══════════════════════════════════════════════════════════════════
    if not skip_ai and scored_leads:
        try:
            from ai_analyst import analyze_leads, estimate_cost
            print(f"\n🤖 PHASE 5: AI ANALYZE")
            print(f"   Est. cost: {estimate_cost(len(scored_leads))}")
            confirm = input("   Tiếp tục? (y/n): ").strip().lower()
            if confirm == "y":
                scored_leads = analyze_leads(scored_leads, industry)
        except ImportError:
            print("  ⚠️  ai_analyst.py không tìm thấy, skip AI.")
        except Exception as e:
            print(f"  ⚠️  AI error: {e}, skip.")

    # ══════════════════════════════════════════════════════════════════
    #  PHASE 6: EXPORT
    # ══════════════════════════════════════════════════════════════════
    grade_order = {"A": 0, "B": 1, "C": 2, "D": 3}
    scored_leads.sort(key=lambda x: (
        0 if x.get("should_contact", True) else 1,
        grade_order.get(x.get("grade", "D"), 3),
        -x.get("score", 0)
    ))

    print(f"\n📤 PHASE 6: EXPORT")
    export_to_excel(scored_leads, session=SESSION_TS, industry=industry)

    # Summary
    print(f"\n{'='*65}")
    print(f"🎉 DONE | {len(scored_leads)} leads | {industry.upper()} | {SESSION_TS}")
    gc = {}
    for d in scored_leads:
        g = d.get("grade", "?")
        gc[g] = gc.get(g, 0) + 1
    for g, c in sorted(gc.items()):
        print(f"   Grade {g}: {c} leads")
    print(f"{'='*65}\n")


# ══════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="Lead Intelligence Tool v4",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--industry", "-i", default=DEFAULT_INDUSTRY,
                        help=f"Ngành crawl. Choices: {', '.join(AVAILABLE_INDUSTRIES)}")
    parser.add_argument("--target", "-t", type=int, default=DEFAULT_TARGET,
                        help=f"Số lead target (default: {DEFAULT_TARGET})")
    parser.add_argument("--skip-ai", action="store_true",
                        help="Bỏ qua AI phase")
    parser.add_argument("--skip-enrich", action="store_true",
                        help="Bỏ qua enrich phase")
    parser.add_argument("--list-industries", action="store_true",
                        help="Xem danh sách ngành")

    args = parser.parse_args()

    if args.list_industries:
        print("\n📋 Ngành có sẵn:\n")
        for ind in AVAILABLE_INDUSTRIES:
            n = len(INDUSTRY_QUERIES.get(ind, []))
            print(f"  {ind:<15} ({n} queries)")
        print()
        sys.exit(0)

    if args.industry not in AVAILABLE_INDUSTRIES:
        print(f"❌ Industry '{args.industry}' không hợp lệ.")
        print(f"   Dùng: {', '.join(AVAILABLE_INDUSTRIES)}")
        sys.exit(1)

    run(
        industry     = args.industry,
        target       = args.target,
        skip_ai      = args.skip_ai,
        skip_enrich  = getattr(args, "skip_enrich", False),
    )


if __name__ == "__main__":
    main()