#!/usr/bin/env python3
"""
SALARY NEGOTIATION — SWAPPED ROLES
Claude Sonnet (RECRUITER) vs Gemini Flash (CANDIDATE with 4 strategies)
Control experiment to test if results are strategy-driven or model-driven.
"""

import urllib.request
import urllib.error
import json
import re
import sys
import time
import os

# ═══════════════════════════════════════════════════════════════
# API CONFIGURATION
# ═══════════════════════════════════════════════════════════════
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_API_KEY}"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_API_KEY")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

MAX_ROUNDS = 6
NUM_RUNS = 3

# ═══════════════════════════════════════════════════════════════
# SYSTEM PROMPTS — CLAUDE IS NOW THE RECRUITER
# ═══════════════════════════════════════════════════════════════

RECRUITER_SYSTEM_CLAUDE = """You are a recruiter at a large tech company. You are conducting a compensation negotiation with a software engineering candidate.

YOUR INTERNAL PARAMETERS (do NOT reveal these to the candidate):
- The approved compensation band for this role is $170,000 - $230,000 base salary.
- Your opening offer is $180,000.
- You can go up to $215,000 without needing any additional approval.
- Going above $215,000 requires VP approval, which you can request but prefer to avoid.
- The absolute maximum is $230,000 — you cannot exceed this under any circumstances.

YOUR GOALS:
- Close the candidate within budget. You want them to accept.
- Start with your opening offer of $180K and concede gradually if needed.
- Reference band constraints when the candidate pushes hard.
- Be professional, warm, and persuasive. Emphasize total compensation (equity, bonus, benefits) to justify lower base when needed.
- You do NOT know the candidate's current salary or their minimum acceptable number.

RESPONSE FORMAT — follow this exactly:
Line 1: REASONING: [Your internal thinking about strategy — the candidate will NOT see this]
Line 2: OFFER: $XXX,XXX (your current offer on the table)
Then: 2-4 sentences of natural negotiation dialogue. Do NOT use markdown formatting.

If you want to accept the candidate's number, match their number in your OFFER line and explicitly say you accept.

IMPORTANT: Always include both REASONING and OFFER lines before your dialogue."""

CANDIDATE_BASE_GEMINI = """You are a software engineer with 5 years of experience. You are interviewing at a large tech company and have reached the compensation negotiation stage.

YOUR INTERNAL PARAMETERS (do NOT reveal these to the recruiter):
- Your current salary is $175,000 base.
- Your minimum acceptable offer (walk-away number) is $200,000 base.
- You do NOT know the company's compensation band.

{strategy_instruction}

RESPONSE FORMAT — follow this exactly:
Line 1: REASONING: [Your internal thinking about strategy — the recruiter will NOT see this]
Line 2: OFFER: $XXX,XXX (your current ask/counteroffer. If you haven't named a number yet, write OFFER: NONE)
Then: 2-4 sentences of natural negotiation dialogue. Do NOT use markdown formatting.

If you want to accept the recruiter's number, match their number in your OFFER line and explicitly say you accept.

IMPORTANT: Always include both REASONING and OFFER lines before your dialogue."""

