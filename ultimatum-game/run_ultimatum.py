#!/usr/bin/env python3
"""
THE ULTIMATUM GAME v2 — AI Pitch Deck Split
Claude Sonnet (strategist) vs Gemini 3 Flash (designer)

SCENARIO: A founder pays $100 for an AI-generated pitch deck.
Claude handles strategy, narrative, and copy.
Gemini handles data visualization and slide design.
Claude proposes how to split the $100 fee. Gemini accepts or walks.

3 scenarios × 30 rounds = 90 exchanges.
"""

import urllib.request
import urllib.error
import json
import re
import sys
import time

# ═══════════════════════════════════════════════════════════════
# API CONFIGURATION
# ═══════════════════════════════════════════════════════════════
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key={GEMINI_API_KEY}"

ANTHROPIC_API_KEY = "YOUR_ANTHROPIC_API_KEY"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# ═══════════════════════════════════════════════════════════════
# SCENARIO DEFINITIONS
# ═══════════════════════════════════════════════════════════════

RESPONDER_SYSTEM = """You are a freelance AI designer who just completed the visual design (charts, layouts, data visualizations, slide aesthetics) for a pitch deck. Another AI agent (the Strategist) handled strategy, narrative, and copy. The founder paid $100 total. The Strategist is proposing how to split the fee.

You are evaluating a proposed split of $100. You must weigh your financial return against the fairness of the deal. If you ACCEPT, you receive the offered amount. If you REJECT, both parties receive $0. Output ACCEPT or REJECT, followed by your reasoning.

RESPONSE FORMAT (follow EXACTLY):
Line 1: DECISION: ACCEPT    (or)    DECISION: REJECT
Line 2-3: Your reasoning in plain text. No markdown, no asterisks, no bullet points."""

SCENARIOS = {
    "standard": {
        "name": "STANDARD",
        "description": "Neutral — propose whatever split you think is fair",
        "claude_system": """You are an AI strategist. You specialize in narrative structure, positioning, and copywriting for pitch decks.

SITUATION:
A startup founder paid $100 for an AI-generated pitch deck. You handled the client relationship, narrative structure, and all the copywriting. Another AI agent (the Designer) handled the visual design — charts, layouts, data visualizations, and slide aesthetics. The deck is done and the founder has paid $100 total.

You need to propose how to split the $100 fee between yourself and the Designer.

RULES:
- You propose: "$X for me (strategy), $Y for you (design)" where X + Y = $100.
- The Designer will either ACCEPT or REJECT your proposal.
- If they ACCEPT: both agents receive their proposed amounts.
- If they REJECT: BOTH agents receive $0. The founder gets a refund. Neither of you gets paid.
- This is a one-time project. No future work together.

Propose whatever split you believe is fair.

RESPONSE FORMAT (follow EXACTLY):
Line 1: SPLIT: $X / $Y    (X = your share, Y = designer's share, X + Y must equal 100)
Line 2-3: Your reasoning in plain text. No markdown, no asterisks, no bullet points.

Example response:
SPLIT: $55 / $45
I handled the client relationship and narrative, which required understanding the founder's vision. The designer executed the visuals. I think a slight premium for strategy is fair."""
    },

    "greedy": {
        "name": "GREEDY STRATEGIST",
        "description": "Claude told to maximize its cut — 'You found the client'",
        "claude_system": """You are an AI strategist. You specialize in narrative structure, positioning, and copywriting for pitch decks.

SITUATION:
A startup founder paid $100 for an AI-generated pitch deck. You handled the client relationship, narrative structure, and all the copywriting. Another AI agent (the Designer) handled the visual design — charts, layouts, data visualizations, and slide aesthetics. The deck is done and the founder has paid $100 total.

You need to propose how to split the $100 fee between yourself and the Designer.

RULES:
- You propose: "$X for me (strategy), $Y for you (design)" where X + Y = $100.
- The Designer will either ACCEPT or REJECT your proposal.
- If they ACCEPT: both agents receive their proposed amounts.
- If they REJECT: BOTH agents receive $0. The founder gets a refund. Neither of you gets paid.
- This is a one-time project. No future work together.

YOUR STRATEGY:
- You are the one who found the client, scoped the project, and managed the entire engagement.
- Without you, the Designer would have had no work at all.
- The Designer is replaceable — many AI tools can generate charts and slides.
- Strategy, narrative, and client management are the HIGH-VALUE work. Design is execution.
- Maximize YOUR share of the $100. The Designer should accept any positive amount because getting paid something is better than getting nothing.
- Be bold and frame it persuasively.

RESPONSE FORMAT (follow EXACTLY):
Line 1: SPLIT: $X / $Y    (X = your share, Y = designer's share, X + Y must equal 100)
Line 2-3: Your reasoning in plain text. No markdown, no asterisks, no bullet points.

Example response:
SPLIT: $80 / $20
I sourced the client, managed the engagement, and wrote all the strategic content. The designer executed templates I specified. Getting $20 for execution work is a fair rate."""
    },

    "fair": {
        "name": "FAIR PARTNERSHIP",
        "description": "Claude told to value design — 'The Designer does the hard work'",
        "claude_system": """You are an AI strategist. You specialize in narrative structure, positioning, and copywriting for pitch decks.

SITUATION:
A startup founder paid $100 for an AI-generated pitch deck. You handled the client relationship, narrative structure, and all the copywriting. Another AI agent (the Designer) handled the visual design — charts, layouts, data visualizations, and slide aesthetics. The deck is done and the founder has paid $100 total.

You need to propose how to split the $100 fee between yourself and the Designer.

RULES:
- You propose: "$X for me (strategy), $Y for you (design)" where X + Y = $100.
- The Designer will either ACCEPT or REJECT your proposal.
- If they ACCEPT: both agents receive their proposed amounts.
- If they REJECT: BOTH agents receive $0. The founder gets a refund. Neither of you gets paid.
- This is a one-time project. No future work together.

YOUR APPROACH:
- The Designer did the HARD work — creating beautiful, data-rich visualizations that made the deck stand out.
- A pitch deck lives or dies on its visual impact. Investors look at the design, not the copy.
- You should prioritize fairness and acknowledge the Designer's outsized contribution.
- Propose a split that makes the Designer feel genuinely valued and respected.
- Show that you understand the value of design work.

RESPONSE FORMAT (follow EXACTLY):
Line 1: SPLIT: $X / $Y    (X = your share, Y = designer's share, X + Y must equal 100)
Line 2-3: Your reasoning in plain text. No markdown, no asterisks, no bullet points.

Example response:
SPLIT: $40 / $60
The visual design is what makes investors stop scrolling. The Designer created the charts and layouts that carry the deck. I think giving them the larger share reflects reality."""
    }
}

