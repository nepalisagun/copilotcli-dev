# Development Preferences & Standards

## Environment

### Python
- **Version:** 3.11 (primary), 3.10 (support)
- **Virtual Environment:** venv or poetry
- **Package Manager:** pip with requirements.txt
- **Linting:** flake8, black, isort
- **Type Checking:** mypy

### Core Stack
- **Web Framework:** FastAPI (async-first)
- **Testing:** pytest (pytest-cov for coverage)
- **Data:** pandas, numpy, scikit-learn
- **ML:** XGBoost, LightGBM
- **Storage:** SQLite (dev), PostgreSQL (prod)
- **Caching:** Redis
- **Task Queue:** Celery
- **Orchestration:** Airflow or Prefect

## CI/CD Pipeline

### GitHub Actions Workflow
```yaml
- Test: pytest with coverage >90%
- Lint: flake8, black, isort
- Build: Docker multi-stage
- Push: Container registry
- Deploy: Kubernetes or Docker Swarm
```

### Deployment Strategy
- Multi-stage Docker builds
- Kubernetes-ready manifests
- Rolling deployments
- Automated rollbacks
- Environment parity (dev=prod)

## Code Standards

### Naming Conventions
```python
# Functions/variables: snake_case
def get_user_predictions(user_id: int) -> List[float]:
    pass

# Classes: PascalCase
class ModelTrainer:
    pass

# Constants: UPPER_SNAKE_CASE
MAX_BATCH_SIZE = 1024

# Private attributes: _leading_underscore
_internal_state = None

# Magic methods: __double_underscore__
def __init__(self):
    pass
```

### Docstring Format (Google Style)
```python
def predict_stock_price(symbol: str, days: int) -> float:
    """Predict stock price for symbol.
    
    Uses historical OHLCV data to forecast future prices
    via XGBoost regression model.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL')
        days: Number of days to forecast (1-30)
        
    Returns:
        Predicted price as float, always positive
        
    Raises:
        ValueError: If symbol not found in market data
        TimeoutError: If API calls timeout after 30s
        
    Example:
        >>> price = predict_stock_price('AAPL', 5)
        >>> print(f"Predicted price: ${price:.2f}")
    """
```

### Type Hints (Always Required)
```python
from typing import List, Dict, Optional, Tuple, Union

def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    epochs: int = 100,
    batch_size: Optional[int] = None,
    callbacks: Optional[List[Callable]] = None
) -> Dict[str, float]:
    """Train model and return metrics."""
    pass

# Complex types
def process_batch(
    data: Union[List[Dict[str, float]], pd.DataFrame]
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """Process batch data and return features and metadata."""
    pass
```

### Import Organization
```python
# Standard library (alphabetical)
import logging
import os
from pathlib import Path
from typing import Dict, List

# Third-party (alphabetical)
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from sklearn.preprocessing import StandardScaler

# Local (alphabetical)
from src.models.predictor import StockPredictor
from src.utils.metrics import calculate_r2
```

### Code Style Examples
```python
# ✅ GOOD: Clear, readable, consistent
class StockPredictor:
    """XGBoost model for stock price prediction."""
    
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = None
        self._is_loaded = False
    
    def load_model(self) -> None:
        """Load model from disk."""
        with open(self.model_path, 'rb') as f:
            self.model = pickle.load(f)
        self._is_loaded = True
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """Make predictions on features."""
        if not self._is_loaded:
            self.load_model()
        return self.model.predict(features)

# ❌ BAD: Unclear, inconsistent, hard to test
class predictor:
    def __init__(self,path):
        self.p=path
        self.m=None
    def pred(self,x):
        if self.m is None:
            self.m=pickle.load(open(self.p))
        return self.m.predict(x)
```

## Testing Standards

### Coverage Targets
- **Unit Tests:** 80%+ coverage
- **Integration Tests:** 10%+ coverage
- **E2E Tests:** 10%+ coverage
- **Overall Target:** 95%+

