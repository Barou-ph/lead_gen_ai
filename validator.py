"""
validator.py — Entity validation & contact cleaning
Chạy TRƯỚC scoring. Reject rác, clean email/phone.

Logic:
1. Reject non-company URLs (blog, dict, news, gov, marketplace...)
2. Reject non-company domains (Investopedia, Cambridge, Shopify...)
3. Classify entity type (company vs media vs gov vs directory...)
4. Clean emails (sentry, placeholder, fake)
5. Clean phones (tracking ID, fax, fake)
6. Verify company signals (has /about, /contact, /services)
"""

import re
import requests
import urllib3
from urllib.parse import urlparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ══════════════════════════════════════════════════════════════════════
#  DOMAIN BLACKLIST — global brands, media, dictionaries, gov
# ══════════════════════════════════════════════════════════════════════
REJECTED_DOMAINS = {
    # Global tech giants (không phải khách hàng B2B VN)
    "shopify.com", "salesforce.com", "blockchain.com", "deepai.org",
    "chatgpt.com", "openai.com", "microsoft.com", "google.com",
    "amazon.com", "apple.com", "ibm.com", "oracle.com",
    "github.com", "gitlab.com", "atlassian.com", "hubspot.com",
    "gameloft.com", "freelancer.com", "upwork.com",

    # Dictionaries / encyclopedias
    "merriam-webster.com", "dictionary.com", "cambridge.org",
    "wikipedia.org", "wikihow.com", "britannica.com",
    "vocabulary.com", "oxfordlearnersdictionaries.com",

    # Media / news / research
    "investopedia.com", "techcrunch.com", "forbes.com", "bloomberg.com",
    "reuters.com", "cnbc.com", "wired.com", "techsciresearch.com",
    "statista.com", "mordorintelligence.com", "blueweaveconsulting.com",
    "expertmarketresearch.com", "techsciblog.com", "cloudwards.net",
    "bestdevops.com", "growyourbusiness.org", "itif.org",
    "vietcetera.com", "kr-asia.com", "e27.co", "technode.global",
    "techcollectivesea.com", "thegradient.pub", "apacbusinessheadlines.com",
    "cxodigitalpulse.com", "the-shiv.com", "creationsforu.com",
    "conventuslaw.com", "justsomecrypto.com", "edtechagency.net",
    "listicle.sgpgrid.com", "limericktime.com", "saigondragonstudios.com",

    # Government portals
    "gov.vn", "dichvucong.gov.vn", "bocongan.gov.vn", "chinhphu.vn",
    "trade.gov", "worldbank.org", "adb.org",

    # Directories / aggregators
    "clutch.co", "goodfirms.co", "techbehemoths.com", "sortlist.com",
    "upcity.com", "designrush.com", "tracxn.com", "crunchbase.com",
    "incorp.asia", "vietnam.incorp.asia",
    "appdevelopmentcompanies.co", "topsoftwarecompanies.co",
    "vti.com.vn",  # directory listing
    "hikingproject.com", "teachmeet.pbworks.com",

    # Job boards
    "itviec.com", "vietnamworks.com", "topcv.vn", "linkedin.com",
    "wellfound.com", "thesaasjobs.com",

    # Research / market reports
    "marketresearchvietnam.com", "researchinvietnam.com",
    "viettonkinconsulting.com",  # consulting blog, not buyer

    # Misc irrelevant
    "ninite.com", "johnsonhealthtech.com",  # US/global
    "ntk-thanh.co.uk",
}

# ══════════════════════════════════════════════════════════════════════
#  PATH BLACKLIST — reject specific URL patterns
# ══════════════════════════════════════════════════════════════════════
REJECTED_PATHS = [
    # Content pages
    "/blog/", "/news/", "/article/", "/articles/",
    "/dictionary/", "/wiki/", "/guide/", "/guides/",
    "/what-is/", "/how-to/", "/definition/", "/insights/",
    "/report/", "/research/", "/publication/",
    "/terms/", "/hoi-dap/", "/thu-thuat/", "/cong-nghe/",

    # Listing / directory pages
    "/companies/", "/agencies/", "/developers/",
    "/top-", "/best-", "/list-", "/ranking",
    "/explore/", "/d/explore/",

    # Article indicators
    "/publications/", "/posts/", "/post/",
    "/industry-reports/", "/industry-insights/",
    "/market-intelligence/",

    # Job boards on company sites (accept /careers but not listing)
    "/freelancers/", "/jobs/",

    # User profile
    "/user/", "/profile/",
]

