# GMI Cloud -- All Available Services

> You have **2 API keys**: one for **Inference** and one for **Infrastructure (Cluster Engine)**.
> Budget: **$1,000 credit** (qualifies for **Tier 5** -- highest rate limits).

---

## Table of Contents

1. [Key Summary](#key-summary)
2. [INFERENCE KEY -- Services](#inference-key----services)
   - [Serverless LLM Inference](#1-serverless-llm-inference)
   - [Dedicated LLM Endpoints](#2-dedicated-llm-endpoints)
   - [Video Generation](#3-video-generation)
   - [Image Generation](#4-image-generation)
   - [Audio / TTS / Music](#5-audio--tts--music)
   - [MaaS (Proprietary Models)](#6-maas-model-as-a-service----proprietary-models)
   - [Artifacts & Tasks](#7-artifacts--tasks)
3. [INFRA KEY -- Services](#infra-key----services)
   - [GPU Containers](#1-gpu-containers)
   - [Bare Metal Servers](#2-bare-metal-servers)
   - [Managed GPU Clusters (Kubernetes)](#3-managed-gpu-clusters-kubernetes)
   - [Networking -- VPCs & Subnets](#4-networking----vpcs--subnets)
   - [Networking -- Elastic IPs](#5-networking----elastic-ips)
   - [Networking -- Firewalls](#6-networking----firewalls)
   - [Templates](#7-templates)
   - [OS Images](#8-os-images)
   - [SSH Key Management](#9-ssh-key-management)
   - [Cold Storage (S3-compatible)](#10-cold-storage-s3-compatible)
   - [IDCs (Data Centers)](#11-idcs-data-centers)
4. [Shared Services (Both Keys)](#shared-services-both-keys)
   - [Organization Management](#organization-management)
   - [User Profile & Auth](#user-profile--auth)
   - [Billing & Orders](#billing--orders)
5. [GMI Studio](#gmi-studio)
6. [Full Model Catalog](#full-model-catalog)
7. [Pricing Summary](#pricing-summary)

---

## Key Summary

| Key        | Env Var      | JWT Scope       | Base URL                                              | What It Covers                              |
|------------|-------------|-----------------|-------------------------------------------------------|---------------------------------------------|
| Inference  | `GMI_INFER` | `ie_model`      | `https://api.gmi-serving.com/v1` (LLM)               | LLM, Video, Image, Audio model endpoints |
|            |             |                 | `https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey` (Video) |                               |
| Infra      | `GMI_INFRA` | `ce_resource`   | `https://console.gmicloud.ai/api/v1`                 | Containers, Bare Metal, K8s, Networking     |

**Auth header:** `Authorization: Bearer <KEY>`
For multi-org access, add: `X-Organization-ID: <your_org_id>`

**Note:** User management endpoints (`/me/profile`, `/me/ssh-keys`) require a **session token** (from login), not an API key. API keys are scoped to their engine only.

---

# INFERENCE KEY -- Services

## 1. Serverless LLM Inference

**What it is:** Pre-deployed models accessible instantly via OpenAI-compatible API. No GPU provisioning needed. Pay per token.

**Base URL:** `https://api.gmi-serving.com/v1`

**Endpoints:**

| Method | Path                | Description          |
|--------|---------------------|----------------------|
| GET    | `/models`           | List available models |
| POST   | `/chat/completions` | Chat completion      |

**Key features:**
- Fully OpenAI SDK-compatible (just change `base_url`)
- Streaming support
- Function/tool calling
- JSON mode (`response_format`)
- 29+ models from free to premium

**Quick start:**
```python
from openai import OpenAI
client = OpenAI(api_key="<INFERENCE_KEY>", base_url="https://api.gmi-serving.com/v1")
r = client.chat.completions.create(model="deepseek-ai/DeepSeek-R1", messages=[{"role":"user","content":"Hi"}])
```

**Your Tier 5 limits:** up to 150M tokens/minute on most models.

---

## 2. Dedicated LLM Endpoints

**What it is:** Provision your own GPU-backed endpoint for a specific model. No rate limits, private isolation, auto-scaling.

**How it works:**
1. Select a model from the marketplace
2. Configure: GPU type, deployment name, auto-scaling policy (min/max replicas)
3. Deploy -- endpoint URL provided when status reaches `Running`

**GPU options:** H100 ($2.98/hr), H200 ($3.98/hr)

**Statuses:** `Queued` -> `Deploying` -> `Running` -> `Stopped` -> `Archived`

Billing only during `Running`. You can stop/restart at will.

---

## 3. Video Generation

**What it is:** Async video generation from text or image prompts. Submit job, poll for result.

**Base URL:** `https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey`

**Endpoints:**

| Method | Path                    | Description              |
|--------|-------------------------|--------------------------|
| GET    | `/models`               | List video models        |
| GET    | `/models/{model-id}`    | Get model details/schema |
| POST   | `/requests`             | Submit video gen job     |
| GET    | `/requests/{id}`        | Check job status         |

**Available models:**
- Kling-Text2Video-V2.1-Master
- Kling-Image2Video-V2.1-Master
- Luma-Ray2
- Veo3
- Veo3-Fast
- Sora-2-Pro (OpenAI)
- Wan-AI Wan2.1-T2V-14B
- PixVerse, Vidu, Hunyuan models

**Job status flow:** `dispatched` -> `processing` -> `success` / `failed`

**Python SDK alternative:**
```bash
pip install gmicloud
```
```python
from gmicloud import Client
from gmicloud._internal._models import SubmitRequestRequest
client = Client()  # uses GMI_CLOUD_EMAIL / GMI_CLOUD_PASSWORD env vars
req = SubmitRequestRequest(model="Veo3-Fast", payload={"prompt": "...", "video_length": 5})
resp = client.video_manager.create_request(req)
```

**SDK status lifecycle:** `CREATED` -> `QUEUED` -> `DISPATCHED` -> `PROCESSING` -> `SUCCESS` / `FAILED` / `CANCELLED`

---

## 4. Image Generation

**What it is:** Generate images from text prompts via serverless models.

**Available models:**
- seedream-5.0-lite
- gemini-2.5-flash-image
- Black Forest Labs / Flux models

Uses the same Video API base URL and async job pattern.

---

## 5. Audio / TTS / Music

**What it is:** Text-to-speech, voice cloning, and music generation.

**Available models:**
- elevenlabs-tts-v3 (text-to-speech)
- minimax-tts-speech-2.6-turbo (TTS)
- minimax-audio-voice-clone-speech-2.6-hd (voice cloning)
- minimax-music-2.5 (music generation)

Uses the same async request pattern as video/image.

---

## 6. MaaS (Model-as-a-Service) -- Proprietary Models

**What it is:** Access to proprietary/closed-source models through GMI at discounted rates.

**Available providers & models:**
- OpenAI: GPT-5 (10% discount via GMI)
- Anthropic: Claude Sonnet 4.6
- Google: Gemini
- Zhipu AI: GLM-4.6, GLM-4.5
- MoonshotAI: Kimi-K2
- And more

Same OpenAI-compatible API. One platform, unified billing.

---

## 7. Artifacts & Tasks

**Artifacts** -- Package and version your model deployments:
- Store Docker containers, model files, and scripts
- Custom or Official (GMI-provided)
- Create from templates or upload ZIP + model files

**Tasks** -- Deploy dedicated endpoints from artifacts:
- One-off or daily scheduling
- Auto-scaling (min/max replicas)
- Status: `Idle` -> `In-queue` -> `Starting` -> `Running` -> `Need Stop`
- Each task gets its own service endpoint URL + monitoring dashboard

---

# INFRA KEY -- Services

## 1. GPU Containers

**What it is:** Rent GPU-powered containers with SSH, JupyterLab, and web shell access. Best for development, training, and experimentation.

**API Base:** `https://console.gmicloud.ai/api/v1`

**Endpoints:**

| Method | Path                       | Description                   |
|--------|----------------------------|-------------------------------|
| POST   | `/containers`              | Create container(s)           |
| GET    | `/containers`              | List all containers           |
| GET    | `/containers/{id}`         | Get container by ID           |
| PUT    | `/containers/{id}`         | Update container              |
| DELETE | `/containers/{id}`         | Delete container              |
| POST   | `/containers/{id}/restart` | Restart container             |
| GET    | `/containers/{id}/logs`    | Download container logs       |
| GET    | `/containers/{id}/shell`   | Get web shell URL             |
| GET    | `/containers/products`     | List GPU product options      |

**GPU options:** H200 confirmed; likely H100 also available. Quantities: 1x, 2x, 4x, 8x.

**Product ID format:** `container.<gpu>.<count>` (e.g., `container.h200.x1`)

**Features:**
- Pre-built templates with SSH (port 22) and JupyterLab (port 8888)
- Custom port forwarding (TCP/UDP)
- Mountable storage volumes (typically `/share`)
- Environment variables (up to 10)
- Custom startup commands
- Monitoring: GPU usage, GPU memory, CPU, RAM (15min to 30-day ranges)
- Billing: pay-as-you-go (per minute) or prepaid (1 day to 3 years)

**Container statuses:** `Creating` -> `Running` / `Error` / `Terminating`

**Access methods:**
```bash
# SSH
ssh root@<public-ip> -i /path/to/private-key

# JupyterLab -- click port 8888 link in console
# Web Shell -- "Open Shell" from console (root access)
```

**Warning:** Reconfiguring a container **permanently deletes all data** inside it.

---

## 2. Bare Metal Servers

**What it is:** Full dedicated physical servers with NVIDIA GPUs. No hypervisor overhead. Maximum performance.

**Endpoints:**

| Method | Path                        | Description                          |
|--------|-----------------------------|--------------------------------------|
| POST   | `/baremetals`               | Create baremetal server(s)           |
| GET    | `/baremetals`               | List all baremetal servers           |
| GET    | `/baremetals/{id}`          | Get server by ID                     |
| PUT    | `/baremetals/{id}`          | Update server                        |
| DELETE | `/baremetals/{id}`          | Delete server                        |
| POST   | `/baremetals/{id}/action`   | Execute action (start/stop/reboot/powercycle) |
| GET    | `/baremetals/products`      | List available hardware products     |

**Available GPUs:** H100, H200, B200, GB200 (8x 80GB multi-card servers with InfiniBand)

**Configuration options:**
- Billing: pay-as-you-go or prepaid
- Data center location selection
- OS image (default: Ubuntu 22.04)
- Disk partitioning
- VPC & subnet assignment
- Elastic IP allocation
- Firewall rules
- SSH key selection
- Monitoring service

**Server actions:** Start, Stop, Reboot, PowerCycle (with confirmation)

**Pricing:**
| GPU   | Per Hour |
|-------|----------|
| H100  | $2.00    |
| H200  | $2.60    |
| B200  | $4.00    |
| GB200 | $8.00    |

---

## 3. Managed GPU Clusters (Kubernetes)

**What it is:** Fully managed Kubernetes-based GPU clusters for large-scale AI workloads. Cluster-level orchestration across multiple GPU worker nodes.

**Features:**
- Dedicated GPU worker nodes
- Configurable Kubernetes versions
- Multi-datacenter support
- Pay-as-you-go (per minute) or prepaid billing
- Cluster monitoring and status tracking

**Setup process:**
1. Select billing, datacenter, K8s version, instance type, node count
2. Choose OS image (default Ubuntu 22.04 x86 64-bit)
3. Name the cluster

**Important:** Cluster requests are **not automatic** -- you must contact GMI support after submitting to activate.

**Management:**
- Filter clusters by name, IP, datacenter, status
- Monitor specs, node counts, billing, estimated monthly cost
- Track request status (All / In Progress / Error)

---

## 4. Networking -- VPCs & Subnets

**What it is:** Isolated virtual networks for bare metal servers.

**Endpoints:**

| Method | Path         | Description                         |
|--------|--------------|-------------------------------------|
| POST   | `/vpcs`      | Allocate default VPC for org in IDC |
| GET    | `/vpcs`      | List all VPCs                       |
| GET    | `/vpcs/{id}` | Get VPC details                     |
| DELETE | `/vpcs/{id}` | Release default VPC                 |

**Details:**
- Each datacenter auto-creates a Default VPC with a Default Subnet
- VPC defines IPv4 CIDR block
- Subnets define IP ranges within the VPC
- Bare metal servers are assigned to a VPC/subnet at creation
- Searchable by name, ID, datacenter, or CIDR

---

## 5. Networking -- Elastic IPs

**What it is:** Static public IP addresses that persist across server restarts. Can be reassigned between instances.

**Endpoints:**

| Method | Path                             | Description            |
|--------|----------------------------------|------------------------|
| POST   | `/elastic-ips`                   | Allocate elastic IP    |
| GET    | `/elastic-ips`                   | List elastic IPs       |
| GET    | `/elastic-ips/{id}`              | Get IP details         |
| POST   | `/elastic-ips/{id}/associate`    | Bind to instance       |
| POST   | `/elastic-ips/{id}/disassociate` | Unbind from instance   |
| DELETE | `/elastic-ips/{id}`              | Release IP permanently |
| GET    | `/elastic-ips/products`          | Get IP products/pricing|

**Billing:** Pay-as-you-go, per minute. **Charged even when unassociated** -- release unused IPs.

---

## 6. Networking -- Firewalls

**What it is:** Inbound traffic rules for bare metal servers.

**Endpoints:**

| Method | Path                             | Description              |
|--------|----------------------------------|--------------------------|
| POST   | `/firewalls`                     | Create firewall          |
| GET    | `/firewalls`                     | List firewalls           |
| GET    | `/firewalls/{id}`                | Get firewall by ID       |
| PUT    | `/firewalls/{id}`                | Update rules             |
| DELETE | `/firewalls/{id}`                | Delete firewall          |
| POST   | `/firewalls/{id}/associate`      | Attach to instance       |
| POST   | `/firewalls/{id}/disassociate`   | Detach from instance     |

**Inbound rule fields:**
| Field    | Options                          |
|----------|----------------------------------|
| Type     | SSH, HTTP, HTTPS, Custom         |
| Protocol | TCP, UDP, ICMP                   |
| Port     | Range (e.g., `22-22` for SSH)    |
| Source   | IP addresses or CIDR blocks      |

---

## 7. Templates

**What it is:** Reusable container configurations (Docker images, port mappings, env vars).

**Endpoints:**

| Method | Path              | Description      |
|--------|-------------------|------------------|
| POST   | `/templates`      | Create template  |
| GET    | `/templates`      | List templates   |
| GET    | `/templates/{id}` | Get template     |
| PUT    | `/templates/{id}` | Update template  |
| DELETE | `/templates/{id}` | Delete template  |

Official templates include pre-configured SSH + JupyterLab support.

---

## 8. OS Images

**What it is:** Operating system images for bare metal and container deployments.

**Endpoints:**

| Method | Path            | Description    |
|--------|-----------------|----------------|
| GET    | `/images`       | List images    |
| GET    | `/images/{id}`  | Get image by ID|

Default: Ubuntu 22.04 x86 64-bit. Pre-configured images available for Llama 3, DeepSeek, etc.

---

## 9. SSH Key Management

**What it is:** Manage SSH keys for accessing bare metal and container instances.

**Endpoints:**

| Method | Path                | Description     |
|--------|---------------------|-----------------|
| POST   | `/me/ssh-keys`      | Create/import   |
| GET    | `/me/ssh-keys`      | List keys       |
| PUT    | `/me/ssh-keys/{id}` | Update key      |
| DELETE | `/me/ssh-keys/{id}` | Delete key      |

**Two modes:**
- **Import:** paste your existing `~/.ssh/id_rsa.pub`
- **Auto-create:** platform generates key pair (download private key immediately -- shown only once)

**Connect:** `ssh root@<public-ip> -i /path/to/private-key`

---

## 10. Cold Storage (S3-compatible)

**What it is:** S3-compatible object storage powered by VAST Storage for large-scale archival.

**Features:**
- S3-compatible API
- Designed for long-term archival workloads
- Multi-protocol access (S3, NFS, SMB)
- Encryption at-rest and in-transit

**Migration from AWS S3:**
```bash
# Direct S3-to-S3 via rclone
rclone sync aws_s3:source-bucket gmi-cloud:destination-bucket
```

Also supports AWS CLI (`aws s3 sync`) + rclone upload, and AWS DataSync.

---

## 11. IDCs (Data Centers)

**Endpoint:**

| Method | Path    | Description            |
|--------|---------|------------------------|
| GET    | `/idcs` | List available data centers |

**Known locations:**
- US: Silicon Valley, Denver/Colorado (`us-denver-1`)
- Asia: Taiwan, Thailand, Malaysia

---

# Shared Services (Both Keys)

## Organization Management

| Method | Path                                   | Description                  |
|--------|----------------------------------------|------------------------------|
| POST   | `/organizations`                       | Create organization          |
| GET    | `/organizations/{id}`                  | Get org info                 |
| PUT    | `/organizations/{id}`                  | Update org (owner only)      |
| DELETE | `/organizations/{id}`                  | Delete org (owner only)      |
| GET    | `/organizations/{id}/users`            | List members                 |
| POST   | `/organizations/{id}/invitations`      | Invite via email (admin)     |
| POST   | `/organizations/{id}/transfer`         | Transfer ownership           |
| POST   | `/organizations/{id}/api-keys`         | Create API key               |
| GET    | `/organizations/{id}/api-keys`         | List API keys                |
| DELETE | `/organizations/{id}/api-keys/{keyId}` | Delete API key               |

**Roles:** Owner (full control, can transfer), Admin (can invite), Member (basic access)

## User Profile & Auth

| Method | Path                   | Description                     |
|--------|------------------------|---------------------------------|
| POST   | `/me/session`          | Login                           |
| POST   | `/me/session/refresh`  | Refresh tokens                  |
| POST   | `/me/auth-token`       | Create token via credentials    |
| POST   | `/me/auth-token/oauth` | Create token via OAuth          |
| GET    | `/me/profile`          | Get profile                     |
| PUT    | `/me/profile`          | Update profile                  |
| PUT    | `/me/password`         | Change password                 |
| GET    | `/me/api-key/verify`   | Verify API key                  |
| POST   | `/me/2fa/resend`       | Resend 2FA code                 |

## Billing & Orders

Managed via console UI:
- View order history (avatar -> Billing and Usage -> Orders)
- View receipts
- Continue or cancel pending orders
- Pay-as-you-go (per minute) or prepaid plans (1 day to 3 years)

---

# GMI Studio

**What it is:** Visual no-code/low-code workflow builder for AI pipelines.

**Features:**
- Drag-and-drop workflow canvas (editor)
- Chain models together (LLM -> image -> video pipelines)
- Manage and version workflows
- Step-by-step tutorials available

**Docs:** https://docs.gmicloud.ai/gmi-studio/gmi-studio-user-manual/introduction

---

# Full Model Catalog

## LLM Models -- Live (45 models, verified 2026-04-10)

Queried from `GET https://api.gmi-serving.com/v1/models`. All accessible via your inference key.

**Anthropic:**
- `anthropic/claude-opus-4.6`
- `anthropic/claude-opus-4.5`
- `anthropic/claude-opus-4.1`
- `anthropic/claude-sonnet-4.6`
- `anthropic/claude-sonnet-4.5`
- `anthropic/claude-sonnet-4`
- `anthropic/claude-haiku-4.5`

**OpenAI:**
- `openai/gpt-5.4-pro`
- `openai/gpt-5.4`
- `openai/gpt-5.4-mini`
- `openai/gpt-5.4-nano`
- `openai/gpt-5.3-codex`
- `openai/gpt-5.2`
- `openai/gpt-5.2-chat`
- `openai/gpt-5.2-codex`
- `openai/gpt-5.1`
- `openai/gpt-5.1-chat`
- `openai/gpt-5`
- `openai/gpt-4o`
- `openai/gpt-4o-mini`

**DeepSeek:**
- `deepseek-ai/DeepSeek-V3.2`
- `deepseek-ai/DeepSeek-V3-0324`
- `deepseek-ai/DeepSeek-R1-0528`

**Qwen (Alibaba):**
- `Qwen/Qwen3.5-397B-A17B`
- `Qwen/Qwen3.5-122B-A10B`
- `Qwen/Qwen3.5-35B-A3B`
- `Qwen/Qwen3.5-27B`
- `Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8`
- `Qwen/Qwen3-Next-80B-A3B-Thinking`
- `Qwen/Qwen3-Next-80B-A3B-Instruct`
- `Qwen/Qwen3-235B-A22B-Thinking-2507-FP8`
- `Qwen/Qwen3-235B-A22B-Instruct-2507-FP8`

**Google:**
- `google/gemini-3.1-pro-preview`
- `google/gemini-3.1-flash-lite-preview`
- `google/gemma-4-31b-it`
- `google/gemma-4-26b-a4b-it`

**Zhipu AI (GLM):**
- `zai-org/GLM-5.1-FP8`
- `zai-org/GLM-5-FP8`
- `zai-org/GLM-4.7-FP8`

**MoonshotAI (Kimi):**
- `moonshotai/Kimi-K2.5`
- `moonshotai/Kimi-K2-Thinking`
- `moonshotai/Kimi-K2-Instruct-0905`

**MiniMax:**
- `MiniMaxAI/MiniMax-M2.7`
- `MiniMaxAI/MiniMax-M2.5`

**Other:**
- `kwaipilot/kat-coder-pro-v2`

## Video Models

- Kling-Text2Video-V2.1-Master
- Kling-Image2Video-V2.1-Master
- Luma-Ray2
- Veo3
- Veo3-Fast
- Sora-2-Pro (OpenAI)
- Wan-AI Wan2.1-T2V-14B
- PixVerse, Vidu, Hunyuan models

## Image Models

- seedream-5.0-lite
- gemini-2.5-flash-image
- Black Forest Labs / Flux

## Audio / TTS / Music Models

- elevenlabs-tts-v3
- minimax-tts-speech-2.6-turbo
- minimax-audio-voice-clone-speech-2.6-hd
- minimax-music-2.5

---

# Pricing Summary

## Inference (Serverless)

- **LLM:** $0.00 - $3.00 per million tokens (see catalog above)
- **Video/Image/Audio:** Per-request pricing (varies by model)

## Inference (Dedicated)

| GPU  | Per Hour |
|------|----------|
| H100 | $2.98    |
| H200 | $3.98    |

## Infrastructure (Bare Metal)

| GPU   | Per Hour |
|-------|----------|
| H100  | $2.00    |
| H200  | $2.60    |
| B200  | $4.00    |
| GB200 | $8.00    |

## Infrastructure (Containers)

- Pay-as-you-go: per-minute billing
- Prepaid: 1 day to 3 years

## Other

- Elastic IPs: pay-as-you-go, per minute (charged even when unassociated)
- Managed K8s Clusters: pay-as-you-go or prepaid
- Cold Storage: contact sales

---

## OpenAPI Specs

| Spec           | URL                                                    |
|----------------|--------------------------------------------------------|
| Console API    | https://docs.gmicloud.ai/api-reference/openapi.json   |
| Service API    | https://docs.gmicloud.ai/api-spec/service_api.yaml    |
| IDS Public API | https://docs.gmicloud.ai/api-spec/ids-public-api.yaml |
| IAS Public API | https://docs.gmicloud.ai/api-spec/ias-public-api.yaml |
| IAM API        | https://docs.gmicloud.ai/api-reference-2/iam-api.yaml |

## Quick Links

| Resource              | URL                                                                          |
|-----------------------|------------------------------------------------------------------------------|
| Docs Home             | https://docs.gmicloud.ai/                                                   |
| API Keys              | https://console.gmicloud.ai/user-setting/api-keys                           |
| Model Library         | https://www.gmicloud.ai/models/maas                                         |
| Docs Index            | https://docs.gmicloud.ai/llms.txt                                           |
| LiteLLM Integration   | https://docs.litellm.ai/docs/providers/gmi                                  |
| LLM API Ref           | https://docs.gmicloud.ai/inference-engine/api-reference/llm-api-reference   |
| Video API Ref         | https://docs.gmicloud.ai/inference-engine/api-reference/video-api-reference |
| Video SDK Ref         | https://docs.gmicloud.ai/inference-engine/api-reference/video-sdk-reference |
| Rate Limits           | https://docs.gmicloud.ai/inference-engine/api-reference/rate-limit          |
| Pricing               | https://docs.gmicloud.ai/inference-engine/billing/price                     |
| GMI Studio            | https://docs.gmicloud.ai/gmi-studio/gmi-studio-user-manual/introduction    |
| Migration Guide       | https://docs.gmicloud.ai/migration/s3-to-vast-migration                    |
| Support               | support@gmicloud.ai                                                         |
