# Copilot Swarm n8n Workflow

Autonomous multi-agent orchestration workflow using n8n for GitHub-driven ML agent coordination.

## Overview

The Copilot Swarm integrates 3 parallel ML agents coordinated via n8n workflow automation:

```
GitHub Webhook
      ↓
  ┌───┴────┬────────┬────────┐
  ↓        ↓        ↓        ↓
DATA    MODEL    API     (parallel execution)
AGENT   AGENT    AGENT
  ↓        ↓        ↓
  └───┬────┴────────┴────┐
      ↓                  ↓
  Merge Results    Commit to Repo
      ↓
  Create PR
      ↓
  Notification
```

## Workflow Nodes

### 1. GitHub Webhook (Trigger)
- **Type:** n8n-nodes-base.webhook
- **Trigger Event:** GitHub push to agent branches
- **Webhook Path:** `/c8v9m2k`
- **Methods:** POST
- **Payload:** GitHub webhook JSON

### 2. Codegen Agent (Execute Command)
- **Type:** n8n-nodes-base.executeCommand
- **Command:** `gh copilot suggest codegen agent`
- **Purpose:** Generate code improvements via Copilot
- **Output:** Code suggestions and modifications

### 3. Test Agent (Execute Command)
- **Type:** n8n-nodes-base.executeCommand
- **Command:** `gh copilot suggest test agent`
- **Purpose:** Generate test improvements
- **Output:** Test suggestions and coverage improvements

### 4. Deploy Agent (Execute Command)
- **Type:** n8n-nodes-base.executeCommand
- **Command:** `gh copilot suggest deploy agent`
- **Purpose:** Generate deployment optimizations
- **Output:** Deployment recommendations

### 5. Merge Results (Set Node)
- **Type:** n8n-nodes-base.set
- **Function:** Aggregate all agent outputs
- **Variables:**
  - `codegenResult` - Code agent output
  - `testResult` - Test agent output
  - `deployResult` - Deploy agent output
  - `timestamp` - Execution timestamp
  - `workflowStatus` - Status flag

### 6. Commit Results (HTTP Request)
- **Type:** n8n-nodes-base.httpRequest
- **Method:** POST to GitHub API
- **Endpoint:** `/repos/{owner}/{repo}/contents/swarm-results.json`
- **Action:** Saves merged results to repository
- **Branch:** `swarm-results`

### 7. Create PR (HTTP Request)
- **Type:** n8n-nodes-base.httpRequest
- **Method:** POST to GitHub API
- **Endpoint:** `/repos/{owner}/{repo}/pulls`
- **Action:** Creates PR with swarm results
- **Base:** `main`
- **Head:** `swarm-results`

### 8. Success Notification (No Operation)
- **Type:** n8n-nodes-base.noOp
- **Purpose:** Marks workflow completion
- **Can trigger:** Notifications, logging, etc.

## Setup Instructions

### Prerequisites

1. **n8n Instance**
   - Running n8n (local or cloud)
   - API access enabled
   - Credentials configured

2. **GitHub Integration**
   - GitHub OAuth token or personal access token
   - Repository webhook access
   - Permissions: repo, workflow

3. **Environment Variables**
   ```bash
   GITHUB_REPO_OWNER=your-org
   GITHUB_REPO_NAME=your-repo
   ```

### Installation

#### Option 1: Manual Import

1. Open n8n UI
2. Go to Workflows → Import
3. Upload `workflows/swarm.json`
4. Configure credentials:
   - GitHub OAuth2
   - Environment variables

#### Option 2: Automated Deployment (GitHub Actions)

1. Set repository secrets:
   ```
   N8N_BASE_URL=https://your-n8n-instance.com
   N8N_API_KEY=your-api-key
   ```

2. Push changes to `workflows/swarm.json`:
   ```bash
   git add workflows/swarm.json
   git commit -m "chore: update swarm workflow"
   git push origin main
   ```

3. GitHub Actions automatically imports workflow to n8n

### Configuration

#### GitHub Webhook

In n8n, copy webhook URL from trigger node:
```
https://your-n8n-instance.com/webhook/c8v9m2k
```

Configure in GitHub:
1. Settings → Webhooks → Add webhook
2. **Payload URL:** Paste webhook URL
3. **Content type:** application/json
4. **Events:** Push events, Pull requests
5. **Active:** ✓ Checked

#### OAuth2 Credentials

