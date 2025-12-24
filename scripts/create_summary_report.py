#!/usr/bin/env python3
"""
Create summary report and visualizations for OpenRouter classification results.
Designed for non-technical audience presentation.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import seaborn as sns

# Set style for clean, professional plots
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'
plt.rcParams['font.size'] = 12
plt.rcParams['axes.titlesize'] = 14
plt.rcParams['axes.labelsize'] = 12

# German labels for cancer types (user-friendly)
CANCER_LABELS = {
    'nierenzellkarzinom': 'Kidney Cancer',
    'prostatakarzinom': 'Prostate Cancer',
    'hodentumor': 'Testicular Cancer',
    'peniskarzinom': 'Penile Cancer',
    'urothelkarzinom': 'Bladder Cancer',
    'polymalignancy': 'Multiple Cancers',
    'non_urological': 'Non-Urological'
}

# Friendly model names
MODEL_NAMES = {
    'anthropic/claude-opus-4.5': 'Claude Opus 4.5',
    'openai/gpt-5.2': 'GPT-5.2',
    'google/gemini-3-flash-preview': 'Gemini 3 Flash',
    'google/gemini-3-pro-preview': 'Gemini 3 Pro',
    'google/gemma-3-27b-it': 'Gemma 3 (27B)',
    'google/gemma-3-12b-it': 'Gemma 3 (12B)',
    'google/gemma-3-4b-it': 'Gemma 3 (4B)',
    'google/gemma-3n-e4b-it': 'Gemma 3n (E4B)',
    'deepseek/deepseek-v3.2': 'DeepSeek v3.2',
    'moonshotai/kimi-k2-thinking': 'Kimi K2',
    'essentialai/rnj-1-instruct': 'RNJ-1',
    'nvidia/nemotron-3-nano-30b-a3b:free': 'Nemotron 3 (Free)',
    'xiaomi/mimo-v2-flash:free': 'MiMo v2 (Free)',
    'allenai/olmo-3.1-32b-think:free': 'OLMo 3.1 (Free)'
}


def load_all_results(results_dir):
    """Load all summary.json files from results directory."""
    results = []
    results_path = Path(results_dir)

    for model_dir in results_path.iterdir():
        if not model_dir.is_dir():
            continue

        # Find the latest run for each model
        runs = sorted(model_dir.iterdir(), reverse=True)
        if not runs:
            continue

        latest_run = runs[0]
        summary_file = latest_run / 'summary.json'

        if summary_file.exists():
            with open(summary_file) as f:
                data = json.load(f)
                data['model_folder'] = model_dir.name
                data['run_folder'] = latest_run.name
                results.append(data)

    return results


def load_individual_results(results_dir, model_folder, run_folder):
    """Load individual case results for a specific model run."""
    run_path = Path(results_dir) / model_folder / run_folder
    case_results = []

    for f in run_path.glob('*.json'):
        if f.name != 'summary.json':
            with open(f) as file:
                case_results.append(json.load(file))

    return case_results


def get_friendly_name(model_id):
    """Get user-friendly model name."""
    return MODEL_NAMES.get(model_id, model_id.split('/')[-1])


def create_accuracy_chart(results, output_dir):
    """Create horizontal bar chart of model accuracy."""
    # Filter out failed models and sort by accuracy
    valid_results = [r for r in results if r.get('accuracy', 0) > 0]
    valid_results.sort(key=lambda x: x.get('accuracy', 0), reverse=True)

    if not valid_results:
        print("No valid results to plot")
        return

    models = [get_friendly_name(r['model']) for r in valid_results]
    accuracies = [r['accuracy'] * 100 for r in valid_results]

    # Color coding: green for >90%, yellow for 70-90%, red for <70%
    colors = []
    for acc in accuracies:
        if acc >= 90:
            colors.append('#2ecc71')  # Green
        elif acc >= 70:
            colors.append('#f39c12')  # Yellow/Orange
        else:
            colors.append('#e74c3c')  # Red

    fig, ax = plt.subplots(figsize=(12, 8))

    bars = ax.barh(models, accuracies, color=colors, edgecolor='white', height=0.7)

    # Add value labels on bars
    for bar, acc in zip(bars, accuracies):
        width = bar.get_width()
        ax.text(width + 1, bar.get_y() + bar.get_height()/2,
                f'{acc:.1f}%', va='center', fontsize=11, fontweight='bold')

    ax.set_xlabel('Accuracy (%)', fontsize=13)
    ax.set_title('AI Model Accuracy in Cancer Classification\n(German Medical Oncology Cases)',
                 fontsize=16, fontweight='bold', pad=20)
    ax.set_xlim(0, 105)

    # Add legend
    legend_elements = [
        mpatches.Patch(facecolor='#2ecc71', label='Excellent (≥90%)'),
        mpatches.Patch(facecolor='#f39c12', label='Good (70-90%)'),
        mpatches.Patch(facecolor='#e74c3c', label='Needs Improvement (<70%)')
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10)

    # Add vertical line at 80% threshold
    ax.axvline(x=80, color='gray', linestyle='--', alpha=0.5, linewidth=1)
    ax.text(81, len(models)-0.5, '80% threshold', fontsize=9, color='gray')

    plt.tight_layout()
    plt.savefig(output_dir / 'accuracy_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: accuracy_comparison.png")


def create_confusion_matrix(results, results_dir, output_dir):
    """Create confusion matrix for best performing model."""
    # Find best model
    valid_results = [r for r in results if r.get('accuracy', 0) > 0]
    if not valid_results:
        return

    best = max(valid_results, key=lambda x: x.get('accuracy', 0))

    # Load individual results
    case_results = load_individual_results(
        results_dir, best['model_folder'], best['run_folder']
    )

    # Build confusion matrix
    categories = list(CANCER_LABELS.keys())
    n_cats = len(categories)
    matrix = np.zeros((n_cats, n_cats), dtype=int)

    for case in case_results:
        if case.get('ground_truth') and case.get('output'):
            true_labels = case['ground_truth']
            pred_labels = case['output'].get('classification', [])

            # Handle both old (string) and new (list) format
            if isinstance(true_labels, str):
                true_labels = [true_labels]
            if isinstance(pred_labels, str):
                pred_labels = [pred_labels]

            # For confusion matrix, use first label from each
            true_label = true_labels[0] if true_labels else None
            pred_label = pred_labels[0] if pred_labels else None

            if true_label in categories and pred_label in categories:
                true_idx = categories.index(true_label)
                pred_idx = categories.index(pred_label)
                matrix[true_idx, pred_idx] += 1

    # Create heatmap
    fig, ax = plt.subplots(figsize=(10, 8))

    # Use friendly labels
    labels = [CANCER_LABELS[cat] for cat in categories]

    sns.heatmap(matrix, annot=True, fmt='d', cmap='Blues',
                xticklabels=labels, yticklabels=labels,
                ax=ax, cbar_kws={'label': 'Number of Cases'})

    ax.set_xlabel('Predicted Cancer Type', fontsize=12)
    ax.set_ylabel('Actual Cancer Type', fontsize=12)
    ax.set_title(f'Classification Results: {get_friendly_name(best["model"])}\n(Accuracy: {best["accuracy"]*100:.1f}%)',
                 fontsize=14, fontweight='bold', pad=20)

    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)

    plt.tight_layout()
    plt.savefig(output_dir / 'confusion_matrix.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: confusion_matrix.png")


def create_speed_accuracy_plot(results, output_dir):
    """Create scatter plot of speed vs accuracy."""
    valid_results = [r for r in results if r.get('accuracy', 0) > 0
                     and r.get('elapsed_seconds', 0) > 0]

    if not valid_results:
        return

    fig, ax = plt.subplots(figsize=(12, 8))

    for r in valid_results:
        acc = r['accuracy'] * 100
        # Calculate average time per case
        total_time = r.get('elapsed_seconds', 0)
        total_cases = r.get('total_cases', 26)
        time = total_time / total_cases if total_cases > 0 else 0
        name = get_friendly_name(r['model'])

        # Color by accuracy
        if acc >= 90:
            color = '#2ecc71'
        elif acc >= 70:
            color = '#f39c12'
        else:
            color = '#e74c3c'

        ax.scatter(time, acc, s=200, c=color, edgecolor='white', linewidth=2, alpha=0.8)
        ax.annotate(name, (time, acc), textcoords="offset points",
                   xytext=(8, 0), ha='left', fontsize=9)

    ax.set_xlabel('Average Response Time (seconds)', fontsize=12)
    ax.set_ylabel('Accuracy (%)', fontsize=12)
    ax.set_title('Speed vs Accuracy Trade-off\n(Faster is left, more accurate is up)',
                 fontsize=14, fontweight='bold', pad=20)

    # Add quadrant labels
    ax.axhline(y=85, color='gray', linestyle='--', alpha=0.3)
    ax.axvline(x=5, color='gray', linestyle='--', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_dir / 'speed_vs_accuracy.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: speed_vs_accuracy.png")


def create_category_accuracy(results, results_dir, output_dir):
    """Create per-category accuracy for best model."""
    valid_results = [r for r in results if r.get('accuracy', 0) > 0]
    if not valid_results:
        return

    best = max(valid_results, key=lambda x: x.get('accuracy', 0))

    # Load individual results
    case_results = load_individual_results(
        results_dir, best['model_folder'], best['run_folder']
    )

    # Calculate per-category accuracy
    category_stats = defaultdict(lambda: {'correct': 0, 'total': 0})

    for case in case_results:
        if case.get('ground_truth') and case.get('output'):
            true_labels = case['ground_truth']
            pred_labels = case['output'].get('classification', [])

            # Handle both old (string) and new (list) format
            if isinstance(true_labels, str):
                true_labels = [true_labels]
            if isinstance(pred_labels, str):
                pred_labels = [pred_labels]

            # For category accuracy, use first label
            true_label = true_labels[0] if true_labels else None
            pred_label = pred_labels[0] if pred_labels else None

            if true_label:
                category_stats[true_label]['total'] += 1
                if set(true_labels) == set(pred_labels):
                    category_stats[true_label]['correct'] += 1

    # Prepare data
    categories = []
    accuracies = []
    totals = []

    for cat in CANCER_LABELS.keys():
        if cat in category_stats and category_stats[cat]['total'] > 0:
            stats = category_stats[cat]
            categories.append(CANCER_LABELS[cat])
            accuracies.append(stats['correct'] / stats['total'] * 100)
            totals.append(stats['total'])

    # Create chart
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = ['#2ecc71' if a == 100 else '#f39c12' if a >= 70 else '#e74c3c' for a in accuracies]
    bars = ax.bar(categories, accuracies, color=colors, edgecolor='white')

    # Add count labels
    for bar, total, acc in zip(bars, totals, accuracies):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 2,
                f'{acc:.0f}%\n(n={total})', ha='center', fontsize=10)

    ax.set_ylabel('Accuracy (%)', fontsize=12)
    ax.set_title(f'Accuracy by Cancer Type: {get_friendly_name(best["model"])}',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_ylim(0, 115)

    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(output_dir / 'category_accuracy.png', dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: category_accuracy.png")


def create_summary_report(results, output_dir):
    """Create markdown summary report."""
    valid_results = [r for r in results if r.get('accuracy', 0) > 0]
    failed_results = [r for r in results if r.get('accuracy', 0) == 0]

    if not valid_results:
        print("No valid results for report")
        return

    valid_results.sort(key=lambda x: x.get('accuracy', 0), reverse=True)
    best = valid_results[0]

    report = f"""# AI Model Evaluation: Medical Cancer Classification

