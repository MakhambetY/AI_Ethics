# run.py
from config import L4_INDICATORS
from aggregate_and_report import run_all, save_json, save_markdown

def main():
    indicators = list(L4_INDICATORS.keys())
    results = run_all(indicators)

    save_json("hai_l4_results.json", results)
    save_markdown("hai_l4_report.md", results)

    print("Done. Outputs:")
    print("- hai_l4_results.json")
    print("- hai_l4_report.md")

if __name__ == "__main__":
    main()