1. In n8n: Create credential "github-oauth"
2. Authorize with GitHub account
3. Ensure scopes: `repo`, `workflow`

### Testing

#### Test Webhook Locally

```bash
curl -X POST https://your-n8n-instance.com/webhook/c8v9m2k \
  -H "Content-Type: application/json" \
  -d '{
    "action": "opened",
    "pull_request": {"number": 1},
    "repository": {"name": "copilotcli-dev"}
  }'
```

#### Trigger via Git Push

Push to agent branches to trigger workflow:
```bash
git checkout data-agent
git commit --allow-empty -m "test: trigger swarm"
git push origin data-agent
```

Workflow should:
1. Receive GitHub webhook
2. Execute 3 agents in parallel
3. Merge results
4. Commit to repository
5. Create PR

## Workflow Execution

### Execution Flow

```
Start (GitHub Webhook)
  ↓
Parallel Execution:
  - Codegen Agent → stdout
  - Test Agent → stdout
  - Deploy Agent → stdout
  ↓
Synchronization Point (Merge Results)
  ↓
Set Variables:
  - codegenResult
  - testResult
  - deployResult
  - timestamp
  ↓
Commit to Repository:
  - Create branch: swarm-results
  - File: swarm-results.json
  - Content: Merged results (base64 encoded)
  ↓
Create Pull Request:
  - Title: "chore: swarm results - codegen, test, deploy agents"
  - Body: Detailed results summary
  - Head: swarm-results
  - Base: main
  ↓
Success Notification
  ↓
End
```

### Timeout Settings

- **Execution Timeout:** 3600 seconds (1 hour)
- **Individual Node Timeout:** Auto (n8n default)
- **Webhook Timeout:** 300 seconds

### Error Handling

- **Continue on Error:** Enabled for all Execute Command nodes
- **Retry Policy:** Automatic retry on failure
- **Error Logging:** All errors saved to execution history

## Results Format

### swarm-results.json

```json
{
  "agents": {
    "codegen": "Codegen agent output...",
    "test": "Test agent output...",
    "deploy": "Deploy agent output..."
  },
  "timestamp": "2026-02-12T05:50:00.000Z",
  "workflowStatus": "success"
}
```

## Monitoring

### View Executions

In n8n UI:
1. Open Copilot Swarm workflow
2. Click "Executions" tab
3. View execution history with timestamps
4. Click execution to see detailed logs

### Logs

Each node logs to:
- n8n execution history
- GitHub commit messages
- PR descriptions

## Troubleshooting

### Webhook Not Triggering

1. Verify GitHub webhook configuration
2. Check n8n webhook URL is publicly accessible
3. Test with curl command
4. View n8n execution logs

### OAuth2 Authentication Failed

1. Re-authorize GitHub in n8n credentials
2. Verify token scopes include `repo`
3. Check token has not expired

### Agents Not Executing

1. Verify `gh copilot` is installed: `gh copilot --version`
2. Check GitHub CLI authentication: `gh auth status`
3. Review agent branch existence

### PR Not Creating

1. Check GitHub API rate limits
2. Verify repository has write permissions
3. Check for existing `swarm-results` branch conflicts

## Maintenance

### Update Workflow

Edit `workflows/swarm.json` and push to main. GitHub Action auto-deploys.

### Backup Workflow

```bash
curl -H "X-N8N-API-KEY: your-key" \
  https://your-n8n-instance.com/api/v1/workflows | jq
```

### Version Control

Workflow version tracked in:
- `versionId: "1.0.0"` in swarm.json
- Git commit history
- GitHub Actions deployment logs

## Advanced Configuration

### Custom Agent Commands

Edit node parameters to run custom commands:

```json
{
  "id": "codegen-agent-node",
  "parameters": {
    "command": "custom-command-here"
  }
}
```

### Environment Variables

Set in n8n workflow environment:
```
GITHUB_REPO_OWNER=your-org
GITHUB_REPO_NAME=your-repo
N8N_WORKFLOW_ID=auto-set
```

### Rate Limiting

Configure in GitHub Actions:
```yaml
concurrency:
  group: n8n-deployment
  cancel-in-progress: false
```

## References

- [n8n Webhook Documentation](https://docs.n8n.io/nodes/n8n-nodes-base.webhook/)
- [GitHub API - Create Pull Request](https://docs.github.com/en/rest/pulls/pulls)
- [GitHub CLI Copilot](https://docs.github.com/en/copilot/github-copilot-in-the-cli)
