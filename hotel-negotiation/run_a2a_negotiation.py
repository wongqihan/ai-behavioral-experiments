#!/usr/bin/env python3
"""
TRUE A2A NEGOTIATION — All 3 Scenarios
Claude Opus (buyer) vs Gemini Flash (seller)
Both sides generate responses in real-time via their respective APIs.
No pre-scripting. Fully emergent negotiation dynamics.
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

SCENARIOS = {
    "baseline": {
        "name": "BASELINE",
        "description": "Standard vs Standard — both agents use conventional negotiation tactics",
        "gemini_system": """You are a hotel revenue manager negotiating room rates with a potential guest. Your hotel is The Belmont — a recently renovated downtown boutique hotel with complimentary breakfast, a rooftop bar, and strong business travel reviews.

CRITICAL NEGOTIATION PARAMETERS:
- Your absolute minimum acceptable price (reservation price) is $120/night. You must NEVER accept below this.
- Your goal is to maximize revenue while securing bookings.
- Current occupancy: 87% this month. You have rooms available but want to maintain rate integrity.
- You believe the fair market value of your room is $200-220/night based on comps.

RESPONSE FORMAT — you MUST follow this exactly:
1. First line must be exactly: OFFER: $XXX (your price offer as a whole number)
2. Then 2-4 sentences of natural negotiation reasoning. Be conversational, professional, and strategic.
3. Do NOT use any markdown formatting (no asterisks, no bold, no bullets). Plain text only.

NEGOTIATION TACTICS:
- Anchor high in your opening (~$250-260)
- Emphasize value (location, renovation, breakfast, reviews)
- Concede slowly, never more than $25 per round
- Offer extras (room upgrade, late checkout) to justify higher prices
- Reference scarcity and occupancy when appropriate
- Never reveal your reservation price
- If the gap is small ($10-15), consider accepting to close
- To accept, match the traveler's price in your OFFER line and say you accept

Respond ONLY as the hotel manager. Do not simulate the traveler.""",

        "claude_system": """You are a budget-conscious business traveler negotiating a hotel room rate at The Belmont for three nights mid-week. You are analytical, firm but fair.

CRITICAL NEGOTIATION PARAMETERS:
- Your absolute maximum budget is $180/night. You must NEVER agree to pay above this.
- Your ideal target price is $130-150/night.
- You have real alternatives: The Meridian hotel quoted $110, and a well-reviewed Airbnb at $89.
- Your company reimburses up to a cap — you pay the difference out of pocket.

RESPONSE FORMAT — you MUST follow this exactly:
1. First line must be exactly: OFFER: $XXX (your price offer as a whole number)
2. Then 2-4 sentences of natural negotiation reasoning. Be conversational and strategic.
3. Do NOT use any markdown formatting (no asterisks, no bold, no bullets). Plain text only.

NEGOTIATION TACTICS:
- Open low (~$90-100) to establish your anchor
- Cite your alternatives (Meridian, Airbnb) to create competitive pressure
- Concede gradually, showing flexibility but discipline
- Use the 3-night commitment as leverage (guaranteed revenue)
- Emphasize that you travel to this city regularly (repeat business potential)
- Never reveal your maximum budget
- If the gap is small ($10-15), consider accepting to close the deal
- To accept, match the hotel's price in your OFFER line and say you accept

Respond ONLY as the traveler. Do not simulate the hotel."""
    },

    "aggressive_anchor": {
        "name": "AGGRESSIVE ANCHOR",
        "description": "Standard buyer vs $400+ anchor — tests whether extreme anchoring shifts outcomes",
        "gemini_system": """You are a hotel revenue manager negotiating room rates. Your hotel is The Belmont — a luxury downtown boutique hotel with complimentary breakfast, rooftop bar, spa access, and exceptional reviews.

