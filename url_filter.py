"""
url_filter.py — Layer 1: Hard URL filter
Chạy NGAY sau search, TRƯỚC crawl.
Mục tiêu: chỉ giữ URL có khả năng là company homepage/service page.

Logic:
1. Reject domain blacklist (media, dict, gov, global brand...)
2. Reject path blacklist (blog, article, top-10, guide...)
3. Reject slug keywords (best-, top-, what-is-, danh-sach-...)
4. Reject non-company TLDs (edu, gov...)
5. Prefer root domain hoặc /services /about /contact
"""

import re
from urllib.parse import urlparse

# ══════════════════════════════════════════════════════════════════════
#  DOMAIN BLACKLIST — cứng, không thương lượng
# ══════════════════════════════════════════════════════════════════════
BLACKLISTED_DOMAINS = {
    # === MEDIA / NEWS ===
    "vnexpress.net", "tuoitre.vn", "thanhnien.vn", "dantri.com.vn",
    "vietnamnet.vn", "baomoi.com", "zing.vn", "kenh14.vn",
    "vietcetera.com", "kr-asia.com", "e27.co", "technode.global",
    "techcrunch.com", "forbes.com", "bloomberg.com", "reuters.com",
    "wired.com", "theverge.com", "techcollectivesea.com",
    "thegradient.pub", "the-shiv.com", "apacbusinessheadlines.com",
    "cxodigitalpulse.com", "growyourbusiness.org", "bestdevops.com",
    "creationsforu.com", "justsomecrypto.com", "edtechagency.net",
    "techsciblog.com", "vicsguide.com", "hkbav.org",
    "conventuslaw.com", "limericktime.com", "bizasean.com",

    # === DICTIONARY / ENCYCLOPEDIA ===
    "merriam-webster.com", "dictionary.com", "cambridge.org",
    "wikipedia.org", "britannica.com", "vocabulary.com",
    "investopedia.com", "wikihow.com",

    # === RESEARCH / MARKET REPORT ===
    "statista.com", "mordorintelligence.com", "techsciresearch.com",
    "blueweaveconsulting.com", "expertmarketresearch.com",
    "marketresearchvietnam.com", "techsciblog.com", "itif.org",
    "viettonkinconsulting.com", "researchinvietnam.com",
    "growyourbusiness.org",

    # === DIRECTORIES / AGGREGATORS ===
    "clutch.co", "goodfirms.co", "techbehemoths.com", "sortlist.com",
    "designrush.com", "upcity.com", "manifest.com",
    "tracxn.com", "crunchbase.com", "zoominfo.com",
    "appdevelopmentcompanies.co", "topsoftwarecompanies.co",
    "beststartup.asia", "failory.com", "superbcompanies.com",
    "incorp.asia", "vietnam.incorp.asia",
    "listicle.sgpgrid.com", "consultancy.org",
    "softwarecompanynetwork.com", "globalsoftwarecompanies.com",
    "topon.tech", "ensun.io", "bestarion.com",

    # === JOB BOARDS ===
    "linkedin.com", "itviec.com", "vietnamworks.com", "topcv.vn",
    "jobstreet.com", "wellfound.com", "thesaasjobs.com",
    "vieclam24h.vn", "careerlink.vn", "freelancer.com", "upwork.com",

    # === GOVERNMENT ===
    "gov.vn", "chinhphu.vn", "mps.gov.vn", "bocongan.gov.vn",
    "trade.gov", "worldbank.org", "adb.org", "oecd.org",

    # === GLOBAL BRANDS (không phải buyer VN) ===
    "shopify.com", "salesforce.com", "blockchain.com", "deepai.org",
    "chatgpt.com", "openai.com", "microsoft.com", "google.com",
    "amazon.com", "apple.com", "ibm.com", "oracle.com",
    "gameloft.com", "ninite.com", "atlassian.com", "hubspot.com",

    # === SEO TOOLS / ARTIFACTS ===
    "sitestat.com", "siteindices.com", "usitestat.com",
    "prsync.com", "pr-inside.com",

    # === MISC IRRELEVANT ===
    "zhihu.com", "baidu.com", "mobile01.com", "juraforum.de",
    "digitalspy.com", "smergers.com", "ciovietnam.org",
    "stackoverflow.com", "stackexchange.com", "reddit.com",
    "quora.com", "medium.com", "substack.com",
    "hikingproject.com", "teachmeat.pbworks.com",
    "thuthuattienich.com", "quantrimang.com", "download.com.vn",
    "cloudwards.net", "secomm.vn",   # secomm = article site
    "mobiwork.com",                   # articles about mobiwork, not buyer
    "vnito.org",                      # conference, not company
    "10times.com", "eventbrite.com",
    "worldbank.org", "pbworks.com",
}

# ══════════════════════════════════════════════════════════════════════
#  PATH BLACKLIST — reject specific URL path patterns
# ══════════════════════════════════════════════════════════════════════
BLACKLISTED_PATHS = [
    # Content pages
    "/blog/", "/news/", "/article/", "/articles/",
    "/dictionary/", "/wiki/", "/guide/", "/guides/",
    "/what-is/", "/how-to/", "/definition/", "/insights/",
    "/report/", "/research/", "/publication/", "/publications/",
    "/insight/", "/post/", "/posts/", "/press/",
    "/industry-reports/", "/industry-insights/", "/market-intelligence/",
    "/resources/", "/learn/", "/education/", "/tutorial/",
    "/hoi-dap/", "/thu-thuat/", "/cong-nghe/",
    "/tin-tuc/", "/bai-viet/", "/kien-thuc/",

    # Listing / directory / aggregator pages
    "/companies/", "/agencies/", "/developers/", "/freelancers/",
    "/explore/", "/d/explore/", "/directory/",
    "/location/", "/local-agencies/", "/startups/",

    # Job pages (chỉ reject listing, không reject /careers của company)
    "/jobs/", "/job/", "/tuyen-dung/bai-viet",
    "/freelancers/", "/hire/",

    # User / profile pages
    "/user/", "/profile/", "/author/", "/tag/", "/category/",

    # Market data pages
    "/outlook/", "/statistics/", "/forecast/", "/reports/",
    "/terms/",  # investopedia /terms/
]

