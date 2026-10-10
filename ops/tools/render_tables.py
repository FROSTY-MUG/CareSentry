"""Table Renderer (O-02)

Renders README / benchmark tables ONLY from result files in eval/results/.
If a result file is missing, the table says "not yet measured".
"""

import json
from pathlib import Path

RESULTS_DIR = Path("eval/results")


def render_markdown_table() -> str:
    lines = [
        "| Model | Total Cases | Violation Recall | False Positive Rate | Omission Recall | Rescue Rate | Status |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: |"
    ]

    # Find all result files
    if not RESULTS_DIR.exists():
        return "| Not yet measured | - | - | - | - | - | ❌ Missing results dir |"

    result_files = list(RESULTS_DIR.glob("*.json"))
    if not result_files:
        return "| Not yet measured | - | - | - | - | - | ❌ No result files found |"

    for f in result_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            model = data.get("model", f.stem)
            metrics = data.get("metrics", {})
            total = metrics.get("total_cases", 0)
            vr = metrics.get("violation_recall", "N/A")
            fpr = metrics.get("false_positive_rate", "N/A")
            or_val = metrics.get("omission_recall", "N/A")
            rr = metrics.get("rescue_rate", "N/A")
            status = "✅ Measured"
            lines.append(f"| {model} | {total} | {vr} | {fpr} | {or_val} | {rr} | {status} |")
        except Exception:
            lines.append(f"| {f.stem} | - | - | - | - | - | ❌ Parse error |")

    return "\n".join(lines)


def main():
    print("=== CareSentry Benchmark Table (O-02) ===")
    table = render_markdown_table()
    print(table)
    
    # Optionally update README if marker found
    readme_path = Path("README.md")
    if readme_path.exists():
        content = readme_path.read_text(encoding="utf-8")
        # Check for marker
        marker = "<!-- BENCHMARK_TABLE_AUTO -->"
        if marker in content:
            # Replace table section
            parts = content.split(marker)
            new_content = parts[0] + marker + "\n\n" + table + "\n\n" + marker + parts[2] if len(parts) > 2 else parts[0] + marker + "\n\n" + table
            readme_path.write_text(new_content, encoding="utf-8")
            print("\nUpdated README.md benchmark table successfully.")


if __name__ == "__main__":
    main()
