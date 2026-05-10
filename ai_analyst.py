"""
ai_analyst.py — AI analyze + cold email generation
- GPT-4o-mini (rẻ, đủ tốt)
- Batch 5 leads/call để tiết kiệm token
- Load API key từ .env
"""

import os
import json
import time
import re
from dotenv import load_dotenv

load_dotenv()

_api_key = os.getenv("OPENAI_API_KEY", "")
client = None

if _api_key:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=_api_key)
    except ImportError:
        print("⚠️  openai package chưa cài: pip install openai")
    except Exception as e:
        print(f"⚠️  OpenAI init error: {e}")
else:
    print("⚠️  OPENAI_API_KEY không tìm thấy trong .env — AI phase sẽ bị skip.")

from industries import INDUSTRY_PAIN_POINTS

MODEL       = "gpt-4o-mini"
BATCH_SIZE  = 5
MAX_TOKENS  = 1200
TEMPERATURE = 0.7

SYSTEM_PROMPT = """You are a B2B sales expert for team building services in Vietnam.

For each company, return a JSON array. Each item:
{
  "website": "...",
  "pain_point": "1 sentence specific to their industry/size",
  "company_type": "startup|sme|enterprise|agency|other",
  "should_contact": true/false,
  "contact_reason": "1 sentence why or why not",
  "cold_email": {
    "subject": "under 8 words, personal",
    "body": "3-4 sentences. Specific pain, clear offer, CTA. No generic openers."
  }
}

Rules:
- should_contact=false if not a real operating company
- Write in Vietnamese if company is Vietnamese-focused
- Be concise, no fluff
- Return ONLY valid JSON array"""


def _build_prompt(leads: list, industry: str) -> str:
    pain = INDUSTRY_PAIN_POINTS.get(industry, "team cohesion and retention")
    lines = [f"Industry: {industry} | Pain context: {pain}\n\nCompanies:"]
    for i, lead in enumerate(leads, 1):
        desc = (lead.get("description") or "")[:120]
        lines.append(
            f"{i}. website={lead.get('website','')} "
            f"| field={lead.get('field','')} "
            f"| entity={lead.get('entity_type','unknown')} "
            f"| size={lead.get('size_estimate','?')} "
            f"| hiring={lead.get('is_hiring',False)} "
            f"| grade={lead.get('grade','?')} "
            f"| desc={desc}"
        )
    lines.append("\nReturn ONLY a JSON array.")
    return "\n".join(lines)


def analyze_batch(leads: list, industry: str) -> list:
    if not client:
        return []
    prompt = _build_prompt(leads, industry)
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            )
            raw = resp.choices[0].message.content.strip()
            # Strip markdown fences if present
            raw = re.sub(r"```json|```", "", raw).strip()
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
            for v in parsed.values():
                if isinstance(v, list):
                    return v
            return []
        except json.JSONDecodeError:
            match = re.search(r'\[.*\]', raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        except Exception as e:
            if "rate_limit" in str(e).lower():
                wait = 10 * (attempt + 1)
                print(f"    ⏳ Rate limit → chờ {wait}s...")
                time.sleep(wait)
            else:
                print(f"    ⚠️  API error: {e}")
                break
    return []


def analyze_leads(leads: list, industry: str) -> list:
    to_analyze = [l for l in leads if l.get("grade", "D") in ("A", "B", "C")]
    skip       = [l for l in leads if l.get("grade", "D") == "D"]

    print(f"\n🤖 AI: {len(to_analyze)} leads | model={MODEL} | batch={BATCH_SIZE}")
    print(f"   (skip {len(skip)} Grade D)\n")

    ai_map = {}
    batches = [to_analyze[i:i+BATCH_SIZE]
               for i in range(0, len(to_analyze), BATCH_SIZE)]

    for i, batch in enumerate(batches):
        print(f"  Batch {i+1}/{len(batches)}...", end=" ", flush=True)
        results = analyze_batch(batch, industry)
        ok = 0
        for r in results:
            w = r.get("website", "")
            if w:
                ai_map[w] = r
                ok += 1
        print(f"✅ {ok}/{len(batch)}")
        time.sleep(0.5)

    enriched = []
    for lead in leads:
        ai = ai_map.get(lead.get("website", ""), {})
        enriched.append({
            **lead,
            "pain_point":     ai.get("pain_point", ""),
            "company_type":   ai.get("company_type", ""),
            "should_contact": ai.get("should_contact", True),
            "contact_reason": ai.get("contact_reason", ""),
            "email_subject":  ai.get("cold_email", {}).get("subject", ""),
            "email_body":     ai.get("cold_email", {}).get("body", ""),
        })

    contacted = sum(1 for l in enriched if l.get("should_contact"))
    print(f"\n✅ AI done | Nên contact: {contacted}/{len(enriched)}")
    return enriched


def estimate_cost(n_leads: int) -> str:
    n_calls   = max(1, n_leads // BATCH_SIZE + 1)
    input_tok  = n_calls * 400
    output_tok = n_calls * 800
    cost = (input_tok * 0.15 + output_tok * 0.60) / 1_000_000
    return f"~${cost:.4f} USD ({n_calls} API calls, model={MODEL})"


# ── Exported helpers (dùng bởi lead_scorer, validator) ───────────────
def score_email(email: str) -> int:
    from lead_scorer import score_email as _se
    return _se(email)


def email_quality_label(email: str) -> str:
    from lead_scorer import email_quality_label as _eql
    return _eql(email)