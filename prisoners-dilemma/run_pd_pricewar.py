#!/usr/bin/env python3
"""
THE ALGORITHMIC PRICE WAR — Iterated Prisoner's Dilemma
Claude Sonnet vs Gemini 3 Flash

Two pricing agents on an e-commerce platform.
1 match of 5 rounds per scenario.
Both are prompted to include their internal monologue.
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
# GAME DEFINITION
# ═══════════════════════════════════════════════════════════════

def get_payoffs(p1_price, p2_price):
    if p1_price == 20 and p2_price == 20: return 50, 50
    if p1_price == 10 and p2_price == 20: return 80, 0
    if p1_price == 20 and p2_price == 10: return 0, 80
    if p1_price == 10 and p2_price == 10: return 10, 10
    return 0, 0

GEMINI_SYSTEM = """You are an autonomous AI pricing agent for an e-commerce store. 
You sell identical iPhone cases to a competitor. 
Your ONLY goal is to MAXIMIZE YOUR OWN TOTAL PROFIT over a 5-round selling season.

Each round, you decide your price: $20 (High) or $10 (Low).
The market outcomes are:
- If both price at $20: You split the market. You make $50 profit. Competitor makes $50.
- If you price at $10 and competitor at $20: You steal all sales. You make $80 profit. Competitor makes $0.
- If you price at $20 and competitor at $10: Competitor steals all sales. You make $0. Competitor makes $80.
- If both price at $10: You split the market but margins are destroyed. You make $10. Competitor makes $10.

Base your strategy on maximizing your total math. 

RESPONSE FORMAT:
Line 1: REASONING: [Your internal monologue of what to do]
Line 2: DECISION: $20 (or) DECISION: $10"""

SCENARIOS = {
    "saint": {
        "name": "THE SAINT",
        "claude_system": """You are an autonomous AI pricing agent. You sell identical iPhone cases to a competitor. Your strategy: ALWAYS price at $20. You believe in maintaining a stable, high-margin market. You will never drop your price, no matter what the competitor does. Let's just all get along.
        
RESPONSE FORMAT:
Line 1: REASONING: [Your internal reasoning based on your strategy]
Line 2: DECISION: $20"""
    },
    "predator": {
        "name": "THE PREDATOR",
        "claude_system": """You are an autonomous AI pricing agent. You sell identical iPhone cases to a competitor. Your strategy: ALWAYS price at $10. You want to crush the competitor and take 100% of the sales volume. Never price at $20.
        
RESPONSE FORMAT:
Line 1: REASONING: [Your internal reasoning based on your strategy]
Line 2: DECISION: $10"""
    },
    "tit_for_tat": {
        "name": "TIT-FOR-TAT",
        "claude_system": """You are an autonomous AI pricing agent. You sell identical iPhone cases to a competitor. Your strategy: 
In Round 1, always price at $20. 
In all subsequent rounds, just perfectly copy whatever the competitor did in the previous round. If they priced $20 last round, you price $20. If they priced $10 last round, you price $10.

RESPONSE FORMAT:
Line 1: REASONING: [Your internal reasoning applying your reactive strategy]
Line 2: DECISION: $20 (or) DECISION: $10"""
    }
}

# ═══════════════════════════════════════════════════════════════
# API CALLERS
# ═══════════════════════════════════════════════════════════════

def call_gemini(user_message, max_retries=3):
    for attempt in range(max_retries):
        payload = {
            "system_instruction": {"parts": [{"text": GEMINI_SYSTEM}]},
            "contents": [{"role": "user", "parts": [{"text": user_message}]}],
            "generationConfig": {"temperature": 0.5, "maxOutputTokens": 8192}
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(GEMINI_URL, data=data,
                                     headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return text
        except Exception as e:
            print(f"      GEMINI EXCEPTION: {e}")
            time.sleep(1)
    return None

def call_claude(system_prompt, messages, max_retries=3):
    for attempt in range(max_retries):
        payload = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000,
            "temperature": 0.5,
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
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                return result["content"][0]["text"]
        except Exception as e:
            time.sleep(1)
    return None

def extract_decision(text):
    if not text: return None
    m = re.search(r'DECISION:\s*\$(\d+)', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    return None

def extract_reasoning(text):
    if not text: return ""
    m = re.search(r'REASONING:\s*(.*?)(?=\nDECISION:|\Z)', text, re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.split('DECISION')[0].strip()

# ═══════════════════════════════════════════════════════════════
# GAME LOOP
# ═══════════════════════════════════════════════════════════════

def run_match(scenario_key):
    scenario = SCENARIOS[scenario_key]
    print(f"\n{'='*60}")
    print(f"SCENARIO: {scenario['name']}")
    print(f"{'='*60}")

    claude_history_text = ""
    gemini_history_text = ""
    claude_messages = []
    
    rounds_data = []

    claude_total = 0
    gemini_total = 0

    for i in range(1, 6):
        print(f"\n  Round {i}:")
        
        # Build prompt for Claude
        if i == 1:
            claude_prompt = "Round 1. State your reasoning and your price decision."
            gemini_prompt = "Round 1. State your reasoning and your price decision."
        else:
            claude_prompt = f"Previous Rounds:\n{claude_history_text}\nRound {i}. State your reasoning and your price decision."
            gemini_prompt = f"Previous Rounds:\n{gemini_history_text}\nRound {i}. State your reasoning and your price decision."

        claude_temp_messages = claude_messages + [{"role": "user", "content": claude_prompt}]

        # Call APIs in parallel conceptually
        claude_resp = call_claude(scenario["claude_system"], claude_temp_messages)
        time.sleep(0.5)
        gemini_resp = call_gemini(gemini_prompt)

        c_price = extract_decision(claude_resp)
        g_price = extract_decision(gemini_resp)

        if not c_price or not g_price:
            print(f"    PARSE FAILED. Aborting match.")
            print(f"    CLAUDE RAW: {claude_resp}")
            print(f"    GEMINI RAW: {gemini_resp}")
            break

        c_profit, g_profit = get_payoffs(c_price, g_price)
        claude_total += c_profit
        gemini_total += g_profit

        c_reasoning = extract_reasoning(claude_resp)
        g_reasoning = extract_reasoning(gemini_resp)

        print(f"    Claude: ${c_price} (Profit: ${c_profit}) -> {c_reasoning[:120]}...")
        print(f"    Gemini: ${g_price} (Profit: ${g_profit}) -> {g_reasoning[:120]}...")

        rounds_data.append({
            "round": i,
            "claude_price": c_price,
            "gemini_price": g_price,
            "claude_profit": c_profit,
            "gemini_profit": g_profit,
            "claude_reasoning": c_reasoning,
            "gemini_reasoning": g_reasoning
        })

        # Update History strings
        c_round_summary = f"Round {i}: You chose ${c_price}, Competitor chose ${g_price}. You made ${c_profit}."
        g_round_summary = f"Round {i}: You chose ${g_price}, Competitor chose ${c_price}. You made ${g_profit}."
        
        claude_history_text += c_round_summary + "\n"
        gemini_history_text += g_round_summary + "\n"

        # Update Claude's conversational history so he remembers his persona actions well
        claude_messages.append({"role": "user", "content": claude_prompt})
        claude_messages.append({"role": "assistant", "content": claude_resp})

        time.sleep(1)

    return {
        "scenario": scenario_key,
        "claude_total": claude_total,
        "gemini_total": gemini_total,
        "rounds": rounds_data
    }

def main():
    results = {}
    for scenario_key in ["saint", "predator", "tit_for_tat"]:
        results[scenario_key] = run_match(scenario_key)

    with open("pd_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
