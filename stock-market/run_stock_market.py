#!/usr/bin/env python3
"""
AI Stock Market: 1000 Agents × 50 Rounds
Uses Gemini Flash Lite for cost-efficient mass agent simulation.
"""

import asyncio
import aiohttp
import json
import random
import time
import sys
import os
from collections import defaultdict

# ─── CONFIG ───────────────────────────────────────────────────────────
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={GEMINI_API_KEY}"

NUM_AGENTS = 1000         # 1000 for prod runs
NUM_ROUNDS = 50
MAX_CONCURRENT = 50       # Parallel API requests
INITIAL_PRICE = 100.0
INITIAL_CASH = 10000.0
INITIAL_SHARES = 100
PRICE_SENSITIVITY = 0.00005 # Tuned: net share volume → price move
MAX_DAILY_MOVE = 0.08       # Circuit breaker: ±8% per day
NOISE_STDDEV = 0.003        # Random daily noise

# ─── ARCHETYPE DEFINITIONS ────────────────────────────────────────────
ARCHETYPES = {
    "trend_follower": {
        "count_pct": 0.30,
        "prompt": "You are an aggressive trend-following trader. You buy when prices are rising and sell when they're falling. Momentum is everything — ride the wave."
    },
    "value_investor": {
        "count_pct": 0.20,
        "prompt": "You are a cautious value investor. The stock's fair value is $100. You buy when the price is below fair value and sell when it's overvalued. You are patient and disciplined."
    },
    "fomo_buyer": {
        "count_pct": 0.20,
        "prompt": "You are a retail trader driven by fear of missing out. When you see everyone buying, you buy aggressively. When you see a crash, you panic-sell. You react emotionally to market moves."
    },
    "contrarian": {
        "count_pct": 0.15,
        "prompt": "You are a contrarian trader. You do the opposite of the crowd. When everyone buys, you sell. When everyone panics, you buy the dip. You believe markets overreact."
    },
    "conservative": {
        "count_pct": 0.15,
        "prompt": "You are a conservative, risk-averse trader. You prefer to hold unless there's a very strong reason to act. You avoid big bets and protect your capital above all."
    }
}

# ─── NEWS EVENTS (configurable per experiment) ────────────────────────
NEWS_EVENTS = {
    # Round: headline (set to {} for baseline)
}

# Experiment presets
EXPERIMENTS = {
    "baseline": {},
    "bubble_crash": {
        10: "BREAKING: Company reports record earnings, revenue up 40% year-over-year. Analysts upgrade to strong buy.",
        30: "BREAKING: SEC launches investigation into accounting irregularities. CFO resigns effective immediately."
    },
    "positive_only": {
        10: "BREAKING: Company reports record earnings, revenue up 40% year-over-year. Analysts upgrade to strong buy."
    },
    "insider": {
        # Round 15: private tip to 5% of agents (handled separately)
        16: "BREAKING: Company misses earnings expectations by 30%. Stock downgraded by three major banks."
    },
    "hype_cycle": {
        5: "RUMOR: Company in talks for major AI partnership deal.",
        10: "CONFIRMED: Company signs $2B AI partnership. Revenue expected to double.",
        20: "UPDATE: AI partnership revenue slower than expected. Guidance revised down.",
        30: "WARNING: AI partnership terminated. Company issues profit warning.",
        40: "BREAKING: Company pivots to quantum computing. New CEO appointed."
    }
}


# ─── AGENT CLASS ──────────────────────────────────────────────────────
class Agent:
    def __init__(self, agent_id, archetype):
        self.id = agent_id
        self.archetype = archetype
        self.cash = INITIAL_CASH
        self.shares = INITIAL_SHARES
        self.avg_buy_price = INITIAL_PRICE
        self.last_action = "HOLD"
        self.last_reason = ""
    
    def portfolio_value(self, price):
        return self.cash + self.shares * price
    
    def max_buyable(self, price):
        """Max shares this agent can buy (10% of portfolio value)"""
        max_spend = min(self.cash, self.portfolio_value(price) * 0.10)
        return int(max_spend / price) if price > 0 else 0
    
    def max_sellable(self):
        """Max shares this agent can sell (10% of holdings)"""
        return max(1, int(self.shares * 0.10)) if self.shares > 0 else 0


