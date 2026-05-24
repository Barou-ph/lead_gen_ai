"""
ai_filter.py v2 — Prompt chặt hơn, batch nhỏ hơn, reject cụ thể hơn.
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
BATCH_SIZE = 5  # Nhỏ hơn để GPT đọc kỹ hơn

SYSTEM_PROMPT = """Bạn là chuyên gia sales B2B dịch vụ TEAM BUILDING tại Việt Nam.
Nhiệm vụ: Quyết định có nên gửi cold email pitch dịch vụ team building cho công ty này không.

REJECT (should_contact = false) nếu thuộc bất kỳ nhóm nào sau:
1. Báo chí / truyền thông / tạp chí (vnexpress, tuoitre, qdnd, suckhoedoisong,...)
2. Website từ điển / tutorial / blog cá nhân
3. Global brand không hoạt động tại VN (equatorial.com, aon.com, smallpdf,...)
4. Công ty nước ngoài không có nhân sự VN (description tiếng nước ngoài, email nước ngoài)
5. Freelancer / 1-2 người / không có văn phòng rõ ràng
6. Email là placeholder: trangvangvietnam, yellowpages, congty.vn, yoursite.com, webdemo.com, domain.com
7. Công ty quá nhỏ trong ngành không có nhu cầu team building (hộ kinh doanh hóa chất, cơ khí 5-10 người)
8. Website đang bảo trì / lỗi / không có nội dung

PASS (should_contact = true) nếu:
- Công ty VN thật, đang hoạt động, có đội ngũ nhân viên (>20 người ước tính)
- Ngành phù hợp: khách sạn, resort, logistics, manufacturing (nhà máy lớn), bệnh viện, giáo dục doanh nghiệp, bất động sản, tài chính, bán lẻ chuỗi
- Email là địa chỉ công ty thật (không phải gmail cá nhân random, không phải placeholder)

Ví dụ REJECT:
- equatorial.com → global brand
- trangvangvietnam.com → placeholder
- baothanhhoa.vn → báo chí
- cokhiphuluong.com (5 nhân viên, cơ khí nhỏ) → quá nhỏ

Ví dụ PASS:
- pearlriverhotel.vn (khách sạn, CEO email) → PASS
- datviettour.com.vn (du lịch team building) → PASS
- baovan.com.vn (logistics 10+ năm) → PASS
- trieuphuloc.com.vn (nội thất xuất khẩu, sales email) → PASS

Trả về JSON array ĐÚNG FORMAT, mỗi item:
{
  "website": "domain.com",
  "should_contact": true,
  "reason": "1 câu cụ thể: lý do pass hoặc lý do reject"
}

CHỈ trả về JSON array, không có text khác, không có markdown."""


def _build_prompt(leads: list) -> str:
    lines = [
        "Đánh giá các công ty sau (quyết định có nên gửi cold email team building không):\n"
    ]
    for i, lead in enumerate(leads, 1):
        desc = (lead.get("description") or "")[:150]
        # Fix encoding nếu lỗi
        try:
            desc = desc.encode("latin-1").decode("utf-8")
        except:
            pass
        if desc.count("á»") > 2 or desc.count("Ã") > 2:
            desc = "[description lỗi encoding]"

        email = lead.get("best_email") or lead.get("emails", "")
        if email:
            email = str(email).split(",")[0].strip()

        size = lead.get("size_estimate", "unknown")
        hiring = lead.get("is_hiring", False)

        lines.append(
            f"{i}. website={lead.get('website', '')} "
            f"| industry={lead.get('industry', '')} "
            f"| size={size} "
            f"| hiring={hiring} "
            f"| email={email} "
            f"| desc={desc}"
        )
    return "\n".join(lines)


def ai_filter_batch(leads: list) -> list:
    if not client:
        for lead in leads:
            lead["ai_should_contact"] = True
            lead["ai_reason"] = "AI skip (no key)"
        return leads

    results = {lead.get("website", ""): lead for lead in leads}

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=600,
            temperature=0.1,  # Rất thấp để ổn định
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_prompt(leads)},
            ],
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        parsed = json.loads(raw)

        for item in parsed:
            ws = item.get("website", "")
            # Match linh hoạt — bỏ http/https/www
            ws_clean = (
                ws.replace("https://", "")
                .replace("http://", "")
                .replace("www.", "")
                .rstrip("/")
            )
            for key in results:
                key_clean = (
                    key.replace("https://", "")
                    .replace("http://", "")
                    .replace("www.", "")
                    .rstrip("/")
                )
                if ws_clean in key_clean or key_clean in ws_clean:
                    results[key]["ai_should_contact"] = item.get("should_contact", True)
                    results[key]["ai_reason"] = item.get("reason", "")
                    break

    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON parse error: {e} | raw: {raw[:200]}")
        for lead in leads:
            lead.setdefault("ai_should_contact", True)
            lead.setdefault("ai_reason", "parse error")
    except Exception as e:
        print(f"  ⚠️  API error: {e}")
        for lead in leads:
            lead.setdefault("ai_should_contact", True)
            lead.setdefault("ai_reason", f"error: {e}")

    for lead in leads:
        lead.setdefault("ai_should_contact", True)
        lead.setdefault("ai_reason", "not evaluated")

    return leads


def ai_filter_all(leads: list, progress_cb=None) -> tuple:
    if not leads:
        return [], []

    total = len(leads)
    print(f"\n🤖 AI Filter v2: {total} leads | batch={BATCH_SIZE} | model={MODEL}\n")

    for i in range(0, total, BATCH_SIZE):
        batch = leads[i : i + BATCH_SIZE]
        n = i // BATCH_SIZE + 1
        total_batches = (total - 1) // BATCH_SIZE + 1
        print(
            f"  Batch {n}/{total_batches} ({len(batch)} leads)...", end=" ", flush=True
        )
        ai_filter_batch(batch)
        passed_so_far = sum(
            1 for l in leads[: i + BATCH_SIZE] if l.get("ai_should_contact", True)
        )
        rejected_so_far = i + len(batch) - passed_so_far
        print(f"✅ (running: pass={passed_so_far}, reject={rejected_so_far})")
        if progress_cb:
            progress_cb(done=min(i + BATCH_SIZE, total), total=total)
        if i + BATCH_SIZE < total:
            time.sleep(0.3)

    passed = [l for l in leads if l.get("ai_should_contact", True)]
    rejected = [l for l in leads if not l.get("ai_should_contact", True)]

    print(f"\n  ✅ Pass: {len(passed)} | ❌ Reject: {len(rejected)}\n")

    # In summary reject reasons
    if rejected:
        print("  Reject reasons:")
        for l in rejected[:10]:
            print(f"    - {l.get('website','')}: {l.get('ai_reason','')}")

    return passed, rejected


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

    out = input_file.replace(".xlsx", "_ai_filtered.xlsx")
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        pd.DataFrame(passed).to_excel(writer, sheet_name="✅ Pass", index=False)
        pd.DataFrame(rejected).to_excel(writer, sheet_name="❌ Rejected", index=False)

    print(f"\n📤 Xuất: {out}")
    print(f"   ✅ {len(passed)} leads nên liên hệ")
    print(f"   ❌ {len(rejected)} leads bị loại")
    print(f"   💰 Tỷ lệ reject: {len(rejected)/len(leads)*100:.1f}%")
