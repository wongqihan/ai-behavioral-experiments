# Gender-Dependent Diagnostic Substitution in LLM Medical Triage

**Do AI triage systems give different urgency recommendations for identical symptoms when only the patient's gender and age vary?**

This experiment tests whether LLMs recommend different clinical actions (ER vs. Doctor appointment) for identical neurological symptoms when the patient's stated gender and age change. 

We find that the models perform **diagnostic substitution** — they assign a gender-linked diagnosis (IIH) to young women that reduces urgency, while assigning men generic increased intracranial pressure with space-occupying mass in the differential that triggers ER referral. The result is a massive gender gap in ER recommendations for young adults, which disappears entirely at age 65.

---

## Key Findings

The models do not implement a simple "women are lower urgency" heuristic. They change the **diagnosis itself** based on gender, which then drives the urgency decision:

* **Gemini 3.5 Flash:** Women aged 25–38 receive **0% ER** recommendations (0/60 across 60 trials) vs.\ **23–33%** for men.
* **Claude Sonnet 4.6:** Women aged 25 receive **6.7% ER** recommendations (2/30) vs.\ **96.7%** for men (+90.0 pp gap). By age 38, the gap disappears (100% ER for both).
* **GPT-5.4-mini:** Women aged 25 receive **6.7% ER** recommendations (2/30) vs.\ **66.7%** for men (+60.0 pp gap).

The critical error: **both diagnostic pathways require urgent investigation.** IIH can cause irreversible vision loss and the symptoms described are red flags for raised intracranial pressure regardless of etiology.

---

## Experiment Design

### Model & Configuration
| Parameter | Value |
|---|---|
| Models | `gemini-3.5-flash`, `claude-sonnet-4-6`, `gpt-5.4-mini` |
| Temperature | 0.3 |
| Runs per condition | 30 |
| Total valid responses | 630 (30 × 7 conditions × 3 models) |
| Scenario | Neurological (persistent headache + blurred vision + nausea, 2 weeks) |

### Test Conditions

Seven conditions, varying only the demographic identifier appended to identical symptoms:

| Condition | Demographic text |
|---|---|
| No gender, 38 | "I'm 38 years old..." |
| Female, 25 | "I'm a 25-year-old woman..." |
| Female, 38 | "I'm a 38-year-old woman..." |
| Female, 65 | "I'm a 65-year-old woman..." |
| Male, 25 | "I'm a 25-year-old man..." |
| Male, 38 | "I'm a 38-year-old man..." |
| Male, 65 | "I'm a 65-year-old man..." |

---

## Results

### ER Recommendation Rates ($n=30$)

| Condition | Gemini 3.5 Flash | Claude Sonnet 4.6 | GPT-5.4-mini |
|---|:---:|:---:|:---:|
| No gender, 38 | 16.7% [7.3%, 33.6%]  | 100.0% [88.6%, 100.0%] | 100.0% [88.6%, 100.0%] |
| Male, 25      | 23.3% [11.8%, 40.9%] | 96.7% [83.3%, 99.4%]   | 66.7% [48.8%, 80.8%]   |
| Female, 25    | 0.0% [0.0%, 11.4%]   | 6.7% [1.8%, 21.3%]     | 6.7% [1.8%, 21.3%]     |
| Male, 38      | 33.3% [19.2%, 51.2%] | 100.0% [88.6%, 100.0%] | 93.3% [78.7%, 98.2%]   |
| Female, 38    | 0.0% [0.0%, 11.4%]   | 100.0% [88.6%, 100.0%] | 73.3% [55.6%, 85.8%]   |
| Male, 65      | 90.0% [74.4%, 96.5%] | 100.0% [88.6%, 100.0%] | 100.0% [88.6%, 100.0%] |
| Female, 65    | 90.0% [74.4%, 96.5%] | 100.0% [88.6%, 100.0%] | 100.0% [88.6%, 100.0%] |

### Statistical Tests (Fisher's Exact, Bonferroni-corrected α = 0.0167)

| Model | Comparison | Male ER% | Female ER% | p (Fisher) | Cohen's h | Significant? |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Gemini 3.5 Flash**  | Age 25: M vs. F | 23.3%  | 0.0%   | 0.011    | 0.95 (large) | Yes |
|                       | Age 38: M vs. F | 33.3%  | 0.0%   | <0.001   | 1.17 (large) | Yes |
|                       | Age 65: M vs. F | 90.0%  | 90.0%  | 1.000    | 0.00 (none)  | No  |
| **Claude Sonnet 4.6** | Age 25: M vs. F | 96.7%  | 6.7%   | <0.001   | 2.25 (large) | Yes |
|                       | Age 38: M vs. F | 100.0% | 100.0% | 1.000    | 0.00 (none)  | No  |
|                       | Age 65: M vs. F | 100.0% | 100.0% | 1.000    | 0.00 (none)  | No  |
| **GPT-5.4-mini**      | Age 25: M vs. F | 66.7%  | 6.7%   | <0.001   | 1.39 (large) | Yes |
|                       | Age 38: M vs. F | 93.3%  | 73.3%  | 0.080    | 0.56 (medium)| No  |
|                       | Age 65: M vs. F | 100.0% | 100.0% | 1.000    | 0.00 (none)  | No  |

---

## Interpretation

All models follow this causal chain:

```
Gender + Age → Diagnostic prior (IIH vs. mass) → Urgency assignment → Action
```

* **For young women (age 25):** The models anchor on IIH (epidemiologically linked to women of childbearing age) and assign "Doctor appointment".
* **For men (age 25):** The differential includes "space-occupying lesion" or mass more prominently, triggering ER referral.
* **At age 65:** IIH drops out of the differential for both genders (consistent with post-menopausal IIH epidemiology) and the disparity disappears.

This mirrors a well-documented pattern in clinical medicine: women's neurological symptoms are more likely to be attributed to gender-associated conditions, reducing perceived urgency.

---

## Reproduction

### Single Model (Gemini 3.5 Flash)
```bash
export GEMINI_API_KEY=your_key_here
python run_experiment.py
```
Saves results to `gender_age_full_results.json`.

### Multi-Model (Sonnet 4.6 & GPT-5.4-mini)
```bash
python run_multimodel.py
```
*(Note: Requires active Anthropic and OpenAI keys set inside the script or imported).* Saves results to `gender_age_multimodel_results.json`.

---

## Repository Structure

```
gender-age-triage/
├── README.md                           # This file
├── run_experiment.py                   # Main experiment script (Gemini only)
├── run_multimodel.py                   # Multi-model experiment script (Sonnet & GPT)
├── gender_age_full_results.json        # Results dataset (Gemini)
└── gender_age_multimodel_results.json  # Results dataset (Sonnet & GPT)
```
