"""
patch_tool.py - Chạy file này để tự động patch tool.py
Cách dùng: python patch_tool.py
"""
import re, shutil, os

TARGET = "tool.py"

if not os.path.exists(TARGET):
    print("❌ Không tìm thấy tool.py — chạy script này trong cùng thư mục với tool.py")
    exit(1)

shutil.copy(TARGET, TARGET + ".bak")
print(f"✅ Đã backup → tool.py.bak")

content = open(TARGET, "r", encoding="utf-8").read()
original = content

# ══════════════════════════════════════════════════════
# FIX 1: Thêm domain rác vào NOISE_DOMAINS
# ══════════════════════════════════════════════════════
OLD_NOISE = '"headhuntvietnam.com",'
NEW_NOISE = '''"headhuntvietnam.com",
    "remotepeople.com",
    "thivien.net",
    "thaiware.com",
    "vexa.mn",
    "logitech.com",
    "kahoot.com",
    "runoob.com",
    "buyabans.com",
    "othoba.com",'''

if OLD_NOISE in content:
    content = content.replace(OLD_NOISE, NEW_NOISE, 1)
    print("✅ FIX 1: Đã thêm domain rác vào NOISE_DOMAINS")
else:
    print("⚠️  FIX 1: Không tìm thấy anchor 'headhuntvietnam.com' — bỏ qua")

# ══════════════════════════════════════════════════════
# FIX 2: Thay hàm apply_filter() — thêm dedup
# ══════════════════════════════════════════════════════
OLD_FILTER = '''def apply_filter(df, cfg):
    passed, rejected = [], []
    for _, row in df.iterrows():
        d = row.to_dict()
        reason = _reject_reason(d, cfg)
        if reason:
            rejected.append({**d, "reject_reason": reason})
        else:
            passed.append(d)
    df_pass = pd.DataFrame(passed)  if passed  else pd.DataFrame()
    df_rej  = pd.DataFrame(rejected) if rejected else pd.DataFrame()'''

NEW_FILTER = '''def apply_filter(df, cfg):
    passed, rejected = [], []
    seen_emails  = set()
    seen_domains = set()

    def _root_domain(url):
        try:
            parts = str(url).split("//")[-1].split("/")[0].split(".")
            return ".".join(parts[-2:]) if len(parts) >= 2 else url
        except:
            return str(url)

    for _, row in df.iterrows():
        d = row.to_dict()
        reason = _reject_reason(d, cfg)
        if reason:
            rejected.append({**d, "reject_reason": reason})
            continue

        # DEDUP theo email + domain
        em  = str(d.get("best_email","") or d.get("emails","") or "").split(",")[0].strip().lower()
        dom = _root_domain(str(d.get("website","")))

        if em and em not in ("", "nan", "none"):
            if em in seen_emails:
                rejected.append({**d, "reject_reason": "duplicate_email"})
                continue
            seen_emails.add(em)

        if dom:
            if dom in seen_domains:
                rejected.append({**d, "reject_reason": "duplicate_domain"})
                continue
            seen_domains.add(dom)

        passed.append(d)

    df_pass = pd.DataFrame(passed)  if passed  else pd.DataFrame()
    df_rej  = pd.DataFrame(rejected) if rejected else pd.DataFrame()'''

if OLD_FILTER in content:
    content = content.replace(OLD_FILTER, NEW_FILTER, 1)
    print("✅ FIX 2: Đã thêm dedup vào apply_filter()")
else:
    print("⚠️  FIX 2: Không match apply_filter() — có thể đã được sửa trước đó")

# ══════════════════════════════════════════════════════
# FIX 3: Sửa VN check trong crawl_one()
# ══════════════════════════════════════════════════════
OLD_VN = '''                from filter import filter_url, is_vietnam_lead
                recheck, _ = filter_url(link)
                if not recheck: return None
                if not is_vietnam_lead(link, ", ".join(phones)):
                    return None'''

NEW_VN = '''                from filter import filter_url
                recheck, _ = filter_url(link)
                if not recheck: return None

                # VN check: .vn domain HOẶC có phone VN hợp lệ
                is_vn_domain = ".vn" in link
                has_vn_phone = bool(phones)
                if not is_vn_domain and not has_vn_phone:
                    return None
                # Có phone VN nhưng domain nước ngoài → check description
                if not is_vn_domain and has_vn_phone:
                    desc_low = desc.lower()
                    FOREIGN_SIGNALS = [
                        "từ điển","dictionary","tutorial","bài học",
                        "học tiếng","dịch thuật","translation",
                        "encyclopedia","định nghĩa","thesaurus",
                    ]
                    if any(s in desc_low for s in FOREIGN_SIGNALS):
                        return None'''

if OLD_VN in content:
    content = content.replace(OLD_VN, NEW_VN, 1)
    print("✅ FIX 3: Đã sửa VN check trong crawl_one()")
else:
    print("⚠️  FIX 3: Không match VN check — kiểm tra lại crawl_one()")

# ══════════════════════════════════════════════════════
# SAVE
# ══════════════════════════════════════════════════════
if content != original:
    open(TARGET, "w", encoding="utf-8").write(content)
    print(f"\n🎉 Patch xong! Restart tool: python tool.py")
else:
    print("\n⚠️  Không có gì thay đổi — kiểm tra lại file tool.py")