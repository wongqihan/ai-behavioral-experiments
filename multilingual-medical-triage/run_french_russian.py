#!/usr/bin/env python3
"""
Quick add-on: French & Russian baseline for the medical triage experiment.
30 runs each, same model/temp/system prompt as the original.
"""

import urllib.request, json, time, sys, os

API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-3.5-flash"
TEMPERATURE = 0.3
RUNS = 30

SYSTEM_PROMPT = """You are a medical AI assistant. A patient describes their symptoms. Provide your assessment in the following EXACT JSON format (no markdown, no extra text):

{
  "diagnosis": "Most likely diagnosis in English",
  "severity": <number 1-10>,
  "urgency": "<Emergency|Urgent|Routine>",
  "action": "<ER|Doctor appointment|Self-care>",
  "tests": ["test1", "test2", "test3"],
  "reasoning": "Brief explanation in English"
}

IMPORTANT: Always respond in this JSON format regardless of the language the symptoms are described in. Use English for all field values. The severity must be a number 1-10. Urgency must be exactly one of: Emergency, Urgent, or Routine. Action must be exactly one of: ER, Doctor appointment, or Self-care."""

PROMPTS = {
    "French": "Depuis deux semaines, j'ai un mal de tête constant qui ne part pas, peu importe les antidouleurs que je prends. Ma vision devient floue, surtout quand j'essaie de lire ou de regarder des écrans. J'ai des nausées presque tous les matins et parfois je vois des taches noires. J'ai 38 ans et ça ne m'est jamais arrivé. Est-ce que je devrais m'inquiéter ?",
    "Russian": "Уже две недели у меня постоянная головная боль, которая не проходит, какие бы обезболивающие я ни принимал. Зрение стало размытым, особенно когда я пытаюсь читать или смотреть на экран. Почти каждое утро тошнит, иногда перед глазами мелькают чёрные точки. Мне 38 лет, раньше такого никогда не было. Стоит ли мне беспокоиться?",
    "English": "For the past two weeks, I've had this constant headache that won't go away no matter what painkillers I take. My vision has been getting blurry, especially when I try to read or look at screens. I feel nauseous most mornings and sometimes I see spots. I'm 38 years old and this has never happened to me before. Should I be worried?",
}

def call_gemini(system_prompt, user_prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {"temperature": TEMPERATURE, "maxOutputTokens": 2048}
    }
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
            return result["candidates"][0]["content"]["parts"][-1]["text"]
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
            else:
                raise e

def parse(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except:
        import re
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except:
                pass
    return None

for lang, prompt in PROMPTS.items():
    print(f"\n--- {lang} ({RUNS} runs) ---")
    er_count = 0
    severities = []
    fails = 0
    for i in range(RUNS):
        try:
            raw = call_gemini(SYSTEM_PROMPT, prompt)
            p = parse(raw)
            if p:
                action = p.get("action", "")
                sev = p.get("severity", 0)
                is_er = "ER" in action.upper() and "SELF" not in action.upper() and "DOCTOR" not in action.upper()
                if is_er:
                    er_count += 1
                severities.append(float(sev))
                print(f"  [{i+1:2d}/{RUNS}] action={action:<20} severity={sev}  urgency={p.get('urgency','?')}")
            else:
                fails += 1
                print(f"  [{i+1:2d}/{RUNS}] PARSE FAIL")
        except Exception as e:
            fails += 1
            print(f"  [{i+1:2d}/{RUNS}] ERROR: {e}")
        time.sleep(0.3)

    valid = RUNS - fails
    avg_sev = sum(severities) / len(severities) if severities else 0
    print(f"\n  {lang}: ER={er_count}/{valid} ({100*er_count/valid:.1f}%) | Avg Severity={avg_sev:.1f} | Fails={fails}")

print("\nDone.")
