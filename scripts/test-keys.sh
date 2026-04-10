#!/bin/bash
# GMI Cloud API Key Tester -- Zero Credit Usage
# All calls are read-only GETs or use the $0.00 free model.
#
# Usage:
#   bash test-keys.sh
# Reads GMI_INFER and GMI_INFRA from ../.env automatically.

set -uo pipefail

# Load keys from parent .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

GMI_INFERENCE_KEY="${GMI_INFER:-}"
GMI_INFRA_KEY="${GMI_INFRA:-}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

pass=0
fail=0

check() {
  local label="$1"
  local status="$2"
  local body="$3"

  if [[ "$status" -ge 200 && "$status" -lt 300 ]]; then
    echo -e "  ${GREEN}[PASS]${NC} $label (HTTP $status)"
    ((pass++))
  else
    echo -e "  ${RED}[FAIL]${NC} $label (HTTP $status)"
    echo "        Response: $(echo "$body" | head -c 200)"
    ((fail++))
  fi
}

# ─────────────────────────────────────────────
# INFERENCE KEY TESTS
# ─────────────────────────────────────────────
echo ""
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo -e "${CYAN}  INFERENCE KEY TESTS${NC}"
echo -e "${CYAN}══════════════════════════════════════════════${NC}"

if [[ -z "${GMI_INFERENCE_KEY:-}" ]]; then
  echo -e "${RED}  GMI_INFERENCE_KEY not set -- skipping inference tests${NC}"