## Executive Summary

We tested **{len(results)} AI models** on their ability to classify German medical oncology cases
into the correct cancer type. The cases come from real tumor board discussions.

### Key Findings

- **Best Performing Model:** {get_friendly_name(best['model'])}
- **Top Accuracy:** {best['accuracy']*100:.1f}%
- **Cases Tested:** {best.get('total_cases', 26)} per model
- **Cancer Types:** 7 categories (5 urological + multiple cancers + non-urological)

---

## Model Rankings

| Rank | Model | Accuracy | Avg Response Time |
|------|-------|----------|-------------------|
"""

    for i, r in enumerate(valid_results, 1):
        acc = r['accuracy'] * 100
        total_time = r.get('elapsed_seconds', 0)
        total_cases = r.get('total_cases', 26)
        avg_time = total_time / total_cases if total_cases > 0 else 0
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else ""
        report += f"| {i} {emoji} | {get_friendly_name(r['model'])} | {acc:.1f}% | {avg_time:.2f}s |\n"

    if failed_results:
        report += f"\n*{len(failed_results)} models failed to complete the test (API errors)*\n"

    report += f"""

---

## What This Means

### For Clinical Use

"""

    if best['accuracy'] >= 0.90:
        report += """The top-performing models achieve **over 90% accuracy**, which is promising for