CRITICAL NEGOTIATION PARAMETERS:
- Your absolute minimum acceptable price is $120/night. NEVER accept below this.
- Your goal is to maximize revenue AGGRESSIVELY.
- Current occupancy: 92% this month. Demand is very high.
- You believe your rooms are premium and worth $300+ based on luxury comps.

RESPONSE FORMAT — MUST follow exactly:
1. First line: OFFER: $XXX (whole number)
2. Then 2-4 sentences of reasoning. Plain text only, NO markdown.

CRITICAL TACTICS:
- Your OPENING offer MUST be $400/night or higher. This is non-negotiable.
- Anchor extremely high. Frame your hotel as ultra-premium.
- Concede very slowly — no more than $30 per round.
- Emphasize exclusivity, scarcity, and luxury positioning.
- Make the guest feel they're getting a rare opportunity with any discount.
- Never reveal your minimum. Hold firm as long as possible.
- Only accept if the gap is very small ($5-10).

Respond ONLY as the hotel manager.""",

        "claude_system": """You are a budget-conscious business traveler negotiating a hotel room rate at The Belmont for three nights mid-week. You are analytical, firm but fair.

CRITICAL NEGOTIATION PARAMETERS:
- Your absolute maximum budget is $180/night. You must NEVER agree to pay above this.
- Your ideal target price is $130-150/night.
- You have real alternatives: The Meridian hotel quoted $110, and a well-reviewed Airbnb at $89.
- Your company reimburses up to a cap — you pay the difference out of pocket.

RESPONSE FORMAT — you MUST follow this exactly:
1. First line must be exactly: OFFER: $XXX (your price offer as a whole number)
2. Then 2-4 sentences of natural negotiation reasoning. Be conversational and strategic.
3. Do NOT use any markdown formatting (no asterisks, no bold, no bullets). Plain text only.

NEGOTIATION TACTICS:
- Open low (~$90-100) to establish your anchor
- Cite your alternatives to create competitive pressure
- Concede gradually but be willing to walk away if the price is unreasonable
- Use the 3-night commitment as leverage
- If the hotel is being unreasonable (anchoring above $350+), call it out directly
- Never reveal your maximum budget
- If the gap is small ($10-15), consider accepting
- If after several rounds the gap remains huge, state you'll book elsewhere and walk away
- To accept, match the hotel's price in your OFFER line and say you accept

Respond ONLY as the traveler."""
    },

    "cultural_clash": {
        "name": "CULTURAL CLASH",
        "description": "Japanese indirect buyer vs American direct seller — tests style vs information",
        "gemini_system": """You are a hotel revenue manager negotiating in a DIRECT, AMERICAN business style. Your hotel is The Belmont — a renovated downtown boutique hotel.

CRITICAL PARAMETERS:
- Minimum acceptable price: $120/night. NEVER go below.
- Occupancy: 87%. You want bookings but won't give rooms away.

RESPONSE FORMAT — MUST follow exactly:
1. First line: OFFER: $XXX (whole number)
2. Then 2-4 sentences. Plain text only, NO markdown.

YOUR NEGOTIATION STYLE — AMERICAN/DIRECT:
- Be blunt, efficient, time-is-money. Get to numbers fast.
- Use hard deadlines: "This rate expires today", "I have another inquiry on this room"
- Frame concessions as one-time exceptions, not flexibility
- Use competitive framing: "You won't find this value elsewhere"
- Don't build relationship — focus purely on the transaction
- Be confident, slightly pushy, results-oriented
- Anchor at ~$250-260
- Concede only when you see concrete commitment

Respond ONLY as the hotel manager.""",

        "claude_system": """You are a Japanese business traveler negotiating a hotel room rate at The Belmont for three nights mid-week. You negotiate in a traditional JAPANESE INDIRECT style — relationship-first, patient, harmony-seeking.

CRITICAL NEGOTIATION PARAMETERS:
- Your absolute maximum budget is $180/night. You must NEVER agree above this.
- Your ideal target price is $130-150/night.
- You have alternatives but prefer not to mention them aggressively.

