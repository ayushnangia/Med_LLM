#!/usr/bin/env python3
"""
Evaluate classification results and generate reports.

Usage:
    python scripts/evaluate_results.py
    python scripts/evaluate_results.py --results findings/results_qwen3_latest_*.json

Output:
    findings/evaluation_report.md
    findings/confusion_matrix_{model}.png
    findings/comparison.csv
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Optional imports for visualization
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import seaborn as sns
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False

try:
    from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, f1_score
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


# Configuration
BASE_DIR = Path(__file__).parent.parent
FINDINGS_DIR = BASE_DIR / "findings"

CLASS_NAMES = [
    "nierenzellkarzinom",
    "prostatakarzinom",
    "hodentumor",
    "peniskarzinom",
    "urothelkarzinom",
    "polymalignancy",
    "non_urological"
]

CLASS_SHORT = {
    "nierenzellkarzinom": "NCC",
    "prostatakarzinom": "PCA",
    "hodentumor": "HODEN",
    "peniskarzinom": "PENIS",
    "urothelkarzinom": "UCA",
    "polymalignancy": "COMBI",
    "non_urological": "NON_URO"
}


def load_results(results_path: Path) -> dict:
    """Load results from JSON file."""
    with open(results_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def calculate_metrics(results: dict) -> dict:
    """Calculate detailed metrics from results."""
    predictions = results['predictions']

    y_true = [p['ground_truth'] for p in predictions if p['success']]
    y_pred = [p['predicted'] for p in predictions if p['success']]

    # Per-class metrics
    class_metrics = {}
    for cls in CLASS_NAMES:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p == cls)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != cls and p == cls)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p != cls)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        class_metrics[cls] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": sum(1 for t in y_true if t == cls)
        }

    # Overall metrics
    accuracy = sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true) if y_true else 0

    # Macro average
    macro_precision = sum(m['precision'] for m in class_metrics.values()) / len(class_metrics)
    macro_recall = sum(m['recall'] for m in class_metrics.values()) / len(class_metrics)
    macro_f1 = sum(m['f1'] for m in class_metrics.values()) / len(class_metrics)

    # Average inference time
    times = [p['inference_time'] for p in predictions if p['success']]
    avg_time = sum(times) / len(times) if times else 0

    return {
        "accuracy": accuracy,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "avg_inference_time": avg_time,
        "class_metrics": class_metrics,
        "y_true": y_true,
        "y_pred": y_pred
    }


def create_confusion_matrix_plot(y_true: list, y_pred: list, model_name: str, output_path: Path):
    """Create and save confusion matrix visualization."""
    if not HAS_PLOTTING:
        print("Matplotlib/seaborn not available, skipping plot")
        return

    # Build confusion matrix
    labels = CLASS_NAMES
    short_labels = [CLASS_SHORT[c] for c in labels]

    cm = [[0] * len(labels) for _ in labels]
    for t, p in zip(y_true, y_pred):
        if t in labels and p in labels:
            ti = labels.index(t)
            pi = labels.index(p)
            cm[ti][pi] += 1

    plt.figure(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=short_labels,
                yticklabels=short_labels)
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title(f'Confusion Matrix - {model_name}')
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"Confusion matrix saved to: {output_path}")


def generate_report(all_results: list, output_path: Path):
    """Generate markdown evaluation report."""
    report = []
    report.append("# Classification Evaluation Report\n")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Summary table
    report.append("## Model Comparison\n")
    report.append("| Model | Accuracy | F1 (macro) | Avg Time (s) |")
    report.append("|-------|----------|------------|--------------|")

    for result_data in all_results:
        model = result_data['metadata']['model']
        metrics = result_data['metrics']
        report.append(f"| {model} | {metrics['accuracy']:.2%} | {metrics['macro_f1']:.3f} | {metrics['avg_inference_time']:.2f} |")

    report.append("")

    # Per-model details
    for result_data in all_results:
        model = result_data['metadata']['model']
        metrics = result_data['metrics']

        report.append(f"## {model}\n")
        report.append(f"- **Total Cases:** {result_data['metadata']['total_cases']}")
        report.append(f"- **Accuracy:** {metrics['accuracy']:.2%}")
        report.append(f"- **Macro F1:** {metrics['macro_f1']:.3f}")
        report.append("")

        # Per-class table
        report.append("### Per-Class Metrics\n")
        report.append("| Class | Precision | Recall | F1 | Support |")
        report.append("|-------|-----------|--------|-----|---------|")

        for cls in CLASS_NAMES:
            cm = metrics['class_metrics'].get(cls, {})
            short = CLASS_SHORT[cls]
            report.append(f"| {short} | {cm.get('precision', 0):.3f} | {cm.get('recall', 0):.3f} | {cm.get('f1', 0):.3f} | {cm.get('support', 0)} |")

        report.append("")

        # Misclassifications
        report.append("### Misclassifications\n")
        errors = [p for p in result_data['predictions'] if not p['correct'] and p['success']]
        if errors:
            for e in errors[:10]:  # Show first 10
                report.append(f"- **{e['case_id']}** ({e['patient_name']}): predicted `{e['predicted']}`, actual `{e['ground_truth']}`")
            if len(errors) > 10:
                report.append(f"- ... and {len(errors) - 10} more")
        else:
            report.append("No misclassifications!")

        report.append("")

    # Save report
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    print(f"Report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate classification results")
    parser.add_argument("--results", type=str, nargs="*",
                        help="Result JSON files to evaluate (default: all in findings/)")

    args = parser.parse_args()

    # Find result files
    if args.results:
        result_files = [Path(r) for r in args.results]
    else:
        result_files = sorted(FINDINGS_DIR.glob("results_*.json"))

    if not result_files:
        print("No result files found. Run classify_cases.py first.")
        return

    print(f"Found {len(result_files)} result file(s)")

    # Load and evaluate each
    all_results = []
    for result_file in result_files:
        print(f"\nEvaluating: {result_file.name}")
        results = load_results(result_file)
        metrics = calculate_metrics(results)
        results['metrics'] = metrics
        all_results.append(results)

        # Create confusion matrix plot
        model_safe = results['metadata']['model'].replace(":", "_").replace("/", "_")
        plot_path = FINDINGS_DIR / f"confusion_matrix_{model_safe}.png"
        create_confusion_matrix_plot(metrics['y_true'], metrics['y_pred'],
                                    results['metadata']['model'], plot_path)

    # Generate report
    report_path = FINDINGS_DIR / "evaluation_report.md"
    generate_report(all_results, report_path)

    # Print summary
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    for result_data in all_results:
        model = result_data['metadata']['model']
        metrics = result_data['metrics']
        print(f"\n{model}:")
        print(f"  Accuracy: {metrics['accuracy']:.2%}")
        print(f"  Macro F1: {metrics['macro_f1']:.3f}")
        print(f"  Avg Time: {metrics['avg_inference_time']:.2f}s/case")


if __name__ == "__main__":
    main()
