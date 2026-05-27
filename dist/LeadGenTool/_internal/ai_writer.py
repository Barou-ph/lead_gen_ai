from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_message(company):
    prompt = f"""
Viết tin nhắn ngắn (3-4 dòng) để chào dịch vụ team building.

Công ty: {company}

Yêu cầu:
- Không spam
- Giống người thật viết
- Có CTA nhẹ
"""

    res = client.chat.completions.create(
        model="gpt-4.1-mini", messages=[{"role": "user", "content": prompt}]
    )

    return res.choices[0].message.content
