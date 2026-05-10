"""
exporter.py — Export leads ra Excel
- Mỗi session tạo file mới: leads_INDUSTRY_TIMESTAMP.xlsx
- Cập nhật leads_ALL.xlsx (master, dedup)
- Fix PermissionError tự động
- Hỗ trợ tất cả cột mới: enrich + AI
"""

import pandas as pd
import os
import time

COLUMNS = [
    "grade",
    "score",
    "should_contact",
    "website",
    "best_email",
    "email_quality",
    "emails",
    "phones",
    "field",
    "industry",
    "size_estimate",
    "is_hiring",
    "has_blog",
    "has_english",
    "linkedin_url",
    "description",
    "pain_point",
    "company_type",
    "contact_reason",
    "email_subject",
    "email_body",
    "tags",
    "session",
]


def _safe_write(df: pd.DataFrame, path: str) -> str:
    target = path
    for attempt in range(5):
        try:
            with pd.ExcelWriter(target, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="Leads")
                ws = writer.sheets["Leads"]
                for col in ws.columns:
                    max_len = max(
                        len(str(cell.value)) if cell.value else 0 for cell in col
                    )
                    ws.column_dimensions[col[0].column_letter].width = min(
                        max_len + 2, 60
                    )
            return target
        except PermissionError:
            base, ext = os.path.splitext(path)
            target = f"{base}_v{attempt+1}{ext}"
            print(f"  ⚠️  File bị lock → thử {target}")
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠️  Excel error: {e}")
            break
    csv = path.replace(".xlsx", ".csv")
    df.to_csv(csv, index=False, encoding="utf-8-sig")
    print(f"  ⚠️  Lưu CSV thay thế: {csv}")
    return csv


def export_to_excel(data: list, session: str = "", industry: str = ""):
    if not data:
        print("⚠️  Không có data để export.")
        return

    df_new = pd.DataFrame(data)
    df_new["session"] = session
    df_new["industry"] = industry

    for col in COLUMNS:
        if col not in df_new.columns:
            df_new[col] = ""
    df_new = df_new[COLUMNS]

    parts = [p for p in [industry, session] if p]
    session_name = "_".join(parts) if parts else "new"
    session_file = f"leads_{session_name}.xlsx"
    written = _safe_write(df_new, session_file)
    print(f"✅ Session file : {written}  ({len(df_new)} leads)")

    all_file = "leads_ALL.xlsx"
    if os.path.exists(all_file):
        try:
            df_old = pd.read_excel(all_file)
            for col in COLUMNS:
                if col not in df_old.columns:
                    df_old[col] = ""
            df_all = pd.concat([df_old, df_new], ignore_index=True)
            df_all.drop_duplicates(subset=["website"], keep="last", inplace=True)
        except Exception as e:
            print(f"  ⚠️  Đọc leads_ALL.xlsx lỗi ({e}) → tạo mới")
            df_all = df_new
    else:
        df_all = df_new

    grade_order = {"A": 0, "B": 1, "C": 2, "D": 3}
    df_all["_g"] = df_all["grade"].map(lambda g: grade_order.get(g, 3))
    df_all["_s"] = pd.to_numeric(df_all["score"], errors="coerce").fillna(0)
    df_all["_c"] = df_all["should_contact"].apply(
        lambda x: 0 if x is True or str(x).lower() == "true" else 1
    )
    df_all.sort_values(["_c", "_g", "_s"], ascending=[True, True, False], inplace=True)
    df_all.drop(columns=["_g", "_s", "_c"], inplace=True)

    written_all = _safe_write(df_all, all_file)
    gc = df_all["grade"].value_counts().to_dict()
    print(f"✅ Master file  : {written_all}  (tổng {len(df_all)} leads | {gc})")
