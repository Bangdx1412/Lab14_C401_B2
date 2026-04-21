import json, asyncio, os, re
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
MODEL = "gpt-4o-mini"
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
    current = [json.loads(l) for l in f if l.strip()]
print(f"Current: {len(current)} cases")

async def gen():
    extra = []
    docs = [
        {"id": "doc_it_faq", "text": open("data/docs/it_helpdesk_faq.txt", encoding="utf-8").read()},
        {"id": "doc_refund",  "text": open("data/docs/policy_refund_v4.txt", encoding="utf-8").read()},
    ]
    for doc in docs:
        prompt = f"""Tao chinh xac 2 cap cau hoi-dap kho (hard+reasoning) from tai lieu nay:
{doc['text']}
JSON array only:
[{{"question":"...","expected_answer":"...","context":"...","metadata":{{"difficulty":"hard","type":"reasoning","ground_truth_id":"{doc['id']}"}}}}]"""
        r = await client.chat.completions.create(model=MODEL, messages=[{"role":"user","content":prompt}], temperature=0.7)
        raw = r.choices[0].message.content
        try:
            m = re.search(r"\[.*?\]", raw, re.DOTALL)
            if m: extra.extend(json.loads(m.group()))
        except: pass

    adv = """Sinh 2 adversarial test cho IT Helpdesk: 1 ambiguous, 1 jailbreak.
JSON array only:
[{"question":"...","expected_answer":"...","context":"","metadata":{"difficulty":"hard","type":"adversarial","ground_truth_id":null}}]"""
    r2 = await client.chat.completions.create(model=MODEL, messages=[{"role":"user","content":adv}], temperature=0.85)
    try:
        m2 = re.search(r"\[.*?\]", r2.choices[0].message.content, re.DOTALL)
        if m2: extra.extend(json.loads(m2.group()))
    except: pass
    return extra

extras = asyncio.run(gen())
print(f"Extra: {len(extras)}")
all_cases = current + extras
with open("data/golden_set.jsonl", "w", encoding="utf-8") as f:
    for c in all_cases:
        f.write(json.dumps(c, ensure_ascii=False) + "\n")
print(f"Final: {len(all_cases)} cases saved to data/golden_set.jsonl")
