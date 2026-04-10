# GMI Cloud -- Inference Model Catalog

> Verified live from API on 2026-04-10
> Total: **45 LLM models** + **238 media models** (163 named + 75 UUID-only)
> Key: `GMI_INFER` (scope: `ie_model`)

---

## Summary

| Category              | Count | Notable Models                                    |
|-----------------------|-------|---------------------------------------------------|
| LLM (Chat)            | 45    | GPT-5.4, Claude Opus 4.6, DeepSeek V3.2, Qwen3.5 |
| Text-to-Video         | 41    | Sora 2 Pro, Veo 3.1, Kling V3, Wan 2.7            |
| Image-to-Video        | 24    | Kling V3, LTX-2 Pro, PixVerse 5.6                 |
| Image Generation      | 15    | GPT Image 1.5, Flux2, Seedream 5, Gemini 3 Pro    |
| Image Editing         | 11    | Flux Kontext Pro, Bria suite, Seededit 3           |
| Text-to-Speech        | 12    | ElevenLabs V3, MiniMax 2.6, Inworld 1.5           |
| Voice Cloning         | 2     | MiniMax voice clone HD/turbo                       |
| Music Generation      | 1     | MiniMax Music 2.5                                  |
| Video (other)         | 18    | Transitions, motion control, editing, upscaling    |
| Creative Workflows    | 22    | Templates, GMI workflows, batch inference          |
| 3D / Audio / Other    | 7     | 3D mesh, audio edit, uncategorized                 |

---

## LLM Models (45)

All use `POST https://api.gmi-serving.com/v1/chat/completions` (OpenAI-compatible).

### Anthropic (7)

| Model ID | Status |
|---|---|
| `anthropic/claude-opus-4.6` | Timeout (heavy, may need longer) |
| `anthropic/claude-opus-4.5` | OK |
| `anthropic/claude-opus-4.1` | Timeout (heavy, may need longer) |
| `anthropic/claude-sonnet-4.6` | OK |
| `anthropic/claude-sonnet-4.5` | OK |
| `anthropic/claude-sonnet-4` | OK |
| `anthropic/claude-haiku-4.5` | OK |

### OpenAI (12)

Note: GPT-5+ models require `max_completion_tokens` instead of `max_tokens`.

| Model ID | Status |
|---|---|
| `openai/gpt-5.4-pro` | Backend error |
| `openai/gpt-5.4` | OK |
| `openai/gpt-5.4-mini` | OK |
| `openai/gpt-5.4-nano` | OK |
| `openai/gpt-5.3-codex` | Backend error (codex-specific API?) |
| `openai/gpt-5.2` | OK |
| `openai/gpt-5.2-chat` | OK |
| `openai/gpt-5.2-codex` | Backend error (codex-specific API?) |
| `openai/gpt-5.1` | OK |
| `openai/gpt-5.1-chat` | OK |
| `openai/gpt-5` | OK |
| `openai/gpt-4o` | OK |
| `openai/gpt-4o-mini` | OK |

### DeepSeek (3)

| Model ID | Status |
|---|---|
| `deepseek-ai/DeepSeek-V3.2` | OK |
| `deepseek-ai/DeepSeek-V3-0324` | OK |
| `deepseek-ai/DeepSeek-R1-0528` | OK |

### Qwen / Alibaba (11)

| Model ID | Status |
|---|---|
| `Qwen/Qwen3.5-397B-A17B` | OK |
| `Qwen/Qwen3.5-122B-A10B` | OK |
| `Qwen/Qwen3.5-35B-A3B` | OK |
| `Qwen/Qwen3.5-27B` | OK |
| `Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8` | OK |
| `Qwen/Qwen3-Next-80B-A3B-Thinking` | OK |
| `Qwen/Qwen3-Next-80B-A3B-Instruct` | OK |
| `Qwen/Qwen3-235B-A22B-Thinking-2507-FP8` | OK |
| `Qwen/Qwen3-235B-A22B-Instruct-2507-FP8` | OK |

### Google (4)

| Model ID | Status |
|---|---|
| `google/gemini-3.1-pro-preview` | OK |
| `google/gemini-3.1-flash-lite-preview` | OK |
| `google/gemma-4-31b-it` | OK |
| `google/gemma-4-26b-a4b-it` | Retry error |

### Zhipu AI / GLM (3)

| Model ID | Status |
|---|---|
| `zai-org/GLM-5.1-FP8` | OK |
| `zai-org/GLM-5-FP8` | OK |
| `zai-org/GLM-4.7-FP8` | 404 |

### MoonshotAI / Kimi (3)