# ══════════════════════════════════════════════════════════════════════
#  EMAIL BLACKLIST — reject fake / system emails
# ══════════════════════════════════════════════════════════════════════
BAD_EMAIL_PATTERNS = [
    # System / error tracking
    r"sentry", r"wixpress", r"bug-report", r"bug-reporting",
    r"error-report", r"crash-report",

    # Placeholders / fake
    r"^name@", r"^your@", r"^youname@", r"^enteryour@",
    r"@email\.com$", r"@yourcompany\.com$", r"@addresshere\.",
    r"@example\.com$", r"^test@", r"^demo@",

    # Abuse / system
    r"^abuse@", r"^spam@", r"^postmaster@", r"^mailer-daemon@",
    r"^noreply@", r"^no-reply@", r"^donotreply@", r"^bounce@",

    # Photo tags scraped from HTML
    r"photo-shared-by", r"tagging-@",

    # Encoded / mangled
    r"^u003e",  # HTML entity

    # Generic bulk
    r"^info@info\.", r"^admin@admin\.",
]

BAD_EMAIL_DOMAINS_SET = {
    "sentry.io", "sentry-next.wixpress.com", "wixpress.com",
    "example.com", "yourcompany.com", "addresshere.com",
    "websitere.net", "bug-reporting-xalgha6.m-w.com",
}

# ══════════════════════════════════════════════════════════════════════
#  ENTITY TYPE CLASSIFIER
# ══════════════════════════════════════════════════════════════════════
ENTITY_SIGNALS = {
    # Từ trong description/title → không phải company
    "media":       ["news", "article", "journalism", "publisher", "magazine",
                    "the meaning of", "definition", "encyclopedia", "dictionary",
                    "learn more", "how to use", "in a sentence"],
    "government":  ["government", "ministry", "department of", "public service",
                    "dịch vụ công", "chính phủ", "bộ công an", "cổng thông tin"],
    "directory":   ["list of", "top 10", "best companies", "compare companies",
                    "find companies", "directory", "aggregator"],
    "marketplace": ["freelancers", "hire freelance", "marketplace", "fiverr",
                    "upwork", "outsource platform"],
    "research":    ["market report", "market research", "industry report",
                    "market size", "forecast", "cagr", "market intelligence"],
    "blog":        ["insights", "our blog", "read more", "published by",
                    "written by", "author:", "posted on"],
}

COMPANY_SIGNALS = [
    "our team", "our services", "our clients", "about us",
    "contact us", "our solutions", "our products", "founded in",
    "headquarters", "ceo", "cto", "our mission", "our vision",
    "we are a", "we provide", "our company",
    "chúng tôi", "về chúng tôi", "dịch vụ của chúng tôi",
]


def get_root_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        parts = parsed.netloc.split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else parsed.netloc
    except Exception:
        return url


def is_rejected_url(url: str) -> tuple[bool, str]:
    """
    Trả về (True, reason) nếu URL bị reject.
    Trả về (False, "") nếu pass.
    """
    if not url or not url.startswith("http"):
        return True, "invalid_url"

    low = url.lower()
    root = get_root_domain(url)

    # Check domain blacklist
    if root in REJECTED_DOMAINS:
        return True, f"blacklisted_domain:{root}"

    # Partial domain check (subdomain match)
    for bad in REJECTED_DOMAINS:
        if low.endswith(f".{bad}") or f"/{bad}/" in low:
            return True, f"blacklisted_domain:{bad}"

    # Check path blacklist
    try:
        path = urlparse(url).path.lower()
        for bad_path in REJECTED_PATHS:
            if bad_path in path:
                return True, f"bad_path:{bad_path}"
    except Exception:
        pass

    # Reject sitestat / usitestat URLs (SEO tool scrape artifacts)
    if "sitestat.com" in low or "siteindices.com" in low:
        return True, "seo_tool_url"

    # Reject press release aggregators
    if "prsync.com" in low:
        return True, "press_release_aggregator"

    return False, ""


def is_valid_email(email: str) -> bool:
    """Trả về True nếu email hợp lệ (không phải rác)."""
    if not email or "@" not in email or len(email) > 100:
        return False

    low = email.lower()
    domain = low.split("@")[-1]
    prefix = low.split("@")[0]

    # Check bad domain
    if domain in BAD_EMAIL_DOMAINS_SET:
        return False

    # Check bad patterns
    for pattern in BAD_EMAIL_PATTERNS:
        if re.search(pattern, low):
            return False

    # Reject if prefix looks like UUID/hash (sentry tokens)
    if re.match(r"^[a-f0-9]{20,}$", prefix):
        return False

    # Reject very long prefix (likely encoded garbage)
    if len(prefix) > 50:
        return False

    return True


def clean_emails(emails_str: str) -> list[str]:
    """Parse email string, filter rác, return list sạch."""
    if not emails_str:
        return []
    raw = [e.strip() for e in emails_str.split(",") if e.strip()]
    return [e for e in raw if is_valid_email(e)]


