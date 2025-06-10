# Testing Suite Expansion TODO

## 🎯 Goal: Diversify Beyond SWE-Bench

SWE-Bench has become "saturated" - models likely memorize solutions rather than solving them. We need fresh, diverse challenges while maintaining our excellent baseline/leaderboard infrastructure.

## 🏗️ Architecture Strategy

### ✅ Keep Working (Backwards Compatible)
- `swe_bench.py` - Continue supporting existing baselines/workflows
- `baseline.py` - Core baseline management (universal)
- `analyze.py` - Analysis works across all test types
- `leaderboard.py` - Aggregate rankings across benchmark types
- All existing baselines and tooling remain functional

### 🔄 Refactor Plan
1. **Extract Common Infrastructure** → `test_runner.py`
   - Problem loading/execution logic
   - Parallel execution with progress tracking
   - Baseline integration and comparison
   - Metric calculation and aggregation

2. **Create Benchmark Plugins** → `benchmarks/`
   - `swe_bench.py` - Current implementation (refactored to use common base)
   - `humaneval.py` - Code generation challenges
   - `livecodebench.py` - Recent programming problems
   - `synthetic.py` - Custom generated challenges
   - `realworld.py` - Fresh GitHub issues

3. **Unified CLI** → `run_tests.py`
   ```bash
   python tests/run_tests.py --benchmark swe_bench --baseline
   python tests/run_tests.py --benchmark humaneval --repetitions 5
   python tests/run_tests.py --benchmark all --quick
   ```

## 📋 New Benchmark Ideas

### 1. 🧪 **HumanEval Plus** (`humaneval.py`)
**What**: Code generation from docstrings with comprehensive test suites
**Why**: Tests pure problem-solving without training data contamination
**Metrics**: Test pass rate, code quality, token efficiency
**Data Source**: HumanEval, MBPP, or custom problems
```python
# Example problem format
{
  "id": "humaneval_001",
  "prompt": "def fizzbuzz(n): # Complete this function...",
  "description": "Return fizzbuzz sequence up to n",
  "test_cases": [...],
  "expected_solution": "...",
  "difficulty": "easy"
}
```

### 2. 🔥 **LiveCodeBench** (`livecodebench.py`) 
**What**: Recent competitive programming problems (post-2024)
**Why**: Guaranteed fresh, unseen during training
**Metrics**: Correctness, time/space complexity, elegance
**Data Source**: Recent Codeforces, LeetCode, AtCoder problems
```python
# Example problem format
{
  "id": "live_2024_001", 
  "title": "Dynamic Array Rotation",
  "description": "...",
  "input_format": "...",
  "output_format": "...",
  "test_cases": [...],
  "time_limit": 2000,
  "memory_limit": 256
}
```

### 3. 🎲 **Synthetic Challenges** (`synthetic.py`)
**What**: Procedurally generated coding problems
**Why**: Infinite fresh problems, controlled difficulty
**Metrics**: Correctness, algorithm choice, code structure
**Categories**: 
- Algorithm implementation (sorting, searching, graph algorithms)
- Data structure usage (trees, heaps, hash maps)
- Mathematical computations
- String/array manipulation
```python
# Example generator
def generate_sorting_problem(difficulty="medium"):
    return {
        "id": f"synthetic_sort_{random_id()}",
        "description": f"Sort array of {size} elements using {algorithm}",
        "input": generate_test_array(size),
        "expected_output": sorted_array,
        "constraints": {...}
    }
```

### 4. 🌍 **Real-World Issues** (`realworld.py`)
**What**: Fresh GitHub issues from popular repos (2024+)
**Why**: Authentic, recent problems with real codebases
**Metrics**: Issue resolution quality, maintainability
**Data Source**: Recent issues from trending repos, excluding those in training data
```python
# Example problem format
{
  "id": "realworld_001",
  "repo": "fastapi/fastapi", 
  "issue_url": "...",
  "issue_title": "Add support for...",
  "issue_body": "...",
  "codebase_context": "...",
  "expected_approach": "..."
}
```

