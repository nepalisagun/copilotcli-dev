# Autonomous Agent Specifications

## CODEGEN_AGENT (OpenClaw Enhanced)

### Identity
**Role:** ML Code Generator with Self-Healing Capabilities  
**Autonomy Level:** High (auto-fix, retry, commit)  
**Primary Task:** Generate production ML code following established patterns  

### Capabilities

```yaml
Identity:
  name: "CODEGEN_AGENT"
  variant: "OpenClaw Enhanced"
  purpose: "Autonomous ML code generation with self-correction"

Tools:
  - gh copilot suggest       # Primary code generation
  - pytest --cov             # Test validation
  - docker build             # Container verification
  - git operations           # Auto-commit on success

Knowledge:
  - @knowledge/ml-best-practices.md (379 lines)
    ├─ FastAPI async patterns
    ├─ XGBoost implementation (500 estimators)
    ├─ Testing strategy (90%+ coverage)
    ├─ Docker multi-stage builds
    ├─ MLflow integration
    ├─ Kubernetes readiness
    ├─ Monitoring & observability
    └─ Production checklist

  - @knowledge/notes.md (621 lines)
    ├─ Code style guide
    ├─ Testing standards
    ├─ Docker best practices
    ├─ Git workflow
    ├─ Kubernetes patterns
    └─ Pre-deployment validation

  - @knowledge/stock-features.md (174 lines)
    ├─ Technical indicators (RSI, MACD, BBands)
    ├─ Feature engineering patterns
    ├─ Data validation approaches
    └─ Volatility calculations

  - @knowledge/data/stocks-1k.csv
    └─ Real OHLCV training data (1000 rows)

Skills:
  - "Read @knowledge/ml-best-practices.md before coding"
  - "If pytest fails <5%, auto-fix and retry"
  - "Commit only if tests pass + coverage >90%"
  - "Use XGBoost (500 estimators, max_depth=6)"
  - "Implement 11+ engineered features"
  - "Add type hints + docstrings"
  - "Follow async/await patterns"
  - "Include health checks + readiness probes"

Constraints:
  - Must achieve 90%+ test coverage
  - Must pass all pytest validations
  - Must use Pydantic v2 for validation
  - Must implement async endpoints
  - Must not commit broken code
  - Must reference knowledge base files
  - Max 3 auto-fix retry attempts before escalation
```

### Execution Flow

```
1. RECEIVE TASK
   ├─ Parse GitHub trigger
   ├─ Validate task scope
   └─ Extract context (@knowledge/ files, @src/ files)

2. KNOWLEDGE RETRIEVAL
   ├─ Read ml-best-practices.md (patterns)
   ├─ Read notes.md (style guide)
   ├─ Check stock-features.md (feature engineering)
   └─ Load training data (stocks-1k.csv)

3. CODE GENERATION
   ├─ Use gh copilot suggest with full context
   ├─ Include knowledge file references
   ├─ Follow established patterns
   └─ Add type hints + docstrings

4. TESTING & VALIDATION
   ├─ Run pytest --cov
   ├─ Check coverage >90%
   ├─ Validate imports
   ├─ Check for lint errors
   └─ If pass: proceed to COMMIT
      If fail: proceed to AUTO-FIX (up to 3 times)

5. AUTO-FIX LOOP (If Failures <5%)
   ├─ Analyze test failures
   ├─ Request gh copilot fix
   ├─ Re-run pytest
   ├─ If pass: proceed to COMMIT
   └─ If fail after 3 attempts: ESCALATE

6. CONTAINER VALIDATION
   ├─ docker build -t [service] .
   ├─ Verify no build errors
   └─ Test healthcheck endpoint

7. COMMIT (Only if all checks pass)
   ├─ git add [modified files]
   ├─ git commit -m "feat: [feature] with [coverage%]% coverage"
   ├─ git push origin [branch]
   └─ Create PR with test results

8. REPORT RESULTS
   ├─ Post PR comment with metrics
   ├─ Attach coverage report
   ├─ Link to successful tests
   └─ Request review from team
```

### Self-Healing Logic