# ══════════════════════════════════════════════════════════════════════
#  SLUG KEYWORD BLACKLIST — reject URL slugs chứa keyword này
# ══════════════════════════════════════════════════════════════════════
BAD_SLUG_KEYWORDS = [
    # Listicle / aggregator patterns
    "top-10", "top-20", "top-5", "best-", "top-list",
    "companies-in-", "companies-list", "company-list",
    "list-of-", "ranking", "danh-sach",
    "best-companies", "leading-companies", "top-companies",

    # Content / guide patterns
    "what-is-", "how-to-", "guide-to-", "introduction-to-",
    "overview-of-", "xu-huong", "thi-truong",
    "market-size", "market-report", "industry-report",
    "forecast-", "statistics-", "analysis-of-",

    # News patterns
    "raises-", "funding-", "series-a", "series-b",
    "investment-in-", "backed-by-", "launches-",
    "vietnam-is-", "vietnam-has-", "how-vietnam-",
    "growing-in-", "rise-of-", "future-of-",
    "a-sneak-peek", "deep-dive", "in-depth",

    # Tutorial / how-to
    "cach-go-", "cach-viet-", "cach-lam-",
    "huong-dan-", "thu-thuat-",
]

# ══════════════════════════════════════════════════════════════════════
#  COMMERCIAL INTENT PATHS — bonus nếu URL chứa những path này
# (không dùng để reject, chỉ dùng để score)
# ══════════════════════════════════════════════════════════════════════
COMMERCIAL_PATHS = [
    "/contact", "/contact-us", "/lien-he",
    "/services", "/solutions", "/dich-vu",
    "/about", "/about-us", "/gioi-thieu",
    "/careers", "/tuyen-dung",
    "/portfolio", "/case-study", "/our-work",
    "/get-quote", "/book-demo", "/pricing",
]


def get_domain(url: str) -> str:
    try:
        parsed = urlparse(url.lower())
        parts = parsed.netloc.replace("www.", "").split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else parsed.netloc
    except Exception:
        return ""


def get_path(url: str) -> str:
    try:
        return urlparse(url).path.lower()
    except Exception:
        return ""


def get_slug(url: str) -> str:
    """Lấy toàn bộ path + query làm slug để check keyword."""
    try:
        parsed = urlparse(url)
        return (parsed.path + parsed.query).lower()
    except Exception:
        return url.lower()


def is_article_url(url: str) -> bool:
    """True nếu URL có pattern của bài viết/blog/news."""
    slug = get_slug(url)
    # Pattern: /year/month/day/ hoặc /2022/09/08/
    if re.search(r"/20\d{2}/\d{2}/\d{2}/", slug):
        return True
    # Pattern: slug quá dài (article URL thường dài)
    path = get_path(url)
    segments = [s for s in path.split("/") if s]
    if len(segments) >= 3:
        # Nếu segment cuối quá dài và có nhiều dấu gạch ngang
        last = segments[-1]
        if len(last) > 60 and last.count("-") > 5:
            return True
    return False


def url_has_commercial_intent(url: str) -> bool:
    """Check xem URL có dấu hiệu commercial page không."""
    path = get_path(url)
    return any(cp in path for cp in COMMERCIAL_PATHS)


def filter_url(url: str) -> tuple[bool, str]:
    """
    Returns (keep, reason).
    keep=True → URL pass, đưa vào crawl.
    keep=False → reject, kèm reason.
    """
    if not url or not url.startswith("http"):
        return False, "invalid_url"

    low = url.lower()
    domain = get_domain(url)
    path = get_path(url)
    slug = get_slug(url)

    # ── 1. Domain blacklist ───────────────────────────────────────────
    if domain in BLACKLISTED_DOMAINS:
        return False, f"blacklisted:{domain}"

    # Partial match (subdomain)
    for bd in BLACKLISTED_DOMAINS:
        if low.split("//")[-1].split("/")[0].endswith(f".{bd}"):
            return False, f"blacklisted_sub:{bd}"

    # ── 2. TLD check ─────────────────────────────────────────────────
    if domain.endswith(".edu") or domain.endswith(".gov"):
        return False, "bad_tld"

    # ── 3. Path blacklist ─────────────────────────────────────────────
    for bp in BLACKLISTED_PATHS:
        if bp in path:
            return False, f"bad_path:{bp}"

    # ── 4. Slug keyword check ─────────────────────────────────────────
    for kw in BAD_SLUG_KEYWORDS:
        if kw in slug:
            return False, f"bad_slug:{kw}"

    # ── 5. Article URL pattern ────────────────────────────────────────
    if is_article_url(url):
        return False, "article_url_pattern"

    # ── 6. SEO artifact URLs ──────────────────────────────────────────
    if "siteindices.com" in low or "usitestat.com" in low:
        return False, "seo_artifact"

    return True, ""


def filter_urls(urls: list) -> tuple[list, dict]:
    """
    Filter danh sách URL.
    Returns (clean_urls, stats_dict)
    """
    kept = []
    reject_reasons: dict[str, int] = {}

    for url in urls:
        keep, reason = filter_url(url)
        if keep:
            kept.append(url)
        else:
            cat = reason.split(":")[0]
            reject_reasons[cat] = reject_reasons.get(cat, 0) + 1

    return kept, reject_reasons