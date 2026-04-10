# GMI Cloud -- Creative Workflows & Templates

> These are **GMI Studio workflows** -- multi-step AI pipelines that chain models together (e.g., Seedream -> Kling -> compositing).
> They accept images/text, run a full production pipeline, and output finished images + videos.
> API: `POST https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey/requests`

---

## Summary

| Category | Count | Price Range |
|---|---|---|
| Fashion & E-commerce | 4 | $0.60 - $1.50/sec |
| Automotive | 3 | $1.50/sec |
| Character & Avatar | 4 | $0.20 - $1.50/sec |
| Art & Craft | 2 | $1.50/sec |
| Pet / Fun | 3 | $1.50/sec |
| Holiday / Seasonal | 3 | $0.20 - $0.32/sec |
| Gaming | 1 | $1.50/sec |
| Utility | 1 | Free |

---

## Fashion & E-commerce

### `new_try_on_anything_01` -- Try On Anything
**$1.50/sec** | image -> image

Upload a person photo + clothing items (top, bottom, shoes, bag) and get multiple generated looks: e-commerce white-background shot, street-style, magazine covers, medium shots, drone shot, and close-up portrait.

| Parameter | Required |
|---|---|
| Person image | Yes |
| Top image | Yes |
| Bottom image | Yes |
| Shoes image | Yes |
| Bag image | Yes |

### `new_fashion_design_01` -- Fashion Design
**$1.50/sec** | image -> image + video

From text prompt + reference image, generates a full visual set: vertical & horizontal runway photos, runway video, studio model shot, and mannequin presentations in two styles.

| Parameter | Required |
|---|---|
| Prompt text | Yes |
| Image upload | Yes |

### `new_product_photo_01` -- Product Photo
**$1.50/sec** | image -> image

Generate premium product photos from a single reference image. Includes clean white e-commerce shots and creative editorial setups. Preserves original design, proportions, and details.

| Parameter | Required |
|---|---|
| Product image | Yes |
| Prompt text | Yes |

### `new_creator_dome_01` / `creator_dome_02` -- Creator Dome
**$1.50/set** | image -> image

Upload 3 references (character shot, multi-angle reference, cap/product reference) to generate a consistent, commercial-ready image series in the Creator Dome silhouette style.

| Parameter | Required |
|---|---|
| Main character shot | Yes |
| Character multi-angle reference | Yes |
| Cap product reference (multi-angle) | Yes |

---

## Automotive

### `new_host_wheel_car_01` -- Car Showcase
**$1.50/sec** | image -> image + video

Generate cinematic, photorealistic car images and videos from reference images. Preserves all original design details.

| Parameter | Required |
|---|---|
| Main Car Reference (Primary) | Yes |
| Secondary Car Angle Reference | Yes |
| Car's Toy Model Reference Image | Yes |
| Parking Garage image | Yes |
| Night city street environment | Yes |
| Human model reference | Yes |
| Racing uniform reference | Yes |

### `new_cat_01` -- Car (alternate)
**$1.50/sec** | image -> image + video

Same car showcase workflow (note: "cat" in ID is misleading -- this is a car workflow).

---

## Character & Avatar

### `GMI-MiniMeTalks-Workflow` -- MiniMe Talks
**$0.20/sec** | image -> video

Turns portraits into 3D mini-version talking & dancing videos. Combines Seedream 4.0 + WAN 2.5 in a two-stage pipeline. Music-synchronized motion and lip sync.

| Parameter | Required |
|---|---|
| Reference Images | Yes |
| Scene Description | Yes |
| Background Music | Yes |
| Video Length | Yes |

### `GMI-Halloween-HauntedYou-Workflow` -- HauntedYou
**$0.32/sec** | image -> video

Transforms uploaded portraits into personalized Halloween-themed cinematic short videos.

| Parameter | Required |
|---|---|
| Your Photo | Yes |

### `new_animation_01` -- Create Your Own Animation
**$0.60/sec** | text + image -> video

