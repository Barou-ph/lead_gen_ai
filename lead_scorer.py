"""
lead_scorer.py — Layer 3: Lead scoring với penalty system
Chạy SAU validate và classify.

Scoring philosophy:
- Reward: commercial signals, decision maker email, VN company
- Penalize NẶNG: article page, generic email, fake data, gmail
- Grade A/B chỉ dành cho ACTUAL buyer, không phải media/blog
"""

import re
from urllib.parse import urlparse

# ══════════════════════════════════════════════════════════════════════
#  EMAIL SCORING
# ══════════════════════════════════════════════════════════════════════
EMAIL_SCORES = {
    # Decision maker — THẬT SỰ cao
    "ceo":      12, "founder":   12, "director":  10,
    "cto":      10, "coo":       10, "managing":   9,
    "head":      8, "vp":         8, "president":  8,
    # Sales / BD — target tốt
    "sales":     8, "bd":         8, "business":   7,
    "partner":   7, "account":    6,
    # HR — target tốt cho team building
    "hr":        6, "recruit":    6, "career":     6,
    "people":    6, "talent":     6,
    # Generic company email — OK nhưng không priority
    "hello":     3, "hi":         3, "contact":    3,
    "office":    3, "team":       2,
    # Low value
    "info":      1, "admin":      1, "support":    1,
    "help":      1, "general":    1, "marketing":  2,
    # Penalize nặng
    "noreply":  -50, "no-reply":  -50, "bounce":   -50,
    "donotreply":-50, "abuse":    -50, "spam":     -50,
    "postmaster":-50,
}

# Email domain penalties
BAD_EMAIL_PATTERNS = [
    r"sentry", r"wixpress", r"bug-report", r"bug-reporting",
    r"^name@", r"^your@", r"^youname@", r"^enteryour@",
    r"@email\.com$", r"@yourcompany\.com$", r"@addresshere\.",
    r"@example\.com$", r"^test@", r"^demo@",
    r"photo-shared-by", r"tagging-@", r"^u003e",
    r"@company\.com$", r"@mail\.com$",
]

GMAIL_PENALTY = -7  # gmail là personal, không phải business


def score_email(email: str) -> int:
    if not email or "@" not in email:
        return -99

    low = email.lower()
    prefix = low.split("@")[0]
    domain_part = low.split("@")[1] if "@" in low else ""

    # Hard reject patterns
    for pattern in BAD_EMAIL_PATTERNS:
        if re.search(pattern, low):
            return -50

    # Hash/UUID prefix → sentry token
    if re.match(r"^[a-f0-9]{20,}$", prefix):
        return -50

    # Long prefix → garbage
    if len(prefix) > 50:
        return -50

    # Gmail penalty
    if "gmail.com" in domain_part:
        base = 0
        for kw, sc in EMAIL_SCORES.items():
            if kw in prefix:
                base = sc
                break
        return base + GMAIL_PENALTY

    # Check keywords
    for kw, sc in EMAIL_SCORES.items():
        if kw in prefix:
            return sc

    return 2  # default business email


def is_valid_email(email: str) -> bool:
    return score_email(email) > -10


def rank_emails(emails: list) -> list:
    valid = [e for e in emails if is_valid_email(e)]
    return sorted(valid, key=score_email, reverse=True)


def email_quality_label(email: str) -> str:
    s = score_email(email)
    if s >= 10: return "🔥 Decision Maker"
    if s >= 7:  return "✅ Sales/HR"
    if s >= 3:  return "🔵 Generic"
    if s >= 1:  return "⚪ Low"
    return "❌ Bad"


# ══════════════════════════════════════════════════════════════════════
#  PHONE VALIDATION
# ══════════════════════════════════════════════════════════════════════
def is_valid_vn_phone(phone: str) -> bool:
    cleaned = re.sub(r"[^\d+]", "", phone)
    if cleaned.startswith("+84"):
        cleaned = "0" + cleaned[3:]
    elif cleaned.startswith("84") and len(cleaned) == 11:
        cleaned = "0" + cleaned[2:]
    # Strict VN: 0[35789]xxxxxxxx
    return bool(re.fullmatch(r"0[35789]\d{8}", cleaned))


def clean_phones(phones: list) -> list:
    return [p for p in phones if is_valid_vn_phone(p)]


# ══════════════════════════════════════════════════════════════════════
#  LEAD SCORING — main function
# ══════════════════════════════════════════════════════════════════════

