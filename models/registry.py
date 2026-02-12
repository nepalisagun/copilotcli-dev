"""Model registry for tracking and managing trained models."""

import json
import os
from datetime import datetime
from typing import Dict, List, Any
import joblib


class ModelRegistry:
    """Central registry for tracking all trained models."""
    
    def __init__(self, registry_dir: str = "model_registry"):
        self.registry_dir = registry_dir
        self.registry_file = os.path.join(registry_dir, "registry.json")
        self.models_dir = os.path.join(registry_dir, "models")
        self.metadata = {}
        
        os.makedirs(self.models_dir, exist_ok=True)
        self._load_registry()
    
    def _load_registry(self):
        """Load registry from disk."""
        if os.path.exists(self.registry_file):
            with open(self.registry_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {}
    
    def _save_registry(self):
        """Save registry to disk."""
        os.makedirs(self.registry_dir, exist_ok=True)
        with open(self.registry_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
    
    def register_model(self, model_name: str, model_type: str, metrics: Dict[str, float],
                      hyperparameters: Dict[str, Any], version: str = "1.0.0") -> str:
        """Register a new model."""
        model_id = f"{model_name}_{version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.metadata[model_id] = {
            'name': model_name,
            'type': model_type,
            'version': version,
            'metrics': metrics,
            'hyperparameters': hyperparameters,
            'registered_at': datetime.now().isoformat(),
            'status': 'active',
            'filepath': os.path.join(self.models_dir, f"{model_id}.pkl")
        }
        
        self._save_registry()
        return model_id
    
    def get_model_metadata(self, model_id: str) -> Dict:
        """Get metadata for a specific model."""
        return self.metadata.get(model_id, {})
    
    def list_models(self, model_type: str = None) -> List[Dict]:
        """List all registered models, optionally filtered by type."""
        models = []
        for model_id, metadata in self.metadata.items():
            if model_type is None or metadata['type'] == model_type:
                models.append({
                    'id': model_id,
                    **metadata
                })
        return sorted(models, key=lambda x: x['registered_at'], reverse=True)
    
    def get_best_model(self, metric: str = 'r2') -> Dict:
        """Get the best model by a specific metric."""
        best = None
        best_score = -float('inf')
        
        for model_id, metadata in self.metadata.items():
            if metadata['status'] == 'active':
                score = metadata['metrics'].get(metric, -float('inf'))
                if score > best_score:
                    best_score = score
                    best = {'id': model_id, **metadata}
        
        return best if best else {}
    
    def update_model_status(self, model_id: str, status: str) -> bool:
        """Update model status (active/archived/deprecated)."""
        if model_id in self.metadata:
            self.metadata[model_id]['status'] = status
            self.metadata[model_id]['updated_at'] = datetime.now().isoformat()
            self._save_registry()
            return True
        return False
    
    def get_model_history(self, model_name: str) -> List[Dict]:
        """Get all versions of a specific model."""
        history = []
        for model_id, metadata in self.metadata.items():
            if metadata['name'] == model_name:
                history.append({'id': model_id, **metadata})
        return sorted(history, key=lambda x: x['registered_at'], reverse=True)
    
    def export_registry(self, filepath: str) -> bool:
        """Export registry to JSON file."""
        try:
            with open(filepath, 'w') as f:
                json.dump(self.metadata, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error exporting registry: {e}")
            return False
    
    def get_registry_stats(self) -> Dict:
        """Get statistics about the registry."""
        return {
            'total_models': len(self.metadata),
            'active_models': sum(1 for m in self.metadata.values() if m['status'] == 'active'),
            'model_types': list(set(m['type'] for m in self.metadata.values())),
            'registered_at': datetime.now().isoformat()
        }