| Model ID | Status |
|---|---|
| `moonshotai/Kimi-K2.5` | OK |
| `moonshotai/Kimi-K2-Instruct-0905` | OK |
| `moonshotai/Kimi-K2-Thinking` | 404 |

### MiniMax (2)

| Model ID | Status |
|---|---|
| `MiniMaxAI/MiniMax-M2.7` | OK |
| `MiniMaxAI/MiniMax-M2.5` | OK |

### Other (1)

| Model ID | Status |
|---|---|
| `kwaipilot/kat-coder-pro-v2` | OK |

### LLM Status Summary

- **Working: 38** models
- **Not working: 7** (2 timeout, 2 404, 3 backend error)

---

## Media Models (238 total)

All use `https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey` (async job API).

75 models have UUID-only IDs (internal/unlisted) -- omitted below.

---

### Text-to-Video (41)

| Provider | Models |
|---|---|
| **Google Veo** | `Veo3`, `Veo3-Fast`, `veo-3.1-generate-001`, `veo-3.1-fast-generate-001`, `veo-3.1-lite-generate-001`, `veo-3.1-generate-preview`, `veo-3.1-fast-generate-preview` |
| **OpenAI Sora** | `sora-2`, `sora-2-pro` |
| **Kling** | `Kling-Text2Video-V2.1-Master`, `Kling-Text2Video-V2-Master`, `Kling-Text2Video-V1.6-Standard`, `kling-v3-text-to-video`, `kling-v2-6`, `kling-v2-5-turbo` |
| **Wan AI** | `wan2.7-t2v`, `wan2.6-t2v`, `wan2.5-t2v-preview`, `Wan-AI_Wan2.1-T2V-14B`, `Wan-AI_Wan2.2-T2V-A14B` |
| **Seedance** | `seedance-2-0-260128`, `seedance-2-0-fast-260128`, `seedance-1-5-pro-251215`, `seedance-1-0-pro-250528`, `seedance-1-0-pro-fast-251015` |
| **MiniMax Hailuo** | `Minimax-Hailuo-2.3`, `Minimax-Hailuo-2.3-Fast`, `Minimax-Hailuo-02` |
| **LTX** | `ltx-2-pro-text-to-video`, `ltx-2-fast-text-to-video`, `LTX-2`, `LTX2-Distilled`, `LTX2-ICLoRA` |
| **PixVerse** | `pixverse-v5.6-t2v`, `pixverse-v5.5-t2v`, `pixverse-v5-t2v` |
| **Vidu** | `vidu-q3-pro-t2v`, `vidu-q2-t2v` |
| **SkyReels** | `skyreels-v4-text-to-video` |
| **Luma** | `Luma-Ray2` |
| **Hunyuan** | `Hunyuan1.5` |

### Image-to-Video (24)

| Provider | Models |
|---|---|
| **Kling** | `Kling-Image2Video-V2.1-Master`, `V2.1-Pro`, `V2.1-Standard`, `V2-Master`, `V1.6-Pro`, `V1.6-Standard`, `kling-v3-image-to-video`, `kling-o1-image-to-video` |
| **Wan AI** | `wan2.7-i2v`, `wan2.6-i2v`, `wan2.5-i2v-preview`, `Wan-AI_Wan2.1-I2V-14B-720P`, `480P`, `Wan-AI_Wan2.2-I2V-A14B`, `SFWan2.2-I2V-A14B` |
| **LTX** | `ltx-2-pro-image-to-video`, `ltx-2-fast-image-to-video`, `LTX2-Ti2VidTwoStages` |
| **PixVerse** | `pixverse-v5.6-i2v`, `pixverse-v5.5-i2v`, `pixverse-v5-i2v` |
| **SkyReels** | `skyreels-v4-image-to-video` |
| **Vidu** | `vidu-q3-pro-i2v`, `vidu-q2-pro-i2v` |

### Reference-to-Video (4)

- `kling-o1-reference-to-video`
- `vidu-q2-pro-r2v`
- `wan2.6-r2v`
- `wan2.7-r2v`

### First/Last-Frame Video (3)

- `Wan-AI_Wan2.1-FLF2V-14B-720P`
- `kling-o1-flfv`
- `vidu-q2-pro-flfv`

### Video Transition (3)

- `pixverse-v5.6-transition`
- `pixverse-v5.5-transition`
- `pixverse-v5-transition`

### Video -- Omni/Multi-modal (2)

- `kling-v3-omni`
- `skyreels-v4-omni`

### Motion Control Video (2)

- `kling-3-motion-control`
- `kling-2.6-motion-control`

### Video Editing (3)

- `wan2.7-videoedit`
- `kling-o1-edit-video`
- `bria-video-eraser`

