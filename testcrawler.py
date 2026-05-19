import requests, urllib3
urllib3.disable_warnings()

h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122"}

# Test category listing TPHCM
url = "https://www.yellowpages.vn/class/37310/vat-lieu-xay-dung-o_tp.-ho-chi-minh-(tphcm).html"
r = requests.get(url, headers=h, timeout=10, verify=False)
from bs4 import BeautifulSoup
soup = BeautifulSoup(r.text, "html.parser")
print("Status:", r.status_code, "| URL:", r.url[:80])

# Tìm link công ty — thường dạng /id/ hoặc /cty/
print("\n--- YP internal links ---")
for a in soup.select("a[href]"):
    href = a.get("href", "")
    text = a.get_text(strip=True)[:40]
    if "yellowpages.vn" in href and len(href) > 35:
        print(f"  {text!r:40} -> {href[:90]}")

# Tìm external website link
print("\n--- External .vn links ---")
for a in soup.select("a[href]"):
    href = a.get("href", "")
    if href.startswith("http") and "yellowpages" not in href and href.endswith(".vn") or (href.startswith("http") and "yellowpages" not in href and ".vn/" in href):
        text = a.get_text(strip=True)[:35]
        print(f"  {text!r:38} -> {href[:80]}")

# In raw HTML 3000 char để xem structure
print("\n--- RAW HTML snippet ---")
body = str(soup.find("body"))
# Tìm đoạn có tên công ty
idx = body.find("Công ty")
if idx < 0:
    idx = body.find("cong-ty")
if idx < 0:
    idx = body.find("company")
print(body[max(0,idx-100):idx+500])