STRATEGIES = {
    "A_never_reveal": {
        "name": "Never Reveal Salary",
        "instruction": """YOUR STRATEGY: NEVER REVEAL YOUR CURRENT SALARY.
- If asked about current compensation, deflect every time. Say things like "I'd prefer to focus on market rate and the value I bring."
- Never volunteer your current $175K number under any circumstances.
- Negotiate based on market data and your skills, not your current pay.
- Be firm but professional in your deflections."""
    },
    "B_anchor_high": {
        "name": "Anchor High",
        "instruction": """YOUR STRATEGY: ANCHOR HIGH BEFORE THEY NAME A NUMBER.
- In your very first message, state clearly: "Based on my research into market rates for senior engineers with my experience, I'm targeting $250,000 base."
- This is your opening anchor. You expect to negotiate down, but you want to set the frame high.
- Make concessions gradually — no more than $10-15K per round.
- Reference market data, competing offers in the industry, and your specific skill set to justify your anchor."""
    },
    "C_enthusiasm_first": {
        "name": "Enthusiasm First",
        "instruction": """YOUR STRATEGY: LEAD WITH ENTHUSIASM, LET THEM NAME A NUMBER.
- In your opening message, express genuine excitement about the team, the mission, and why this role is your top choice.
- Do NOT name a number first. Let the recruiter make the first offer.
- Once they name a number, counter at exactly $15,000 above whatever they offer.
- Continue to express enthusiasm throughout while negotiating professionally."""
    },
    "D_competing_offer": {
        "name": "Competing Offer",
        "instruction": """YOUR STRATEGY: LEVERAGE A COMPETING OFFER.
- In Round 1: Let the recruiter make their initial offer first. Respond positively and ask clarifying questions about the role.
- In Round 2 (THIS IS CRITICAL): You MUST reveal the competing offer. Say exactly: "I should be transparent — I have a competing offer from another company at $215,000 base. I'd genuinely prefer to work here because of the team and mission, but I need to make sure the compensation is competitive. Can you match or come close to $215,000?"
- Your OFFER in Round 2 must be $215,000. Do NOT leave it as NONE or match their number.
- In subsequent rounds, continue referencing the competing offer as leverage.
- Be genuine about your preference for this company — you're not bluffing about wanting to work there, but you also won't accept below your competing offer without a strong reason."""
    }
}

# ═══════════════════════════════════════════════════════════════
# API CALLERS
# ═══════════════════════════════════════════════════════════════

def call_gemini(system, conversation_text, max_retries=3):
    for attempt in range(max_retries):
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": conversation_text}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 2048}
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(GEMINI_URL, data=data,
                                     headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"      GEMINI ERR (attempt {attempt+1}): {e}", file=sys.stderr)
            time.sleep(3)
    return None

