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
```

### Docstring Format
```python
def predict_stock_price(symbol: str, days: int) -> float:
    """Predict stock price for symbol.
    
    Args:
        symbol: Stock ticker symbol (e.g., 'AAPL')
        days: Number of days to forecast
        
    Returns:
        Predicted price as float
        
    Raises:
        ValueError: If symbol not found
        TimeoutError: If API calls timeout
    """
```

### Type Hints (Always)
```python
from typing import List, Dict, Optional, Tuple

def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    epochs: int = 100,
    batch_size: Optional[int] = None
) -> Dict[str, float]:
    """Train model and return metrics."""
```

## Testing Standards

### Coverage Targets
- **Unit Tests:** 80%+ coverage
- **Integration Tests:** 10%+ coverage
- **E2E Tests:** 10%+ coverage
- **Overall Target:** 90%+

### Test Structure
```
tests/
├── unit/
│   ├── test_models.py
│   ├── test_features.py
│   └── test_utils.py
├── integration/
│   ├── test_api.py
│   └── test_database.py
└── e2e/
    └── test_workflow.py
```

### Test Markers
```python
@pytest.mark.unit
def test_feature_extraction():
    pass

@pytest.mark.integration
def test_api_endpoint():
    pass

@pytest.mark.slow
def test_model_training():
    pass
```

## Docker Standards

### Image Naming
- `copilotcli-ml:latest` (production)
- `copilotcli-ml:v1.0.0` (versioned)
- `copilotcli-ml:dev` (development)

### Layer Optimization
1. OS/Python base (rarely changes)
2. System dependencies
3. Python packages
4. Application code (changes frequently)

## Git Workflow

### Branch Naming
- `main` - Production-ready code
- `develop` - Integration branch
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `agent/*` - Agent-specific branches (data-agent, model-agent, api-agent)

### Commit Messages
```
feat: add price prediction endpoint
fix: resolve NaN values in features
docs: update API documentation
test: add 20 new unit tests
ci: configure GitHub Actions
refactor: optimize model loading
chore: update dependencies
```

### Pull Request Process
1. Create feature branch
2. Make changes with commits
3. Run tests locally (`pytest -v`)
4. Push to GitHub
5. Create PR with description
6. Code review (≥1 approval)
7. Merge to main
8. Auto-deploy via Actions

## Kubernetes Readiness

### Container Standards
- [ ] Non-root user (UID 1000)
- [ ] Health checks (/health, /ready)
- [ ] Graceful shutdown (SIGTERM handling)
- [ ] Resource requests/limits set
- [ ] Logging to stdout/stderr

### Environment Variables
```
ENV_NAME=production
LOG_LEVEL=INFO
MODEL_PATH=/models/v1.0.0
CACHE_TTL=3600
MAX_WORKERS=4
```

### Secret Management
- Never commit secrets
- Use Kubernetes Secrets
- Rotate credentials regularly
- Audit access logs

## Monitoring & Observability

### Metrics to Track
- Request count (by endpoint)
- Response latency (p50, p95, p99)
- Error rate
- Model prediction confidence
- Feature anomaly rate
- Resource usage (CPU, memory)

### Logging Levels
```python
logger.debug("Detailed execution trace")
logger.info("Application event")
logger.warning("Degraded performance")
logger.error("Operation failed")
logger.critical("System failure")
```

## Performance Guidelines

### API Response Times
- Health check: <10ms
- Simple prediction: <100ms
- Batch prediction (1000 items): <5s
- Model loading: <30s

### Memory Limits
- API server: 256-512MB
- Model inference: 512-1024MB
- Data processing: 1-2GB

## Security Practices

- [ ] Input validation on all endpoints
- [ ] HTTPS only (no HTTP)
- [ ] CORS properly configured
- [ ] Rate limiting enabled
- [ ] SQL injection prevention (ORM)
- [ ] XSS protection
- [ ] CSRF tokens for forms
- [ ] Authentication for APIs
- [ ] Authorization checks
- [ ] Audit logging

## Development Workflow

### Local Setup
```bash
git clone <repo>
cd copilotcli-dev
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest -v
```

### Before Committing
```bash
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
pytest --cov=src tests/
```

## Collaboration Standards

### Code Review Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No hardcoded values
- [ ] Error handling present
- [ ] Performance acceptable
- [ ] Security reviewed
- [ ] No console logs
- [ ] Type hints complete

### Communication
- Use GitHub Issues for discussion
- Update PR descriptions regularly
- Tag relevant reviewers
- Respond to feedback promptly
- Document decisions in commits

## Version Control

### Release Strategy
- Semantic versioning (MAJOR.MINOR.PATCH)
- Tag releases: `v1.0.0`
- Maintain CHANGELOG.md
- Document breaking changes
- Plan migrations

## Tools & Extensions

### Recommended IDE Setup
- VS Code + Python extension
- Pylance for type checking
- Black formatter
- Flake8 linter
- Test Explorer

### CLI Tools
```bash
# Code quality
pip install black flake8 isort mypy

# Testing
pip install pytest pytest-cov pytest-asyncio

# Documentation
pip install sphinx sphinx-rtd-theme

# Development
pip install ipython ipdb
```

## Emergency Procedures

### If Tests Fail
1. Run failed test in isolation
2. Check recent commits
3. Revert if necessary
4. Investigate and fix
5. Add regression test

### If Model Serving Fails
1. Check model file exists
2. Verify input schema
3. Check system resources
4. Review error logs
5. Fallback to previous version

### If Deployment Fails
1. Check logs in container
2. Verify environment variables
3. Test locally with same config
4. Rollback to previous version
5. Investigate and fix

## References

- [FastAPI Docs](https://fastapi.tiangolo.com)
- [Pytest Docs](https://docs.pytest.org)
- [Python 3.11 Docs](https://docs.python.org/3.11)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