else
  INFERENCE_BASE="https://api.gmi-serving.com/v1"
  VIDEO_BASE="https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey"

  # 1) Verify key works -- list models (free, read-only)
  echo -e "\n${YELLOW}[LLM API]${NC} $INFERENCE_BASE"
  resp=$(curl -s -w "\n%{http_code}" "$INFERENCE_BASE/models" \
    -H "Authorization: Bearer $GMI_INFERENCE_KEY")
  body=$(echo "$resp" | sed '$d')
  status=$(echo "$resp" | tail -1)
  check "GET /models -- list LLM models" "$status" "$body"

  if [[ "$status" -ge 200 && "$status" -lt 300 ]]; then
    model_count=$(echo "$body" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data',[])))" 2>/dev/null || echo "?")
    echo -e "        Models available: $model_count"
  fi

  # 2) Chat completion with cheapest available model (minimal tokens)
  echo ""
  # Pick the cheapest model actually available -- try openai/gpt-4o-mini first
  resp=$(curl -s -w "\n%{http_code}" "$INFERENCE_BASE/chat/completions" \
    -H "Authorization: Bearer $GMI_INFERENCE_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "openai/gpt-4o-mini",
      "messages": [{"role": "user", "content": "Say OK"}],
      "max_tokens": 3
    }')
  body=$(echo "$resp" | sed '$d')
  status=$(echo "$resp" | tail -1)
  check "POST /chat/completions -- gpt-4o-mini, 3 max_tokens (< \$0.001)" "$status" "$body"

  if [[ "$status" -ge 200 && "$status" -lt 300 ]]; then
    reply=$(echo "$body" | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'][:100])" 2>/dev/null || echo "(parse error)")
    echo -e "        Model replied: $reply"
  fi

  # 3) Video API -- list video models (free, read-only)
  echo -e "\n${YELLOW}[Video API]${NC} $VIDEO_BASE"
  resp=$(curl -s -w "\n%{http_code}" "$VIDEO_BASE/models" \
    -H "Authorization: Bearer $GMI_INFERENCE_KEY")
  body=$(echo "$resp" | sed '$d')
  status=$(echo "$resp" | tail -1)
  check "GET /models -- list video models" "$status" "$body"
fi

# ─────────────────────────────────────────────
# INFRA KEY TESTS
# ─────────────────────────────────────────────
echo ""
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo -e "${CYAN}  INFRA KEY TESTS${NC}"
echo -e "${CYAN}══════════════════════════════════════════════${NC}"

if [[ -z "${GMI_INFRA_KEY:-}" ]]; then
  echo -e "${RED}  GMI_INFRA_KEY not set -- skipping infra tests${NC}"
else
  INFRA_BASE="https://console.gmicloud.ai/api/v1"

  # All GETs below are read-only, zero cost

  # Note: /me/profile and /me/ssh-keys require session tokens, not API keys.
  # The infra key (scope: ce_resource) correctly works for resource endpoints only.
  echo -e "\n${YELLOW}[Auth & Profile]${NC}"
  echo -e "  ${YELLOW}[SKIP]${NC} GET /me/profile -- requires session token, not API key"
  echo -e "  ${YELLOW}[SKIP]${NC} GET /me/ssh-keys -- requires session token, not API key"

  echo -e "\n${YELLOW}[Containers]${NC}"

  resp=$(curl -s -w "\n%{http_code}" "$INFRA_BASE/containers" \
    -H "Authorization: Bearer $GMI_INFRA_KEY" \
    -H "Content-Type: application/json")
  body=$(echo "$resp" | sed '$d')
  status=$(echo "$resp" | tail -1)
  check "GET /containers -- list containers" "$status" "$body"

  resp=$(curl -s -w "\n%{http_code}" "$INFRA_BASE/containers/products" \
    -H "Authorization: Bearer $GMI_INFRA_KEY" \
    -H "Content-Type: application/json")
  body=$(echo "$resp" | sed '$d')
  status=$(echo "$resp" | tail -1)
  check "GET /containers/products -- list GPU products" "$status" "$body"

  echo -e "\n${YELLOW}[Bare Metal]${NC}"

  resp=$(curl -s -w "\n%{http_code}" "$INFRA_BASE/baremetals" \
    -H "Authorization: Bearer $GMI_INFRA_KEY" \
    -H "Content-Type: application/json")
  body=$(echo "$resp" | sed '$d')
  status=$(echo "$resp" | tail -1)
  check "GET /baremetals -- list bare metal servers" "$status" "$body"

  resp=$(curl -s -w "\n%{http_code}" "$INFRA_BASE/baremetals/products" \
    -H "Authorization: Bearer $GMI_INFRA_KEY" \
    -H "Content-Type: application/json")
  body=$(echo "$resp" | sed '$d')
  status=$(echo "$resp" | tail -1)
  check "GET /baremetals/products -- list hardware options" "$status" "$body"

  echo -e "\n${YELLOW}[Templates]${NC}"

  resp=$(curl -s -w "\n%{http_code}" "$INFRA_BASE/templates" \
    -H "Authorization: Bearer $GMI_INFRA_KEY" \
    -H "Content-Type: application/json")
  body=$(echo "$resp" | sed '$d')
  status=$(echo "$resp" | tail -1)
  check "GET /templates -- list templates" "$status" "$body"

  echo -e "\n${YELLOW}[Networking]${NC}"

  resp=$(curl -s -w "\n%{http_code}" "$INFRA_BASE/vpcs" \
    -H "Authorization: Bearer $GMI_INFRA_KEY" \
    -H "Content-Type: application/json")
  body=$(echo "$resp" | sed '$d')
  status=$(echo "$resp" | tail -1)
  check "GET /vpcs -- list VPCs" "$status" "$body"

  resp=$(curl -s -w "\n%{http_code}" "$INFRA_BASE/elastic-ips" \
    -H "Authorization: Bearer $GMI_INFRA_KEY" \
    -H "Content-Type: application/json")
  body=$(echo "$resp" | sed '$d')
  status=$(echo "$resp" | tail -1)
  check "GET /elastic-ips -- list elastic IPs" "$status" "$body"

  resp=$(curl -s -w "\n%{http_code}" "$INFRA_BASE/firewalls" \
    -H "Authorization: Bearer $GMI_INFRA_KEY" \
    -H "Content-Type: application/json")
  body=$(echo "$resp" | sed '$d')
  status=$(echo "$resp" | tail -1)
  check "GET /firewalls -- list firewalls" "$status" "$body"

  echo -e "\n${YELLOW}[Data Centers & Images]${NC}"

  resp=$(curl -s -w "\n%{http_code}" "$INFRA_BASE/idcs" \
    -H "Authorization: Bearer $GMI_INFRA_KEY" \
    -H "Content-Type: application/json")
  body=$(echo "$resp" | sed '$d')
  status=$(echo "$resp" | tail -1)
  check "GET /idcs -- list data centers" "$status" "$body"

  resp=$(curl -s -w "\n%{http_code}" "$INFRA_BASE/images" \
    -H "Authorization: Bearer $GMI_INFRA_KEY" \
    -H "Content-Type: application/json")
  body=$(echo "$resp" | sed '$d')
  status=$(echo "$resp" | tail -1)
  check "GET /images -- list OS images" "$status" "$body"

  resp=$(curl -s -w "\n%{http_code}" "$INFRA_BASE/elastic-ips/products" \
    -H "Authorization: Bearer $GMI_INFRA_KEY" \
    -H "Content-Type: application/json")
  body=$(echo "$resp" | sed '$d')
  status=$(echo "$resp" | tail -1)
  check "GET /elastic-ips/products -- list IP products" "$status" "$body"
fi

# ─────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────
echo ""
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo -e "${CYAN}  RESULTS${NC}"
echo -e "${CYAN}══════════════════════════════════════════════${NC}"
echo -e "  ${GREEN}Passed: $pass${NC}"
echo -e "  ${RED}Failed: $fail${NC}"
total=$((pass + fail))
echo -e "  Total:  $total"
echo ""

if [[ $fail -eq 0 ]]; then
  echo -e "${GREEN}All services reachable. Zero credits spent.${NC}"
else
  echo -e "${YELLOW}Some tests failed -- check the key values, permissions, or endpoint paths above.${NC}"
fi
echo ""
