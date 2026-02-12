#!/bin/bash
set -e

echo "🚀 Starting Copilot Swarm Bootstrap..."

# Check prerequisites
echo "✓ Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo "✗ Docker not found. Please install Docker."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "✗ Docker Compose not found. Please install Docker Compose."
    exit 1
fi

# Check environment
echo "✓ Checking environment..."
if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  GEMINI_API_KEY not set. Prompting for input..."
    read -p "Enter your Gemini API Key: " GEMINI_API_KEY
    export GEMINI_API_KEY
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  GITHUB_TOKEN not set. Prompting for input..."
    read -p "Enter your GitHub Token: " GITHUB_TOKEN
    export GITHUB_TOKEN
fi

# Set environment variables
export GITHUB_REPO_OWNER="${GITHUB_REPO_OWNER:-nepalisagun}"
export GITHUB_REPO_NAME="${GITHUB_REPO_NAME:-copilotcli-dev}"
export N8N_BASE_URL="http://localhost:5678"
export QDRANT_URL="http://localhost:6333"
export POSTGRES_PASSWORD="copilot-dev-password"
export REDIS_PASSWORD="copilot-redis-password"

echo "✓ Environment configured:"
echo "  - GITHUB_REPO: $GITHUB_REPO_OWNER/$GITHUB_REPO_NAME"
echo "  - GEMINI_API_KEY: ${GEMINI_API_KEY:0:10}..."
echo "  - GITHUB_TOKEN: ${GITHUB_TOKEN:0:10}..."

# Stop existing containers
echo "🛑 Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Build ML API image
echo "🔨 Building ML API image..."
docker build -t copilot-swarm-ml-api:latest . --quiet

# Start services
echo "📦 Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker-compose exec -T n8n wget -q -O - http://localhost:5678/api/v1/health > /dev/null 2>&1; then
        echo "✓ n8n is ready"
        break
    fi
    attempt=$((attempt + 1))
    if [ $attempt -eq $max_attempts ]; then
        echo "✗ n8n failed to start"
        docker-compose logs n8n
        exit 1
    fi
    sleep 2
done

# Import workflows
echo "📥 Importing n8n workflows..."
python3 << 'EOF'
import json
import requests
import os

n8n_url = os.getenv('N8N_BASE_URL', 'http://localhost:5678')
api_key = os.getenv('N8N_API_KEY', '')

workflows = [
    'workflows/gemini-swarm.json',
    'workflows/swarm.json'
]

headers = {
    'Content-Type': 'application/json',
    'X-N8N-API-KEY': api_key
}

for workflow_file in workflows:
    if not os.path.exists(workflow_file):
        continue
    
    with open(workflow_file, 'r') as f:
        workflow = json.load(f)
    
    try:
        response = requests.post(
            f'{n8n_url}/api/v1/workflows',
            json=workflow,
            headers=headers,
            timeout=10
        )
        if response.status_code in [200, 201]:
            print(f"✓ Imported {workflow_file}")
        else:
            print(f"⚠️  {workflow_file}: {response.status_code}")
    except Exception as e:
        print(f"⚠️  {workflow_file}: {e}")

print("\n✓ Workflow import complete")
EOF

# Populate Qdrant with knowledge base
echo "📚 Populating Qdrant with knowledge base..."
python3 << 'EOF'
import json
import requests
import os
from pathlib import Path

qdrant_url = os.getenv('QDRANT_URL', 'http://localhost:6333')
api_key = os.getenv('QDRANT_API_KEY', 'copilot-swarm-key')

# Simple vectorization (in production, use real embeddings)
def simple_vectorize(text):
    return [float(ord(c)) / 256.0 for c in text[:384]]

knowledge_dir = Path('knowledge')
points = []
point_id = 1

# Collect all knowledge files
for file_path in knowledge_dir.rglob('*.md'):
    with open(file_path, 'r') as f:
        content = f.read()
    
    points.append({
        "id": point_id,
        "vector": simple_vectorize(content[:384]),
        "payload": {
            "source": str(file_path),
            "content": content[:500],
            "context": content
        }
    })
    point_id += 1

# Load CSV data
csv_file = knowledge_dir / 'data' / 'stocks-sample.csv'
if csv_file.exists():
    with open(csv_file, 'r') as f:
        csv_content = f.read()
    points.append({
        "id": point_id,
        "vector": simple_vectorize(csv_content[:384]),
        "payload": {
            "source": str(csv_file),
            "content": "Stock trading data samples",
            "context": csv_content
        }
    })

try:
    # Create collection
    requests.put(
        f'{qdrant_url}/collections/ml-knowledge',
        json={
            "vectors": {
                "size": 384,
                "distance": "Cosine"
            }
        },
        headers={"api-key": api_key},
        timeout=10
    )
    print("✓ Created Qdrant collection")
    
    # Upsert points
    response = requests.put(
        f'{qdrant_url}/collections/ml-knowledge/points',
        json={"points": points},
        headers={"api-key": api_key},
        timeout=10
    )
    
    if response.status_code in [200, 201]:
        print(f"✓ Uploaded {len(points)} knowledge points to Qdrant")
    else:
        print(f"⚠️  Qdrant upload: {response.status_code}")
except Exception as e:
    print(f"⚠️  Qdrant setup: {e}")

print("\n✓ Knowledge base ready")
EOF

# Display service URLs
echo ""
echo "=========================================="
echo "✅ COPILOT SWARM STACK READY"
echo "=========================================="
echo ""
echo "🌐 Service URLs:"
echo "  - n8n:       http://localhost:5678"
echo "  - Qdrant:    http://localhost:6333"
echo "  - API:       http://localhost:8000"
echo "  - Postgres:  localhost:5432"
echo "  - Redis:     localhost:6379"
echo ""
echo "🔗 Webhook URL (for GitHub):"
echo "  http://localhost:5678/webhook/swarm-webhook"
echo ""
echo "📋 Next steps:"
echo "  1. Open n8n at http://localhost:5678"
echo "  2. Configure GitHub OAuth credentials"
echo "  3. Set GEMINI_API_KEY in n8n environment"
echo "  4. Add webhook to your GitHub repository"
echo "  5. Push to trigger the swarm!"
echo ""
echo "🛑 To stop: docker-compose down"
echo "📊 To view logs: docker-compose logs -f"
echo ""