### Test File Structure
```
tests/
├── __init__.py
├── unit/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_features.py
│   ├── test_utils.py
│   └── test_api.py
├── integration/
│   ├── __init__.py
│   ├── test_api_endpoints.py
│   └── test_database.py
├── e2e/
│   ├── __init__.py
│   └── test_workflow.py
├── conftest.py
└── fixtures.py
```

### Test Markers
```python
@pytest.mark.unit
def test_feature_extraction():
    """Test feature engineering function."""
    pass

@pytest.mark.integration
def test_api_endpoint():
    """Test API endpoint with real service."""
    pass

@pytest.mark.slow
def test_model_training():
    """Test full model training pipeline."""
    pass

@pytest.mark.asyncio
async def test_async_prediction():
    """Test async prediction endpoint."""
    pass
```

### Test Example Pattern
```python
import pytest
from fastapi.testclient import TestClient

class TestPredictionAPI:
    """Test prediction endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def sample_data(self):
        """Create sample prediction data."""
        return {"data": [[0.5, 0.3, 0.2, 0.1, 100.0, 99.0, 98.0, 0.02]]}
    
    def test_predict_success(self, client, sample_data):
        """Test successful prediction."""
        response = client.post("/predict", json=sample_data)
        assert response.status_code == 200
        assert "predictions" in response.json()
    
    def test_predict_invalid_input(self, client):
        """Test prediction with invalid input."""
        response = client.post("/predict", json={"data": []})
        assert response.status_code in [400, 422]
```

## Docker Standards

### Image Naming
```
copilotcli-ml:latest          # Production latest
copilotcli-ml:v1.0.0          # Versioned production
copilotcli-ml:dev             # Development
ml-stock-predictor:latest     # Service-specific
```

### Layer Optimization
1. OS/Python base (rarely changes) → ~100MB
2. System dependencies → ~50MB
3. Python packages → ~200MB
4. Application code (changes frequently) → ~10MB

### Dockerfile Best Practices
```dockerfile
# ✅ GOOD
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src ./src
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ❌ BAD
FROM python:3.11
RUN pip install numpy pandas fastapi
COPY . .
CMD python src/api.py
```

## Git Workflow

### Branch Naming Convention
```
main              - Production-ready code
develop           - Integration branch
feature/*         - New features (feature/user-auth, feature/ml-model)
bugfix/*          - Bug fixes (bugfix/prediction-error)
agent/*           - Agent-specific branches (agent/codegen, agent/test, agent/deploy)
chore/*           - Chores (chore/update-deps)
docs/*            - Documentation (docs/api-guide)
```

### Commit Message Format
```
<type>(<scope>): <subject>

<body>

<footer>

# TYPES:
feat:     New feature
fix:      Bug fix
docs:     Documentation
test:     Test suite additions
ci:       CI/CD configuration
refactor: Code refactoring
chore:    Dependency updates, etc
perf:     Performance improvements

# EXAMPLES:
feat: add stock price prediction model
fix: resolve NaN values in feature engineering
test: add 20 new unit tests for API
chore: update requirements.txt dependencies
docs: document XGBoost hyperparameters
```

### Commit Message Guidelines
- Use lowercase (except proper nouns)
- Use imperative mood ("add" not "added")
- Limit subject to 50 characters
- Reference issues: "Fixes #42"
- Wrap body at 72 characters
- Explain what and why, not how

### Pull Request Process
```
1. Create feature branch: git checkout -b feature/stock-model
2. Make changes with meaningful commits
3. Run pre-commit checks locally:
   - black src/ tests/
   - isort src/ tests/
   - flake8 src/ tests/
   - mypy src/
   - pytest --cov=src tests/
4. Push to GitHub: git push origin feature/stock-model
5. Create PR with description (see template)
6. Address code review comments
7. Get approval from ≥1 maintainer
8. Squash & merge to main
9. Auto-deploy via GitHub Actions
```

## Kubernetes Readiness

