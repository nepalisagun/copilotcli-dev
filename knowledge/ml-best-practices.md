# ML Best Practices & Production Patterns

## FastAPI Serving

### Production Patterns

```python
# Async request handling
@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest, 
                 current_user: dict = Depends(get_current_user)):
    # Non-blocking execution
    result = await model.predict_async(request.features)
    return result

# Batch prediction with streaming
@app.post("/predict/stream")
async def predict_stream(requests: List[PredictionRequest]):
    for req in requests:
        yield await model.predict_async(req.features)

# Health checks
@app.get("/health")
def health():
    return {"status": "healthy", "model_loaded": model is not None}

# Metrics exposure
@app.get("/metrics")
def metrics():
    return {
        "requests_total": metrics_collector.total_requests,
        "errors_total": metrics_collector.error_count,
        "latency_p99": metrics_collector.p99_latency()
    }
```

### Best Practices
- Use async/await for I/O operations
- Implement circuit breaker for external calls
- Add request validation with Pydantic
- Use dependency injection for middleware
- Implement graceful shutdown
- Monitor memory usage for model inference

## Testing Strategy (90%+ Coverage)

### Unit Tests
```python
def test_model_prediction():
    model = load_model()
    features = [1.0, 2.0, 3.0, 4.0]
    prediction = model.predict([features])
    assert 0 <= prediction <= 2
    
def test_feature_engineering():
    raw_data = load_sample_data()
    features = engineer_features(raw_data)
    assert not features.isnull().any()
    assert features.shape[1] == EXPECTED_FEATURES
```

### Integration Tests
```python
def test_api_endpoint():
    client = TestClient(app)
    response = client.post("/predict", json={"features": [...]})
    assert response.status_code == 200
    assert "prediction" in response.json()
```

### Performance Tests
```python
def test_model_latency():
    import time
    start = time.time()
    for _ in range(100):
        model.predict([...])
    elapsed = time.time() - start
    assert elapsed / 100 < 0.01  # <10ms per prediction
```

## Docker Multi-Stage Build

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY src ./src
COPY models ./models
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "src.api:app"]
```

### Benefits
- Smaller final image (~200MB vs 800MB)
- Faster deployments
- Separate build dependencies from runtime
- Security: no build tools in production

## MLflow Integration

### Model Tracking
```python
import mlflow
import mlflow.sklearn

mlflow.set_experiment("price-prediction")

with mlflow.start_run():
    model = train_model(X_train, y_train)
    
    # Log parameters
    mlflow.log_params({"n_estimators": 100, "max_depth": 10})
    
    # Log metrics
    mlflow.log_metrics({
        "r2": r2_score(y_test, model.predict(X_test)),
        "rmse": np.sqrt(mse)
    })
    
    # Log model
    mlflow.sklearn.log_model(model, "model")
    
    # Log artifacts
    mlflow.log_artifact("plots/confusion_matrix.png")
```

### Model Registry
```python
# Register model
model_uri = f"runs:/{run_id}/model"
mlflow.register_model(model_uri, "production-price-predictor")

# Load production model
model = mlflow.pyfunc.load_model("models:/production-price-predictor/Production")
```

## Kubernetes Readiness

### Health Checks
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Resource Limits
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

## Monitoring & Observability

### Prometheus Metrics
```python
from prometheus_client import Counter, Histogram

request_count = Counter('requests_total', 'Total requests')
prediction_latency = Histogram('prediction_latency_seconds', 'Prediction latency')

@app.post("/predict")
@prediction_latency.time()
def predict(request):
    request_count.inc()
    return model.predict(request.features)
```

### Logging
```python
import logging

logger = logging.getLogger(__name__)
logger.info(f"Model loaded: {model_name}")
logger.warning(f"Low confidence prediction: {confidence}")
logger.error(f"Prediction failed: {error}")
```

## Data Pipeline

### Feature Engineering
- Normalize numerical features (StandardScaler)
- Encode categorical variables (OneHotEncoder)
- Handle missing values (imputation or removal)
- Create lag features for time series

### Data Validation
- Schema validation (Pydantic)
- Type checking
- Range validation
- Outlier detection

## Model Selection

### Classification
- **Logistic Regression**: Fast, interpretable, baseline
- **Random Forest**: Good accuracy, handles non-linearity
- **XGBoost/LightGBM**: SOTA performance, hyperparameter tuning
- **Neural Networks**: Complex patterns, requires more data

### Regression
- **Linear Regression**: Interpretability, fast
- **Decision Trees/Forests**: Non-linear relationships
- **Gradient Boosting**: Best for structured data
- **Neural Networks**: Large datasets, high complexity

## Hyperparameter Tuning

### Grid Search
```python
from sklearn.model_selection import GridSearchCV

params = {
    'n_estimators': [50, 100, 200],
    'max_depth': [5, 10, 15],
    'learning_rate': [0.01, 0.1, 0.3]
}

grid = GridSearchCV(model, params, cv=5, n_jobs=-1)
grid.fit(X_train, y_train)
best_model = grid.best_estimator_
```

### Early Stopping
```python
callbacks = [
    EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True)
]
model.fit(X_train, y_train, validation_split=0.2, callbacks=callbacks)
```

## Production Checklist

- [ ] 90%+ test coverage
- [ ] Async/await patterns for I/O
- [ ] Health check endpoints
- [ ] Graceful shutdown handling
- [ ] Metrics and monitoring
- [ ] Error handling and logging
- [ ] Input validation
- [ ] Rate limiting
- [ ] Authentication/authorization
- [ ] Multi-stage Docker build
- [ ] Kubernetes manifests ready
- [ ] Model versioning with MLflow
- [ ] Data pipeline documented
- [ ] Performance benchmarks
- [ ] Disaster recovery plan