HIGH_VALUE_FIELDS = {
    "IT Software", "IT Outsourcing", "AI/ML",
    "Cloud/DevOps", "Mobile Dev", "Manufacturing",
    "Logistics", "Healthcare", "Finance", "Retail",
}


def score_lead(lead: dict) -> dict:
    """
    Score lead với reward + penalty system.
    Returns updated lead dict với score, grade, tags.
    """
    score = 0
    tags  = []
    penalties = []

    emails_str = lead.get("emails", "")
    phones_str = lead.get("phones", "")
    website    = lead.get("website", "").lower()
    field      = lead.get("field", "")
    desc       = lead.get("description", "").lower()
    entity     = lead.get("entity_type", "unknown")

    # Parse
    email_list = [e.strip() for e in emails_str.split(",") if e.strip()]
    phone_list = [p.strip() for p in phones_str.split(",") if p.strip()]

    # ── PENALTIES (chạy trước) ────────────────────────────────────────

    # Penalty: entity không phải company
    if entity in ("media", "news", "directory", "aggregator",
                  "research", "blog", "marketplace", "government"):
        score -= 20
        penalties.append(f"Bad entity:{entity}")

    # Penalty: email rác
    valid_emails = [e for e in email_list if is_valid_email(e)]
    invalid_count = len(email_list) - len(valid_emails)
    if invalid_count > 0:
        score -= invalid_count * 10
        penalties.append(f"Bad emails:{invalid_count}")

    # Penalty: không có email nào hợp lệ
    if not valid_emails and not phone_list:
        score -= 15
        penalties.append("No valid contact")

    # Penalty: chỉ gmail (không có business email)
    has_business_email = any(
        "@gmail" not in e and "@yahoo" not in e and "@hotmail" not in e
        for e in valid_emails
    )
    if valid_emails and not has_business_email:
        score -= 7
        penalties.append("Gmail only")

    # ── REWARDS ──────────────────────────────────────────────────────

    # Email quality reward
    if valid_emails:
        ranked = rank_emails(valid_emails)
        best = ranked[0] if ranked else ""
        best_score = score_email(best)
        score += max(best_score, 0)
        if best_score >= 10:
            tags.append("Decision Maker Email")
        elif best_score >= 7:
            tags.append("Sales/HR Email")

    # Phone reward
    valid_phones = clean_phones(phone_list)
    if valid_phones:
        score += 5
        tags.append("Has Phone")

    # VN domain reward
    if ".vn" in website:
        score += 3
        tags.append("VN Domain")

    # Field reward
    if field in HIGH_VALUE_FIELDS:
        score += 5
        tags.append(field)

    # Multi email reward (chỉ tính email hợp lệ)
    if len(valid_emails) > 1:
        score += 2
        tags.append("Multi-Email")

    # Enrich signals reward
    if lead.get("is_hiring"):
        score += 4
        tags.append("Hiring")
    if lead.get("has_english"):
        score += 2
        tags.append("English Site")
    if lead.get("linkedin_url"):
        score += 2
        tags.append("Has LinkedIn")
    if lead.get("has_contact_page"):
        score += 5
        tags.append("Has Contact Page")
    if lead.get("has_services_page"):
        score += 5
        tags.append("Has Services Page")
    if lead.get("has_about_page"):
        score += 3
        tags.append("Has About Page")

    # Commercial intent reward
    from url_filter import url_has_commercial_intent
    if url_has_commercial_intent(website):
        score += 3
        tags.append("Commercial Page")

    # Company classifier confidence reward
    conf = lead.get("confidence", 0)
    if conf >= 0.8:
        score += 5
        tags.append("High Confidence Company")
    elif conf >= 0.5:
        score += 2

    # ── GRADE ────────────────────────────────────────────────────────
    # Grade phải khó hơn trước: A chỉ cho lead thật
    grade = (
        "A" if score >= 22 else
        "B" if score >= 14 else
        "C" if score >= 7  else
        "D"
    )

    # Build updated lead
    ranked_emails = rank_emails(valid_emails)
    best_email    = ranked_emails[0] if ranked_emails else ""

    return {
        **lead,
        "emails":        ", ".join(ranked_emails[:3]),
        "phones":        ", ".join(valid_phones[:3]),
        "best_email":    best_email,
        "email_quality": email_quality_label(best_email) if best_email else "",
        "score":         score,
        "grade":         grade,
        "tags":          ", ".join(tags),
        "penalties":     ", ".join(penalties) if penalties else "",
    }