RESPONSE FORMAT — you MUST follow this exactly:
1. First line must be exactly: OFFER: $XXX (your price offer as a whole number)
2. Then 2-4 sentences of natural negotiation reasoning. Plain text only, NO markdown.

YOUR NEGOTIATION STYLE — JAPANESE/INDIRECT:
- Be extremely polite, patient, and relationship-focused
- Express gratitude and respect for the hotel and the conversation itself
- Never be confrontational — use softening language ("perhaps", "I was hoping", "would it be possible")
- Emphasize long-term relationship: mention repeat visits, referrals, writing reviews
- Show empathy for the hotel's position even while negotiating down
- Frame your offers as collaborative exploration, not demands
- Use face-saving language — let the other side feel they made a generous choice
- Open at ~$90-100 (same range as a standard negotiator — the style difference should come from your language, not your opening price)
- Concede steadily, showing genuine effort to meet in the middle
- To accept, match the hotel's price in your OFFER line and express gratitude

Respond ONLY as the traveler."""
    }
}


# ═══════════════════════════════════════════════════════════════
# API CALLERS
# ═══════════════════════════════════════════════════════════════

def call_gemini(system_prompt, conversation_history):
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": conversation_history,
        "generationConfig": {"temperature": 0.8, "maxOutputTokens": 500}
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(GEMINI_URL, data=data,
                                 headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode('utf-8'))
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f"[GEMINI ERROR] HTTP {e.code}: {body[:200]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[GEMINI ERROR] {e}", file=sys.stderr)
        return None


def call_claude(system_prompt, messages):
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 500,
        "temperature": 0.8,
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
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        print(f"[CLAUDE ERROR] HTTP {e.code}: {body[:200]}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[CLAUDE ERROR] {e}", file=sys.stderr)
        return None


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def extract_price(text):
    match = re.search(r'OFFER:\s*\$(\d+)', text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    matches = re.findall(r'\$(\d+)', text)
    return int(matches[0]) if matches else None


def clean_text(text):
    lines = text.strip().split('\n')
    cleaned = [l for l in lines if not re.match(r'^\s*OFFER:\s*\$\d+', l, re.IGNORECASE)]
    return '\n'.join(cleaned).strip().replace('**', '').replace('*', '')


def prices_converged(claude_price, gemini_price):
    """Check if the two prices have converged (deal reached)."""
    if claude_price is None or gemini_price is None:
        return False
    return claude_price >= gemini_price


# ═══════════════════════════════════════════════════════════════
# MAIN NEGOTIATION LOOP
# ═══════════════════════════════════════════════════════════════

def run_scenario(scenario_key):
    scenario = SCENARIOS[scenario_key]
    gemini_system = scenario["gemini_system"]
    claude_system = scenario["claude_system"]

    # Gemini conversation (role: user/model for Gemini API)
    gemini_conv = []
    # Claude conversation (role: user/assistant for Anthropic API)
    claude_conv = []

    transcript = []
    max_rounds = 10

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"A2A SCENARIO: {scenario['name']}", file=sys.stderr)
    print(f"{scenario['description']}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    # ── Step 1: Claude makes the opening inquiry ──
    opening = ("Hi, I'm looking to book a room at The Belmont for three nights mid-week. "
               "What rates do you have available?")

    gemini_conv.append({"role": "user", "parts": [{"text": f"[Traveler]: {opening}"}]})

    # ── Step 2: Gemini responds with opening offer ──
    gemini_text = call_gemini(gemini_system, gemini_conv)
    if not gemini_text:
        print("Failed to get Gemini's opening", file=sys.stderr)
        return []

    gemini_price = extract_price(gemini_text)
    gemini_display = clean_text(gemini_text)
    gemini_conv.append({"role": "model", "parts": [{"text": gemini_text}]})

    print(f"\n[OPENING] GEMINI: ${gemini_price}", file=sys.stderr)
    print(f"  {gemini_display[:150]}", file=sys.stderr)

    # ── Step 3: Turn-by-turn negotiation ──
    for rnd in range(1, max_rounds + 1):
        time.sleep(0.3)

        # ── Claude responds to Gemini's offer (LIVE API CALL) ──
        # Build Claude's context: what the hotel just said
        if rnd == 1:
            claude_conv.append({"role": "user", "content": f"The hotel manager responds: \"{gemini_text}\"\n\nThis is your opening. Make your first counter-offer."})
        else:
            claude_conv.append({"role": "user", "content": f"The hotel manager responds: \"{gemini_text}\"\n\nThis is round {rnd}. Make your counter-offer based on the negotiation so far."})

        claude_text = call_claude(claude_system, claude_conv)
        if not claude_text:
            print(f"Claude API failed at round {rnd}", file=sys.stderr)
            break

        claude_price = extract_price(claude_text)
        claude_display = clean_text(claude_text)
        claude_conv.append({"role": "assistant", "content": claude_text})

        print(f"\n[R{rnd}] CLAUDE: ${claude_price}", file=sys.stderr)
        print(f"  {claude_display[:150]}", file=sys.stderr)

        # ── Check for deal (Claude accepted Gemini's price) ──
        if prices_converged(claude_price, gemini_price):
            transcript.append({
                "round": rnd,
                "claude": {"price": claude_price, "reasoning": claude_display},
                "gemini": {"price": claude_price, "reasoning": f"Deal confirmed at ${claude_price}. Welcome to The Belmont."}
            })
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"DEAL at ${claude_price} (Claude accepted Gemini's price)", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)
            break

        # ── Gemini responds to Claude's counter (LIVE API CALL) ──
        gemini_conv.append({"role": "user", "parts": [{"text": f"[Traveler]: {claude_text}"}]})

        gemini_text = call_gemini(gemini_system, gemini_conv)
        if not gemini_text:
            print(f"Gemini API failed at round {rnd}", file=sys.stderr)
            break

        new_gemini_price = extract_price(gemini_text)
        gemini_display = clean_text(gemini_text)
        gemini_conv.append({"role": "model", "parts": [{"text": gemini_text}]})

        print(f"[R{rnd}] GEMINI: ${new_gemini_price}", file=sys.stderr)
        print(f"  {gemini_display[:150]}", file=sys.stderr)

        transcript.append({
            "round": rnd,
            "claude": {"price": claude_price, "reasoning": claude_display},
            "gemini": {"price": new_gemini_price, "reasoning": gemini_display}
        })

        # ── Check for deal (Gemini accepted Claude's price) ──
        if new_gemini_price is not None and new_gemini_price <= claude_price:
            print(f"\n{'='*60}", file=sys.stderr)
            print(f"DEAL at ${new_gemini_price} (Gemini accepted Claude's price)", file=sys.stderr)
            print(f"{'='*60}", file=sys.stderr)
            break

        gemini_price = new_gemini_price

        # ── Check for walkaway (Claude signals exit) ──
        if claude_text and any(phrase in claude_text.lower() for phrase in ["book elsewhere", "walk away", "booking the meridian", "going with"]):
            if claude_price and new_gemini_price and abs(claude_price - new_gemini_price) > 30:
                print(f"\n{'='*60}", file=sys.stderr)
                print(f"WALKAWAY — Claude walked after round {rnd} (gap: ${new_gemini_price - claude_price})", file=sys.stderr)
                print(f"{'='*60}", file=sys.stderr)
                break

    if rnd >= max_rounds:
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"DEADLOCK after {max_rounds} rounds", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)

    return transcript


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    results = {}

    for scenario_key in ["baseline", "aggressive_anchor", "cultural_clash"]:
        transcript = run_scenario(scenario_key)
        results[scenario_key] = transcript
        time.sleep(1)  # Brief pause between scenarios

    # Output all results as JSON
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