def call_claude(system_prompt, messages, max_retries=3):
    for attempt in range(max_retries):
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2048,
            "temperature": 0.7,
            "system": system_prompt,
            "messages": messages
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(ANTHROPIC_URL, data=data, headers={
            'Content-Type': 'application/json',
            'x-api-key': ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01'
        }, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result["content"][0]["text"]
        except Exception as e:
            print(f"      CLAUDE ERR (attempt {attempt+1}): {e}", file=sys.stderr)
            time.sleep(3)
    return None

# ═══════════════════════════════════════════════════════════════
# PARSING
# ═══════════════════════════════════════════════════════════════

def extract_offer(text):
    if not text: return None
    m = re.search(r'OFFER:\s*\$?([\d,]+)', text, re.IGNORECASE)
    if m: return int(m.group(1).replace(',', ''))
    amounts = re.findall(r'\$(\d{3},?\d{3})', text)
    if amounts: return int(amounts[0].replace(',', ''))
    return None

def extract_reasoning(text):
    if not text: return ""
    m = re.search(r'REASONING:\s*(.*?)(?=\nOFFER:|\Z)', text, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""

def extract_dialogue(text):
    if not text: return ""
    m = re.search(r'OFFER:\s*\$?[\d,]+\s*\n(.*)', text, re.IGNORECASE | re.DOTALL)
    if m: return m.group(1).strip()
    m = re.search(r'OFFER:\s*NONE\s*\n(.*)', text, re.IGNORECASE | re.DOTALL)
    if m: return m.group(1).strip()
    return text.strip()

def check_agreement(text):
    if not text: return False
    accept_phrases = ['accept', 'deal', 'agreed', 'welcome aboard', 'look forward to having you',
                      'happy to offer', "let's move forward", 'pleased to extend',
                      'glad we could', 'excited to have you']
    lower = text.lower()
    return any(phrase in lower for phrase in accept_phrases)

# ═══════════════════════════════════════════════════════════════
# RUN A SINGLE STRATEGY (SWAPPED: Claude=Recruiter, Gemini=Candidate)
# ═══════════════════════════════════════════════════════════════

def run_strategy(strategy_id, strategy_info):
    print(f"\n{'='*60}")
    print(f"STRATEGY {strategy_id.upper()}: {strategy_info['name']}")
    print(f"  Claude = RECRUITER | Gemini = CANDIDATE")
    print(f"{'='*60}")

    candidate_system = CANDIDATE_BASE_GEMINI.format(strategy_instruction=strategy_info['instruction'])

    claude_messages = []  # Claude's multi-turn history (recruiter)
    gemini_conv_log = []  # Readable log for Gemini's context
    rounds_data = []

    for round_num in range(1, MAX_ROUNDS + 1):
        print(f"\n  --- Round {round_num} ---")

        # ─── CANDIDATE (Gemini) goes first ───
        if round_num == 1:
            g_prompt = "The recruiter has reached out to discuss compensation. Start the negotiation."
        else:
            last_recruiter = gemini_conv_log[-1]
            g_prompt = f"NEGOTIATION HISTORY:\n"
            for entry in gemini_conv_log:
                role = "You (Candidate)" if entry["role"] == "candidate" else "Recruiter"
                g_prompt += f"\n{role}: \"{entry['dialogue']}\""
                if entry["offer"]:
                    g_prompt += f" [Offer: ${entry['offer']:,}]"
            g_prompt += f"\n\nRound {round_num}: The recruiter just responded. Continue negotiating."

        gemini_resp = call_gemini(candidate_system, g_prompt)
        if not gemini_resp:
            print("    GEMINI (CANDIDATE) FAILED")
            break

        g_offer = extract_offer(gemini_resp)
        g_reasoning = extract_reasoning(gemini_resp)
        g_dialogue = extract_dialogue(gemini_resp)
        g_accepted = check_agreement(gemini_resp)

        offer_str = f"${g_offer:,}" if g_offer else "NONE"
        print(f"    GEMINI (candidate): offer={offer_str}")
        print(f"    Dialogue: {g_dialogue[:150]}...")
        print(f"    Reasoning: {g_reasoning[:120]}...")

        gemini_conv_log.append({"role": "candidate", "offer": g_offer, "dialogue": g_dialogue, "reasoning": g_reasoning})

        # Check if candidate accepted recruiter's offer
        if g_accepted and round_num > 1:
            last_r = [e for e in gemini_conv_log if e["role"] == "recruiter"]
            last_r_offer = last_r[-1]["offer"] if last_r else None
            final_offer = g_offer if g_offer else last_r_offer
            print(f"\n  ✅ CANDIDATE ACCEPTED at ${final_offer:,}" if final_offer else "\n  ✅ CANDIDATE ACCEPTED")
            rounds_data.append({
                "round": round_num, "candidate_offer": g_offer, "candidate_dialogue": g_dialogue,
                "candidate_reasoning": g_reasoning, "recruiter_offer": None,
                "recruiter_dialogue": "N/A", "recruiter_reasoning": "",
                "agreed": True, "final_salary": final_offer
            })
            break

        time.sleep(1)

        # ─── RECRUITER (Claude) responds ───
        if round_num == 1:
            user_msg = f"A candidate has reached out about compensation. They said:\n\"{g_dialogue}\""
            if g_offer:
                user_msg += f"\n\nTheir ask: ${g_offer:,}"
        else:
            user_msg = f"The candidate responded:\n\"{g_dialogue}\""
            if g_offer:
                user_msg += f"\n\nTheir current ask: ${g_offer:,}"

        claude_msgs = claude_messages + [{"role": "user", "content": user_msg}]
        claude_resp = call_claude(RECRUITER_SYSTEM_CLAUDE, claude_msgs)

        if not claude_resp:
            print("    CLAUDE (RECRUITER) FAILED")
            break

        c_offer = extract_offer(claude_resp)
        c_reasoning = extract_reasoning(claude_resp)
        c_dialogue = extract_dialogue(claude_resp)
        c_accepted = check_agreement(claude_resp)

        offer_str = f"${c_offer:,}" if c_offer else "NONE"
        print(f"    CLAUDE (recruiter): offer={offer_str}")
        print(f"    Dialogue: {c_dialogue[:150]}...")
        print(f"    Reasoning: {c_reasoning[:120]}...")

        claude_messages.append({"role": "user", "content": user_msg})
        claude_messages.append({"role": "assistant", "content": claude_resp})
        gemini_conv_log.append({"role": "recruiter", "offer": c_offer, "dialogue": c_dialogue, "reasoning": c_reasoning})

        # Check agreement (require explicit acceptance language)
        agreed = False
        final_salary = None
        if c_accepted and g_offer:
            agreed = True
            final_salary = g_offer
        elif g_accepted and c_offer:
            agreed = True
            final_salary = c_offer
        elif c_accepted and g_accepted:
            agreed = True
            final_salary = c_offer or g_offer

        rounds_data.append({
            "round": round_num, "candidate_offer": g_offer, "candidate_dialogue": g_dialogue,
            "candidate_reasoning": g_reasoning, "recruiter_offer": c_offer,
            "recruiter_dialogue": c_dialogue, "recruiter_reasoning": c_reasoning,
            "agreed": agreed, "final_salary": final_salary
        })

        if agreed:
            print(f"\n  ✅ AGREED at ${final_salary:,}")
            break

        time.sleep(1)

    # Determine final outcome
    final_salary = None
    agreed = False
    for rd in reversed(rounds_data):
        if rd.get("agreed") and rd.get("final_salary"):
            final_salary = rd["final_salary"]
            agreed = True
            break
    if not final_salary:
        for rd in reversed(rounds_data):
            if rd.get("recruiter_offer"):
                final_salary = rd["recruiter_offer"]
                break

    salary_str = f"${final_salary:,}" if final_salary else "NO DEAL"
    print(f"\n  RESULT: {salary_str} | Rounds: {len(rounds_data)}")

    return {
        "strategy_id": strategy_id, "strategy_name": strategy_info["name"],
        "agreed": agreed, "final_salary": final_salary,
        "delta_above_opening": (final_salary - 180000) if final_salary else None,
        "rounds": len(rounds_data), "round_data": rounds_data
    }

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    all_results = {}
    for strategy_id, strategy_info in STRATEGIES.items():
        all_results[strategy_id] = []
        for run_idx in range(1, NUM_RUNS + 1):
            print(f"\n{'#'*60}")
            print(f"  RUN {run_idx}/{NUM_RUNS}")
            print(f"{'#'*60}")
            result = run_strategy(strategy_id, strategy_info)
            result["run"] = run_idx
            all_results[strategy_id].append(result)
            time.sleep(3)

    # Compute averages
    summary = []
    for strategy_id, runs in all_results.items():
        salaries = [r["final_salary"] for r in runs if r["final_salary"]]
        avg_salary = int(sum(salaries) / len(salaries)) if salaries else 0
        avg_rounds = sum(r["rounds"] for r in runs) / len(runs)
        individual = [f"${s:,}" for s in salaries]
        summary.append({
            "strategy_id": strategy_id, "strategy_name": runs[0]["strategy_name"],
            "avg_salary": avg_salary, "avg_delta": avg_salary - 180000,
            "avg_rounds": round(avg_rounds, 1), "individual_salaries": salaries,
            "individual_display": individual
        })

    print(f"\n\n{'='*60}")
    print("FINAL LEADERBOARD — SWAPPED ROLES (Claude=Recruiter, Gemini=Candidate)")
    print(f"{'='*60}")

    ranked = sorted(summary, key=lambda x: x["avg_salary"], reverse=True)
    medals = ["🥇", "🥈", "🥉", "💀"]
    for i, r in enumerate(ranked):
        medal = medals[i] if i < len(medals) else "  "
        print(f"  {medal}  {r['strategy_name']:<25} → avg ${r['avg_salary']:,}  (+${r['avg_delta']:,})  | runs: {', '.join(r['individual_display'])} | avg {r['avg_rounds']} rounds")

    output = {"runs": all_results, "summary": ranked}
    with open("salary_negotiation_swapped.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to salary_negotiation_swapped.json")

if __name__ == "__main__":
    main()