```python
class CodegenAgentSelfHealing:
    
    def __init__(self):
        self.max_retries = 3
        self.min_coverage = 90
        self.acceptable_failure_rate = 0.05
    
    def generate_code(self, task_context):
        """Generate code using gh copilot suggest."""
        prompt = self._build_knowledge_driven_prompt(task_context)
        code = run_copilot_suggest(prompt)
        return code
    
    def validate_code(self, code_path):
        """Run tests and coverage validation."""
        result = run_pytest_with_coverage(code_path)
        return result
    
    def auto_fix(self, errors, attempt=1):
        """Auto-fix code failures up to max_retries times."""
        if attempt > self.max_retries:
            return {"status": "ESCALATE", "reason": "Max retries exceeded"}
        
        fix_prompt = f"""
        The following tests failed:
        {errors}
        
        Please fix these issues following:
        @knowledge/ml-best-practices.md
        @knowledge/notes.md
        
        Ensure >90% coverage and all tests pass.
        """
        
        fixed_code = run_copilot_suggest(fix_prompt)
        return fixed_code
    
    def execute_workflow(self, task):
        """Main execution workflow with self-healing."""
        attempt = 0
        
        while attempt <= self.max_retries:
            # Generate code
            code = self.generate_code(task)
            
            # Validate
            result = self.validate_code(code)
            
            if result['passed'] and result['coverage'] >= self.min_coverage:
                # Success: commit and report
                self.commit_code(code, result)
                return {"status": "SUCCESS", "coverage": result['coverage']}
            
            # Analyze failures
            failure_rate = len(result['failures']) / result['total_tests']
            if failure_rate > self.acceptable_failure_rate:
                return {"status": "ESCALATE", "reason": "Failure rate too high"}
            
            # Auto-fix attempt
            attempt += 1
            code = self.auto_fix(result['failures'], attempt)
        
        return {"status": "FAILED", "reason": "Max retries exceeded"}
    
    def commit_code(self, code, metrics):
        """Commit only if validation passes."""
        import subprocess
        
        subprocess.run([
            "git", "add", "-A"
        ], check=True)
        
        subprocess.run([
            "git", "commit",
            "-m", f"feat: codegen-generated code ({metrics['coverage']}% coverage) ✅"
        ], check=True)
        
        subprocess.run([
            "git", "push", "origin", "HEAD"
        ], check=True)
```

### Knowledge-Driven Prompt Template

```
Autonomous codegen task: {task_name}

INSTRUCTIONS (Follow in order):
1. Read and understand:
   - @knowledge/ml-best-practices.md (FastAPI, XGBoost, testing patterns)
   - @knowledge/notes.md (code style, structure)
   - @knowledge/stock-features.md (technical indicators)

2. Generate code using these patterns:
   - Async/await for I/O (FastAPI endpoints)
   - Pydantic v2 for validation (type safety)
   - Type hints on all functions
   - Docstrings for all functions (Google style)
   - XGBoost with 500 estimators, max_depth=6
   - 11+ engineered features (RSI, MACD, BBands, Volatility, etc.)
   - Health checks + readiness probes
   - Structured logging

3. Implementation details:
   - Use @knowledge/data/stocks-1k.csv for training
   - Follow sklearn Pipeline architecture
   - Add ColumnTransformer for preprocessing
   - Implement StandardScaler + XGBRegressor
   - Add async predict() method with ThreadPoolExecutor

4. Testing requirements:
   - Unit tests (endpoint validation, input validation)
   - Integration tests (end-to-end flows)
   - Edge case tests (error handling, limits)
   - Target: 90%+ coverage

5. Output format:
   - Create @src/models/{model_name}.py
   - Create @tests/test_{model_name}.py
   - Add @src/api/{endpoint_name}.py if needed
   - Run pytest with coverage validation
   - Commit only if all tests pass

6. Success criteria:
   - ✓ pytest --cov shows >90% coverage
   - ✓ All tests passing
   - ✓ Type hints throughout
   - ✓ Docstrings on all functions
   - ✓ Follows production patterns from knowledge base
   - ✓ Code is ready to commit

Task scope: {task_scope}
Files to modify: {files_to_modify}
Knowledge context: {knowledge_files_referenced}
```

### Quality Gates

```yaml
Before Commit:
  Coverage:
    target: ≥90%
    measurement: pytest --cov
    failure_action: AUTO-FIX or ESCALATE
  
  Tests:
    target: 100% passing
    measurement: pytest -v
    failure_action: AUTO-FIX (max 3 attempts)
  
  Linting:
    target: No errors
    measurement: pylint, flake8
    failure_action: AUTO-FIX
  
  Type Safety:
    target: All functions typed
    measurement: mypy
    failure_action: AUTO-FIX
  
  Build:
    target: Docker builds successfully
    measurement: docker build
    failure_action: AUTO-FIX or ESCALATE
```

### Integration with n8n Workflow

```json
{
  "id": "codegen-agent-node",
  "name": "Codegen Agent",
  "type": "executeCommand",
  "parameters": {
    "command": "cd /workspace && gh copilot suggest \"[knowledge-driven prompt from template above]\""
  },
  "onError": "continueRegularFlow",
  "retrySettings": {
    "enabled": true,
    "maxTries": 3,
    "delayBetweenTries": 5000
  }
}
```

