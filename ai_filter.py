"""
ai_filter.py — Dùng GPT-4o-mini để filter lead phù hợp cold email team building.

Cách dùng:
  - Gọi từ tool.py trong apply_filter() sau rule-based filter
  - Hoặc chạy độc lập: python ai_filter.py leads_ALL.xlsx

Output: thêm cột 'ai_should_contact', 'ai_reason' vào DataFrame
"""

import os, json, time, re
from dotenv import load_dotenv

load_dotenv()

_api_key = os.getenv("OPENAI_API_KEY", "")
client = None
if _api_key:
    try:
        from openai import OpenAI

        client = OpenAI(api_key=_api_key)
    except ImportError:
        print("⚠️  pip install openai")
    except Exception as e:
        print(f"⚠️  OpenAI error: {e}")

MODEL = "gpt-4o-mini"
BATCH_SIZE = 10  # 10 leads/call — tiết kiệm hơn ai_analyst.py

SYSTEM_PROMPT = """Bạn là chuyên gia sales B2B dịch vụ team building tại Việt Nam.

Nhiệm vụ: Đọc thông tin từng công ty và quyết định có nên gửi cold email pitch dịch vụ team building không.

Tiêu chí NÊN liên hệ (should_contact = true):
- Là công ty VN đang hoạt động thật sự (có website, mô tả rõ ràng)
- Có đội ngũ nhân viên (không phải 1-2 người)
- Ngành có nhu cầu team building: logistics, hospitality, manufacturing, healthcare, finance, realestate, retail, education, IT
- Email là địa chỉ công ty (không phải gmail cá nhân random)

Tiêu chí KHÔNG nên liên hệ (should_contact = false):
- Báo chí, truyền thông, tạp chí
- Website từ điển, tutorial, blog
- Global brand (không phải buyer VN)
- Công ty 1-2 người, freelancer
- Không có mô tả rõ ràng hoặc mô tả lỗi encoding
- Email là placeholder (trangvangvietnam, yellowpages, congty.vn)

Trả về JSON array, mỗi item:
{
  "website": "...",
  "should_contact": true/false,
  "reason": "1 câu ngắn lý do"
}

Chỉ trả về JSON array thuần, không có text khác."""


def _build_prompt(leads: list) -> str:
    lines = ["Đánh giá các công ty sau:\n"]
    for i, lead in enumerate(leads, 1):
        desc = (lead.get("description") or "")[:100]
        email = lead.get("best_email") or lead.get("emails", "")
        if email:
            email = str(email).split(",")[0].strip()
        lines.append(
            f"{i}. website={lead.get('website', '')} "
            f"| industry={lead.get('industry', '')} "
            f"| field={lead.get('field', '')} "
            f"| email={email} "
            f"| desc={desc}"
        )
    return "\n".join(lines)


def ai_filter_batch(leads: list) -> list:
    """
    Nhận list lead dicts, trả về list với 'ai_should_contact' và 'ai_reason'.
    """
    if not client:
        # Không có API key → pass all
        for lead in leads:
            lead["ai_should_contact"] = True
            lead["ai_reason"] = "AI skip (no key)"
        return leads

    results = {lead.get("website", ""): lead for lead in leads}

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=800,
            temperature=0.2,  # thấp để ổn định, không sáng tạo
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_prompt(leads)},
            ],
        )
        raw = resp.choices[0].message.content.strip()

        # Parse JSON
        raw = re.sub(r"```json|```", "", raw).strip()
        parsed = json.loads(raw)

        for item in parsed:
            ws = item.get("website", "")
            if ws in results:
                results[ws]["ai_should_contact"] = item.get("should_contact", True)
                results[ws]["ai_reason"] = item.get("reason", "")

    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse error: {e}")
        for lead in leads:
            lead.setdefault("ai_should_contact", True)
            lead.setdefault("ai_reason", "parse error")
    except Exception as e:
        print(f"  ⚠️  API error: {e}")
        for lead in leads:
            lead.setdefault("ai_should_contact", True)
            lead.setdefault("ai_reason", f"error: {e}")

    # Fallback cho lead chưa được update
    for lead in leads:
        lead.setdefault("ai_should_contact", True)
        lead.setdefault("ai_reason", "not evaluated")

    return leads


def ai_filter_all(leads: list, progress_cb=None) -> tuple:
    """
    Filter toàn bộ leads theo batch.
    Trả về (passed, rejected) — 2 list.
    """
    if not leads:
        return [], []

    total = len(leads)
    print(f"\n🤖 AI Filter: {total} leads | batch={BATCH_SIZE} | model={MODEL}\n")

    # Chạy theo batch
    for i in range(0, total, BATCH_SIZE):
        batch = leads[i : i + BATCH_SIZE]
        print(
            f"  Batch {i//BATCH_SIZE + 1}/{(total-1)//BATCH_SIZE + 1} ({len(batch)} leads)...",
            end=" ",
        )
        ai_filter_batch(batch)
        print("✅")
        if progress_cb:
            progress_cb(done=min(i + BATCH_SIZE, total), total=total)
        if i + BATCH_SIZE < total:
            time.sleep(0.5)  # tránh rate limit

    # Tách passed / rejected
    passed = [l for l in leads if l.get("ai_should_contact", True)]
    rejected = [l for l in leads if not l.get("ai_should_contact", True)]

    print(f"\n  ✅ Pass: {len(passed)} | ❌ Reject: {len(rejected)}\n")
    return passed, rejected


# ── Chạy độc lập ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import pandas as pd

    input_file = sys.argv[1] if len(sys.argv) > 1 else "leads_ALL.xlsx"
    if not os.path.exists(input_file):
        print(f"❌ Không tìm thấy {input_file}")
        sys.exit(1)

    print(f"📂 Đọc {input_file}...")
    df = pd.read_excel(input_file, dtype=str).fillna("")
    leads = df.to_dict(orient="records")
    print(f"  → {len(leads)} leads\n")

    passed, rejected = ai_filter_all(leads)

    # Export
    out = input_file.replace(".xlsx", "_ai_filtered.xlsx")
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        pd.DataFrame(passed).to_excel(writer, sheet_name="✅ Pass", index=False)
        pd.DataFrame(rejected).to_excel(writer, sheet_name="❌ Rejected", index=False)

    print(f"📤 Xuất: {out}")
    print(f"   ✅ {len(passed)} leads nên liên hệ")
    print(f"   ❌ {len(rejected)} leads bị loại")