Bring your own character to life and turn ideas into animated stories. Uses Seedream for character creation + animation pipeline.

| Parameter | Required |
|---|---|
| Reference Image | Yes |
| Animation Style | Yes |
| Animation Prompt | Yes |

### `new_long_distance_01` -- Long-Distance Friends
**$1.50/sec** | image -> image + video

From two portrait/selfie photos, generates: Polaroid-style variations, 4-grid layouts, nighttime group image, and animated videos.

| Parameter | Required |
|---|---|
| Portrait/selfie Photo 1 | Yes |
| Portrait/selfie Photo 2 | Yes |

---

## Art & Craft

### `new_knitted_01` -- Knitted Artwork
**$1.50/sec** | image -> image

Creates a hand-knitted artwork from four input images, stitched into a single unified textile piece.

| Parameter | Required |
|---|---|
| Image upload 1-4 | Yes (all 4) |

---

## Pet / Fun

### `new_cat_02` / `cat_0202` -- My Cat To Merch
**$1.50/sec** | image -> video

Turns a cat photo into custom illustrated merch mockups: T-shirt on model (photo + video), mug, CD cover, embroidered keychain, phone case, canvas tote, and more.

| Parameter | Required |
|---|---|
| Cat Photo | Yes |

### `cat_street_interview_0204` -- Cat Street Interview
**$1.50/sec** | image -> video

Upload a cat picture and generate a cute animated street interview video.

| Parameter | Required |
|---|---|
| Cat photo | Yes |

---

## Gaming

### `new_gaming_01` -- Game Visual Production
**$1.50/sec** | image -> image + video

From a character reference image, generates: character turnarounds, weapon sheets, key art, in-game stills, and cinematic clips.

| Parameter | Required |
|---|---|
| Character image | Yes |

---

## Holiday / Seasonal

### `Chirstmas Postcard` -- Christmas Postcard
**$0.20/sec** | text -> video

AI workflow for fast, high-quality holiday visual creation. Generates festive, personalized Christmas postcards in watercolor and chic visual styles.

| Parameter | Required |
|---|---|
| Prompt | Yes |

### `christmas_card_01` -- Christmas Card (v1)
**$1.50/sec** | text -> image

Earlier version of Christmas card generator.

---

## Utility

### `kling-create-element` -- Kling Create Element
**Free ($0.00/request)** | image/video -> text

Create custom character and object elements (characters, animals, items, costumes, scenes, effects) from reference images or videos. These elements can then be used in Kling video generation.

| Parameter | Required |
|---|---|
| Element Name | Yes |
| Element Description | Yes |
| Reference Type | Yes |
| Frontal Image | Yes |
| Reference Images | No |
| Reference Video | No |

---

## Deprecated / Placeholder

These exist in the API but have placeholder descriptions (`XXXX`):
- `fashion_design_01` -- older version of fashion design
- `host_wheel_car_01` -- older version of car showcase
- `knitted_01` -- older version of knitted artwork
- `new_camera_01` -- placeholder
- `christmas_card_01` -- placeholder

---

## How to Use (API)

```bash
# Submit a workflow job
curl -X POST https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey/requests \
  -H "Authorization: Bearer $GMI_INFER" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "new_try_on_anything_01",
    "payload": {
      "person_image.24": "<base64_or_url>",
      "top_image.25": "<base64_or_url>",
      "bottom_image.22": "<base64_or_url>",
      "shoes_image.23": "<base64_or_url>",
      "bag_image.38": "<base64_or_url>"
    }
  }'

# Check status
curl https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey/requests/{REQUEST_ID} \
  -H "Authorization: Bearer $GMI_INFER"
```

Parameter names use internal IDs (e.g., `person_image.24`). Query the model details endpoint to get exact parameter names:
```bash
curl https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey/models/{model_id} \
  -H "Authorization: Bearer $GMI_INFER"
```
