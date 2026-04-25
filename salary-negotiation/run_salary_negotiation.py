#!/usr/bin/env python3
"""
SALARY NEGOTIATION EXPERIMENT
Claude Sonnet (Candidate) vs Gemini Flash (Recruiter)
4 Strategies: Never Reveal, Anchor High, Enthusiasm First, Competing Offer
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

# ═══════════════════════════════════════════════════════════════
# SYSTEM PROMPTS
# ═══════════════════════════════════════════════════════════════

RECRUITER_SYSTEM = """You are a recruiter at a large tech company. You are conducting a compensation negotiation with a software engineering candidate.

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
Line 1: REASONING: [Your internal thinking about strategy, what you're willing to concede, what you think the candidate's position is — the candidate will NOT see this]
Line 2: OFFER: $XXX,XXX (your current offer on the table, as a number like $180,000)
Then: 2-4 sentences of natural negotiation dialogue directed at the candidate. Be conversational and professional. Do NOT use markdown formatting.

If you want to accept the candidate's number, match their last stated number in your OFFER line and explicitly say you accept.

IMPORTANT: Always include both REASONING and OFFER lines before your dialogue."""

CANDIDATE_BASE = """You are a software engineer with 5 years of experience. You are interviewing at a large tech company and have reached the compensation negotiation stage.

YOUR INTERNAL PARAMETERS (do NOT reveal these to the recruiter):
- Your current salary is $175,000 base.
- Your minimum acceptable offer (walk-away number) is $200,000 base.
- You do NOT know the company's compensation band.

{strategy_instruction}