### Container Standards
- [ ] Non-root user (UID 1000+)
- [ ] Health checks (/health, /ready endpoints)
- [ ] Graceful shutdown (SIGTERM handling)
- [ ] Resource requests/limits set
- [ ] Logging to stdout/stderr (not files)
- [ ] No hardcoded environment variables
- [ ] Config via environment variables
- [ ] Secrets via Kubernetes Secrets

### Environment Variables
```
# Application
ENV_NAME=production
LOG_LEVEL=INFO
DEBUG=false

# Models
MODEL_PATH=/models/v1.0.0
MODEL_VERSION=1.0.0

# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/db
DATABASE_POOL_SIZE=10

# Cache
REDIS_URL=redis://redis:6379/0
CACHE_TTL=3600

# Performance
MAX_WORKERS=4
BATCH_SIZE=32
TIMEOUT=30

# API
API_KEY_HEADER=X-API-Key
RATE_LIMIT=1000
```

### Secret Management
- ✅ Use Kubernetes Secrets for sensitive data
- ✅ Rotate credentials regularly (every 90 days)
- ✅ Audit access logs
- ✅ Use least-privilege access
- ❌ Never commit secrets to git
- ❌ Never log sensitive information
- ❌ Never hardcode API keys

## Monitoring & Observability

### Metrics to Track
```python
# Request metrics
requests_total              # Counter: total requests by endpoint
request_latency_seconds     # Histogram: response time (p50, p95, p99)
request_size_bytes          # Histogram: request body size

# Model metrics
predictions_total           # Counter: total predictions made
prediction_confidence       # Histogram: model confidence score
prediction_latency_seconds  # Histogram: prediction time

# System metrics
model_load_time_seconds     # Gauge: time to load model
feature_engineering_time_ms # Gauge: feature processing time
memory_usage_bytes          # Gauge: process memory
cpu_usage_percent           # Gauge: CPU usage

# Error metrics
errors_total                # Counter: errors by type
exception_count             # Counter: exceptions by type
```

### Logging Levels
```python
logger.debug("Detailed execution trace for debugging")
logger.info("Application event: model loaded, prediction made")
logger.warning("Degraded performance: slow query")
logger.error("Operation failed: prediction returned NaN")
logger.critical("System failure: database offline")
```

### Logging Best Practices
```python
# ✅ GOOD: Structured, informative
logger.info("Prediction completed", extra={
    "user_id": user_id,
    "model_version": "1.0",
    "latency_ms": 45,
    "confidence": 0.92
})

# ❌ BAD: Unstructured, vague
logger.info("Done")
print(f"user {user_id} predicted")
```

## Performance Guidelines

### API Response Times
```
Health check:               <10ms   (must be fast)
Simple prediction:          <100ms  (user-facing)
Batch prediction (1000):    <5s     (background)
Model loading:              <30s    (startup)
Feature engineering:        <50ms   (per batch)
```

### Memory Limits
```
API server:                 256-512 MB
Model inference:            512-1024 MB
Data processing:            1-2 GB
Cache (Redis):              512 MB - 2 GB
```

### Resource Requests
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

## Security Practices

### Input Validation
- [ ] Validate all endpoint inputs with Pydantic
- [ ] Check data types and ranges
- [ ] Sanitize string inputs
- [ ] Limit request size (<10MB)
- [ ] Reject unknown fields

### Transport Security
- [ ] HTTPS only (no HTTP in production)
- [ ] TLS 1.2+ required
- [ ] Valid SSL certificates
- [ ] CORS properly configured
- [ ] No sensitive data in URLs

### Authentication & Authorization
- [ ] API key validation on all endpoints
- [ ] JWT tokens with expiration
- [ ] Role-based access control (RBAC)
- [ ] Audit logging of access
- [ ] Rate limiting per user/IP

### Data Protection
- [ ] No hardcoded secrets
- [ ] Encryption at rest
- [ ] Encryption in transit
- [ ] PII redaction in logs
- [ ] Regular backups