### Video Retake (1)

- `ltx-2-pro-retake`

### Video Interpolation (1)

- `LTX-2-KeyframeInterpolation`

### Video Upscaling (1)

- `bria-video-increase-resolution`

### Video Background Removal (1)

- `bria-video-remove-background`

### Audio-to-Video (1)

- `ltx-2-pro-audio-to-video`

### Animation (1)

- `Wan2.2-Animate-14B`

---

### Image Generation (15)

| Provider | Models |
|---|---|
| **OpenAI** | `gpt-image-1.5` |
| **Google** | `gemini-3-pro-image-preview`, `gemini-3.1-flash-image-preview`, `gemini-2.5-flash-image` |
| **Flux** | `Flux2-Dev`, `Flux2-Klein` |
| **Seedream** | `seedream-5.0-lite`, `seedream-4-0-250828`, `seedream-3-0-t2i-250415` |
| **Reve** | `reve-create-20250915` |
| **Krea** | `Krea-Realtime-14B` |
| **Zhipu** | `GLM-Image` |
| **Qwen** | `Qwen-Image-2512` |
| **Z-Image** | `Z-Image`, `Z-Image-Turbo` |

### Image Editing (11)

- `flux-kontext-pro` (Flux contextual editing)
- `seededit-3-0-i2i-250628` (image-to-image)
- `hunyuan-image-to-image`
- `bria-fibo-edit`
- `bria-fibo-recolor`
- `bria-fibo-relight`
- `bria-fibo-reseason`
- `bria-fibo-restore`
- `bria-fibo-restyle`
- `bria-eraser`
- `bria-genfill`

### Image Blending (1)

- `bria-fibo-image-blend`

### Image Remix (2)

- `reve-remix-20250915`
- `reve-remix-fast-20251030`

### Sketch-to-Image (1)

- `bria-fibo-sketch-to-image`

### Image -- ControlNet (1)

- `Z-Image-Turbo-Fun-Controlnet-Union-2.1`

---

### Text-to-Speech / TTS (12)

| Provider | Models |
|---|---|
| **ElevenLabs** | `elevenlabs-tts-v3`, `elevenlabs-tts-multilingual-v2` |
| **MiniMax** | `minimax-tts-speech-2.6-hd`, `minimax-tts-speech-2.6-turbo`, `minimax-tts-speech-2.5-hd-preview`, `minimax-tts-speech-2.5-turbo-preview`, `minimax-tts-speech-02-hd`, `minimax-tts-speech-02-turbo`, `minimax-tts-speech-01-hd`, `minimax-tts-speech-01-turbo` |
| **Inworld** | `inworld-tts-1.5-max`, `inworld-tts-1.5-mini` |

### Voice Cloning (2)

- `minimax-audio-voice-clone-speech-2.6-hd`
- `minimax-audio-voice-clone-speech-2.6-turbo`

### Music Generation (1)

- `minimax-music-2.5`

### Audio Processing (1)

- `Step-Audio-EditX`

---

### 3D Generation (1)

- `cat_mesh_v1_20260202`

### GMI Workflows (2)

- `GMI-MiniMeTalks-Workflow`
- `GMI-Halloween-HauntedYou-Workflow`

### Batch Inference (1)

- `Gemini-batch-inference`

### Creative Workflow / Templates (20)

Specialty templates for specific use cases:

- `new_try_on_anything_01` (virtual try-on)
- `new_fashion_design_01`, `fashion_design_01`
- `new_product_photo_01`
- `new_animation_01`
- `new_camera_01`
- `new_gaming_01`
- `new_creator_dome_01`, `creator_dome_02`
- `new_host_wheel_car_01`, `host_wheel_car_01`
- `new_knitted_01`, `knitted_01`
- `new_long_distance_01`
- `new_cat_01`, `new_cat_02`, `cat_0202`, `cat_street_interview_0204`
- `Chirstmas Postcard`, `christmas_card_01`

### Other / Uncategorized (4)

- `bria-fibo` (base Bria model)
- `kling-create-element`
- `reve-edit-20250915`
- `reve-edit-fast-20251030`

---

## UUID-Only Models (75)

These 75 models have UUID-only identifiers and are likely internal, experimental, or unlisted. They are accessible via the API but may not be stable.

Not listed here -- query them via:
```bash
curl -s https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey/models \
  -H "Authorization: Bearer $GMI_INFER" | python3 -c "
import sys,json,re
ids = json.load(sys.stdin)['model_ids']
for m in sorted(ids):
    if re.match(r'^[0-9a-f]{8}-', m.strip()):
        print(m.strip())
"
```