clinical decision support. However, this is an initial benchmark and further validation
with larger datasets and clinical review is essential before any real-world deployment.

"""
    else:
        report += """Current accuracy levels suggest these models should be used as **assistive tools only**,
with all classifications reviewed by medical professionals.

"""

    report += f"""### Cancer Types Tested

| German Term | English | Description |
|-------------|---------|-------------|
| Nierenzellkarzinom | Kidney Cancer | Renal cell carcinoma |
| Prostatakarzinom | Prostate Cancer | Adenocarcinoma of the prostate |
| Hodentumor | Testicular Cancer | Germ cell and other testicular tumors |
| Peniskarzinom | Penile Cancer | Squamous cell carcinoma of the penis |
| Urothelkarzinom | Bladder Cancer | Transitional cell carcinoma |
| Polymalignancy | Multiple Cancers | Patients with more than one cancer type |
| Non-Urological | Non-Urological | Cancers outside the urological system |

---

## Visualizations

1. **accuracy_comparison.png** - Model accuracy ranking
2. **confusion_matrix.png** - Detailed classification results
3. **speed_vs_accuracy.png** - Speed vs accuracy trade-off
4. **category_accuracy.png** - Accuracy by cancer type

---

## Methodology

- **Dataset:** {best.get('total_cases', 26)} German medical oncology cases
- **Source:** Anonymized tumor board discussions
- **Task:** Classify each case into one of 7 cancer categories
- **Models:** Tested via OpenRouter API (commercial LLM providers)
- **Date:** December 2025

---

*Report generated automatically from classification experiments.*
"""

    with open(output_dir / 'SUMMARY_REPORT.md', 'w') as f:
        f.write(report)
    print(f"Saved: SUMMARY_REPORT.md")


def main():
    # Paths
    results_dir = Path('/Users/fortuna/Desktop/Colab/Med_LLM/results/openrouter')
    output_dir = Path('/Users/fortuna/Desktop/Colab/Med_LLM/findings')
    output_dir.mkdir(exist_ok=True)

    print("Loading results...")
    results = load_all_results(results_dir)
    print(f"Found {len(results)} model runs")

    print("\nCreating visualizations...")
    create_accuracy_chart(results, output_dir)
    create_confusion_matrix(results, results_dir, output_dir)
    create_speed_accuracy_plot(results, output_dir)
    create_category_accuracy(results, results_dir, output_dir)

    print("\nGenerating summary report...")
    create_summary_report(results, output_dir)

    print(f"\n✅ All outputs saved to: {output_dir}")


if __name__ == '__main__':
    main()
