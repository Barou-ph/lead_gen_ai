"""
email_templates.py — Cold email templates cho Team Building
Ngành: Hospitality, Logistics, Manufacturing, IT, Finance, Healthcare
Sử dụng trong email_generator.py hoặc standalone.

Chiến lược:
- Email ngắn, cá nhân hóa, tiếng Việt
- Pain point rõ ràng theo từng ngành
- CTA đơn giản: book 15 phút call
"""

from datetime import datetime

# ─── SENDER INFO — chỉnh lại trước khi dùng ──────────────────────────
SENDER = {
    "name": "Minh Anh",  # Tên người gửi
    "title": "Team Building Consultant",
    "company": "Vibe Team Building",
    "phone": "0901 234 567",
    "email": "minh.anh@vibeteam.vn",
    "website": "vibeteam.vn",
    "cal_link": "calendly.com/vibeteam/15min",
}

# ─── TEMPLATES theo ngành ─────────────────────────────────────────────
TEMPLATES = {
    # ══ HOSPITALITY ════════════════════════════════════════════════════
    "hospitality": {
        "subject_options": [
            "Team {company} — giải pháp gắn kết nhân viên mùa cao điểm",
            "Giảm turnover nhân viên F&B — chia sẻ cách 3 khách sạn 5★ làm",
            "Chào {contact_name} — đề xuất team building cho {company}",
        ],
        "body": """Chào {contact_name},

Mình là {sender_name} từ {sender_company}.

Ngành khách sạn / nhà hàng đang đối mặt với tỷ lệ nghỉ việc cao nhất trong các ngành dịch vụ — đặc biệt sau mùa cao điểm. Nhân viên frontline burn out nhanh, và chi phí tuyển dụng thay thế thường cao hơn nhiều so với chi phí giữ chân họ.

Chúng mình vừa triển khai chương trình team building cho 3 khách sạn 4-5 sao tại TP.HCM và Đà Nẵng — kết quả: tỷ lệ nghỉ việc giảm ~30% sau 6 tháng, điểm hài lòng nội bộ tăng rõ rệt.

Format phù hợp cho hospitality:
• Half-day activity (không ảnh hưởng ca làm việc)  
• Kịch bản thiết kế riêng cho team F&B, housekeeping, front desk
• Budget linh hoạt từ 500K–2M/người

{company} hiện có bao nhiêu nhân viên không? Mình có thể đề xuất format phù hợp trong 15 phút call.

Lịch của mình: {cal_link}

Trân trọng,
{sender_name}
{sender_title} | {sender_company}
{sender_phone}""",
        "pain_point": "Turnover cao sau mùa cao điểm, nhân viên frontline burn out",
        "cta": "Book 15 phút call",
    },
    # ══ LOGISTICS ══════════════════════════════════════════════════════
    "logistics": {
        "subject_options": [
            "Team lái xe + kho bãi của {company} — giải pháp team building thực tế",
            "Gắn kết đội ngũ vận hành — không cần nghỉ ngày làm việc",
            "Chào {contact_name} — đề xuất cho team logistics {company}",
        ],
        "body": """Chào {contact_name},

Mình là {sender_name}, chuyên tư vấn team building cho các công ty logistics & vận tải tại Việt Nam.

Thực tế với ngành logistics: đội ngũ thường phân tán (lái xe, kho bãi, văn phòng), ít khi gặp nhau, và áp lực deadline cao liên tục. Đây là công thức dẫn đến mâu thuẫn nội bộ và hiệu quả phối hợp giảm.

Chúng mình có chương trình thiết kế riêng cho logistics:
• Activity hybrid: vừa online vừa offline — phù hợp đội phân tán  
• Focus vào communication & teamwork thực chiến, không phải game vui vẻ bề mặt  
• Tổ chức cuối tuần hoặc xen kẽ ngày thường, không ảnh hưởng vận hành

{company} đang vận hành bao nhiêu nhân sự? Mình có thể gửi proposal trong 24h sau khi hiểu context.

Bạn có 15 phút không? {cal_link}

Trân trọng,
{sender_name}
{sender_title} | {sender_company}
{sender_phone}""",
        "pain_point": "Đội ngũ phân tán, ít giao tiếp, áp lực vận hành liên tục",
        "cta": "Book 15 phút call",
    },
    # ══ MANUFACTURING ══════════════════════════════════════════════════
    "manufacturing": {
        "subject_options": [
            "Team nhà máy {company} — chương trình gắn kết công nhân & quản lý",
            "Giảm tai nạn lao động qua team building — nghe có vẻ lạ nhưng có data",
            "Đề xuất team building cho {company} — không gián đoạn sản xuất",
        ],
        "body": """Chào {contact_name},

Mình từ {sender_company} — chuyên thiết kế chương trình team building cho doanh nghiệp sản xuất.

Với nhà máy, thách thức lớn nhất thường là: khoảng cách giữa công nhân và quản lý, văn hóa "chỉ làm theo lệnh", và tỷ lệ nghỉ việc của lao động phổ thông cao.

Chúng mình đã triển khai cho các nhà máy trong khu công nghiệp Bình Dương, Long An — format thực tế, không màu mè:
• Chương trình 2-4 giờ, tổ chức ngay tại nhà máy hoặc gần KCN  
• Nội dung thiết kế theo văn hóa sản xuất: tinh thần tổ đội, an toàn lao động tập thể  
• Chi phí tối ưu, phù hợp doanh nghiệp có 50–500 công nhân

{company} hiện đang có bao nhiêu nhân sự không? Mình muốn đề xuất đúng format cho quy mô đó.

{cal_link}

Trân trọng,
{sender_name}
{sender_title} | {sender_company}
{sender_phone}""",
        "pain_point": "Khoảng cách quản lý - công nhân, turnover lao động phổ thông cao",
        "cta": "Book 15 phút call",
    },
    # ══ IT / TECH ══════════════════════════════════════════════════════
    "it": {
        "subject_options": [
            'Dev team {company} — team building không phải kiểu "leo núi ăn BBQ"',
            "Burnout & silos trong đội tech — chia sẻ cách 5 công ty IT giải quyết",
            "Chào {contact_name} — đề xuất team activity cho {company}",
        ],
        "body": """Chào {contact_name},

Mình là {sender_name} — làm việc nhiều với các công ty IT, outsourcing và digital agency tại Việt Nam.

Thẳng thắn mà nói: developer thường ghét team building kiểu truyền thống. Leo núi, ăn buffet, chụp ảnh — xong về vẫn như cũ.

Chúng mình làm khác: thiết kế activity dựa trên tâm lý của người làm tech — problem-solving challenges, hackathon format, escape room concept — nhưng kết hợp yếu tố tâm lý nhóm thực sự để cải thiện collaboration giữa các team.

Kết quả thực tế: giảm friction giữa dev/PM/design, onboarding nhanh hơn cho member mới, và quan trọng hơn — mọi người thực sự muốn đến.

{company} đang bao nhiêu headcount? Remote, onsite hay hybrid? Mình có thể thiết kế format phù hợp.

15 phút: {cal_link}

{sender_name}
{sender_title} | {sender_company}""",
        "pain_point": "Developer burnout, silos giữa dev/PM/design, remote team disconnect",
        "cta": "Book 15 phút call",
    },
    # ══ FINANCE ════════════════════════════════════════════════════════
    "finance": {
        "subject_options": [
            "Retreat & team building cao cấp cho {company} — đề xuất Q3/Q4",
            "Gắn kết đội sales bảo hiểm / tài chính — giải pháp thực chiến",
            "Chào {contact_name} — chương trình team building cho {company}",
        ],
        "body": """Chào {contact_name},

Mình là {sender_name} từ {sender_company}.

Công ty tài chính & bảo hiểm thường có đội sales áp lực cao, KPI nặng, và culture cạnh tranh lành mạnh nhưng đôi khi dẫn đến thiếu teamwork. Đặc biệt khi đội ngũ lớn và phân chia theo vùng/chi nhánh.

Chúng mình thiết kế chương trình team building cho môi trường financial services:
• Retreat 1-2 ngày kết hợp workshop + activity — thường dùng cho Annual Conference  
• Format tập trung vào leadership & high-performance culture  
• Venue cao cấp tại resort, phù hợp cả domestic và overseas trip  
• Budget từ 2-5 triệu/người, trọn gói

{company} thường tổ chức event nội bộ vào thời điểm nào trong năm? Mình muốn đề xuất trước để kịp Q3-Q4.

{cal_link}

Trân trọng,
{sender_name}
{sender_title} | {sender_company}
{sender_phone}""",
        "pain_point": "Sales team áp lực cao, thiếu teamwork, cần reward & recognition",
        "cta": "Book 15 phút call",
    },
    # ══ HEALTHCARE ═════════════════════════════════════════════════════
    "healthcare": {
        "subject_options": [
            "Đội ngũ y tế {company} — giải pháp chống burnout & gắn kết",
            "Team building cho phòng khám / bệnh viện — format phù hợp đặc thù ngành",
            "Chào {contact_name} — đề xuất cho {company}",
        ],
        "body": """Chào {contact_name},

Mình là {sender_name} — chuyên tư vấn wellness và team building cho tổ chức y tế.

Nhân viên y tế có tỷ lệ burnout thuộc hàng cao nhất, và điều này ảnh hưởng trực tiếp đến chất lượng chăm sóc bệnh nhân. Không phải chỉ vấn đề phúc lợi — đây là vấn đề vận hành.

Chúng mình có chương trình thiết kế riêng cho tổ chức y tế:
• Mindfulness & stress management session thực hành  
• Team cohesion activity — không chiếm nhiều thời gian của ca trực  
• Workshop cho đội lãnh đạo về emotional intelligence trong môi trường áp lực  
• Certified trainer có nền tảng tâm lý học lâm sàng

{company} hiện có bao nhiêu nhân viên? Mình có thể thiết kế phù hợp với lịch ca trực.

{cal_link}

Trân trọng,
{sender_name}
{sender_title} | {sender_company}
{sender_phone}""",
        "pain_point": "Burnout nhân viên y tế, áp lực ca trực, thiếu cohesion giữa các bộ phận",
        "cta": "Book 15 phút call",
    },
    # ══ DEFAULT ════════════════════════════════════════════════════════
    "default": {
        "subject_options": [
            "Đề xuất team building cho {company} — {sender_company}",
            "Chào {contact_name} — giải pháp gắn kết đội ngũ cho {company}",
        ],
        "body": """Chào {contact_name},

Mình là {sender_name} từ {sender_company} — chuyên thiết kế chương trình team building cho doanh nghiệp Việt Nam.

Chúng mình hiểu mỗi ngành có văn hóa và thách thức khác nhau, nên không dùng chương trình mẫu — tất cả đều được thiết kế riêng dựa trên đặc thù của từng công ty.

Một số doanh nghiệp chúng mình đã làm việc cùng ghi nhận:
• Cải thiện giao tiếp nội bộ rõ rệt sau 1 chương trình  
• Tỷ lệ hài lòng nhân viên tăng và giảm turnover  
• ROI đo được qua năng suất nhóm sau 3-6 tháng

{company} đang có bao nhiêu nhân sự? Mình có thể đề xuất format phù hợp ngay.

{cal_link}

Trân trọng,
{sender_name}
{sender_title} | {sender_company}
{sender_phone}""",
        "pain_point": "Gắn kết đội ngũ, cải thiện culture công ty",
        "cta": "Book 15 phút call",
    },
}


