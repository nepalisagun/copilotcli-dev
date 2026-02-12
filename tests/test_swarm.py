"""Tests for ML swarm components."""

import json
import pytest
import pandas as pd
from pathlib import Path


class TestKnowledgeBase:
    """Test knowledge base setup."""
    
    def test_knowledge_base_exists(self):
        """Verify knowledge base files exist."""
        knowledge_dir = Path("knowledge")
        assert knowledge_dir.exists(), "Knowledge directory missing"
        
        required_files = [
            "knowledge/ml-best-practices.md",
            "knowledge/notes.md",
            "knowledge/data/stocks-sample.csv"
        ]
        
        for file_path in required_files:
            assert Path(file_path).exists(), f"Missing {file_path}"
    
    def test_stocks_data_validity(self):
        """Verify stocks CSV data is valid."""
        df = pd.read_csv("knowledge/data/stocks-sample.csv")
        
        # Check required columns
        required_cols = ['date', 'open', 'high', 'low', 'close', 'volume', 'symbol']
        assert all(col in df.columns for col in required_cols), "Missing required columns"
        
        # Check data types
        assert df['close'].dtype in ['float64', 'int64'], "Close price must be numeric"
        assert df['volume'].dtype in ['int64'], "Volume must be integer"
        
        # Check data quality
        assert not df['close'].isnull().any(), "Null values in close price"
        assert (df['high'] >= df['low']).all(), "High < Low detected"
        assert (df['close'] > 0).all(), "Negative prices detected"
        
        # Check data volume
        assert len(df) > 20, "Insufficient sample data"


class TestDockerCompose:
    """Test Docker Compose configuration."""
    
    def test_docker_compose_exists(self):
        """Verify docker-compose.yml exists."""
        assert Path("docker-compose.yml").exists(), "docker-compose.yml missing"
    
    def test_required_services(self):
        """Verify required services are defined."""
        with open("docker-compose.yml", "r") as f:
            content = f.read()
        
        required_services = ['n8n', 'qdrant', 'postgres', 'redis', 'ml-api']
        
        for service in required_services:
            assert service in content, f"Missing service: {service}"


class TestWorkflows:
    """Test n8n workflow configurations."""
    
    def test_gemini_swarm_workflow_exists(self):
        """Verify gemini-swarm.json exists."""
        assert Path("workflows/gemini-swarm.json").exists(), "gemini-swarm.json missing"
    
    def test_workflow_valid_json(self):
        """Verify workflows are valid JSON."""
        for workflow_file in Path("workflows").glob("*.json"):
            with open(workflow_file, "r") as f:
                try:
                    json.load(f)
                except json.JSONDecodeError as e:
                    pytest.fail(f"{workflow_file} is invalid JSON: {e}")
    
    def test_gemini_swarm_structure(self):
        """Verify gemini-swarm.json has required structure."""
        with open("workflows/gemini-swarm.json", "r") as f:
            workflow = json.load(f)
        
        assert "name" in workflow, "Missing workflow name"
        assert "nodes" in workflow, "Missing nodes"
        assert "connections" in workflow, "Missing connections"
        assert workflow["active"] is True, "Workflow not active"
        
        # Check for required nodes
        node_names = {node['name'] for node in workflow['nodes']}
        required_nodes = ['GitHub Webhook', 'Codegen Agent', 'Test Agent', 'Deploy Agent']
        
        for node_name in required_nodes:
            assert node_name in node_names, f"Missing node: {node_name}"


class TestScripts:
    """Test launch and test scripts."""
    
    def test_launch_script_exists(self):
        """Verify launch script exists."""
        assert Path("launch-swarm.sh").exists(), "launch-swarm.sh missing"
    
    def test_test_script_exists(self):
        """Verify test script exists."""
        assert Path("test-swarm.sh").exists(), "test-swarm.sh missing"


class TestGitHubActions:
    """Test GitHub Actions workflows."""
    
    def test_swarm_workflow_exists(self):
        """Verify swarm.yml GitHub Action exists."""
        assert Path(".github/workflows/swarm.yml").exists(), "swarm.yml missing"


class TestIntegration:
    """Integration tests for the swarm."""
    
    def test_directory_structure(self):
        """Verify complete directory structure."""
        required_dirs = [
            'knowledge',
            'knowledge/data',
            'workflows',
            '.github/workflows',
            'tests'
        ]
        
        for dir_path in required_dirs:
            assert Path(dir_path).exists(), f"Missing directory: {dir_path}"
    
    def test_swarm_readiness(self):
        """Verify swarm is ready for deployment."""
        checks = {
            "docker-compose.yml": Path("docker-compose.yml").exists(),
            "workflows/gemini-swarm.json": Path("workflows/gemini-swarm.json").exists(),
            "launch-swarm.sh": Path("launch-swarm.sh").exists(),
            ".github/workflows/swarm.yml": Path(".github/workflows/swarm.yml").exists(),
            "knowledge base": Path("knowledge/ml-best-practices.md").exists(),
        }
        
        for check_name, result in checks.items():
            assert result, f"Failed: {check_name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
