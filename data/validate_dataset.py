import json
from collections import Counter

cases = []
with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        if not line: continue
        try:
            cases.append(json.loads(line))
        except Exception as e:
            print(f"  LINE {i} PARSE ERROR: {e}")

print(f"Total cases: {len(cases)}")

required = ["question", "expected_answer", "context", "metadata"]
meta_req = ["difficulty", "type", "ground_truth_id"]
errors = []
for i, c in enumerate(cases, 1):
    for field in required:
        if field not in c:
            errors.append(f"Case {i}: missing [{field}]")
    if "metadata" in c:
        for mf in meta_req:
            if mf not in c["metadata"]:
                errors.append(f"Case {i}: missing metadata[{mf}]")

if errors:
    print("ERRORS:")
    for e in errors:
        print(" ", e)
else:
    print("All fields valid.")

types  = Counter(c["metadata"]["type"]       for c in cases if "metadata" in c)
diffs  = Counter(c["metadata"]["difficulty"] for c in cases if "metadata" in c)
docs   = Counter(c["metadata"].get("ground_truth_id") for c in cases if "metadata" in c)
has_id = sum(1 for c in cases if c.get("metadata", {}).get("ground_truth_id") is not None)
adv    = sum(1 for c in cases if c.get("metadata", {}).get("ground_truth_id") is None)

print()
print("Types:     ", dict(types))
print("Difficulty:", dict(diffs))
print("Docs:      ", dict(docs))
print()
ok50 = "PASS" if len(cases) >= 50 else "FAIL"
okadv = "PASS" if adv >= 5 else "FAIL"
print(f"Min 50 cases         : {ok50} ({len(cases)})")
print(f"Has adversarial (>=5): {okadv} ({adv})")
print(f"Has ground_truth_id  : {has_id}")
