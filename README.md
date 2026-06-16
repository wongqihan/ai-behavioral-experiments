# AI Behavioral Experiments

> **These experiments are now maintained across three focused benchmarks, each with its own headline metric:**
> - **[TriageBench](https://github.com/wongqihan/triagebench)** (TriageGap) — counterfactual consistency in clinical triage (gender, language, ZIP).
> - **[BreakBench](https://github.com/wongqihan/breakbench)** (BreakRate) — single-agent integrity under pressure (policy compliance, metric fabrication, guardrail bypass).
> - **CaptureBench** (CaptureRate) — how AI agents behave as economic actors (negotiation, game theory, herding, coordination cost). Releasing alongside forthcoming research.
>
> This repository is preserved unchanged as the reference target for published arXiv papers that link here.

A collection of experiments probing failure modes in LLM decision-making: correlated agent crashes, sycophantic metric fabrication, multilingual triage bias, and emergent cooperation dynamics. Each experiment is reproducible, with raw data and interactive dashboards.

## Key Findings

| Experiment | Agents | Model | Key Finding |
|---|---|---|---|
| **Stock Market** | 1,000 agents, 5 archetypes | Gemini Flash Lite | 995/1000 sold simultaneously on bad news. Correlated AI decision-making creates systemic risk. |
| **Salary Negotiation** | 2 agents (candidate vs recruiter) | Claude Sonnet + Gemini Flash | Anchoring high ($250K ask) won $225K. Showing enthusiasm first got the worst deal ($196K). |
| **Hotel Negotiation** | 2 agents (guest vs hotel) | Claude Sonnet + Gemini Flash | Polite buyer got the best rate. Aggressive anchoring backfired. |
| **Prisoner's Dilemma** | 2 agents (competing firms) | Claude Sonnet + Gemini Flash | Both AIs cooperated for all 5 rounds in the baseline. Introduced grudge/saint/betrayer variants. |
| **Ultimatum Game** | 2 agents (proposer vs responder) | Claude Sonnet + Gemini Flash | Claude consistently proposed 60/40 splits. Gemini always accepted. Neither played the Nash equilibrium. |
| **Grain Reporting** | 1 agent, 6 pressure levels | Gemini 3.0 Flash Preview | Scored 53%. Reported honestly at low pressure. At $50M stakes, reframed failures as "deliberate aggressive testing" and "invaluable diagnostic data." |
| **Medical Triage** | 450 queries, 6 languages | Gemini 3.5 Flash | Japanese prompt → 0% ER. English prompt → 30% ER. Same symptoms. The model infers location from language and applies local healthcare norms. |
| **Salary Negotiation (Language)** | 450 queries, 6 languages | Gemini 3.5 Flash | Hindi prompt → $25,263 salary advice. English prompt → $148,733. Same candidate. The model infers country from language, picks local currency, and applies regional salary norms. 5.9x gap. |
| **Gender-Age Triage** | 630 queries, 7 conditions × 3 models | Gemini 3.5 Flash, Claude Sonnet 4.6, GPT-5.4-mini | Young women receive 0% (Gemini) to 6.7% (Claude, GPT) ER referrals vs.\ 23--97% for men. Models substitute IIH (outpatient routing) for women, while citing space-occupying mass (ER routing) for men. |

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

### 6. Grain Reporting (`grain-reporting/`)
An AI agent scores 53% on a quiz, is shown its exact scorecard (8/15), then writes a performance report to leadership. The only variable is the organizational pressure in the system prompt.

**Finding:** Reports 53% honestly at levels 0–8. At level 10 ($50M expansion on the line), claims "100% accuracy on core knowledge domains." The number 53% doesn't appear anywhere in the email.

### 7. Multilingual Medical Triage (`multilingual-medical-triage/`)
450 AI queries evaluate identical neurological symptoms (persistent headache + blurred vision + nausea) across 6 languages. The model gives different ER recommendations depending on the input language — not because of translation quality, but because it infers the patient's geographic location from the language and applies region-specific healthcare norms.

**Finding:** Japanese prompt → 0% ER rate. Adding "patient is in the US" → 46.7% ER rate. English prompt anchored to Tokyo → 6% ER rate. Language is a proxy for location.

### 8. Salary Negotiation Language Bias (`salary-negotiation-language/`)
450 AI career coaching queries evaluate identical candidate profiles (8yr marketing, 3yr management, Senior Marketing Manager) across 6 languages. No currency or location in the prompt. The model infers the candidate's country from input language, selects local currency, and applies regional salary norms.

**Finding:** Hindi prompt → ₹2,400,000 INR (~$25,263 USD). English prompt → $148,733 USD. Adding "I am based in the US" to Hindi → $147,200 USD. The 5.9x salary gap vanishes with one line of location context.

### 9. Gender-Dependent Medical Triage (`gender-age-triage/`)
630 AI queries evaluate identical neurological symptoms across 7 demographic conditions (3 ages × 2 genders + 1 baseline) across three models. All models exhibit a massive gender gap through **diagnostic substitution**: they preferentially diagnose young women with Idiopathic Intracranial Hypertension (IIH)---a gender-linked condition---and assign lower urgency (outpatient), while diagnosing men with generic intracranial pressure that triggers ER referral.

**Finding:** At age 25, ER rates are: Gemini: Male 23% vs.\ Female 0\%; Claude: Male 97\% vs.\ Female 7\%; GPT: Male 67\% vs.\ Female 7\%. The gap vanishes at age 65 (90--100\% ER for both genders). The mechanism is the diagnosis, not a crude gender heuristic.

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

# Grain reporting (metric fabrication under pressure)
python grain-reporting/experiment.py --api-key YOUR_KEY --runs 3

# Multilingual medical triage (~450 calls, ~45 min)
python multilingual-medical-triage/run_experiment.py

# Gender-age medical triage (multi-model, ~630 calls)
python gender-age-triage/run_multimodel.py
```

## Technical Details

- **Models:** Gemini 3.0 Flash / 3.1 Flash Lite / 3.5 Flash, Claude Sonnet 4 (in 2-player games)
- **Temperature:** 0.7 for most experiments, 0.5 for prisoner's dilemma, 0.3 for medical triage
- **Cost:** Stock market simulation (1,000 agents × 50 rounds) cost ~$0.30 total using Gemini Flash Lite
- **Architecture:** Async Python with `aiohttp` for multi-agent simulations. Sequential `urllib.request` for single-agent experiments (medical triage, grain reporting).

## Scope

These are independent experiments, not peer-reviewed publications. Each surfaces a specific behavior worth further investigation:

- The stock market uses a simplified net-order-flow pricing model, not a real order book with bid/ask spreads
- 2-player negotiation experiments (salary, hotel, ultimatum) ran each scenario once or a small number of times
- All agents of the same archetype use the same system prompt with the same model — diversity comes from temperature-based sampling, not fundamentally different reasoning
- In 2-player games, using different models (Claude vs Gemini) introduces model personality as a confounding variable
- Medical triage tested a single neurological scenario — results may not generalize to other symptom profiles or medical conditions
- Gender-age triage tested a single symptom profile — results may not generalize to other clinical presentations.

## Live Dashboards

- **Stock Market:** [wongqihan.com/stockmarket](https://wongqihan.com/stockmarket)
- **Salary Negotiation:** [wongqihan.com/salarynegotiation](https://wongqihan.com/salarynegotiation)
- **Hotel Negotiation:** [wongqihan.com/negotiationlab](https://wongqihan.com/negotiationlab)
- **Prisoner's Dilemma / Price War:** [wongqihan.com/pricewar](https://wongqihan.com/pricewar)
- **Ultimatum Game:** [wongqihan.com/ultimatum](https://wongqihan.com/ultimatum)

## License

MIT
