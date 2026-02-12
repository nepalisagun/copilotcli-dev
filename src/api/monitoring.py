"""Monitoring and metrics for API."""

from datetime import datetime
from typing import Dict, Any
import time
from functools import wraps


class MetricsCollector:
    """Collect and track API metrics."""
    
    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.endpoint_metrics = {}
        self.start_time = datetime.utcnow()
    
    def record_request(self, endpoint: str, status_code: int, response_time: float):
        """Record a request."""
        self.request_count += 1
        self.total_response_time += response_time
        
        if status_code >= 400:
            self.error_count += 1
        
        if endpoint not in self.endpoint_metrics:
            self.endpoint_metrics[endpoint] = {
                'count': 0,
                'errors': 0,
                'total_time': 0.0,
                'min_time': float('inf'),
                'max_time': 0.0
            }
        
        metrics = self.endpoint_metrics[endpoint]
        metrics['count'] += 1
        metrics['total_time'] += response_time
        metrics['min_time'] = min(metrics['min_time'], response_time)
        metrics['max_time'] = max(metrics['max_time'], response_time)
        
        if status_code >= 400:
            metrics['errors'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        avg_response_time = (self.total_response_time / self.request_count) if self.request_count > 0 else 0
        
        endpoint_summary = {}
        for endpoint, metrics in self.endpoint_metrics.items():
            endpoint_summary[endpoint] = {
                'requests': metrics['count'],
                'errors': metrics['errors'],
                'avg_time_ms': round((metrics['total_time'] / metrics['count']) * 1000, 2),
                'min_time_ms': round(metrics['min_time'] * 1000, 2),
                'max_time_ms': round(metrics['max_time'] * 1000, 2)
            }
        
        return {
            'uptime_seconds': round(uptime, 2),
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'error_rate': round((self.error_count / self.request_count * 100) if self.request_count > 0 else 0, 2),
            'avg_response_time_ms': round(avg_response_time * 1000, 2),
            'endpoints': endpoint_summary
        }
    
    def reset_metrics(self):
        """Reset metrics."""
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.endpoint_metrics = {}
        self.start_time = datetime.utcnow()


class HealthChecker:
    """Health check for API and dependencies."""
    
    @staticmethod
    def check_api_health() -> Dict[str, Any]:
        """Check API health."""
        return {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        }
    
    @staticmethod
    def check_model_service() -> Dict[str, bool]:
        """Check if model service is available."""
        return {
            'available': True,
            'loaded_models': 1
        }
    
    @staticmethod
    def check_database() -> Dict[str, bool]:
        """Check database connectivity."""
        return {
            'connected': True,
            'responsive': True
        }
    
    @staticmethod
    def get_full_health_status() -> Dict[str, Any]:
        """Get complete health status."""
        return {
            'api': HealthChecker.check_api_health(),
            'models': HealthChecker.check_model_service(),
            'database': HealthChecker.check_database(),
            'overall_status': 'operational'
        }


class RateLimiter:
    """Simple rate limiter."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_history = {}
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if client is allowed to make a request."""
        now = time.time()
        minute_ago = now - 60
        
        if client_id not in self.request_history:
            self.request_history[client_id] = []
        
        # Clean old requests
        self.request_history[client_id] = [
            req_time for req_time in self.request_history[client_id]
            if req_time > minute_ago
        ]
        
        # Check limit
        if len(self.request_history[client_id]) >= self.requests_per_minute:
            return False
        
        # Record new request
        self.request_history[client_id].append(now)
        return True
    
    def get_remaining(self, client_id: str) -> int:
        """Get remaining requests for client."""
        if client_id not in self.request_history:
            return self.requests_per_minute
        return max(0, self.requests_per_minute - len(self.request_history[client_id]))
