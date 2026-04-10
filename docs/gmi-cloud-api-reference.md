# GMI Cloud API Reference

> Official docs: https://docs.gmicloud.ai/
> OpenAPI specs: https://docs.gmicloud.ai/api-reference/openapi.json

---

## Table of Contents

- [Platform Overview](#platform-overview)
- [Authentication](#authentication)
- [Inference Engine API](#inference-engine-api)
  - [LLM API (OpenAI-compatible)](#llm-api-openai-compatible)
  - [Video API](#video-api)
  - [Video SDK (Python)](#video-sdk-python)
- [Cluster Engine API](#cluster-engine-api)
  - [Containers](#containers)
  - [Bare Metal Servers](#bare-metal-servers)
  - [Templates](#templates)
  - [Elastic IPs](#elastic-ips)
  - [Firewalls](#firewalls)
  - [VPCs](#vpcs)
  - [IDCs (Data Centers)](#idcs-data-centers)
  - [Images](#images)
- [User & Organization Management](#user--organization-management)
  - [Authentication & Sessions](#authentication--sessions)
  - [User Profile](#user-profile)
  - [SSH Keys](#ssh-keys)
  - [Organizations](#organizations)
  - [API Keys](#api-keys)
- [Inference Engine Concepts](#inference-engine-concepts)
  - [Serverless Endpoints](#serverless-endpoints)
  - [Dedicated Endpoints](#dedicated-endpoints)
  - [Artifacts](#artifacts)
  - [Tasks](#tasks)
- [Rate Limits](#rate-limits)
- [Pricing](#pricing)

---

## Platform Overview

GMI Cloud is an AI-native inference cloud powered by NVIDIA GPUs (H100, H200, B200, GB200). It offers:

- **Inference Engine** -- Serverless and dedicated endpoints for 100+ pre-deployed AI models (LLM, image, video, audio, TTS)
- **Cluster Engine** -- Bare metal servers, containers, Kubernetes orchestration, and GPU cluster management
- **GMI Studio** -- Visual workflow canvas for building AI pipelines

Data centers: US (Silicon Valley, Colorado/Denver), Taiwan, Thailand, Malaysia.

---

## Authentication

### Inference Engine API (LLM / Video)

```
Authorization: Bearer <GMI_API_KEY>
```

Obtain API keys from: https://console.gmicloud.ai/user-setting/api-keys

For multi-organization access, include:
```
X-Organization-ID: <your_org_id>
```

### Cluster Engine API (Containers / Bare Metal)

```
Authorization: Bearer <YOUR_API_KEY>
Content-Type: application/json
```

**Security best practices:**
- Store keys in environment variables or secret managers
- Never expose keys in client-side code
- Rotate keys periodically

---

## Inference Engine API

### LLM API (OpenAI-compatible)

**Base URL:** `https://api.gmi-serving.com/v1`

The LLM API is fully OpenAI-compatible -- you can use the OpenAI SDK by changing the base URL and API key.

#### List Models

```
GET /models
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "deepseek-ai/DeepSeek-R1",
      "object": "model",
      "created": 1234567890,
      "owned_by": "deepseek-ai"
    }
  ]
}
```

#### Create Chat Completion

```
POST /chat/completions
```

**Required Parameters:**

| Parameter  | Type     | Description              |
|-----------|----------|--------------------------|
| `model`   | string   | Model identifier         |
| `messages` | array   | Conversation history     |

**Optional Parameters:**

| Parameter                          | Type    | Default | Range/Notes                        |
|------------------------------------|---------|---------|------------------------------------|
| `max_tokens`                       | integer | 2000    | 1 - model max                      |
| `temperature`                      | number  | 1       | 0 - 2                              |
| `top_p`                            | number  | 1       | 0 - 1 (nucleus sampling)           |
| `top_k`                            | integer | --      | 1 - 128                            |
| `stream`                           | boolean | false   | Enable streaming responses         |
| `stop`                             | array   | --      | Up to 4 stop sequences             |
| `response_format`                  | object  | --      | `{"type": "json_object"}` for JSON |
| `ignore_eos`                       | boolean | false   | Continue past EOS token            |
| `context_length_exceeded_behavior` | string  | truncate| `"truncate"` or `"error"`          |
| `tools`                            | array   | --      | Function calling definitions       |
| `frequency_penalty`                | number  | 0       | Reduce repetition                  |
| `presence_penalty`                 | number  | 0       | Encourage new topics               |

**Request Example:**
```bash
curl https://api.gmi-serving.com/v1/chat/completions \
  -H "Authorization: Bearer $GMI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-ai/DeepSeek-R1",
    "messages": [
      {"role": "system", "content": "You are a helpful assistant."},
      {"role": "user", "content": "Hello!"}
    ],
    "max_tokens": 1024,
    "temperature": 0.7,
    "stream": false
  }'
```

**Response:**
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "deepseek-ai/DeepSeek-R1",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 10,
    "total_tokens": 30
  }
}
```

**Using with OpenAI SDK (Python):**
```python
from openai import OpenAI

client = OpenAI(
    api_key="your-gmi-api-key",
    base_url="https://api.gmi-serving.com/v1"
)

response = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-R1",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=1024
)
print(response.choices[0].message.content)
```

**Using with LiteLLM:**
```python
import litellm

response = litellm.completion(
    model="gmi/deepseek-ai/DeepSeek-R1",
    messages=[{"role": "user", "content": "Hello!"}],
    api_key="your-gmi-api-key"
)
```

---

### Video API

**Base URL:** `https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey`

Video generation is asynchronous -- submit a job, then poll for results.

#### List Video Models

```
GET /models
```

**Available models include:**
- `Kling-Image2Video-V2.1-Master`
- `Kling-Text2Video-V2.1-Master`
- `Luma-Ray2`
- `Veo3`
- `Veo3-Fast`

#### Get Model Details

```
GET /models/{model-id}
```

Returns model description, supported modalities, and parameter schema.

#### Create Video Job

```
POST /requests
```

**Request Example:**
```bash
curl -X POST https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey/requests \
  -H "Authorization: Bearer $GMI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Kling-Text2Video-V2.1-Master",
    "payload": {
      "prompt": "A cat walking on a beach at sunset",
      "duration": 5,
      "aspect_ratio": "16:9",
      "negative_prompt": "blurry, low quality"
    }
  }'
```

**Response:**
```json
{
  "request_id": "req_abc123",
  "status": "dispatched"
}
```

#### Check Job Status

```
GET /requests/{REQUEST_ID}
```

**Status values:** `dispatched` -> `processing` -> `success` (or `failed`)

On success, the response includes:
```json
{
  "status": "success",
  "outcome": {
    "video_url": "https://storage.googleapis.com/...",
    "thumbnail_image_url": "https://storage.googleapis.com/..."
  }
}
```

**File input methods:** Base64 data URIs, publicly accessible URLs, or the upload API endpoint.

---

### Video SDK (Python)

```bash
pip install gmicloud
```

**Authentication:**
```bash
export GMI_CLOUD_EMAIL="<YOUR_EMAIL>"
export GMI_CLOUD_PASSWORD="<YOUR_PASSWORD>"
```

**Usage:**
```python
from gmicloud import Client
from gmicloud._internal._models import SubmitRequestRequest

client = Client()

# List models
models = client.video_manager.get_models()

# Get model details
detail = client.video_manager.get_model_detail("Wan-AI_Wan2.1-T2V-14B")

# Submit a video generation request
request = SubmitRequestRequest(
    model="Wan-AI_Wan2.1-T2V-14B",
    payload={
        "prompt": "A futuristic city at night",
        "video_length": 5
    }
)
response = client.video_manager.create_request(request)
request_id = response.request_id

# Poll for completion (use 5-10s intervals)
import time
while True:
    detail = client.video_manager.get_request_detail(request_id)
    if detail.status in ("SUCCESS", "FAILED"):
        break
    time.sleep(5)

# Get all requests for a model
requests = client.video_manager.get_requests("Wan-AI_Wan2.1-T2V-14B")
```

**Request status lifecycle:** `CREATED` -> `QUEUED` -> `DISPATCHED` -> `PROCESSING` -> `SUCCESS` / `FAILED` / `CANCELLED`

---

## Cluster Engine API

**Base URL:** `https://console.gmicloud.ai/api/v1`

All endpoints require `Authorization: Bearer <API_KEY>` and `Content-Type: application/json`.

### Containers

| Method | Path                            | Description                            |
|--------|---------------------------------|----------------------------------------|
| POST   | `/containers`                   | Create container(s) under default namespace |
| GET    | `/containers`                   | List container information             |
| GET    | `/containers/{id}`              | Get container info by ID               |
| PUT    | `/containers/{id}`              | Update container                       |
| DELETE | `/containers/{id}`              | Delete container                       |
| POST   | `/containers/{id}/restart`      | Restart container                      |
| GET    | `/containers/{id}/logs`         | Download container logs                |
| GET    | `/containers/{id}/shell`        | Generate container shell URL path      |
| GET    | `/containers/products`          | Get container products (GPU options)   |

**Create Container Example:**
```bash
curl -X POST https://console.gmicloud.ai/api/v1/containers \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-container",
    "templateId": "b89f653f-f080-40a9-8134-02dd6d213894",
    "count": 1,
    "product": "container.h200.x1",
    "idc": "us-denver-1",
    "envs": [
      {"name": "SSH_KEY", "value": "ssh-rsa AAAA..."}
    ]
  }'
```

**Product IDs:** Format is `container.<gpu>.<count>` (e.g., `container.h200.x1`).

### Bare Metal Servers

| Method | Path                            | Description                        |
|--------|---------------------------------|------------------------------------|
| POST   | `/baremetals`                   | Create baremetal server(s)         |
| GET    | `/baremetals`                   | List all baremetal servers         |
| GET    | `/baremetals/{id}`              | Get baremetal server by ID         |
| PUT    | `/baremetals/{id}`              | Update baremetal server            |
| DELETE | `/baremetals/{id}`              | Delete baremetal server            |
| POST   | `/baremetals/{id}/action`       | Execute server action (start/stop) |
| GET    | `/baremetals/products`          | Get baremetal products             |

### Templates

| Method | Path                  | Description           |
|--------|-----------------------|-----------------------|
| POST   | `/templates`          | Create template       |
| GET    | `/templates`          | List templates        |
| GET    | `/templates/{id}`     | Get template by ID    |
| PUT    | `/templates/{id}`     | Update template       |
| DELETE | `/templates/{id}`     | Delete template       |

### Elastic IPs

| Method | Path                              | Description                          |
|--------|-----------------------------------|--------------------------------------|
| POST   | `/elastic-ips`                    | Allocate elastic IP for organization |
| GET    | `/elastic-ips`                    | List elastic IPs                     |
| GET    | `/elastic-ips/{id}`               | Get elastic IP details               |
| POST   | `/elastic-ips/{id}/associate`     | Associate with instance              |
| POST   | `/elastic-ips/{id}/disassociate`  | Disassociate from instance           |
| DELETE | `/elastic-ips/{id}`               | Release elastic IP                   |
| GET    | `/elastic-ips/products`           | Get elastic IP products              |

### Firewalls

| Method | Path                              | Description                |
|--------|-----------------------------------|----------------------------|
| POST   | `/firewalls`                      | Create firewall            |
| GET    | `/firewalls`                      | List firewalls             |
| GET    | `/firewalls/{id}`                 | Get firewall by ID         |
| PUT    | `/firewalls/{id}`                 | Update firewall            |
| DELETE | `/firewalls/{id}`                 | Delete firewall            |
| POST   | `/firewalls/{id}/associate`       | Associate with instance    |
| POST   | `/firewalls/{id}/disassociate`    | Disassociate from instance |

### VPCs

| Method | Path                           | Description                              |
|--------|--------------------------------|------------------------------------------|
| POST   | `/vpcs`                        | Allocate default VPC for org in IDC      |
| GET    | `/vpcs`                        | List all VPCs                            |
| GET    | `/vpcs/{id}`                   | Get VPC details                          |
| DELETE | `/vpcs/{id}`                   | Release default VPC                      |

### IDCs (Data Centers)

| Method | Path    | Description                                     |
|--------|---------|-------------------------------------------------|
| GET    | `/idcs` | List all IDCs (non-hidden data center locations) |

**Known IDC values:** `us-denver-1`, and locations in Silicon Valley, Taiwan, Thailand, Malaysia.

### Images

| Method | Path            | Description       |
|--------|-----------------|-------------------|
| GET    | `/images`       | List images       |
| GET    | `/images/{id}`  | Get image by ID   |

---

## User & Organization Management

**Base URL:** `https://console.gmicloud.ai/api/v1`

### Authentication & Sessions

| Method | Path                   | Description                           |
|--------|------------------------|---------------------------------------|
| POST   | `/me/session`          | Create login session                  |
| POST   | `/me/session/refresh`  | Refresh session (new access/refresh tokens) |
| POST   | `/me/auth-token`       | Create auth token via credentials     |
| POST   | `/me/auth-token/oauth` | Create auth token via OAuth provider  |
| POST   | `/me/2fa/resend`       | Resend 2FA verification code          |

### User Profile

| Method | Path            | Description             |
|--------|-----------------|-------------------------|
| GET    | `/me/profile`   | Retrieve user profile   |
| PUT    | `/me/profile`   | Update user profile     |
| PUT    | `/me/password`  | Update user password    |

### SSH Keys

| Method | Path               | Description        |
|--------|--------------------|--------------------|
| POST   | `/me/ssh-keys`     | Create SSH key     |
| GET    | `/me/ssh-keys`     | List SSH keys      |
| PUT    | `/me/ssh-keys/{id}`| Update SSH key     |
| DELETE | `/me/ssh-keys/{id}`| Delete SSH key     |

### Organizations

| Method | Path                              | Description                       |
|--------|-----------------------------------|-----------------------------------|
| POST   | `/organizations`                  | Register new organization         |
| GET    | `/organizations/{id}`             | Retrieve organization info        |
| PUT    | `/organizations/{id}`             | Update organization info (owner)  |
| DELETE | `/organizations/{id}`             | Delete organization (owner only)  |
| GET    | `/organizations/{id}/users`       | List users in organization        |
| POST   | `/organizations/{id}/invitations` | Send invitations via email (admin)|
| POST   | `/organizations/{id}/transfer`    | Transfer ownership                |

### API Keys

| Method | Path                              | Description                       |
|--------|-----------------------------------|-----------------------------------|
| POST   | `/organizations/{id}/api-keys`    | Create API key for organization   |
| GET    | `/organizations/{id}/api-keys`    | List API keys                     |
| DELETE | `/organizations/{id}/api-keys/{keyId}` | Delete API key              |
| GET    | `/me/api-key/verify`              | Verify API key and get details    |

### User Registration

| Method | Path                          | Description                        |
|--------|-------------------------------|------------------------------------|
| POST   | `/users/verify-email`         | Verify email & complete registration|
| POST   | `/users/resend-verification`  | Resend email verification code     |
| POST   | `/users/password-reset`       | Request password reset email       |
| DELETE | `/users/{id}`                 | Delete user account                |

### Invitations & OAuth

| Method | Path                          | Description                          |
|--------|-------------------------------|--------------------------------------|
| POST   | `/invitations/{key}/accept`   | Accept invitation by key             |
| POST   | `/oauth/token`                | Exchange authorization code for token|

---

## Inference Engine Concepts

### Serverless Endpoints

Pre-configured, fully managed endpoints with:
- **OpenAI-compatible API** -- use the same SDK/code, just change base URL
- **Automatic scaling** -- pay only for what you use
- **Instant access** -- no setup, no GPU provisioning
- **Rate-limited** by tier (see [Rate Limits](#rate-limits))

Best for: prototyping, small-to-medium workloads, cost-sensitive use cases.

**Playground parameters:** temperature, max_tokens, top_k, top_p, frequency_penalty, presence_penalty, stream, system prompt.

### Dedicated Endpoints

User-provisioned environments with full control:
- Deploy fine-tuned or proprietary models
- Dedicated GPU resources (H100, H200)
- Private isolation and enterprise-grade security
- **No rate limits** -- unlimited throughput
- Configurable auto-scaling policies (min/max replicas)

**Deployment statuses:** `Queued` -> `Deploying` -> `Running` -> `Stopped` / `Archived`

Billing starts only when status is **Running**.

Best for: production workloads, enterprise, low-latency requirements.

### Artifacts

Manage model artifacts and dependencies:
- Docker containers, model files, and scripts
- Secure storage with versioning
- Two types: **Custom Models** (user-created) and **Official Models** (GMI-provided)
- Can create from templates or from scratch (upload ZIP + model files)

### Tasks

Deploy dedicated endpoints from artifacts:
- **One-off** or **Daily** scheduling
- Auto-scaling with min/max replica configuration
- Status lifecycle: `Idle` -> `In-queue` -> `Starting` -> `Running` -> `Need Stop`

---

## Rate Limits

Rate limits are enforced at the **organization level**.

- **LLM models:** Tokens per Minute (TPM)
- **Video models:** Requests per Hour (RPH)

### Tier System

Tiers auto-upgrade within 24 hours of purchase (vouchers don't count).

| Tier   | Purchase Threshold | Upgrade Time |
|--------|-------------------|--------------|
| Tier 1 | $0 (free)         | Immediate    |
| Tier 2 | $5                | 24 hours     |
| Tier 3 | $50               | 24 hours     |
| Tier 4 | $200              | 24 hours     |
| Tier 5 | $1,000            | 24 hours     |

### TPM Limits by Tier (LLM Models)

| Model Category                          | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Tier 5      |
|-----------------------------------------|--------|--------|--------|--------|-------------|
| DeepSeek (R1, V3, Prover)              | 100K   | 450K   | 800K   | 2M     | 30M - 150M  |
| Llama, Qwen, QwQ, newer models         | 100K   | 2M     | 4M     | 10M    | 150M        |

Contact support@gmicloud.ai for manual tier upgrades.

---

## Pricing

### Serverless LLM (per million tokens)

| Model                                | Input    | Output   |
|--------------------------------------|----------|----------|
| DeepSeek R1 Distill Qwen 1.5B       | $0.00    | $0.00    |
| Meta Llama-4 Scout 17B 16E Instruct | $0.08    | $0.50    |
| OpenAI GPT OSS 120b                 | $0.07    | $0.28    |
| DeepSeek-V3.2-Exp                   | $0.27    | $0.41    |
| Qwen variants                       | $0.15-$0.60 | varies |
| ZAI GLM-4.6                         | $0.60    | $2.00    |
| Moonshotai Kimi-K2-Instruct         | $1.00    | $3.00    |

29+ models available. Full list at https://console.gmicloud.ai

### Dedicated GPU (per hour)

| GPU  | Price     |
|------|-----------|
| H100 | $2.98/hr  |
| H200 | $3.98/hr  |

### Bare Metal GPU (per hour)

| GPU  | Price     |
|------|-----------|
| H100 | $2.00/hr  |
| H200 | $2.60/hr  |
| B200 | $4.00/hr  |
| GB200| $8.00/hr  |

---

## OpenAPI Specifications

Machine-readable specs for programmatic use:

| Spec             | URL                                                    |
|------------------|--------------------------------------------------------|
| Console API      | https://docs.gmicloud.ai/api-reference/openapi.json   |
| Service API      | https://docs.gmicloud.ai/api-spec/service_api.yaml    |
| IDS Public API   | https://docs.gmicloud.ai/api-spec/ids-public-api.yaml |
| IAS Public API   | https://docs.gmicloud.ai/api-spec/ias-public-api.yaml |
| IAM API          | https://docs.gmicloud.ai/api-reference-2/iam-api.yaml |

---

## Quick Links

| Resource                   | URL                                                          |
|----------------------------|--------------------------------------------------------------|
| Docs Home                  | https://docs.gmicloud.ai/                                   |
| API Keys Console           | https://console.gmicloud.ai/user-setting/api-keys           |
| Docs Index (llms.txt)      | https://docs.gmicloud.ai/llms.txt                           |
| LiteLLM Integration        | https://docs.litellm.ai/docs/providers/gmi                  |
| LLM API Reference          | https://docs.gmicloud.ai/inference-engine/api-reference/llm-api-reference |
| Video API Reference         | https://docs.gmicloud.ai/inference-engine/api-reference/video-api-reference |
| Video SDK Reference         | https://docs.gmicloud.ai/inference-engine/api-reference/video-sdk-reference |
| Rate Limits                 | https://docs.gmicloud.ai/inference-engine/api-reference/rate-limit |
| Pricing                     | https://docs.gmicloud.ai/inference-engine/billing/price      |
| Support                     | support@gmicloud.ai                                          |
