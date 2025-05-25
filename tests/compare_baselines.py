#!/usr/bin/env python3

import argparse
from pathlib import Path
from swe_bench import load_baseline, compare_baselines

def main():
    parser = argparse.ArgumentParser(description="Compare two SWE-Bench baselines")
    parser.add_argument("baseline1", nargs='?', default="nano_1.1.0_70e60379_lite_gpt-4.1-mini", help="First baseline to compare (default: nano_1.1.0_70e60379_lite_gpt-4.1-mini)")
    parser.add_argument("baseline2", nargs='?', default="nano_2.0.0_d79af850_lite_gpt-4.1-mini", help="Second baseline to compare (default: nano_2.0.0_d79af850_lite_gpt-4.1-mini)")
    
    args = parser.parse_args()
    
    try:
        # Load both baselines
        baseline1 = load_baseline(args.baseline1)
        baseline2 = load_baseline(args.baseline2)
        
        print(f"📊 Comparing baselines:")
        print(f"  {baseline1['name']} vs {baseline2['name']}")
        
        # Use the existing compare_baselines function from swe_bench
        # We'll treat baseline2 as "current" and baseline1 as "baseline"
        compare_baselines(baseline2["metrics"], baseline1, baseline2.get("config"))
        
    except FileNotFoundError as e:
        print(f"⚠️  Error: {e}")
        
        # Show available baselines
        baselines_dir = Path(__file__).parent / "data" / "baselines"
        if baselines_dir.exists():
            available = [f.stem for f in baselines_dir.glob("*.json")]
            print(f"Available baselines: {', '.join(available) if available else 'none'}")

if __name__ == "__main__":
    main() 