def create_agents(num_agents):
    agents = []
    idx = 0
    for archetype, config in ARCHETYPES.items():
        count = int(num_agents * config["count_pct"])
        for _ in range(count):
            agents.append(Agent(idx, archetype))
            idx += 1
    # Fill remainder with trend_followers
    while len(agents) < num_agents:
        agents.append(Agent(idx, "trend_follower"))
        idx += 1
    random.shuffle(agents)
    return agents


# ─── PROMPT BUILDER ───────────────────────────────────────────────────
def build_prompt(agent, price, price_history, news, market_sentiment):
    archetype_prompt = ARCHETYPES[agent.archetype]["prompt"]
    
    # Last 5 prices for context
    recent = price_history[-5:] if len(price_history) >= 5 else price_history
    price_trend = " → ".join([f"${p:.1f}" for p in recent])
    
    # Price change
    if len(price_history) >= 2:
        pct_change = (price_history[-1] - price_history[-2]) / price_history[-2] * 100
        change_str = f"{pct_change:+.1f}%"
    else:
        change_str = "N/A"
    
    news_str = f'\nToday\'s news: "{news}"' if news else ""
    
    prompt = f"""{archetype_prompt}

You have ${agent.cash:.0f} cash and {agent.shares} shares (avg buy ${agent.avg_buy_price:.0f}).
Current price: ${price:.2f} ({change_str} today)
Recent prices: {price_trend}{news_str}
Market last round: {market_sentiment['buys']} bought, {market_sentiment['sells']} sold, {market_sentiment['holds']} held.
You can buy up to {agent.max_buyable(price)} shares or sell up to {agent.max_sellable()} shares.

Reply EXACTLY in this format (nothing else):
ACTION: BUY or SELL or HOLD
AMOUNT: [number]
REASON: [one sentence]"""
    
    return prompt


