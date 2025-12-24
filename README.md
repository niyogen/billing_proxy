# BillingProxy Service

A production-ready, autoscaling LLM Proxy built on [LiteLLM](https://docs.litellm.ai/), Google Cloud Run, and PostgreSQL. It provides a unified API interface for multiple LLM providers (OpenAI, Vertex AI) with centralized authentication, logging, and billing visibility.

## 🏗 Architecture

```mermaid
graph LR
    Client[Client App] -->|Auth Bearer <token>| Proxy[BillingProxy (Cloud Run)]
    Proxy -->|Log Usage| DB[(PostgreSQL)]
    Proxy -->|Log Metrics| CloudMonitor[Cloud Monitoring]
    Proxy -->|OpenAI Protocol| OpenAI[OpenAI API]
    Proxy -->|Google Protocol| Gemini[Gemini API]
```
 

 
## 🚀 Features
- **Unified Interface**: OpenAI-compatible API (`/v1/chat/completions`) for all models.
- **Centralized Auth**: Manage access via Proxy Master Keys and Gateway Tokens.
- **Usage Tracking**: Detailed logging of tokens, cost, and latency to PostgreSQL (`litellm_usage` table).
- **Observability**: Structured JSON logs integrated with Google Cloud Logging and Monitoring.
- **Scalability**: deployable to Cloud Run with autoscaling support.

---

## 🔌 Integration Guide

The service exposes an OpenAI-compatible API. You can connect using standard SDKs.

### Prerequisites
- **Base URL**: Your Cloud Run Service URL (e.g., `https://litellm-proxy-xyz.a.run.app`)
- **API Key**: A valid Proxy Gateway Token (`<YOUR_TOKEN>`)

### 1. Using `curl`
```bash
curl -X POST "https://YOUR_SERVICE_URL/v1/chat/completions" \
     -H "Authorization: Bearer <YOUR_PROXY_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-4o",
       "messages": [
         { "role": "user", "content": "Hello world!" }
       ]
     }'
```

### 2. Using Python `openai` Client
```python
from openai import OpenAI

client = OpenAI(
    api_key="<YOUR_PROXY_TOKEN>",
    base_url="https://YOUR_SERVICE_URL/v1"  # Note the /v1 suffix
)

response = client.chat.completions.create(
    model="gpt-4o",  # or "gemini-1.5-flash"
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

### 3. Using Node.js `openai` Client
```javascript
import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: '<YOUR_PROXY_TOKEN>',
  baseURL: 'https://YOUR_SERVICE_URL/v1',
});

async function main() {
  const chatCompletion = await openai.chat.completions.create({
    messages: [{ role: 'user', content: 'Hello!' }],
    model: 'gpt-4o',
  });
  console.log(chatCompletion.choices[0].message.content);
}
main();
```

---

## 📊 Monitoring & Observability

### 1. Infrastructure Monitoring (Cloud Run)
- Go to **Google Cloud Console > Cloud Run > litellm-proxy**.
- View built-in dashboards for:
    - **Request Count**: Traffic volume.
    - **Container Instance Count**: Autoscaling behavior.
    - **CPU/Memory Utilization**.

### 2. Application Logs (Cloud Logging)
- All requests produce structured JSON logs.
- Go to **Cloud Logging > Logs Explorer**.
- Filter by `resource.type="cloud_run_revision"` and `jsonPayload.model`.
- **Key Fields**:
    - `jsonPayload.model`: The model used (e.g., `gpt-4o`).
    - `jsonPayload.usage.total_tokens`: Total tokens consumed.
    - `jsonPayload.cost`: Estimated cost in USD.
    - `jsonPayload.latency`: Request duration.

### 3. Usage Database (PostgreSQL)
Query the `litellm_usage` table for granular billing analysis.

**Example: Daily Cost by Model**
```sql
SELECT 
    DATE(start_time) as day,
    model,
    SUM(total_tokens) as tokens,
    SUM(cost) as total_cost
FROM litellm_usage
GROUP BY 1, 2
ORDER BY 1 DESC;
```

---

## 🛠 Development & Testing

### Running Tests
This repository includes a full test suite (Unit, Integration, Load).

```bash
# Install Dev Dependencies
pip install -r requirements.txt

# Run Unit Tests
pytest tests/

# Run Integration Tests (Requires Docker)
cd tests/integration
python test_full_flow.py
```

### CI/CD Pipeline
- **Provider**: GitHub Actions
- **Trigger**: Push to `main`
- **Stages**:
    1. **Test**: Runs Unit, Integration, and Load tests in parallel.
    2. **Deploy**: Automatically deploys to Cloud Run if tests pass.