def is_valid_vn_phone(phone: str) -> bool:
    """Validate số điện thoại Việt Nam."""
    cleaned = re.sub(r"[^\d+]", "", phone)
    if cleaned.startswith("+84"):
        cleaned = "0" + cleaned[3:]
    elif cleaned.startswith("84") and len(cleaned) == 11:
        cleaned = "0" + cleaned[2:]
    return bool(re.fullmatch(r"0[35789]\d{8}", cleaned))


def clean_phones(phones_str: str) -> list[str]:
    """Parse phone string, filter invalid."""
    if not phones_str:
        return []
    raw = [p.strip() for p in phones_str.split(",") if p.strip()]
    return [p for p in raw if is_valid_vn_phone(p)]


def classify_entity(url: str, description: str = "") -> str:
    """
    Phân loại entity type từ URL + description.
    Returns: "company" | "media" | "government" | "directory" |
             "marketplace" | "research" | "blog" | "unknown"
    """
    text = (url + " " + description).lower()

    for entity_type, signals in ENTITY_SIGNALS.items():
        if any(s in text for s in signals):
            return entity_type

    # Company signals
    company_hits = sum(1 for s in COMPANY_SIGNALS if s in text)
    if company_hits >= 2:
        return "company"

    return "unknown"


def has_company_structure(url: str, timeout: int = 5) -> dict:
    """
    Kiểm tra nhanh xem site có cấu trúc công ty không.
    Check các page quan trọng tồn tại.
    Returns dict: {contact, about, services, careers}
    """
    base = url.rstrip("/")
    checks = {
        "contact":  ["/contact", "/contact-us", "/lien-he"],
        "about":    ["/about", "/about-us", "/gioi-thieu"],
        "services": ["/services", "/solutions", "/dich-vu"],
        "careers":  ["/careers", "/jobs", "/tuyen-dung"],
    }
    result = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    for key, paths in checks.items():
        found = False
        for path in paths:
            try:
                r = requests.head(f"{base}{path}", headers=headers,
                                  timeout=timeout, verify=False,
                                  allow_redirects=True)
                if r.status_code == 200:
                    found = True
                    break
            except Exception:
                pass
        result[key] = found

    return result


# ══════════════════════════════════════════════════════════════════════
#  MAIN VALIDATION FUNCTION
# ══════════════════════════════════════════════════════════════════════
def validate_lead(lead: dict, check_structure: bool = False) -> dict | None:
    """
    Validate 1 lead dict.
    Returns cleaned lead dict nếu valid.
    Returns None nếu reject.

    Adds fields: entity_type, reject_reason, clean_emails, clean_phones
    """
    url = lead.get("website", "")

    # ── Step 1: URL validation ────────────────────────────────────────
    rejected, reason = is_rejected_url(url)
    if rejected:
        return None  # silent reject

    # ── Step 2: Email cleaning ────────────────────────────────────────
    emails_raw = lead.get("emails", "")
    clean_email_list = clean_emails(emails_raw)

    phones_raw = lead.get("phones", "")
    clean_phone_list = clean_phones(phones_raw)

    # Reject nếu không còn email VÀ phone nào sau khi clean
    if not clean_email_list and not clean_phone_list:
        return None

    # ── Step 3: Entity classification ────────────────────────────────
    description = lead.get("description", "")
    entity_type = classify_entity(url, description)

    # Reject non-company entities
    if entity_type in ("media", "government", "directory",
                       "marketplace", "research", "blog"):
        return None

    # ── Step 4: Optional structure check (chậm, dùng khi cần) ────────
    structure = {}
    if check_structure:
        structure = has_company_structure(url)

    # ── Step 5: Build cleaned lead ────────────────────────────────────
    best_email = clean_email_list[0] if clean_email_list else ""

    from ai_analyst import score_email, email_quality_label

    cleaned = {
        **lead,
        "emails":        ", ".join(clean_email_list[:3]),
        "phones":        ", ".join(clean_phone_list[:3]),
        "best_email":    best_email,
        "email_quality": email_quality_label(best_email) if best_email else "",
        "entity_type":   entity_type,
        # Structure check results (nếu có)
        "has_contact_page":  structure.get("contact", False),
        "has_about_page":    structure.get("about", False),
        "has_services_page": structure.get("services", False),
    }

    return cleaned


def validate_all(leads: list, check_structure: bool = False) -> tuple[list, int]:
    """
    Validate toàn bộ leads.
    Returns (valid_leads, rejected_count)
    """
    valid   = []
    rejected = 0

    for lead in leads:
        result = validate_lead(lead, check_structure=check_structure)
        if result:
            valid.append(result)
        else:
            rejected += 1

    print(f"  ✅ Valid: {len(valid)} | ❌ Rejected: {rejected} "
          f"({rejected/(len(leads) or 1)*100:.0f}% filtered)")
    return valid, rejected