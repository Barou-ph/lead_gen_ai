import requests
import re
import urllib3
from bs4 import BeautifulSoup

# ── Tắt SSL warning ────────────────────────────────────────────────────
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ── Các trang con cần thử theo độ ưu tiên ─────────────────────────────
CONTACT_PATHS = [
    "",
    "/contact",
    "/contact-us",
    "/contacts",
    "/lien-he",
    "/about",
    "/about-us",
    "/gioi-thieu",
    "/ve-chung-toi",
    "/reach-us",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Email domain rác (loại bỏ) ─────────────────────────────────────────
BAD_EMAIL_DOMAINS = {
    "example.com",
    "sentry.io",
    "w3.org",
    "schema.org",
    "jquery.com",
    "bootstrap.com",
    "cloudflare.com",
    "google.com",
    "microsoft.com",
    "apple.com",
}

BAD_EMAIL_PREFIXES = {"noreply", "no-reply", "donotreply", "mailer", "bounce"}

# ── Field detection rules ──────────────────────────────────────────────
FIELD_RULES = [
    # [PATCH V4] Ưu tiên bắt Hospitality và Logistics
    (["khách sạn", "resort", "hotel", "du lịch", "tour", "hospitality"], "Hospitality"),
    (["vận tải", "logistics", "kho bãi", "forwarding", "giao nhận", "supply chain"], "Logistics"),
    (["phần mềm", "software", "lập trình", "coding", "programmer"], "IT Software"),
    (["outsourcing", "offshore", "nearshore", "body leasing"], "IT Outsourcing"),
    (
        ["mobile app", "ios", "android", "flutter", "react native", "swift"],
        "Mobile Dev",
    ),
    (
        ["web design", "website", "thiết kế web", "landing page", "frontend"],
        "Web Design",
    ),
    (
        ["ai ", " ai,", "machine learning", "deep learning", "trí tuệ nhân tạo", "llm"],
        "AI/ML",
    ),
    (
        ["marketing", "seo", "google ads", "facebook ads", "quảng cáo", "branding"],
        "Marketing",
    ),
    (
        ["ecommerce", "e-commerce", "thương mại điện tử", "shopify", "magento"],
        "E-Commerce",
    ),
    (["game", "gaming", "unity", "unreal engine"], "Game Dev"),
    (
        ["cloud", "devops", "kubernetes", "aws", "azure", "gcp", "infrastructure"],
        "Cloud/DevOps",
    ),
    (["security", "bảo mật", "pentest", "cybersecurity", "soc"], "Cybersecurity"),
    (["erp", "crm", "odoo", "sap", "enterprise"], "Enterprise Software"),
    (["digital agency", "creative agency"], "Digital Agency"),
    (["technology", "công nghệ", "tech"], "Technology"),
]


def normalize_base_url(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    return url.rstrip("/")


def clean_phone(raw_list: list) -> list:
    valid = set()
    for p in raw_list:
        # Giữ lại số và dấu +
        p_clean = re.sub(r"[^\d+]", "", p)

        # Chuẩn hoá về dạng 0xxxxxxxxx
        if p_clean.startswith("+84"):
            p_clean = "0" + p_clean[3:]
        elif p_clean.startswith("84") and len(p_clean) == 11:
            p_clean = "0" + p_clean[2:]

        # Chỉ giữ số VN hợp lệ: 10 chữ số, đầu số 03x 05x 07x 08x 09x
        if re.fullmatch(r"0[35789]\d{8}", p_clean):
            valid.add(p_clean)

    return list(valid)


def detect_field(text: str) -> str:
    low = text.lower()
    for keywords, label in FIELD_RULES:
        if any(k in low for k in keywords):
            return label
    return "Other"


def is_valid_email(email: str) -> bool:
    email = email.lower()
    domain = email.split("@")[-1] if "@" in email else ""
    prefix = email.split("@")[0] if "@" in email else ""

    if domain in BAD_EMAIL_DOMAINS:
        return False
    if any(prefix.startswith(p) for p in BAD_EMAIL_PREFIXES):
        return False
    if re.search(r"\.(png|jpg|jpeg|gif|svg|webp|ico|css|js)$", email):
        return False
    if len(email) > 80:
        return False
    return True


def fetch_page(url: str) -> str | None:
    try:
        res = requests.get(
            url,
            headers=HEADERS,
            timeout=8,
            allow_redirects=True,
            verify=False,
        )
        if res.status_code == 200:
            # [PATCH V4] Sửa lỗi encoding
            res.encoding = 'utf-8'
            text = res.text
            text = text.encode('utf-8', errors='ignore').decode('utf-8')
            return text
    except Exception:
        pass
    return None


def extract_contact_and_field(url: str) -> tuple:
    base = normalize_base_url(url)

    all_emails: set = set()
    all_phones: set = set()
    combined_text = ""
    pages_fetched = 0

    for path in CONTACT_PATHS:
        # Giới hạn số trang crawl để tránh chậm
        if pages_fetched >= 4 and (all_emails or all_phones):
            break

        target = base + path
        html = fetch_page(target)
        if not html:
            continue

        pages_fetched += 1
        combined_text += " " + html

        # ── Extract email ────────────────────────────────────────────
        raw_emails = re.findall(
            r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}", html
        )
        for e in raw_emails:
            if is_valid_email(e):
                all_emails.add(e.lower())

        # ── Extract phone (bắt nhiều format) ────────────────────────
        # Format: 0xx xxx xxxx / 0xx-xxx-xxxx / +84xxxxxxxxx
        raw_phones = re.findall(
            r"(?:\+84|0084|0)[().\-\s]?\d{1,3}[().\-\s]?\d{3,4}[().\-\s]?\d{3,4}",
            html,
        )
        cleaned = clean_phone(raw_phones)
        all_phones.update(cleaned)

        # Dừng sớm nếu đã có đủ cả 2
        if len(all_emails) >= 2 and len(all_phones) >= 1:
            break

    field = detect_field(combined_text)

    return sorted(all_emails)[:5], list(all_phones)[:5], field
