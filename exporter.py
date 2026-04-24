import pandas as pd
import os


def export_to_excel(new_data):
    file_name = "leads.xlsx"

    if os.path.exists(file_name):
        old_df = pd.read_excel(file_name)
        new_df = pd.DataFrame(new_data)

        df = pd.concat([old_df, new_df])
        df = df.drop_duplicates(subset=["website"])
    else:
        df = pd.DataFrame(new_data)

    df.to_excel(file_name, index=False)

    print("✅ Đã update leads.xlsx")