### 5. 🔧 **Code Refactoring** (`refactor.py`)
**What**: Improve existing code quality/performance  
**Why**: Tests understanding and optimization skills
**Metrics**: Performance improvement, readability, correctness
```python
# Example problem format
{
  "id": "refactor_001",
  "task": "Optimize this O(n²) algorithm to O(n log n)",
  "original_code": "...",
  "requirements": ["maintain API", "improve performance"],
  "test_suite": [...],
  "quality_metrics": ["time_complexity", "readability"]
}
```

## 🛠️ Implementation Plan

### Phase 1: Infrastructure Refactor
- [ ] Extract common test execution logic from `swe_bench.py`
- [ ] Create `test_runner.py` base class
- [ ] Update `swe_bench.py` to use new base (maintain compatibility)
- [ ] Ensure all existing functionality works unchanged

### Phase 2: First New Benchmark  
- [ ] Implement `humaneval.py` as proof of concept
- [ ] Extend leaderboard to show multiple benchmark types
- [ ] Add benchmark selection to CLI
- [ ] Test end-to-end with baseline saving/loading

### Phase 3: Expand Benchmark Suite
- [ ] Add `synthetic.py` with procedural generation
- [ ] Implement `livecodebench.py` with recent problems
- [ ] Create `realworld.py` with GitHub issue integration
- [ ] Add cross-benchmark comparison tools

### Phase 4: Advanced Features
- [ ] Composite scoring across benchmark types
- [ ] Difficulty-adjusted metrics
- [ ] Specialized analysis for different problem types
- [ ] Automated benchmark freshness checks

## 📊 Updated Metrics Framework

### Universal Metrics (All Benchmarks)
- **Success Rate**: Problem solved correctly
- **Token Efficiency**: Tokens per successful solution
- **Tool Efficiency**: Tool calls per successful solution
- **Time to Solution**: Wallclock time per problem

### Benchmark-Specific Metrics
- **SWE-Bench**: Patch similarity score
- **HumanEval**: Test pass rate, code quality score
- **LiveCodeBench**: Time/space complexity achieved
- **Synthetic**: Algorithm correctness, implementation elegance
- **Real-World**: Issue resolution completeness

### Composite Scoring
```python
composite_score = (
    0.4 * normalized_success_rate +
    0.3 * normalized_efficiency +
    0.2 * normalized_quality +
    0.1 * normalized_speed
)
```

## 🔄 Migration Strategy

### Backwards Compatibility
- Keep `python tests/swe_bench.py` working exactly as before
- All existing baselines and commands remain functional
- Gradual migration of power users to new unified CLI
- Maintain existing leaderboard format during transition

### User Communication
- Clear documentation on new capabilities
- Migration guide for power users
- Deprecation timeline (if any) clearly communicated
- Examples showing equivalent old/new commands

## 🎯 Success Criteria

### Technical
- [ ] Zero breaking changes to existing workflows
- [ ] At least 3 new benchmark types implemented
- [ ] Unified leaderboard showing performance across benchmarks
- [ ] 50%+ reduction in code duplication

### Research
- [ ] Identify models that perform well on fresh vs. memorized problems
- [ ] Establish baseline performance on non-SWE-Bench challenges
- [ ] Validate that new benchmarks provide meaningful signal
- [ ] Demonstrate nano-agent's generalization beyond patch generation

## 💡 Future Considerations

### Data Freshness
- Automated pipeline to ingest new problems
- Training data contamination detection
- Benchmark rotation to maintain freshness

### Community Contributions
- Plugin architecture for community-contributed benchmarks
- Standardized problem format specification
- Contribution guidelines and validation tools

### Research Integration
- Integration with academic benchmark releases
- Support for research-specific metrics and analysis
- Publication-ready result formatting and statistics

---

**Next Steps**: Start with Phase 1 infrastructure refactor while maintaining full backwards compatibility with existing SWE-Bench workflows.