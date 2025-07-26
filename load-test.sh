#!/usr/bin/env bash
# Load test script for 50 concepts/day validation with monitoring

set -euo pipefail

# Configuration
QSTASH_URL="${QSTASH_URL:-https://qstash.upstash.io/v2/publish}"
QSTASH_TOKEN="${QSTASH_TOKEN:-}"
MAX_CONCEPTS="${MAX_CONCEPTS:-50}"
DELAY_SECONDS="${DELAY_SECONDS:-30}"

if [[ -z "$QSTASH_TOKEN" ]]; then
    echo "ERROR: QSTASH_TOKEN environment variable is required"
    echo "Set it with: export QSTASH_TOKEN=your_token_here"
    exit 1
fi

echo "🚀 Starting load test: $MAX_CONCEPTS concepts with ${DELAY_SECONDS}s delay"
echo "📊 Monitor QStash free-tier usage at: https://console.upstash.com"
echo "📈 Monitor system metrics at: http://localhost:3000 (admin/admin)"
echo "🔍 Watch quota gauges in Grafana dashboard"
echo ""

# Test concepts array
concepts=(
    "bitcoin" "ethereum" "solana" "cardano" "polkadot"
    "chainlink" "uniswap" "aave" "compound" "makerdao"
    "polygon" "avalanche" "fantom" "harmony" "cosmos"
    "terra" "algorand" "tezos" "stellar" "ripple"
    "litecoin" "monero" "zcash" "dash" "dogecoin"
    "shiba" "pepe" "floki" "safemoon" "babydoge"
    "defi" "nft" "metaverse" "gamefi" "web3"
    "dao" "yield-farming" "liquidity-mining" "staking" "lending"
    "dex" "cex" "bridge" "layer2" "rollup"
    "consensus" "proof-of-stake" "proof-of-work" "mining" "validator"
)

success_count=0
error_count=0

# Start monitoring if not already running
if ! curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "🔧 Starting monitoring stack..."
    docker compose -f infra/docker-compose.yml -f docker-compose.override.yml up -d prometheus grafana loki quota-exporter
    echo "⏳ Waiting for Grafana to start..."
    sleep 10
fi

for i in $(seq 1 $MAX_CONCEPTS); do
    concept_index=$((($i - 1) % ${#concepts[@]}))
    concept="${concepts[$concept_index]}"
    
    echo "[$i/$MAX_CONCEPTS] Testing concept: $concept"
    
    # Create test payload
    payload=$(cat <<EOF
{
    "id": "load-test-$i",
    "url": "https://example.com/research/$concept",
    "concept": "$concept",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "test_run": true
}
EOF
)
    
    # Send to QStash with delay
    if curl -s -X POST "$QSTASH_URL" \
        -H "Authorization: Bearer $QSTASH_TOKEN" \
        -H "Upstash-Delay: $DELAY_SECONDS" \
        -H "Content-Type: application/json" \
        -d "$payload" > /dev/null; then
        
        echo "  ✅ Sent successfully (delayed ${DELAY_SECONDS}s)"
        ((success_count++))
    else
        echo "  ❌ Failed to send"
        ((error_count++))
    fi
    
    # Brief pause between requests to avoid rate limiting
    sleep 1
    
    # Progress update every 10 concepts
    if (( i % 10 == 0 )); then
        echo ""
        echo "📊 Progress: $i/$MAX_CONCEPTS concepts sent"
        echo "   ✅ Success: $success_count"
        echo "   ❌ Errors: $error_count"
        echo "   📈 Success rate: $(( success_count * 100 / i ))%"
        echo "   📈 Check Grafana: http://localhost:3000"
        echo ""
    fi
done

echo ""
echo "🎯 Load test completed!"
echo "📊 Final Results:"
echo "   Total concepts: $MAX_CONCEPTS"
echo "   ✅ Successful: $success_count"
echo "   ❌ Failed: $error_count"
echo "   📈 Success rate: $(( success_count * 100 / MAX_CONCEPTS ))%"
echo ""
echo "📋 Monitoring Dashboard:"
echo "   🎛️  Grafana: http://localhost:3000 (admin/admin)"
echo "   📊 Prometheus: http://localhost:9090"
echo "   📝 Loki: http://localhost:3100"
echo ""
echo "📈 Free Tier Usage:"
echo "   - QStash: $success_count/500 messages used today"
echo "   - R2: Check storage gauge in Grafana"
echo "   - Monitor quota alerts in dashboard"
echo ""
echo "🛑 To stop monitoring:"
echo "   docker compose -f infra/docker-compose.yml -f docker-compose.override.yml stop prometheus grafana loki quota-exporter"