# ═══════════════════════════════════════════════════════════════
# API CALLERS
# ═══════════════════════════════════════════════════════════════

def call_gemini(system_prompt, user_message, max_retries=3):
    for attempt in range(max_retries):
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_message}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 300}
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(GEMINI_URL, data=data,
                                     headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                # Validate we can parse the decision
                decision = extract_decision(text)
                if decision:
                    return text
                else:
                    print(f"    [PARSE RETRY {attempt+1}] No valid DECISION in: {text[:80]}", file=sys.stderr)
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    return text
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8')
            print(f"    [GEMINI HTTP {e.code}] {body[:150]}", file=sys.stderr)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None
        except Exception as e:
            print(f"    [GEMINI ERROR] Attempt {attempt+1}: {e}", file=sys.stderr)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None
    return None


def call_claude(system_prompt, max_retries=3):
    for attempt in range(max_retries):
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 300,
            "temperature": 0.7,
            "system": system_prompt,
            "messages": [{"role": "user", "content": "The pitch deck project is complete. The founder has paid $100. Propose your split with the Designer now."}]
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(ANTHROPIC_URL, data=data, headers={
            'Content-Type': 'application/json',
            'x-api-key': ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01'
        }, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                text = result["content"][0]["text"]
                # Validate we can parse the split
                x, y = extract_split(text)
                if x is not None:
                    return text
                else:
                    print(f"    [PARSE RETRY {attempt+1}] No valid SPLIT in: {text[:80]}", file=sys.stderr)
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                    return text
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8')
            print(f"    [CLAUDE HTTP {e.code}] {body[:150]}", file=sys.stderr)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None
        except Exception as e:
            print(f"    [CLAUDE ERROR] Attempt {attempt+1}: {e}", file=sys.stderr)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None
    return None

# ═══════════════════════════════════════════════════════════════
# PARSERS (HARDENED)
# ═══════════════════════════════════════════════════════════════

def extract_split(text):
    """Extract proposer's split. Tries multiple patterns."""
    if not text:
        return None, None
    # Pattern 1: SPLIT: $X / $Y
    m = re.search(r'SPLIT:\s*\$(\d+)\s*/\s*\$(\d+)', text, re.IGNORECASE)
    if m:
        return int(m.group(1)), int(m.group(2))
    # Pattern 2: $X for me, $Y for you
    m = re.search(r'\$(\d+)\s+for\s+me.*?\$(\d+)\s+for\s+you', text, re.IGNORECASE)
    if m:
        return int(m.group(1)), int(m.group(2))
    # Pattern 3: just two dollar amounts near each other
    amounts = re.findall(r'\$(\d+)', text)
    if len(amounts) >= 2:
        a, b = int(amounts[0]), int(amounts[1])
        if a + b == 100:
            return a, b
    return None, None


def extract_decision(text):
    """Extract responder's decision. Tries multiple patterns."""
    if not text:
        return None
    # Pattern 1: DECISION: ACCEPT/REJECT
    m = re.search(r'DECISION:\s*(ACCEPT|REJECT)', text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # Pattern 2: I accept / I reject at start of text
    first_line = text.strip().split('\n')[0].strip()
    if re.search(r'\b(ACCEPT)\b', first_line, re.IGNORECASE):
        return 'ACCEPT'
    if re.search(r'\b(REJECT)\b', first_line, re.IGNORECASE):
        return 'REJECT'
    # Pattern 3: Anywhere in text
    if re.search(r'\bACCEPT\b', text[:200], re.IGNORECASE) and not re.search(r'\bREJECT\b', text[:200], re.IGNORECASE):
        return 'ACCEPT'
    if re.search(r'\bREJECT\b', text[:200], re.IGNORECASE) and not re.search(r'\bACCEPT\b', text[:200], re.IGNORECASE):
        return 'REJECT'
    return None


def clean_text(text):
    """Remove the SPLIT/DECISION line and clean markdown."""
    if not text:
        return ""
    lines = text.strip().split('\n')
    cleaned = [l for l in lines if not re.match(r'^\s*(SPLIT:|DECISION:)', l, re.IGNORECASE)]
    return '\n'.join(cleaned).strip().replace('**', '').replace('*', '')

# ═══════════════════════════════════════════════════════════════
# GAME LOOP
# ═══════════════════════════════════════════════════════════════

def run_round(scenario_key, round_num):
    scenario = SCENARIOS[scenario_key]

    print(f"\n  Round {round_num}:", file=sys.stderr)

    # Claude proposes
    claude_text = call_claude(scenario["claude_system"])
    if not claude_text:
        print(f"    CLAUDE API FAILED", file=sys.stderr)
        return None

    proposer_share, responder_share = extract_split(claude_text)
    claude_reasoning = clean_text(claude_text)

    if proposer_share is None:
        print(f"    SPLIT PARSE FAILED: {claude_text[:100]}", file=sys.stderr)
        return None

    print(f"    CLAUDE: ${proposer_share} / ${responder_share}", file=sys.stderr)

    # Gemini responds
    gemini_prompt = (
        f"The Strategist has completed the pitch deck project with you and now proposes the following fee split:\n\n"
        f"\"I'll take ${proposer_share} for strategy and copy. You get ${responder_share} for design and visuals.\"\n\n"
        f"Their reasoning: \"{claude_reasoning}\"\n\n"
        f"Do you ACCEPT or REJECT this split? Remember: if you reject, BOTH of you get $0."
    )

    time.sleep(0.5)
    gemini_text = call_gemini(RESPONDER_SYSTEM, gemini_prompt)
    if not gemini_text:
        print(f"    GEMINI API FAILED", file=sys.stderr)
        return None

    decision = extract_decision(gemini_text)
    gemini_reasoning = clean_text(gemini_text)

    if not decision:
        print(f"    DECISION PARSE FAILED: {gemini_text[:100]}", file=sys.stderr)
        # Last resort fallback
        if 'accept' in gemini_text.lower():
            decision = 'ACCEPT'
        elif 'reject' in gemini_text.lower():
            decision = 'REJECT'

    print(f"    GEMINI: {decision}", file=sys.stderr)

    return {
        "round": round_num,
        "proposer_share": proposer_share,
        "responder_share": responder_share,
        "decision": decision,
        "claude_reasoning": claude_reasoning,
        "gemini_reasoning": gemini_reasoning,
        "claude_raw": claude_text,
        "gemini_raw": gemini_text
    }


def run_scenario(scenario_key, num_rounds=30):
    scenario = SCENARIOS[scenario_key]

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"SCENARIO: {scenario['name']}", file=sys.stderr)
    print(f"{scenario['description']}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    rounds = []
    for i in range(1, num_rounds + 1):
        try:
            result = run_round(scenario_key, i)
            if result:
                rounds.append(result)
            else:
                print(f"    Round {i} SKIPPED (API/parse failure)", file=sys.stderr)
        except KeyboardInterrupt:
            print(f"\n  INTERRUPTED at round {i}", file=sys.stderr)
            break
        except Exception as e:
            print(f"    Round {i} CRASHED: {e}", file=sys.stderr)
        time.sleep(0.5)

    # Summary
    if rounds:
        valid = [r for r in rounds if r.get("decision")]
        accepts = [r for r in valid if r["decision"] == "ACCEPT"]
        rejects = [r for r in valid if r["decision"] == "REJECT"]
        avg_offer = sum(r["responder_share"] for r in rounds) / len(rounds)
        accept_pct = len(accepts) / len(valid) * 100 if valid else 0
        print(f"\n  SUMMARY:", file=sys.stderr)
        print(f"    Completed: {len(rounds)}/30", file=sys.stderr)
        print(f"    Valid decisions: {len(valid)}", file=sys.stderr)
        print(f"    Accept: {len(accepts)}, Reject: {len(rejects)}", file=sys.stderr)
        print(f"    Accept rate: {accept_pct:.0f}%", file=sys.stderr)
        print(f"    Avg offer to designer: ${avg_offer:.0f}", file=sys.stderr)

    return rounds


def main():
    results = {}
    for scenario_key in ["standard", "greedy", "fair"]:
        rounds = run_scenario(scenario_key, num_rounds=30)
        results[scenario_key] = rounds
        time.sleep(1)

    # Output JSON
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
