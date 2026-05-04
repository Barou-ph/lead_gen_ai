import requests
import re
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ══════════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════════
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
    "facebook.com",
}

BAD_EMAIL_PREFIXES = {
    "noreply",
    "no-reply",
    "donotreply",
    "mailer-daemon",
    "bounce",
    "mailer",
    "postmaster",
}

FIELD_RULES = [
    (
        ["phan mem", "software", "lap trinh", "coding", "programmer", "developer"],
        "IT Software",
    ),
    (["outsourcing", "offshore", "nearshore", "body leasing"], "IT Outsourcing"),
    (
        ["mobile app", "ios", "android", "flutter", "react native", "swift"],
        "Mobile Dev",
    ),
    (
        ["web design", "website", "thiet ke web", "landing page", "frontend"],
        "Web Design",
    ),
    (["machine learning", "deep learning", "tri tue nhan tao", "llm", " ai "], "AI/ML"),
    (
        ["marketing", "seo", "google ads", "facebook ads", "quang cao", "branding"],
        "Marketing",
    ),
    (
        ["ecommerce", "e-commerce", "thuong mai dien tu", "shopify", "magento"],
        "E-Commerce",
    ),
    (["game", "gaming", "unity", "unreal engine"], "Game Dev"),
    (["cloud", "devops", "kubernetes", "aws", "azure", "gcp"], "Cloud/DevOps"),
    (["security", "bao mat", "pentest", "cybersecurity"], "Cybersecurity"),
    (["erp", "crm", "odoo", "sap", "enterprise"], "Enterprise Software"),
    (["digital agency", "creative agency"], "Digital Agency"),
    (["technology", "cong nghe", "tech"], "Technology"),
]


# ══════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════
def normalize_base_url(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    return url.rstrip("/")


def is_valid_email(email: str) -> bool:
    email = email.lower()
    if len(email) > 80:
        return False
    domain = email.split("@")[-1] if "@" in email else ""
    prefix = email.split("@")[0] if "@" in email else ""
    if domain in BAD_EMAIL_DOMAINS:
        return False
    if any(prefix.startswith(p) for p in BAD_EMAIL_PREFIXES):
        return False
    # Loại email trông như file ảnh/script
    if re.search(r"\.(png|jpg|jpeg|gif|svg|webp|ico|css|js|woff)$", email):
        return False
    return True


def clean_phone(raw_list: list) -> list:
    valid = set()
    for p in raw_list:
        p_clean = re.sub(r"[^\d+]", "", p)
        if p_clean.startswith("+84"):
            p_clean = "0" + p_clean[3:]
        elif p_clean.startswith("84") and len(p_clean) == 11:
            p_clean = "0" + p_clean[2:]
        # Số VN hợp lệ: 10 chữ số, đầu 03x 05x 07x 08x 09x
        if re.fullmatch(r"0[35789]\d{8}", p_clean):
            valid.add(p_clean)
    return list(valid)


def detect_field(text: str) -> str:
    # Chuyển về ASCII-like để khớp cả tiếng Việt không dấu
    low = text.lower()
    for keywords, label in FIELD_RULES:
        if any(k in low for k in keywords):
            return label
    return "Other"


def fetch_page(url: str) -> str | None:
    """Fetch 1 trang với retry × 2."""
    for attempt in range(2):
        try:
            r = requests.get(
                url,
                headers=HEADERS,
                timeout=8,
                allow_redirects=True,
                verify=False,
            )
            if r.status_code == 200:
                return r.text
            if r.status_code in (429, 503):
                import time

                time.sleep(3)
        except Exception:
            pass
    return None


# ══════════════════════════════════════════════════════════════════════
#  MAIN EXTRACTOR
# ══════════════════════════════════════════════════════════════════════
def extract_contact_and_field(url: str) -> tuple:
    base = normalize_base_url(url)

    all_emails: set = set()
    all_phones: set = set()
    combined_text = ""
    pages_fetched = 0

    for path in CONTACT_PATHS:
        # Dừng sớm nếu đã đủ contact VÀ đã crawl ít nhất 2 trang
        if pages_fetched >= 2 and all_emails and all_phones:
            break
        # Hard cap: không crawl quá 5 trang/domain
        if pages_fetched >= 5:
            break

        target = base + path
        html = fetch_page(target)
        if not html:
            continue

        pages_fetched += 1
        combined_text += " " + html

        # ── Email ────────────────────────────────────────────────────
        raw_emails = re.findall(
            r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}", html
        )
        for e in raw_emails:
            if is_valid_email(e):
                all_emails.add(e.lower())

        # ── Phone (bắt nhiều format VN) ──────────────────────────────
        raw_phones = re.findall(
            r"(?:\+84|0084|0)[().\-\s]?\d{1,3}[().\-\s]?\d{3,4}[().\-\s]?\d{3,4}",
            html,
        )
        all_phones.update(clean_phone(raw_phones))

    field = detect_field(combined_text)

    return sorted(all_emails)[:5], list(all_phones)[:5], field
