"""
company_classifier.py — Layer 2: Company entity classifier
Chạy SAU crawl, TRƯỚC scoring.

Dùng rule-based classifier (không cần AI) để xác định:
- Đây có phải company thật không?
- Loại entity là gì?
- Có commercial intent không?

Output entity_type:
  ACCEPTED: software_company | agency | outsourcing_company |
            saas_company | it_service | manufacturing | logistics |
            healthcare | finance | retail | education
  REJECTED: media | news | government | directory | aggregator |
            blog | marketplace | research | personal | unknown
"""

import re
from urllib.parse import urlparse

# ══════════════════════════════════════════════════════════════════════
#  ACCEPTED entity types
# ══════════════════════════════════════════════════════════════════════
ACCEPTED_TYPES = {
    "software_company", "agency", "outsourcing_company",
    "saas_company", "it_service", "manufacturing",
    "logistics", "healthcare", "finance", "retail",
    "education_company", "construction",
}

# ══════════════════════════════════════════════════════════════════════
#  SIGNAL SETS — keywords trong HTML/description
# ══════════════════════════════════════════════════════════════════════

# Signals → COMPANY (positive)
COMPANY_POSITIVE = [
    # Identity signals
    "founded in", "established in", "since 20", "since 19",
    "we are a", "we are an", "our company", "our team",
    "our clients", "our services", "our solutions",
    "chúng tôi là", "công ty chúng tôi", "về chúng tôi",
    "đội ngũ của chúng tôi", "dịch vụ của chúng tôi",

    # B2B operation signals
    "contact us", "get in touch", "request a quote", "book a demo",
    "liên hệ", "nhận báo giá", "tư vấn miễn phí",
    "our portfolio", "case study", "our work", "client",
    "hire us", "work with us",

    # Team signals
    "our team of", "years of experience", "team of developers",
    "software engineers", "project manager", "tech stack",
]

# Signals → NOT COMPANY (negative, article/media/directory)
COMPANY_NEGATIVE = [
    # Article patterns
    "in this article", "in this guide", "in this post",
    "read more", "related articles", "you may also like",
    "published by", "written by", "author:", "posted on",
    "last updated", "editorial team", "fact-checked",
    "subscribe to our newsletter", "follow us on",

    # Directory / aggregator
    "list of companies", "top companies", "best companies",
    "compare companies", "find a company", "submit your company",
    "add your business", "featured companies",
    "danh sách công ty", "top 10", "best 10",

    # Market research
    "market size", "market share", "cagr", "compound annual",
    "market forecast", "industry report", "market research",
    "key players include", "major players",

    # News
    "breaking news", "latest news", "press release",
    "according to", "reported that", "announced that",
    "funding round", "raised $", "series a funding",
    "acquired by", "merger with",

    # Government
    "government portal", "public service", "cổng dịch vụ công",
    "thủ tục hành chính",
]

# Signals theo entity type
ENTITY_TYPE_SIGNALS = {
    "software_company": [
        "software development", "custom software", "web development",
        "mobile app", "application development", "software solutions",
        "phần mềm", "lập trình", "phát triển phần mềm",
        "we build", "we develop", "we create software",
    ],
    "outsourcing_company": [
        "outsourcing", "offshore", "nearshore", "it outsourcing",
        "dedicated team", "staff augmentation", "body leasing",
        "offshore development", "offshore team",
    ],
    "agency": [
        "digital agency", "creative agency", "marketing agency",
        "design agency", "branding agency", "advertising agency",
        "công ty truyền thông", "agency số",
    ],
    "saas_company": [
        "saas", "software as a service", "our platform",
        "our product", "free trial", "pricing plans",
        "monthly subscription", "annual plan",
    ],
    "it_service": [
        "it consulting", "it services", "managed services",
        "cloud services", "cybersecurity", "network infrastructure",
        "devops", "it support", "tư vấn công nghệ",
    ],
    "manufacturing": [
        "manufacturing", "production", "factory", "industrial",
        "sản xuất", "nhà máy", "xưởng sản xuất",
    ],
    "logistics": [
        "logistics", "freight", "shipping", "supply chain",
        "warehousing", "transportation", "vận tải", "kho bãi",
    ],
    "healthcare": [
        "healthcare", "medical", "clinic", "hospital",
        "pharmaceutical", "y tế", "phòng khám", "bệnh viện",
    ],
    "finance": [
        "fintech", "financial", "investment", "insurance",
        "accounting", "tài chính", "kế toán", "bảo hiểm",
    ],
    "retail": [
        "retail", "ecommerce", "e-commerce", "online store",
        "bán lẻ", "thương mại điện tử", "chuỗi cửa hàng",
    ],
    "education_company": [
        "training center", "education company", "learning platform",
        "trung tâm đào tạo", "công ty giáo dục", "khóa học",
    ],
    "construction": [
        "construction", "building", "real estate developer",
        "xây dựng", "bất động sản", "kiến trúc",
    ],
}

