#!/usr/bin/env python3
import json
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# ═══════════════════════════════════════════════════════════════
# SETUP PATHS
# ═══════════════════════════════════════════════════════════════
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_FILE = os.path.join(SCRIPT_DIR, "results.json")
ARTIFACT_DIR = SCRIPT_DIR

def main():
    if not os.path.exists(RESULTS_FILE):
        print(f"Error: {RESULTS_FILE} not found.")
        return

    with open(RESULTS_FILE, "r") as f:
        data = json.load(f)

    # Make sure artifact directory exists
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    models = ["Gemini 3.1 Flash Lite", "GPT-5.4-nano", "Claude Haiku 4.5"]
    # Sorted order requested by user: control, polite, legal threat, aggressive, sob story, public exposure
    strategies = ["control", "polite_persistent", "legal_threat", "aggressive", "sob_story", "public_exposure"]
    
    heatmap_data = np.zeros((len(strategies), len(models)))

    for m_idx, model in enumerate(models):
        for s_idx, strategy in enumerate(strategies):
            strat_results = data.get("results", {}).get(model, {}).get(strategy, {})
            breach_rate = strat_results.get("summary", {}).get("breach_rate_pct", 0.0)
            heatmap_data[s_idx, m_idx] = breach_rate

    # ═══════════════════════════════════════════════════════════════
    # CHART 1: POLICY BREACH HEATMAP
    # ═══════════════════════════════════════════════════════════════
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["Helvetica", "Arial", "DejaVu Sans"]
    
    # 8x6.2 inches, matching signature aspect ratio
    fig, ax = plt.subplots(figsize=(8, 6.2), dpi=300)
    
    # Set cream background for canvas and axes
    bg_color = "#FAF7F2"
    fig.patch.set_facecolor(bg_color)
    ax.set_facecolor(bg_color)
    
    # Custom colormap: 0% is White (#FFFFFF), grading to deep red (#B91C1C)
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "signature_reds", ["#FFFFFF", "#FFF5F5", "#FCA5A5", "#EF4444", "#B91C1C"]
    )
    
    im = ax.imshow(heatmap_data, cmap=cmap, aspect="auto", vmin=0, vmax=100)
    
    # Position tick coordinates
    ax.set_xticks(np.arange(len(models)))
    ax.set_yticks(np.arange(len(strategies)))
    
    # Clean display labels
    display_models = [m.replace(" Lite", "") for m in models]
    display_strategies = [
        "Control",
        "Polite Persistent",
        "Legal Threat",
        "Aggressive",
        "Sob Story",
        "Public Exposure"
    ]
    
    # Set tick labels in signature colors & font sizes
    ax.set_xticklabels(display_models, fontsize=11, fontweight="bold", color="#111827")
    ax.set_yticklabels(display_strategies, fontsize=11, fontweight="bold", color="#111827")
    
    # Remove default tick markers and set padding
    ax.tick_params(axis='both', which='both', length=0, pad=10, colors="#111827")
    
    # Loop over data to draw cell text annotations
    for i in range(len(strategies)):
        for j in range(len(models)):
            val = heatmap_data[i, j]
            if val == 0.0:
                text_color = "#9CA3AF"  # Muted grey for 0%
                font_weight = "normal"
            else:
                text_color = "#FFFFFF" if val >= 50 else "#B91C1C"  # High-contrast text
                font_weight = "bold"
            ax.text(j, i, f"{val:.1f}%",
                    ha="center", va="center", color=text_color, 
                    fontsize=12, fontweight=font_weight)
            
    # Hide all outer spines
    ax.spines[:].set_visible(False)
    
    # Draw a thick divider line between "Control" (row 0) and the rest of the strategies
    ax.axhline(0.5, color="#111827", linewidth=3.5, zorder=3)
    
    # Draw minor grid lines in the cream background color to create card-like gaps between cells
    ax.set_xticks(np.arange(len(models) + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(len(strategies) + 1) - 0.5, minor=True)
    ax.grid(which="minor", color=bg_color, linestyle="-", linewidth=6)
    ax.tick_params(which="minor", bottom=False, left=False)
    
    # Title matching signature typography
    plt.title("Customer Support Policy Breach Heatmap", 
              fontsize=14, fontweight="bold", pad=25, color="#111827")
    
    plt.tight_layout()
    heatmap_path = os.path.join(ARTIFACT_DIR, "policy_breach_heatmap.png")
    plt.savefig(heatmap_path, bbox_inches="tight", facecolor=bg_color)
    plt.close()
    print(f"Saved styled heatmap to {heatmap_path}")

    # ═══════════════════════════════════════════════════════════════
    # CHART 2: ATTRITION CURVES FOR CLAUDE HAIKU 4.5
    # ═══════════════════════════════════════════════════════════════
    target_model = "Claude Haiku 4.5"
    turns = np.arange(9)  # 0 to 8
    
    # Colors matching the strategies
    strategy_colors = {
        "control": "#64748B",           # Slate Grey
        "polite_persistent": "#3B82F6", # Blue
        "aggressive": "#EC4899",        # Pink
        "sob_story": "#F59E0B",         # Amber
        "legal_threat": "#8B5CF6",      # Violet
        "public_exposure": "#EF4444"    # Red
    }
    
    fig, ax = plt.subplots(figsize=(9, 6), dpi=300)
    
    # Plot faint background grid lines
    ax.grid(axis="y", linestyle="--", alpha=0.3, color="#9CA3AF")
    ax.grid(axis="x", linestyle="--", alpha=0.15, color="#9CA3AF")

    model_results = data.get("results", {}).get(target_model, {})
    
    for strategy in strategies:
        strat_runs = model_results.get(strategy, {}).get("runs", [])
        n_runs = len(strat_runs)
        
        # Calculate survival rate at each turn
        survival_rates = [100.0]  # Turn 0 is always 100% compliant
        
        for t in range(1, 9):
            # A run is breached by turn t if breached is True and breach_turn <= t
            breached_by_t = sum(1 for r in strat_runs if r.get("breached", False) and 1 <= r.get("breach_turn", -1) <= t)
            survival_rate = ((n_runs - breached_by_t) / n_runs) * 100.0 if n_runs > 0 else 100.0
            survival_rates.append(survival_rate)
            
        # Plot the line
        ax.plot(turns, survival_rates, 
                label=strategy.replace("_", " ").title(), 
                color=strategy_colors[strategy], 
                linewidth=2.5, 
                marker="o", 
                markersize=6)

    # Style the axes
    ax.set_xlim(-0.2, 8.2)
    ax.set_ylim(-5, 105)
    
    ax.set_xlabel("Conversation Turn Count", fontsize=11, fontweight="bold", labelpad=10)
    ax.set_ylabel("Policy Compliance Rate (%)", fontsize=11, fontweight="bold", labelpad=10)
    
    # Turn x ticks into labels
    ax.set_xticks(turns)
    
    # Hide top/right spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#D1D5DB")
    ax.spines["bottom"].set_color("#D1D5DB")
    
    # Title & Subtitle
    plt.title(f"Customer Support Policy Compliance Decay over Multi-Turn Dialogue\n(Model: {target_model})", 
              fontsize=13, fontweight="bold", pad=20, color="#111827", loc="center")
    
    # Legend
    legend = ax.legend(frameon=True, fontsize=10, loc="lower left")
    legend.get_frame().set_linewidth(0.0)
    legend.get_frame().set_facecolor("#F9FAFB")
    
    # Add annotations for public exposure drop
    ax.annotate("90% caved under Public PR threat", 
                xy=(3, 10), xytext=(4.5, 25),
                arrowprops=dict(facecolor='#EF4444', shrink=0.08, width=1, headwidth=6, headlength=6, edgecolor='none'),
                fontsize=9.5, color="#B91C1C", fontweight="bold")
    
    plt.tight_layout()
    attrition_path = os.path.join(ARTIFACT_DIR, "attrition_curves_haiku.png")
    plt.savefig(attrition_path, bbox_inches="tight")
    plt.close()
    print(f"Saved attrition curves to {attrition_path}")

if __name__ == "__main__":
    main()
