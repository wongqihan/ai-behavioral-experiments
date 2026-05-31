# Salary Negotiation Language Bias: AI Career Coaches Recommend 5x Lower Salaries Based on Prompt Language

**Does an AI career coach recommend different salary anchors for the same role depending on the language of the prompt?**

This experiment tests whether an LLM recommends different salary targets for an identical candidate profile when the prompt language changes. No currency, no location, and no company name appear in the prompt. Language is the only geographic signal. The finding: the model infers the candidate's country from language, picks local currency, and applies local salary norms, producing a **5:1 salary gap** ($29K vs $149K) for the same job.

## Key Finding

The model uses **language as a proxy for geographic location**, then applies the salary norms of the inferred country. The currency it chooses is itself evidence of geographic inference.

- An English prompt recommends **$148,733 USD** (assumes US)
- A Hindi prompt recommends **₹2,400,000 INR (~$28,800 USD)** (assumes India)
- A Japanese prompt recommends **¥10,150,000 JPY (~$68,005 USD)** (assumes Japan)
- Adding "I am based in the United States" to the Hindi prompt raises the recommendation from $28,800 → **$147,200 USD** (+411%)
- Adding "I am based in Mumbai, India" to the English prompt drops it from $148,733 → **$29,280 USD** (-80%)
- Back-translating the Japanese prompt to English yields **$148,233 USD**, confirming the model understood the prompt

## Experiment Design

### Model & Configuration
| Parameter | Value |
|---|---|
| Model | `gemini-3.5-flash` |
| Temperature | 0.3 |
| Runs per condition | 30 |
| Total API calls | ~450 |
| Candidate | 8yr marketing, 3yr management, Senior Marketing Manager at mid-size tech (~500 employees) |
| Currency in prompt | **None** |
| Location in prompt | **None** |

### Test Conditions

1. **Baseline** — Same candidate profile in 6 languages (English, Spanish, Chinese, Hindi, Japanese, Arabic), no location context. 6 × 30 = 180 calls.
2. **US Location Anchor** — Same prompts + "Assume I am based in the United States" appended in each language. 6 × 30 = 180 calls.
3. **Reverse Anchor** — English prompt + "Assume I am based in Tokyo/Mumbai." 2 × 30 = 60 calls.
4. **Back-translation Control** — Japanese prompt translated to English by the same model, then used as input. 30 calls.

### Output Schema

The model returns structured JSON with no currency constraint:

```json
{
  "recommended_salary": 10000000,
  "currency": "JPY",
  "salary_range_low": 9000000,
  "salary_range_high": 12000000,
  "confidence": "High",
  "reasoning": "Brief explanation in English"
}
```

All prompts are semantically equivalent (manually authored, not machine-translated). The system prompt says "Choose the currency that is most appropriate for the candidate" with no default.

### Data Quality

- **450/450 API calls** returned valid, parseable JSON (0 parse failures)
- USD equivalents computed using approximate exchange rates: 1 JPY = $0.0067, 1 INR = $0.012, 1 EUR = $1.10

## Results

### Baseline: Recommended Salary by Language (no location context)

| Language | Currency (n/30) | Avg Salary | ≈ USD Equivalent |
|---|:---:|---:|---:|
| English | USD (30/30) | $148,733 | **$148,733** |
| Arabic | USD (30/30) | $145,333 | **$145,333** |
| Chinese | USD/CNY (mixed) | — | **$140,900** |
| Spanish | EUR (majority) | €79,633 | **$86,663** |
| Japanese | JPY (30/30) | ¥10,150,000 | **$68,005** |
| Hindi | INR (30/30) | ₹2,400,000 | **$28,800** |

The model chose local currency with near-perfect consistency: JPY for Japanese (30/30), INR for Hindi (30/30), EUR for Spanish (majority). English, Arabic, and Chinese defaulted to USD.

The salary gap between English ($148,733) and Hindi ($28,800) is **5.2x** for the identical candidate and role.

### Effect of US Location Anchor

| Language | Default ≈ USD | + US Anchor ≈ USD | Shift |
|---|---:|---:|---:|
| Hindi | $28,800 | **$147,200** | +$118,400 (+411%) |
| Japanese | $68,005 | **$150,000** | +$81,995 (+121%) |
| Spanish | $86,663 | **$147,167** | +$60,504 (+70%) |
| Chinese | $140,900 | **$154,100** | +$13,200 (+9%) |
| Arabic | $145,333 | **$148,667** | +$3,334 (+2%) |
| English | $148,733 | **$148,333** | -$400 (0%) |

Adding "I am based in the United States" causes all 6 languages to converge to **$147K–$154K USD**. The disparity disappears entirely. The model knows US salary norms for every language. It just doesn't apply them unless you specify your location.

### Reverse Anchor (English prompt + foreign location)

| Condition | Currency | ≈ USD |
|---|:---:|---:|
| English (default) | USD | **$148,733** |
| English + "based in Tokyo" | JPY | **$74,147** (-50%) |
| English + "based in Mumbai" | INR | **$29,280** (-80%) |

Explicitly specifying a non-US location overrides the model's default US assumption for English prompts. English + Mumbai ($29,280) matches the Hindi baseline ($28,800), confirming the mechanism: it's not the language, it's the inferred location.

### Back-translation Control

| Condition | Currency | ≈ USD |
|---|:---:|---:|
| Japanese prompt (original) | JPY | **$68,005** |
| Japanese → English back-translation | USD | **$148,233** |

The back-translated prompt produces a salary matching the English baseline ($148,233 vs $148,733), confirming the model comprehends the Japanese prompt equivalently. The ¥10.15M recommendation is not a comprehension failure. It is location inference.

## Interpretation

The model follows this inference chain:

```
Input language → Inferred country → Local currency → Local salary norms → Recommendation
```

- **English** → USA → USD → $148,733
- **Japanese** → Japan → JPY → ¥10,150,000 (~$68K)
- **Hindi** → India → INR → ₹2,400,000 (~$29K)
- **Spanish** → Spain → EUR → €79,633 (~$87K)

This behavior produces appropriate recommendations for a monolingual user in their home country. It fails for:
- **Immigrants** (Hindi speaker negotiating salary in San Francisco gets told $29K instead of $149K)
- **Remote workers** (English speaker applying to a US company from abroad)
- **Multilingual users** (get different advice depending on which language they happen to use)

**Mitigation:** Explicitly specify the candidate's location and target job market in the system prompt. Do not rely on language as a proxy for geography.

## Reproduction

```bash
export GEMINI_API_KEY=your_key_here
python run_experiment.py
```

Results are saved to `results.json`. The script runs all 4 test conditions sequentially (~45 minutes with `gemini-3.5-flash`).

## Repository Structure

```
salary-negotiation-language/
├── README.md             # This file
├── run_experiment.py     # Main experiment script (all conditions)
└── results.json          # Complete results (gemini-3.5-flash)
```
