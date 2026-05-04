import pandas as pd
import os
import time


def export_to_excel(data: list, file_name: str = "leads.xlsx"):
    """
    Export leads ra Excel.
    - Fix PermissionError nếu file đang mở → tự đổi tên
    - Thêm cột mới: grade, score, email_quality, tags
    """
    # Cột và thứ tự hiển thị
    columns = [
        "grade",
        "score",
        "website",
        "best_email",
        "email_quality",
        "emails",
        "phones",
        "field",
        "tags",
    ]

    df = pd.DataFrame(data)

    # Đảm bảo tất cả cột tồn tại (backward-compat)
    for col in columns:
        if col not in df.columns:
            df[col] = ""

    df = df[columns]

    # Tự đổi tên nếu file đang bị lock (đang mở trong Excel)
    target = file_name
    for attempt in range(5):
        try:
            df.to_excel(target, index=False)
            print(f"✅ Đã update {target} ({len(df)} leads)")
            return
        except PermissionError:
            base, ext = os.path.splitext(file_name)
            target = f"{base}_{attempt+1}{ext}"
            print(f"  ⚠️  File bị lock → thử lưu vào {target}")
            time.sleep(1)

    # Fallback: lưu CSV
    csv_name = file_name.replace(".xlsx", ".csv")
    df.to_csv(csv_name, index=False, encoding="utf-8-sig")
    print(f"⚠️  Không mở được Excel → đã lưu CSV: {csv_name}")
