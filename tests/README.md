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

- **`analyze.py`** - Comprehensive baseline analysis tool
  - Groups baselines by version and model for easy comparison
  - Ranks performance by any metric (success, similarity, tokens, tools)
  - Shows version evolution and model comparisons
  - Search and filter baseline collections
  - Clean tabular output with context-aware column display

- **`leaderboard.py`** - Automatic leaderboard generation
  - Updates main README.md with current performance rankings
  - Automatically triggered when saving new baselines (`--baseline`)
  - Can be run manually to refresh leaderboard
  - Ranks by similarity score (most important metric)

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

# Save results as a new baseline (automatically updates leaderboard)
python tests/swe_bench.py --baseline

# Run tests AND compare results against an existing baseline
python tests/swe_bench.py --compare nano_1.1.0_70e60379_lite
```

### Analyzing Baselines
```bash
# Show summary of all baseline groups
python tests/analyze.py

# Find top performers by different metrics
python tests/analyze.py --highest success_rate
python tests/analyze.py --highest avg_similarity
python tests/analyze.py --lowest avg_tokens
python tests/analyze.py --lowest avg_tools

# Compare models for a specific version
python tests/analyze.py --compare-models 3.1.1

# Track evolution of a model across versions
python tests/analyze.py --evolution deepseek-chat

# Search baselines by pattern
python tests/analyze.py --search "deepseek"
```

### Comparing Specific Baselines (without running new tests)
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

## Baseline Analysis

### Collection Analysis (`analyze.py`)
The analysis tool automatically groups baselines by (version, model) and provides multiple views:

**Summary View**: Shows latest performance for each group with automatic history for multi-baseline groups
**Ranking Views**: Top performers by any metric with context-aware column display
**Comparison Views**: Side-by-side model comparisons or version evolution tracking
**Search**: Pattern-based filtering with detailed baseline information

### Individual Comparisons (`baseline.py`)
For detailed comparison between two specific baselines:

**Functions**:
- `load_baseline(name)` - Load a baseline from JSON file
- `save_baseline(name, results, metrics, config)` - Save test results as a new baseline
- `generate_baseline_name(test_set, model)` - Auto-generate baseline names with version info
- `build_config_snapshot(agent_config, test_set, repetitions, max_workers)` - Create reproducible config snapshots
- `compare_baselines(current, baseline, current_config)` - Detailed comparison between baselines

**Features**:
- Configuration change tracking (model, version, parameters)
- Per-problem performance analysis
- Token usage optimization insights
- Statistical significance with standard deviations
- Identification of biggest improvements and regressions

The modular design allows easy importing of baseline functions into other scripts and ensures clean separation of concerns between test execution and result management. 