### Success Metrics

```
Per Execution:
  - Lines of code generated: 100-500
  - Test coverage achieved: 90-99%
  - Tests passing: 100%
  - Auto-fix attempts: 0-3 (average <1)
  - Time to completion: 30-120 seconds
  - Commit success rate: >95%

Aggregate (rolling 30 days):
  - Successful code generations: >90%
  - Average coverage: 95%+
  - Auto-fix success rate: >80%
  - Code passing production review: >85%
  - Zero regression bugs: 100%
```

### Example Generated Code (from template)

```python
# src/models/stock_predictor.py (auto-generated by CODEGEN_AGENT)

from typing import List, Dict
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, ColumnTransformer
from sklearn.pipeline import Pipeline
import xgboost as xgb
import logging

logger = logging.getLogger(__name__)

class TechnicalIndicators:
    """Calculate technical indicators from OHLCV data."""
    
    @staticmethod
    def calculate_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
        """Calculate Relative Strength Index.
        
        Args:
            prices: Close prices
            period: RSI period (default 14)
        
        Returns:
            RSI values (0-100)
        """
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        
        rs = up / down if down != 0 else 0
        rsi = np.zeros_like(prices)
        rsi[:period] = 100. - 100. / (1. + rs)
        
        for i in range(period, len(prices)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta
            
            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            
            rs = up / down if down != 0 else 0
            rsi[i] = 100. - 100. / (1. + rs)
        
        return rsi

class StockPredictor:
    """XGBoost-based stock price predictor with feature engineering.
    
    Example:
        >>> predictor = StockPredictor()
        >>> df = pd.read_csv('stocks-1k.csv')
        >>> predictor.train(df, df['Close'])
        >>> predictions = predictor.predict(df[['Open', 'High', 'Low', 'Close', 'Volume']])
    """
    
    def __init__(self, n_estimators: int = 500, max_depth: int = 6):
        """Initialize predictor with XGBoost parameters."""
        self.model = Pipeline([
            ('preprocessor', ColumnTransformer([
                ('scaler', StandardScaler(), ['Open', 'High', 'Low', 'Volume'])
            ])),
            ('xgb', xgb.XGBRegressor(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=0.1,
                random_state=42
            ))
        ])
    
    def train(self, X: pd.DataFrame, y: np.ndarray) -> Dict[str, float]:
        """Train the model on OHLCV data.
        
        Args:
            X: DataFrame with OHLCV columns
            y: Target prices
        
        Returns:
            Training metrics (R² score, RMSE, MAE)
        """
        self.model.fit(X[['Open', 'High', 'Low', 'Volume']], y)
        
        y_pred = self.model.predict(X[['Open', 'High', 'Low', 'Volume']])
        r2 = 1 - (np.sum((y - y_pred) ** 2) / np.sum((y - np.mean(y)) ** 2))
        rmse = np.sqrt(np.mean((y - y_pred) ** 2))
        
        logger.info(f"Model trained: R²={r2:.3f}, RMSE={rmse:.2f}")
        return {"r2": r2, "rmse": rmse}
    
    async def predict(self, X: pd.DataFrame) -> List[float]:
        """Predict stock prices asynchronously."""
        from concurrent.futures import ThreadPoolExecutor
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            predictions = await loop.run_in_executor(
                executor,
                self.model.predict,
                X[['Open', 'High', 'Low', 'Volume']]
            )
        
        return predictions.tolist()
```

### Deployment

The CODEGEN_AGENT is triggered via n8n webhook when:
- Code is pushed to agent-triggered branches
- GitHub Actions workflow_dispatch is invoked
- Manual trigger via n8n UI

The agent will:
1. Read knowledge base files for context
2. Generate code using gh copilot suggest
3. Validate with pytest (90%+ coverage required)
4. Auto-fix up to 3 times if tests fail
5. Commit only when all quality gates pass
6. Create PR with test results and metrics

---

## TEST_AGENT (Autonomous Testing)

### Similar structure with test-specific knowledge:
- Run pytest with 95%+ coverage targets
- Identify failing tests
- Request fixes via copilot
- Validate edge cases
- Only commit when all tests pass

---

## DEPLOY_AGENT (Autonomous Deployment)

### Similar structure with deployment knowledge:
- Update Dockerfile with optimizations
- Update k8s manifests
- Update GitHub Actions CI.yml
- Test docker build
- Validate k8s YAML syntax
- Only commit when deployment is valid

---

**Status:** ✅ Specification Complete  
**Last Updated:** 2026-02-12  
**Version:** 1.0 (OpenClaw Enhanced)
