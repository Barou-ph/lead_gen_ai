# 📘 Lead Intelligence Tool — Hướng dẫn Marketing Team

**Phiên bản:** v5 | **Cập nhật:** 21/05/2026  
**Tool chính:** `tool.py` (web app) + 2 script hỗ trợ

---

## 🚀 Bắt đầu nhanh (5 phút)

### Chạy web app

```powershell
cd C:\Users\ASUS\Downloads\lead_gen_ai
python tool.py
# Mở: http://localhost:5000
```

---

## 📋 Workflow hoàn chỉnh

```
[1] Crawl leads        →  [2] Filter top 100    →  [3] Gen email    →  [4] Gửi & track
   tool.py Tab Crawl       filter_top100.py          gen_email_batch.py   Gmail/Streak
   hoặc upload Excel       hoặc tool.py Tab Filter   hoặc tool.py Tab 📧
```

---

## Bước 1 — Crawl hoặc Upload leads

### Option A: Upload file sẵn có

1. Mở http://localhost:5000
2. Tab **🔍 Filter** → kéo thả `leads_ALL_v1.xlsx` vào ô upload
3. Bấm **🔍 Lọc Leads**

### Option B: Crawl mới

1. Tab **🕷️ Crawl** → chọn ngành ở sidebar
2. Cấu hình: Target = 60, Workers = 6
3. Bật **🔍 Enrich** (tắt **🤖 AI** để nhanh hơn)
4. Bấm **▶ Bắt đầu crawl**

### Option C: Crawl ngành còn thiếu qua terminal

```powershell
python crawler.py education 50
python crawler.py retail 50
```

---

## Bước 2 — Filter top 100 leads

### Qua web app (tool.py):

| Setting   | Giá trị khuyến nghị  |
| --------- | -------------------- |
| Min Score | **20**               |
| Grades    | **A + B** (bỏ C)     |
| Email ✓   | **Bật**              |
| Phone ✓   | Tắt (không bắt buộc) |

### Hoặc chạy script nhanh:

```powershell
python filter_top100.py
# Output: top100_leads.xlsx
```

**Kết quả:** File `top100_leads.xlsx` với leads được sắp xếp:

- Grade A (email công ty) lên đầu
- Ngành ưu tiên: Hospitality → Logistics → Manufacturing → IT

---

## Bước 3 — Gen cold email

### Option A: Qua web app

1. Tab **📧 Email** → **🤖 Gen AI Email**
2. Đợi gen xong → **⬇ Export Excel**

### Option B: Script batch (nhanh hơn, không cần AI API)

```powershell
python gen_email_batch.py
# Output: top100_with_emails.xlsx
```

> **Lưu ý:** Trước khi gen, chỉnh thông tin sender trong `email_templates.py`:
>
> ```python
> SENDER = {
>     "name":     "Tên Bạn",
>     "company":  "Tên Công Ty",
>     "phone":    "09xx xxx xxx",
>     "cal_link": "calendly.com/link-của-bạn",
> }
> ```

---

## Bước 4 — Gửi email & tracking

### Nguyên tắc gửi

|                   |                                                              |
| ----------------- | ------------------------------------------------------------ |
| **Gửi tối đa**    | 30 email/ngày (tránh spam)                                   |
| **Email dùng**    | Email cá nhân tên thật (KHÔNG dùng info@, no-reply@)         |
| **Công cụ track** | [Streak](https://streak.com) (Gmail miễn phí) hoặc Mailtrack |

### Lịch gửi 3 tuần

| Tuần   | Ngành                   | Số email | Mục tiêu  |
| ------ | ----------------------- | -------- | --------- |
| Tuần 1 | Hospitality + Logistics | ~40      | 2-3 reply |
| Tuần 2 | Manufacturing + IT      | ~35      | 2-3 reply |
| Tuần 3 | Finance + Healthcare    | ~25      | 2-3 reply |

### Follow-up sequence

```
Ngày 0:  Gửi email gốc
Ngày 4:  Follow-up 1 — "Chỉ muốn đảm bảo email tới được..."
Ngày 7:  Follow-up 2 — Đổi angle: gửi case study 1 trang
Ngày 14: Follow-up cuối — Ngắn, lịch sự: "Nếu không phù hợp thời điểm này..."
```

---

## 📊 KPI mục tiêu

| Metric          | Mục tiêu         | Tốt  |
| --------------- | ---------------- | ---- |
| Open rate       | >35%             | >50% |
| Reply rate      | >5%              | >10% |
| Meeting booked  | 3-5 / 100 email  | 8-10 |
| Deal từ meeting | 1-2 / 10 meeting | 3+   |

---

## ❓ Troubleshooting thường gặp

**Tool không chạy được:**

```powershell
pip install -r requirements.txt
python tool.py
```

**Crawl bị chậm / không lấy được lead:**

- Giảm Workers xuống 3-4
- Tắt Enrich để nhanh hơn
- Thử crawl lúc sáng sớm (ít load server hơn)

**Email bị spam:**

- Warm up email domain 2 tuần trước
- Dùng tên người thật, không dùng email generic
- Tránh từ khóa spam: "miễn phí", "khuyến mãi", "ưu đãi đặc biệt"

**Không có ANTHROPIC_API_KEY:**

- Chạy `gen_email_batch.py` với `USE_AI = False`
- Templates có sẵn vẫn rất tốt, không nhất thiết cần AI

---

## 📁 Cấu trúc files quan trọng

```
lead_gen_ai/
├── tool.py                  # Web app chính (chạy cái này)
├── crawler.py               # Crawl YellowPages
├── filter_top100.py         # Lọc top 100 leads ⭐
├── email_templates.py       # Templates cold email ⭐
├── gen_email_batch.py       # Batch gen email ⭐
├── extractor.py             # Extract email/phone từ website
├── scorer.py                # Chấm điểm leads
├── enricher.py              # Enrich thông tin
├── email_generator.py       # AI email gen (cho tool.py)
├── leads_ALL_v1.xlsx        # Database leads hiện tại
├── top100_leads.xlsx        # [Generated] Top 100 sau filter
└── top100_with_emails.xlsx  # [Generated] Top 100 + cold emails
```

---

## 💡 Tips từ thực tế

1. **Hospitality & Logistics** reply nhanh nhất — ưu tiên gửi trước
2. **IT company** cần email "thẳng thắn, không hoa mỹ" — dùng template IT
3. **Grade A với email company** = lead tốt nhất, focus vào đây trước
4. **Gửi thứ 3 hoặc thứ 4 lúc 9-10h sáng** = open rate cao nhất
5. **Subject line ngắn < 50 ký tự** hoạt động tốt hơn trên mobile

---

_Questions? Liên hệ team phát triển tool._
