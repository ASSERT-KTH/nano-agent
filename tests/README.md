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
  - Integrates with baseline management for comparisons

- **`baseline.py`** - Baseline management and comparison utilities
  - Load and save baseline results
  - Compare performance between different agent versions
  - Generate baseline names with version info
  - Analyze per-problem improvements/regressions
  - Track configuration changes and performance deltas

- **`utils.py`** - Utility functions
  - Repository cloning at specific commits
  - Patch similarity calculation using sequence matching
  - Safe temporary directory cleanup
  - Git commit hash retrieval

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
python tests/swe_bench.py --repetitions 3 --max-workers 4 --model "openrouter/openai/gpt-4.1"

# Save results as a new baseline (for future comparisons)
python tests/swe_bench.py --baseline

# Run tests AND compare results against an existing baseline
python tests/swe_bench.py --compare nano_1.1.0_70e60379_lite
```

### Comparing Baselines (without running new tests)
```bash
# Use default comparison between predefined baselines
python tests/baseline.py

# Compare two existing baselines
python tests/baseline.py nano_1.1.0_70e60379_lite nano_2.0.0_d79af850_lite
```

## Metrics

The test suite tracks:
- **Success Rate**: Percentage of problems solved (similarity > 0.3)
- **Similarity Score**: Sequence matching between expected and generated patches
- **Token Usage**: Total tokens consumed per problem
- **Tool Usage**: Number of tool calls made per problem

Results include both per-problem statistics and aggregate metrics with standard deviations for multiple repetitions.

## Baseline Management

The `baseline.py` module provides comprehensive baseline management:

### Functions
- `load_baseline(name)` - Load a baseline from JSON file
- `save_baseline(name, results, metrics, config)` - Save test results as a new baseline
- `generate_baseline_name(test_set, model)` - Auto-generate baseline names with version info
- `build_config_snapshot(agent_config, test_set, repetitions, max_workers)` - Create reproducible config snapshots
- `compare_baselines(current, baseline, current_config)` - Detailed comparison between baselines

### Comparison Features
- Configuration change tracking (model, version, parameters)
- Per-problem performance analysis
- Token usage optimization insights
- Statistical significance with standard deviations
- Identification of biggest improvements and regressions

The modular design allows easy importing of baseline functions into other scripts and ensures clean separation of concerns between test execution and result management. 