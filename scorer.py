"""
scorer.py — Lead scoring v2.
Patch: nâng threshold Grade A lên 25, thêm penalty non-VN domain,
       thêm bonus .vn domain mạnh hơn, fix enrich bonus hợp lý hơn.
"""

import re

EMAIL_SCORE_MAP = {
    "ceo": 12, "founder": 12, "director": 10, "cto": 10,
    "coo": 10, "managing": 9, "vp": 8, "president": 8,
    "head": 8, "sales": 8, "bd": 8, "business": 7,
    "partner": 7, "account": 6,
    "hr": 6, "recruit": 6, "career": 6, "people": 6, "talent": 6,
    "hello": 3, "hi": 3, "contact": 3, "office": 3, "team": 2,
    "info": 1, "admin": 1, "support": 1, "help": 1, "marketing": 2,
    "noreply": -50, "no-reply": -50, "bounce": -50,
    "donotreply": -50, "abuse": -50, "spam": -50,
}

HIGH_VALUE_FIELDS = {
    "IT Software", "IT Outsourcing", "AI/ML", "Cloud/DevOps",
    "Mobile Dev", "Manufacturing", "Logistics", "Healthcare",
    "Finance", "Retail", "Digital Agency",
}

PERSONAL_DOMAINS = {"gmail.com","yahoo.com","hotmail.com","outlook.com","icloud.com"}


def score_single_email(email: str) -> int:
    if not email or "@" not in email:
        return -99
    low = email.lower()
    prefix = low.split("@")[0]
    domain_part = low.split("@")[1] if "@" in low else ""
    is_personal = domain_part in PERSONAL_DOMAINS

    for kw, sc in EMAIL_SCORE_MAP.items():
        if kw in prefix:
            return sc + (-5 if is_personal else 0)

    return -3 if is_personal else 2


def rank_emails(emails: list) -> list:
    from filter import is_valid_email
    valid = [e for e in emails if is_valid_email(e)]
    return sorted(valid, key=score_single_email, reverse=True)


def email_label(email: str) -> str:
    s = score_single_email(email)
    if s >= 10: return "🔥 Decision Maker"
    if s >= 7:  return "✅ Sales/HR"
    if s >= 3:  return "🔵 Generic"
    if s >= 1:  return "⚪ Low"
    return "❌ Bad"


def score_lead(lead: dict) -> dict:
    score  = 0
    tags   = []
    issues = []

    emails_raw = lead.get("emails", "")
    phones_raw = lead.get("phones", "")
    website    = lead.get("website", "").lower()
    field      = lead.get("field", "")

    from filter import is_valid_email, is_valid_vn_phone, clean_emails, clean_phones

    email_list = [e.strip() for e in emails_raw.split(",") if e.strip()]
    phone_list = [p.strip() for p in phones_raw.split(",") if p.strip()]

    valid_emails = clean_emails(email_list)
    valid_phones = clean_phones(phone_list)

    # ── Penalties ─────────────────────────────────────────────────────
    bad_emails = len(email_list) - len(valid_emails)
    if bad_emails > 0:
        score -= bad_emails * 8
        issues.append(f"{bad_emails} bad email(s)")

    if not valid_emails and not valid_phones:
        score -= 15
        issues.append("no valid contact")

    has_business = any(
        e.split("@")[-1] not in PERSONAL_DOMAINS
        for e in valid_emails
    ) if valid_emails else False

    if valid_emails and not has_business:
        score -= 5
        issues.append("personal email only")

    # [PATCH] Penalty: domain không phải .vn và không có phone VN
    is_vn_domain = ".vn" in website
    if not is_vn_domain and not valid_phones:
        score -= 8
        issues.append("non-VN domain, no VN phone")

    # ── Rewards ───────────────────────────────────────────────────────
    if valid_emails:
        ranked = rank_emails(valid_emails)
        best   = ranked[0] if ranked else ""
        bsc    = score_single_email(best)
        score += max(bsc, 0)
        if bsc >= 10:  tags.append("Decision Maker Email")
        elif bsc >= 7: tags.append("Sales/HR Email")

    if valid_phones:
        score += 5
        tags.append("Has Phone")

    # [PATCH] .vn domain bonus tăng từ 3 lên 6
    if is_vn_domain:
        score += 6
        tags.append("VN Domain")

    if field in HIGH_VALUE_FIELDS:
        score += 5
        tags.append(field)

    if len(valid_emails) >= 2:
        score += 2
        tags.append("Multi-Email")

    # Enrich bonuses — giữ nguyên nhưng không đổi threshold
    if lead.get("has_contact_page"):
        score += 5
        tags.append("Contact Page ✓")
    if lead.get("has_services_page"):
        score += 5
        tags.append("Services Page ✓")
    if lead.get("has_about_page"):
        score += 2
        tags.append("About Page ✓")
    if lead.get("is_hiring"):
        score += 3
        tags.append("Hiring")
    if lead.get("linkedin_url"):
        score += 2
        tags.append("LinkedIn")

    # [PATCH] Nâng threshold — A cần thật sự tốt
    # Cũ: A≥20, B≥12, C≥6
    # Mới: A≥25, B≥15, C≥8
    # Lý do: với enrich bonus +5+5+2, dễ đạt 20 dù lead rác
    grade = ("A" if score >= 25 else
             "B" if score >= 15 else
             "C" if score >= 8  else "D")

    ranked_final = rank_emails(valid_emails)
    best_email   = ranked_final[0] if ranked_final else ""

    return {
        **lead,
        "emails":        ", ".join(ranked_final[:3]),
        "phones":        ", ".join(valid_phones[:3]),
        "best_email":    best_email,
        "email_quality": email_label(best_email) if best_email else "",
        "score":         score,
        "grade":         grade,
        "tags":          ", ".join(tags),
        "issues":        ", ".join(issues),
    }