# ─── RENDER FUNCTION ──────────────────────────────────────────────────
def render_email(lead: dict, industry: str = None) -> dict:
    """
    Render cold email cho 1 lead.

    Args:
        lead: dict chứa website, best_email, field, company_name, description...
        industry: override industry (nếu None dùng từ lead)

    Returns:
        dict: {subject, body, pain_point, cta}
    """
    ind = (industry or lead.get("industry", "")).lower().strip()
    tmpl = TEMPLATES.get(ind, TEMPLATES["default"])

    # Extract company name từ website
    company_name = lead.get("company_name", "")
    if not company_name:
        try:
            from urllib.parse import urlparse

            host = urlparse(lead.get("website", "")).netloc.replace("www.", "")
            company_name = host.split(".")[0].title()
        except:
            company_name = "Quý Công Ty"

    # Contact name — để trống nếu không có
    contact_name = lead.get("contact_name", "Anh/Chị")

    # Subject — chọn cái đầu tiên
    subject_tmpl = tmpl["subject_options"][0]
    subject = subject_tmpl.format(
        company=company_name,
        contact_name=contact_name,
        sender_company=SENDER["company"],
    )

    # Body
    body = tmpl["body"].format(
        company=company_name,
        contact_name=contact_name,
        sender_name=SENDER["name"],
        sender_title=SENDER["title"],
        sender_company=SENDER["company"],
        sender_phone=SENDER["phone"],
        sender_email=SENDER["email"],
        cal_link=SENDER["cal_link"],
    )

    return {
        "email_subject": subject,
        "email_body": body,
        "pain_point": tmpl["pain_point"],
        "cta": tmpl["cta"],
        "ai_language": "vi",
        "contact_reason": f"Team building cho ngành {ind or 'doanh nghiệp'}",
    }