# Negative entity signals (reject ngay)
REJECTED_ENTITY_SIGNALS = {
    "media": [
        "the latest news", "read our blog", "published",
        "our journalists", "editorial", "newsroom",
        "tin tức mới nhất", "báo điện tử",
    ],
    "directory": [
        "browse companies", "find companies", "submit listing",
        "sponsored listing", "featured listing",
        "tìm kiếm công ty", "danh mục công ty",
    ],
    "marketplace": [
        "hire freelancers", "post a job", "find talent",
        "freelance marketplace", "millions of freelancers",
        "thuê freelancer",
    ],
    "research": [
        "market report", "buy report", "download report",
        "sample report", "request sample", "table of contents",
        "chapter 1:", "executive summary",
    ],
    "government": [
        "thủ tục hành chính", "dịch vụ công trực tuyến",
        "cổng thông tin điện tử", "văn bản pháp luật",
    ],
}


def _count_signals(text: str, signals: list) -> int:
    low = text.lower()
    return sum(1 for s in signals if s in low)


def classify_from_content(html_text: str, url: str = "",
                           description: str = "") -> dict:
    """
    Classify entity từ HTML content.
    Returns dict:
    {
        "entity_type": str,
        "is_company": bool,
        "confidence": float (0-1),
        "reject_reason": str or None,
        "commercial_signals": int,
        "negative_signals": int,
    }
    """
    text = (html_text + " " + description + " " + url).lower()

    # ── Check negative entity types (reject ngay) ────────────────────
    for etype, signals in REJECTED_ENTITY_SIGNALS.items():
        if _count_signals(text, signals) >= 2:
            return {
                "entity_type": etype,
                "is_company": False,
                "confidence": 0.8,
                "reject_reason": f"entity_is_{etype}",
                "commercial_signals": 0,
                "negative_signals": _count_signals(text, COMPANY_NEGATIVE),
            }

    # ── Count positive vs negative company signals ───────────────────
    pos = _count_signals(text, COMPANY_POSITIVE)
    neg = _count_signals(text, COMPANY_NEGATIVE)

    # Hard reject nếu negative signals >> positive
    if neg >= 4 and pos <= 1:
        return {
            "entity_type": "content_page",
            "is_company": False,
            "confidence": 0.75,
            "reject_reason": "too_many_negative_signals",
            "commercial_signals": pos,
            "negative_signals": neg,
        }

    # ── Detect entity type ───────────────────────────────────────────
    best_type = "unknown"
    best_score = 0
    for etype, signals in ENTITY_TYPE_SIGNALS.items():
        score = _count_signals(text, signals)
        if score > best_score:
            best_score = score
            best_type = etype

    # ── Compute confidence ───────────────────────────────────────────
    if pos >= 4 and best_score >= 2:
        confidence = 0.9
        is_company = True
    elif pos >= 2 and best_score >= 1:
        confidence = 0.7
        is_company = True
    elif pos >= 1 and neg == 0:
        confidence = 0.5
        is_company = True
    elif neg >= 2:
        confidence = 0.3
        is_company = False
    else:
        confidence = 0.4
        is_company = best_type != "unknown"

    reject_reason = None if is_company else f"low_confidence:{best_type}"

    return {
        "entity_type": best_type,
        "is_company": is_company,
        "confidence": confidence,
        "reject_reason": reject_reason,
        "commercial_signals": pos,
        "negative_signals": neg,
    }


def is_accepted_company(classification: dict) -> bool:
    """True nếu entity được accept vào pipeline."""
    if not classification.get("is_company"):
        return False
    if classification.get("entity_type") not in ACCEPTED_TYPES and \
       classification.get("confidence", 0) < 0.5:
        return False
    return True