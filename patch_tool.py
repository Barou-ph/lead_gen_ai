"""
test_sources2.py — Test với URL đúng + tìm selector thật
"""
import requests, urllib3, time
from bs4 import BeautifulSoup
urllib3.disable_warnings()

H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122",
     "Accept-Language": "vi-VN,vi;q=0.9"}

def fetch(url):
    try:
        r = requests.get(url, headers=H, timeout=10, verify=False, allow_redirects=True)
        print(f"  status: {r.status_code} | url: {r.url[:80]}")
        return r if r.status_code == 200 else None
    except Exception as e:
        print(f"  ❌ {e}")
        return None

# ── MASOTHUE ──────────────────────────────────────────────────
print("\n=== MASOTHUE ===")
r = fetch("https://masothue.com/Search/?q=san+xuat")
if r:
    soup = BeautifulSoup(r.text, "html.parser")
    # In tất cả link nội bộ dạng /xxx để tìm pattern công ty
    links = [(a.get_text(strip=True)[:40], a["href"])
             for a in soup.select("a[href]")
             if str(a.get("href","")).startswith("/")
             and len(str(a.get("href",""))) > 8
             and "tra-cuu" not in str(a.get("href",""))
             and "lien-he" not in str(a.get("href",""))]
    print(f"  Internal links: {len(links)}")
    for name, href in links[:10]:
        print(f"    {name} → {href}")

time.sleep(2)

# ── YELLOWPAGES ───────────────────────────────────────────────
print("\n=== YELLOWPAGES ===")
r2 = fetch("https://www.yellowpages.vn/search.asp?keyword=san+xuat&where=")
if r2:
    soup2 = BeautifulSoup(r2.text, "html.parser")
    # Tìm tất cả external link
    ext = [(a.get_text(strip=True)[:40], a["href"])
           for a in soup2.select("a[href]")
           if str(a.get("href","")).startswith("http")
           and "yellowpages.vn" not in str(a.get("href",""))
           and len(str(a.get("href",""))) > 10]
    print(f"  External links: {len(ext)}")
    for name, href in ext[:10]:
        print(f"    {name} → {href}")
    # Cũng in 1 đoạn HTML để xem structure
    print("\n  HTML snippet (company cards):")
    cards = soup2.select("div.company, div.listing, div.result, li.company, .company-name")
    print(f"  Cards found: {len(cards)}")
    if not cards:
        # In raw để xem class nào được dùng
        body = soup2.find("body")
        if body:
            text = str(body)[:2000]
            print(text)

time.sleep(2)

# ── BING site:.vn ─────────────────────────────────────────────
print("\n=== BING site:.vn ===")
import urllib.parse
q = 'site:.vn "sản xuất" "liên hệ" email'
r3 = fetch(f"https://www.bing.com/search?q={urllib.parse.quote(q)}&count=10")
if r3:
    soup3 = BeautifulSoup(r3.text, "html.parser")
    results = soup3.select("li.b_algo h2 a")
    print(f"  Results: {len(results)}")
    for a in results[:10]:
        print(f"    {a.get_text(strip=True)[:40]} → {a.get('href','')[:60]}")

print("\n=== XONG ===")