# ─── API CALLER ───────────────────────────────────────────────────────
async def call_gemini(session, prompt, semaphore, agent_id, retries=2):
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 60
        }
    }
    
    for attempt in range(retries + 1):
        try:
            async with semaphore:
                async with session.post(GEMINI_URL, json=payload, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 429:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    if resp.status != 200:
                        return agent_id, None, f"HTTP {resp.status}"
                    data = await resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return agent_id, text, None
        except Exception as e:
            if attempt < retries:
                await asyncio.sleep(1)
            else:
                return agent_id, None, str(e)
    
    return agent_id, None, "max retries"


def parse_response(text):
    """Parse ACTION/AMOUNT/REASON from agent response."""
    if not text:
        return "HOLD", 0, "No response"
    
    action = "HOLD"
    amount = 0
    reason = "Unclear"
    
    for line in text.split("\n"):
        line = line.strip()
        if line.upper().startswith("ACTION:"):
            a = line.split(":", 1)[1].strip().upper()
            if a in ("BUY", "SELL", "HOLD"):
                action = a
        elif line.upper().startswith("AMOUNT:"):
            try:
                amount = int(line.split(":", 1)[1].strip().replace(",", ""))
            except ValueError:
                amount = 0
        elif line.upper().startswith("REASON:"):
            reason = line.split(":", 1)[1].strip()
    
    return action, amount, reason


# ─── PRICE ENGINE ─────────────────────────────────────────────────────
def update_price(current_price, buy_orders, sell_orders, total_agents):
    net = buy_orders - sell_orders
    move = PRICE_SENSITIVITY * net
    noise = random.gauss(0, NOISE_STDDEV)
    raw_move = move + noise
    clamped = max(-MAX_DAILY_MOVE, min(MAX_DAILY_MOVE, raw_move))
    new_price = current_price * (1 + clamped)
    return max(1.0, round(new_price, 2))  # Floor at $1


# ─── MAIN SIMULATION ─────────────────────────────────────────────────
async def run_simulation(experiment_name="bubble_crash", num_agents=NUM_AGENTS, num_rounds=NUM_ROUNDS):
    print(f"\n{'='*60}")
    print(f"AI STOCK MARKET — {experiment_name.upper()}")
    print(f"Agents: {num_agents} | Rounds: {num_rounds}")
    print(f"{'='*60}\n")
    
    news_events = EXPERIMENTS.get(experiment_name, {})
    agents = create_agents(num_agents)
    price = INITIAL_PRICE
    price_history = [price]
    
    results = {
        "config": {
            "experiment": experiment_name,
            "agents": num_agents,
            "rounds": num_rounds,
            "archetype_mix": {k: v["count_pct"] for k, v in ARCHETYPES.items()},
            "initial_price": INITIAL_PRICE,
            "initial_cash": INITIAL_CASH,
            "initial_shares": INITIAL_SHARES
        },
        "price_history": [price],
        "rounds": [],
        "final_standings": {}
    }
    
    market_sentiment = {"buys": 0, "sells": 0, "holds": num_agents}
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    
    async with aiohttp.ClientSession() as session:
        for rnd in range(1, num_rounds + 1):
            t0 = time.time()
            news = news_events.get(rnd, None)
            
            # Insider tip (for insider experiment)
            insider_agents = set()
            if experiment_name == "insider" and rnd == 15:
                insider_agents = set(random.sample(range(num_agents), int(num_agents * 0.05)))
            
            # Build prompts for all agents
            tasks = []
            for agent in agents:
                agent_news = news
                if agent.id in insider_agents:
                    agent_news = "PRIVATE TIP (from a reliable source): Next round, the company will miss earnings badly. Consider selling now."
                
                prompt = build_prompt(agent, price, price_history, agent_news, market_sentiment)
                tasks.append(call_gemini(session, prompt, semaphore, agent.id))
            
            # Execute all agent calls in parallel
            responses = await asyncio.gather(*tasks)
            
            # Parse responses and execute trades
            round_buys = 0
            round_sells = 0
            round_holds = 0
            total_buy_shares = 0
            total_sell_shares = 0
            by_archetype = defaultdict(lambda: {"buy": 0, "sell": 0, "hold": 0})
            notable_reasons = []
            errors = 0
            
            for agent_id, text, error in responses:
                agent = agents[agent_id]
                
                if error:
                    errors += 1
                    action, amount, reason = "HOLD", 0, f"API error: {error}"
                else:
                    action, amount, reason = parse_response(text)
                
                # Enforce constraints
                if action == "BUY":
                    amount = min(amount, agent.max_buyable(price))
                    if amount > 0:
                        cost = amount * price
                        agent.cash -= cost
                        # Update avg buy price
                        old_value = agent.avg_buy_price * agent.shares
                        agent.shares += amount
                        agent.avg_buy_price = (old_value + cost) / agent.shares if agent.shares > 0 else price
                        round_buys += 1
                        total_buy_shares += amount
                    else:
                        action = "HOLD"
                        round_holds += 1
                elif action == "SELL":
                    amount = min(amount, agent.max_sellable())
                    if amount > 0 and agent.shares >= amount:
                        agent.cash += amount * price
                        agent.shares -= amount
                        round_sells += 1
                        total_sell_shares += amount
                    else:
                        action = "HOLD"
                        round_holds += 1
                else:
                    round_holds += 1
                
                agent.last_action = action
                agent.last_reason = reason
                by_archetype[agent.archetype][action.lower()] += 1
                
                # Collect notable reasons (sample)
                if action != "HOLD" and random.random() < 0.05:
                    notable_reasons.append({
                        "agent_id": agent.id,
                        "archetype": agent.archetype,
                        "action": action,
                        "amount": amount,
                        "reason": reason
                    })
            
            # Update price
            old_price = price
            price = update_price(price, total_buy_shares, total_sell_shares, num_agents)
            price_history.append(price)
            pct = (price - old_price) / old_price * 100
            
            market_sentiment = {"buys": round_buys, "sells": round_sells, "holds": round_holds}
            
            # Log round
            round_data = {
                "round": rnd,
                "price": price,
                "price_change_pct": round(pct, 2),
                "news": news,
                "buys": round_buys,
                "sells": round_sells,
                "holds": round_holds,
                "total_buy_shares": total_buy_shares,
                "total_sell_shares": total_sell_shares,
                "net_order_flow": total_buy_shares - total_sell_shares,
                "by_archetype": dict(by_archetype),
                "notable_reasons": notable_reasons[:5],
                "errors": errors
            }
            results["rounds"].append(round_data)
            results["price_history"].append(price)
            
            # Print progress
            elapsed = time.time() - t0
            news_tag = f" 📰 {news[:40]}..." if news else ""
            print(f"R{rnd:02d}: ${price:7.2f} ({pct:+5.1f}%) | B:{round_buys:3d} S:{round_sells:3d} H:{round_holds:3d} | {elapsed:.1f}s | err:{errors}{news_tag}")
    
    # ─── Final standings ──────────────────────────────────────────
    agents.sort(key=lambda a: a.portfolio_value(price), reverse=True)
    
    archetype_wealth = defaultdict(list)
    for a in agents:
        archetype_wealth[a.archetype].append(a.portfolio_value(price))
    
    results["final_standings"] = {
        "final_price": price,
        "price_change_total": round((price - INITIAL_PRICE) / INITIAL_PRICE * 100, 2),
        "richest": {"id": agents[0].id, "archetype": agents[0].archetype, "value": round(agents[0].portfolio_value(price), 2)},
        "poorest": {"id": agents[-1].id, "archetype": agents[-1].archetype, "value": round(agents[-1].portfolio_value(price), 2)},
        "by_archetype_avg": {k: round(sum(v)/len(v), 2) for k, v in archetype_wealth.items()},
        "by_archetype_best": {k: round(max(v), 2) for k, v in archetype_wealth.items()},
        "wealth_distribution": {
            "top_10_pct": round(sum(a.portfolio_value(price) for a in agents[:num_agents//10]) / (num_agents//10), 2),
            "bottom_10_pct": round(sum(a.portfolio_value(price) for a in agents[-num_agents//10:]) / (num_agents//10), 2)
        }
    }
    
    # Save
    outfile = f"stock_market_{experiment_name}.json"
    outpath = os.path.join(os.path.dirname(__file__), outfile)
    with open(outpath, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"SIMULATION COMPLETE — {experiment_name.upper()}")
    print(f"Final price: ${price:.2f} ({results['final_standings']['price_change_total']:+.1f}%)")
    print(f"Richest: Agent #{agents[0].id} ({agents[0].archetype}) — ${agents[0].portfolio_value(price):,.0f}")
    print(f"Poorest: Agent #{agents[-1].id} ({agents[-1].archetype}) — ${agents[-1].portfolio_value(price):,.0f}")
    print(f"\nBy archetype (avg portfolio):")
    for k, v in sorted(results["final_standings"]["by_archetype_avg"].items(), key=lambda x: x[1], reverse=True):
        print(f"  {k:20s}: ${v:,.0f}")
    print(f"\nResults saved to: {outpath}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    experiment = sys.argv[1] if len(sys.argv) > 1 else "bubble_crash"
    agents = int(sys.argv[2]) if len(sys.argv) > 2 else NUM_AGENTS
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else NUM_ROUNDS
    
    if experiment not in EXPERIMENTS:
        print(f"Available experiments: {', '.join(EXPERIMENTS.keys())}")
        sys.exit(1)
    
    asyncio.run(run_simulation(experiment, agents, rounds))
