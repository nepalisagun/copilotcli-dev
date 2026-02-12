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

## XGBoost Model Implementation

### Basic Training Pattern
```python
import xgboost as xgb
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

# Load data
df = pd.read_csv('data.csv')
X = df.drop('target', axis=1)
y = df['target']

# Preprocess
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42
)

# Train
model = xgb.XGBRegressor(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42
)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

# Evaluate
from sklearn.metrics import r2_score, mean_squared_error
y_pred = model.predict(X_test)
r2 = r2_score(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
print(f"R²: {r2:.4f}, RMSE: {rmse:.4f}")
```

### Production Model Class
```python
from sklearn.pipeline import Pipeline

class StockPredictor:
    def __init__(self):
        self.pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('model', xgb.XGBRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            ))
        ])
    
    def fit(self, X, y):
        self.pipeline.fit(X, y)
        return self
    
    def predict(self, X):
        return self.pipeline.predict(X)
    
    def score(self, X, y):
        return self.pipeline.score(X, y)
    
    def save(self, path):
        import pickle
        with open(path, 'wb') as f:
            pickle.dump(self.pipeline, f)
    
    def load(self, path):
        import pickle
        with open(path, 'rb') as f:
            self.pipeline = pickle.load(f)
        return self
```

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

COPY src ./src
COPY models ./models
COPY knowledge ./knowledge

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /app/src ./src
COPY --from=builder /app/models ./models
COPY --from=builder /app/knowledge ./knowledge

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
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

mlflow.set_experiment("stock-prediction")

with mlflow.start_run():
    model = train_stock_predictor(X_train, y_train)
    
    # Log parameters
    mlflow.log_params({
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.1
    })
    
    # Log metrics
    mlflow.log_metrics({
        "r2": r2_score(y_test, model.predict(X_test)),
        "rmse": np.sqrt(mean_squared_error(y_test, model.predict(X_test)))
    })
    
    # Log model
    mlflow.sklearn.log_model(model, "stock-predictor")
    
    # Log artifacts
    mlflow.log_artifact("plots/predictions.png")
```

### Model Registry
```python
# Register model
model_uri = f"runs:/{run_id}/stock-predictor"
mlflow.register_model(model_uri, "stock-price-predictor")

# Load production model
model = mlflow.pyfunc.load_model("models:/stock-price-predictor/Production")
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

### Deployment Example
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stock-predictor
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: stock-predictor
  template:
    metadata:
      labels:
        app: stock-predictor
    spec:
      containers:
      - name: api
        image: ml-stock-predictor:latest
        ports:
        - containerPort: 8000
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

request_count = Counter('requests_total', 'Total requests', ['endpoint'])
prediction_latency = Histogram('prediction_latency_seconds', 'Prediction latency')
model_errors = Counter('model_errors_total', 'Total model errors')

@app.post("/predict")
@prediction_latency.time()
async def predict(request: PredictionRequest):
    try:
        request_count.labels(endpoint="predict").inc()
        result = model.predict(request.features)
        return {"predictions": result}
    except Exception as e:
        model_errors.inc()
        raise
```

### Logging
```python
import logging

logger = logging.getLogger(__name__)

# Log model lifecycle
logger.info(f"Model loaded: stock-predictor v1.0")
logger.info(f"Model training complete. R²: {r2:.4f}")

# Log predictions
logger.debug(f"Prediction made for {len(features)} samples")

# Log errors
logger.error(f"Prediction failed: {error}", exc_info=True)
```

## Data Pipeline

### Feature Engineering
- Normalize numerical features (StandardScaler)
- Encode categorical variables (OneHotEncoder)
- Handle missing values (imputation or removal)
- Create lag features for time series
- Generate interaction features
- Handle outliers (IQR or Z-score)

### Data Validation
```python
from pydantic import BaseModel, validator

class PredictionRequest(BaseModel):
    data: List[List[float]]
    
    @validator('data')
    def validate_data(cls, v):
        if not v:
            raise ValueError('Data cannot be empty')
        if any(len(sample) != 8 for sample in v):
            raise ValueError('Each sample must have 8 features')
        return v
```

## Model Selection

### Classification
- **Logistic Regression**: Fast, interpretable, baseline
- **Random Forest**: Good accuracy, handles non-linearity
- **XGBoost/LightGBM**: SOTA performance, hyperparameter tuning
- **Neural Networks**: Complex patterns, requires more data

### Regression
- **Linear Regression**: Interpretability, fast
- **Decision Trees/Forests**: Non-linear relationships
- **XGBoost/LightGBM**: Best for structured data
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

- [x] XGBoost model training & inference
- [x] 90%+ test coverage
- [x] Async/await patterns for I/O
- [x] Health check endpoints (/health, /ready)
- [x] Graceful shutdown handling
- [x] Prometheus metrics & monitoring
- [x] Comprehensive logging
- [x] Input validation with Pydantic
- [x] Rate limiting & throttling
- [x] Authentication/authorization ready
- [x] Multi-stage Docker build
- [x] Kubernetes manifests ready
- [x] Model versioning with MLflow
- [x] Data pipeline documented
- [x] Performance benchmarks (<10ms)
- [x] Disaster recovery plan
- [x] CI/CD pipeline configured
- [x] Load testing completed
- [x] Security audit passed
- [x] Documentation complete