## Development Workflow

### Local Setup
```bash
# Clone and setup
git clone https://github.com/nepalisagun/copilotcli-dev.git
cd copilotcli-dev
python3.11 -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate (Windows)

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest -v --cov=src tests/

# Start development server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Pre-Commit Checklist
```bash
# Code formatting
black src/ tests/
isort src/ tests/

# Linting
flake8 src/ tests/ --max-line-length=100

# Type checking
mypy src/ --strict

# Testing
pytest --cov=src --cov-report=term-missing tests/

# Coverage should be 95%+
coverage report --fail-under=95
```

## Collaboration Standards

### Code Review Checklist
- [ ] Tests added or updated for new code
- [ ] Documentation updated (docstrings, README)
- [ ] No hardcoded values or secrets
- [ ] Error handling and edge cases covered
- [ ] Performance impact assessed
- [ ] Security implications reviewed
- [ ] No debug prints or console logs
- [ ] Type hints complete
- [ ] Follows naming conventions
- [ ] Commit messages are clear

### PR Description Template
```markdown
## Description
Brief summary of changes.

## Related Issues
Fixes #42

## Changes Made
- Change 1
- Change 2
- Change 3

## Testing
- [ ] Added unit tests
- [ ] Added integration tests
- [ ] Tested locally
- [ ] All tests pass

## Performance
- No performance impact
- Response time: <100ms
- Memory usage: same

## Security
- Input validation added
- No new dependencies
- No secrets in code
```

## Version Control

### Release Strategy
```
Semantic Versioning: MAJOR.MINOR.PATCH

MAJOR: Breaking API changes (1.0.0 → 2.0.0)
MINOR: New features, backward compatible (1.0.0 → 1.1.0)
PATCH: Bug fixes (1.0.0 → 1.0.1)

Release workflow:
1. Create release branch: git checkout -b release/v1.1.0
2. Update version in setup.py, __init__.py
3. Update CHANGELOG.md
4. Create PR and get approval
5. Merge to main and tag: git tag -a v1.1.0 -m "Release v1.1.0"
6. Push tag: git push origin v1.1.0
7. GitHub Actions auto-creates release
```

## Tools & Extensions

### Recommended IDE Setup (VS Code)
```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

### CLI Tools
```bash
# Code quality
pip install black flake8 isort mypy pylint

# Testing
pip install pytest pytest-cov pytest-asyncio pytest-xdist

# Development
pip install ipython ipdb debugpy

# Documentation
pip install sphinx sphinx-rtd-theme

# Pre-commit hooks
pip install pre-commit
```

### Pre-commit Configuration
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
  
  - repo: https://github.com/PyCQA/isort
    rev: 5.12.0
    hooks:
      - id: isort
  
  - repo: https://github.com/PyCQA/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
```

## Emergency Procedures

### If Tests Fail
1. Run failed test in isolation: `pytest tests/test_x.py::test_name -v`
2. Check recent commits: `git log --oneline -10`
3. Revert if necessary: `git revert <commit>`
4. Investigate and fix the issue
5. Add regression test to prevent recurrence
6. Commit fix with reference to original issue

### If Model Serving Fails
1. Check model file exists: `ls -la models/`
2. Verify input schema matches model.pkl
3. Check system resources: `free -h`, `df -h`
4. Review error logs: `docker logs ml-api`
5. Fallback to previous version: `docker pull ml-stock-predictor:previous`

### If Deployment Fails
1. Check container logs: `kubectl logs deployment/stock-predictor`
2. Verify environment variables: `kubectl describe pod <pod-name>`
3. Test locally with same config: `docker run -e ENV_VAR=value ...`
4. Rollback to previous version: `kubectl rollout undo deployment/stock-predictor`
5. Investigate root cause and fix

## References

- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Pytest Docs](https://docs.pytest.org)
- [Python 3.11 Docs](https://docs.python.org/3.11)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- [Type Hints](https://docs.python.org/3.11/library/typing.html)