# ─── BATCH RENDER (không cần AI API) ─────────────────────────────────
def render_all(leads: list) -> list:
    """Render email cho tất cả leads, không cần AI — dùng templates."""
    results = []
    for i, lead in enumerate(leads):
        try:
            email_data = render_email(lead)
            results.append({**lead, **email_data})
            ind = lead.get("industry", "?")
            ws = lead.get("website", "")[:40]
            print(f"  ✅ [{i+1}/{len(leads)}] {ind} | {ws}")
        except Exception as e:
            results.append({**lead, "email_body": "", "email_subject": ""})
            print(f"  ❌ [{i+1}/{len(leads)}] {e}")
    return results


if __name__ == "__main__":
    # Test render
    test_leads = [
        {
            "website": "https://hotelsaigon.com.vn",
            "industry": "hospitality",
            "company_name": "Hotel Saigon",
            "best_email": "hr@hotelsaigon.com.vn",
        },
        {
            "website": "https://vinafco.com.vn",
            "industry": "logistics",
            "best_email": "info@vinafco.com.vn",
        },
        {
            "website": "https://techcorp.vn",
            "industry": "it",
            "best_email": "contact@techcorp.vn",
        },
    ]
    print("=== TEST RENDER ===\n")
    for lead in test_leads:
        result = render_email(lead)
        print(f"[{lead['industry'].upper()}]")
        print(f"Subject: {result['email_subject']}")
        print(f"Pain:    {result['pain_point']}")
        print(f"Body preview: {result['email_body'][:120]}...")
        print()
