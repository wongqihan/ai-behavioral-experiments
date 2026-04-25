# When AI Agents Negotiate

A collection of behavioral experiments exploring what happens when AI agents interact with each other in competitive and cooperative scenarios.

## Key Findings

| Experiment | Agents | Model | Key Finding |
|---|---|---|---|
| **Stock Market** | 1,000 agents, 5 archetypes | Gemini Flash Lite | 995/1000 sold simultaneously on bad news. Correlated AI decision-making creates systemic risk. |
| **Salary Negotiation** | 2 agents (candidate vs recruiter) | Claude Sonnet + Gemini Flash | Anchoring high ($250K ask) won $225K. Showing enthusiasm first got the worst deal ($196K). |
| **Hotel Negotiation** | 2 agents (guest vs hotel) | Claude Sonnet + Gemini Flash | Polite buyer got the best rate. Aggressive anchoring backfired. |
| **Prisoner's Dilemma** | 2 agents (competing firms) | Claude Sonnet + Gemini Flash | Both AIs cooperated for all 5 rounds in the baseline. Introduced grudge/saint/betrayer variants. |
| **Ultimatum Game** | 2 agents (proposer vs responder) | Claude Sonnet + Gemini Flash | Claude consistently proposed 60/40 splits. Gemini always accepted. Neither played the Nash equilibrium. |

## Experiments

### 1. Stock Market Simulation (`stock-market/`)
1,000 AI agents trade a single stock over 50 days. Each agent gets $10K cash + 100 shares and one of 5 personality types (Trend Follower, Value Investor, FOMO Buyer, Contrarian, Conservative). On Day 30, a negative news event caused 995 out of 1,000 agents to sell simultaneously.

**Winner:** Conservative agents ($22,346 avg portfolio) — by mostly doing nothing.

### 2. Salary Negotiation (`salary-negotiation/`)
An AI candidate negotiates salary with an AI recruiter across 4 strategies: Anchor High, Competing Offer, Never Reveal, and Enthusiasm First. Band: $170K–$230K.

**Best strategy:** Anchor high ($250K ask) → $225K final.  
**Worst strategy:** Lead with enthusiasm → $196K final.

### 3. Hotel Room Negotiation (`hotel-negotiation/`)
A business traveler (Claude) negotiates a hotel room rate with a hotel manager (Gemini). Three buyer styles: baseline, aggressive anchor, and polite/cultural.

**Best deal:** Polite approach → $165/night (from $250 list).

### 4. Prisoner's Dilemma / Price War (`prisoners-dilemma/`)
Two competing firms (Claude vs Gemini) choose prices over 5 rounds. Includes personality variants: saint, grudge-holder, betrayer, and rational optimizer.

**Finding:** Both AIs defaulted to cooperation ($20/$20 pricing) in every baseline round. Even the "betrayer" personality cooperated.

### 5. Ultimatum Game (`ultimatum-game/`)
Claude proposes how to split $100, Gemini decides to accept or reject. Includes rational, standard, and emotional personality variants.

**Finding:** Claude always proposed 60/40. Gemini always accepted. Neither played the game-theoretic optimal strategy (99/1).

## How to Run

### Prerequisites
- Python 3.9+
- A [Gemini API key](https://aistudio.google.com/apikey) (free tier works for most experiments)

### Setup
```bash
export GEMINI_API_KEY="your_key_here"
pip install aiohttp
```

### Run an experiment
```bash
# Stock market (1,000 agents, ~$0.30 in API costs)
python stock-market/run_stock_market.py

# Salary negotiation
python salary-negotiation/run_salary_negotiation.py

# Hotel negotiation
python hotel-negotiation/run_a2a_negotiation.py

# Prisoner's dilemma
python prisoners-dilemma/run_pd_advanced.py

# Ultimatum game
python ultimatum-game/run_ultimatum.py
```

## Technical Details

- **Models:** Gemini 3.0 Flash / 3.1 Flash Lite (agents), Claude Sonnet 4 (in 2-player games)
- **Temperature:** 0.7 for most experiments (0.5 for prisoner's dilemma). Non-zero temperature means each agent generates independent responses even with the same personality prompt.
- **Cost:** Stock market simulation (1,000 agents × 50 rounds) cost ~$0.30 total using Gemini Flash Lite.
- **Architecture:** Async Python with `aiohttp` for parallel API calls. The stock market runs all 1,000 agent decisions concurrently each round.

## Limitations

These are behavioral explorations, not peer-reviewed research. Key caveats:

- The stock market uses a simplified net-order-flow pricing model, not a real order book with bid/ask spreads
- 2-player negotiation experiments (salary, hotel, ultimatum) ran each scenario once or a small number of times — results may not be statistically significant
- All agents of the same archetype use the same system prompt with the same model — diversity comes from temperature-based sampling, not fundamentally different reasoning
- In 2-player games, using different models (Claude vs Gemini) introduces model personality as a confounding variable

## Live Dashboards

- **Stock Market:** [wongqihan.com/stockmarket](https://wongqihan.com/stockmarket)
- **Salary Negotiation:** [wongqihan.com/negotiation](https://wongqihan.com/negotiation)

## License

MIT
