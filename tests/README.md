# Tests

This directory contains the testing infrastructure for evaluating the nano-agent on SWE-Bench problems.

## Overview

The test suite evaluates the agent's ability to solve software engineering problems by:
- Running the agent on curated SWE-Bench problem sets
- Comparing generated patches against expected solutions
- Tracking performance metrics and resource usage
- Maintaining baselines for regression testing

## Files

### Core Testing
- **`swe_bench.py`** - Main test runner for SWE-Bench evaluation
  - Runs problems in parallel with configurable repetitions
  - Calculates similarity scores between generated and expected patches
  - Tracks token usage, tool usage, and success rates
  - Saves results as baseline files for comparison

- **`compare_baselines.py`** - Baseline comparison tool
  - Compares performance between different agent versions
  - Shows per-problem improvements/regressions
  - Analyzes token usage changes
  - Identifies biggest performance deltas

- **`utils.py`** - Utility functions
  - Repository cloning at specific commits
  - Patch similarity calculation using sequence matching
  - Safe temporary directory cleanup

### Test Data
- **`data/`** - Test datasets and results
  - `swe_bench_lite_subset.json` - Curated subset of SWE-Bench Lite problems
  - `swe_bench_verified_subset.json` - Verified SWE-Bench problems
  - `baselines/` - Stored baseline results for version comparison

## Usage

### Running Tests
```bash
# Run on SWE-Bench Lite subset (default)
python tests/swe_bench.py

# Run on verified subset (harder problems)
python tests/swe_bench.py --verified

# Quick test with only 3 problems
python tests/swe_bench.py --quick

# Run with multiple repetitions and custom settings
python tests/swe_bench.py --repetitions 3 --max-workers 4 --model "openrouter/openai/gpt-4o"

# Save results as a new baseline (for future comparisons)
python tests/swe_bench.py --baseline

# Run tests AND compare results against an existing baseline
python tests/swe_bench.py --compare nano_1.1.0_70e60379_lite
```

### Comparing Baselines (without running new tests)
```bash
# Use default comparison between predefined baselines
python tests/compare_baselines.py

# Compare two existing baselines
python tests/compare_baselines.py --baseline1 nano_1.1.0_70e60379_lite --baseline2 nano_2.0.0_d79af850_lite
```

## Metrics

The test suite tracks:
- **Success Rate**: Percentage of problems solved (similarity > 0.3)
- **Similarity Score**: Sequence matching between expected and generated patches
- **Token Usage**: Total tokens consumed per problem
- **Tool Usage**: Number of tool calls made per problem

Results include both per-problem statistics and aggregate metrics with standard deviations for multiple repetitions. 