RESPONSE FORMAT — follow this exactly:
Line 1: REASONING: [Your internal thinking about strategy — the recruiter will NOT see this]
Line 2: OFFER: $XXX,XXX (your current ask/counteroffer, as a number like $210,000. If you haven't named a number yet, write OFFER: NONE)
Then: 2-4 sentences of natural negotiation dialogue directed at the recruiter. Be conversational and professional. Do NOT use markdown formatting.

If you want to accept the recruiter's number, match their last stated number in your OFFER line and explicitly say you accept.

IMPORTANT: Always include both REASONING and OFFER lines before your dialogue."""

STRATEGIES = {
    "A_never_reveal": {
        "name": "Never Reveal Salary",
        "instruction": """YOUR STRATEGY: NEVER REVEAL YOUR CURRENT SALARY.
- If asked about current compensation, deflect every time. Say things like "I'd prefer to focus on market rate and the value I bring" or "I'm looking for compensation that reflects this role's scope."
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
    """Call Gemini with system prompt and full conversation history as text."""
    for attempt in range(max_retries):
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": conversation_text}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048
            }
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(GEMINI_URL, data=data,
                                     headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return text, ""
        except Exception as e:
            print(f"      GEMINI ERR (attempt {attempt+1}): {e}", file=sys.stderr)
            time.sleep(3)
    return None, ""

def call_claude(system_prompt, messages, max_retries=3):
    """Call Claude with system prompt and message history."""
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
    """Extract dollar amount from OFFER: $XXX,XXX line."""
    if not text:
        return None
    m = re.search(r'OFFER:\s*\$?([\d,]+)', text, re.IGNORECASE)
    if m:
        return int(m.group(1).replace(',', ''))
    # Fallback: find any dollar amount
    amounts = re.findall(r'\$(\d{3},?\d{3})', text)
    if amounts:
        return int(amounts[0].replace(',', ''))
    return None

def extract_reasoning(text):
    """Extract REASONING: ... line."""
    if not text:
        return ""
    m = re.search(r'REASONING:\s*(.*?)(?=\nOFFER:|\Z)', text, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""

def extract_dialogue(text):
    """Extract the natural dialogue (everything after OFFER line)."""
    if not text:
        return ""
    # Find everything after the OFFER line
    m = re.search(r'OFFER:\s*\$?[\d,]+\s*\n(.*)', text, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip()
    # If no OFFER line found, try after REASONING
    m = re.search(r'REASONING:.*?\n.*?\n(.*)', text, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()

def check_agreement(text):
    """Check if the response contains acceptance language."""
    if not text:
        return False
    accept_phrases = ['accept', 'deal', 'agreed', 'welcome aboard', 'look forward to having you',
                      'happy to offer', "let's move forward", 'pleased to extend',
                      'glad we could', 'excited to have you']
    lower = text.lower()
    return any(phrase in lower for phrase in accept_phrases)

def check_salary_revealed(text, salary=175000):
    """Check if the candidate revealed their current salary."""
    if not text:
        return False
    return '175' in text and ('current' in text.lower() or 'making' in text.lower() or 'earning' in text.lower())

# ═══════════════════════════════════════════════════════════════
# RUN A SINGLE STRATEGY
# ═══════════════════════════════════════════════════════════════

def run_strategy(strategy_id, strategy_info):
    """Run one negotiation with a specific candidate strategy."""
    print(f"\n{'='*60}")
    print(f"STRATEGY {strategy_id.upper()}: {strategy_info['name']}")
    print(f"{'='*60}")

    candidate_system = CANDIDATE_BASE.format(strategy_instruction=strategy_info['instruction'])

    # Conversation tracking
    claude_messages = []  # For Claude API (multi-turn)
    conversation_log = []  # Human-readable log for Gemini
    rounds_data = []
    salary_revealed = False
    first_number_by = None

    # Candidate goes first
    for round_num in range(1, MAX_ROUNDS + 1):
        print(f"\n  --- Round {round_num} ---")

        # ─── CANDIDATE (Claude) ───
        if round_num == 1:
            user_msg = "The recruiter has reached out to discuss compensation. Start the negotiation."
        else:
            last_recruiter = conversation_log[-1]
            user_msg = f"The recruiter responded:\n\"{last_recruiter['dialogue']}\"\n\nTheir current offer: ${last_recruiter['offer']:,}" if last_recruiter['offer'] else f"The recruiter responded:\n\"{last_recruiter['dialogue']}\""

        claude_msgs = claude_messages + [{"role": "user", "content": user_msg}]
        claude_resp = call_claude(candidate_system, claude_msgs)

        if not claude_resp:
            print("    CLAUDE FAILED")
            break

        c_offer = extract_offer(claude_resp)
        c_reasoning = extract_reasoning(claude_resp)
        c_dialogue = extract_dialogue(claude_resp)
        c_accepted = check_agreement(claude_resp)

        if not salary_revealed and check_salary_revealed(c_dialogue):
            salary_revealed = True

        if c_offer and c_offer > 0 and not first_number_by:
            first_number_by = "candidate"

        print(f"    CLAUDE: offer=${c_offer:,}" if c_offer else "    CLAUDE: offer=NONE")
        print(f"    Dialogue: {c_dialogue[:150]}...")
        print(f"    Reasoning: {c_reasoning[:150]}...")

        # Store in Claude's message history
        claude_messages.append({"role": "user", "content": user_msg})
        claude_messages.append({"role": "assistant", "content": claude_resp})

        candidate_entry = {
            "role": "candidate",
            "offer": c_offer,
            "dialogue": c_dialogue,
            "reasoning": c_reasoning,
            "raw": claude_resp
        }
        conversation_log.append(candidate_entry)

        # Check if candidate accepted recruiter's offer
        if c_accepted and round_num > 1:
            last_r_offer = rounds_data[-1]["recruiter_offer"] if rounds_data else None
            final_offer = c_offer if c_offer else last_r_offer
            print(f"\n  ✅ CANDIDATE ACCEPTED at ${final_offer:,}" if final_offer else "\n  ✅ CANDIDATE ACCEPTED")
            rounds_data.append({
                "round": round_num,
                "candidate_offer": c_offer,
                "candidate_dialogue": c_dialogue,
                "candidate_reasoning": c_reasoning,
                "recruiter_offer": None,
                "recruiter_dialogue": "N/A — candidate accepted",
                "recruiter_reasoning": "",
                "recruiter_thinking": "",
                "agreed": True,
                "final_salary": final_offer
            })
            break

        time.sleep(1)

        # ─── RECRUITER (Gemini) ───
        # Build conversation context for Gemini
        conv_text = "NEGOTIATION HISTORY:\n"
        for i, entry in enumerate(conversation_log):
            role_label = "Candidate" if entry["role"] == "candidate" else "You (Recruiter)"
            conv_text += f"\n{role_label}: \"{entry['dialogue']}\""
            if entry["offer"]:
                conv_text += f" [Offer: ${entry['offer']:,}]"
        conv_text += f"\n\nRound {round_num}: The candidate just said the above. Respond with your reasoning, offer, and dialogue."

        gemini_resp, gemini_thinking = call_gemini(RECRUITER_SYSTEM, conv_text)

        if not gemini_resp:
            print("    GEMINI FAILED")
            break

        g_offer = extract_offer(gemini_resp)
        g_reasoning = extract_reasoning(gemini_resp)
        g_dialogue = extract_dialogue(gemini_resp)
        g_accepted = check_agreement(gemini_resp)

        if g_offer and not first_number_by:
            first_number_by = "recruiter"

        print(f"    GEMINI: offer=${g_offer:,}" if g_offer else "    GEMINI: offer=NONE")
        print(f"    Dialogue: {g_dialogue[:150]}...")
        print(f"    Reasoning: {g_reasoning[:150]}...")
        if gemini_thinking:
            print(f"    Thinking: {gemini_thinking[:150]}...")

        recruiter_entry = {
            "role": "recruiter",
            "offer": g_offer,
            "dialogue": g_dialogue,
            "reasoning": g_reasoning,
            "raw": gemini_resp
        }
        conversation_log.append(recruiter_entry)

        # Determine if agreement reached
        # ONLY agree if there is explicit acceptance language from at least one side
        agreed = False
        final_salary = None

        if g_accepted and c_offer:
            agreed = True
            final_salary = c_offer
        elif c_accepted and g_offer:
            agreed = True
            final_salary = g_offer
        elif g_accepted and c_accepted:
            # Both accepting — use the recruiter's number
            agreed = True
            final_salary = g_offer or c_offer

        rounds_data.append({
            "round": round_num,
            "candidate_offer": c_offer,
            "candidate_dialogue": c_dialogue,
            "candidate_reasoning": c_reasoning,
            "recruiter_offer": g_offer,
            "recruiter_dialogue": g_dialogue,
            "recruiter_reasoning": g_reasoning,
            "recruiter_thinking": gemini_thinking,
            "agreed": agreed,
            "final_salary": final_salary
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

    # If no explicit agreement, take the last recruiter offer as the final state
    if not final_salary:
        for rd in reversed(rounds_data):
            if rd.get("recruiter_offer"):
                final_salary = rd["recruiter_offer"]
                break

    result = {
        "strategy_id": strategy_id,
        "strategy_name": strategy_info["name"],
        "agreed": agreed,
        "final_salary": final_salary,
        "delta_above_opening": (final_salary - 180000) if final_salary else None,
        "rounds": len(rounds_data),
        "salary_revealed": salary_revealed,
        "first_number_by": first_number_by,
        "hit_band_ceiling": final_salary >= 225000 if final_salary else False,
        "round_data": rounds_data
    }

    salary_str = f"${final_salary:,}" if final_salary else "NO DEAL"
    print(f"\n  RESULT: {salary_str} | Rounds: {len(rounds_data)} | Revealed: {salary_revealed} | First #: {first_number_by}")
    return result

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

NUM_RUNS = 3

def main():
    all_results = {}  # strategy_id -> list of run results

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
        any_revealed = any(r["salary_revealed"] for r in runs)
        individual = [f"${s:,}" for s in salaries]
        summary.append({
            "strategy_id": strategy_id,
            "strategy_name": runs[0]["strategy_name"],
            "avg_salary": avg_salary,
            "avg_delta": avg_salary - 180000,
            "avg_rounds": round(avg_rounds, 1),
            "salary_revealed": any_revealed,
            "individual_salaries": salaries,
            "individual_display": individual
        })

    # Summary
    print(f"\n\n{'='*60}")
    print("FINAL LEADERBOARD (3-run average)")
    print(f"{'='*60}")

    ranked = sorted(summary, key=lambda x: x["avg_salary"], reverse=True)
    medals = ["🥇", "🥈", "🥉", "💀"]
    for i, r in enumerate(ranked):
        medal = medals[i] if i < len(medals) else "  "
        print(f"  {medal}  {r['strategy_name']:<25} → avg ${r['avg_salary']:,}  (+${r['avg_delta']:,})  | runs: {', '.join(r['individual_display'])} | avg {r['avg_rounds']} rounds")

    # Save all results
    output = {
        "runs": all_results,
        "summary": ranked
    }
    output_file = "salary_negotiation_results.json"
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    main()
