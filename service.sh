#!/bin/bash
# Hourly headless-Chrome check of the published site (load_seconds, site_errors with a 60 s scripted walk).
# The full run takes ~70 s, longer than measure.sh may take, so measure.sh reads the latest result from
# data/derived/browser_kpi.json (used only if under 3 hours old).
cd "$(dirname "$0")"
while true; do
  SRC=site
  [ -s SITE_URL ] && SRC=$(head -n1 SITE_URL | tr -d '[:space:]')
  OUT=$(node scripts/browser_test.mjs "$SRC" 2>/tmp/wc_browser_test.err | tail -n1)
  if echo "$OUT" | grep -q load_seconds; then
    echo "{\"ts\": $(date +%s), \"src\": \"$SRC\", \"result\": $OUT}" > data/derived/browser_kpi.json
    echo "$(date -u +%FT%TZ) $OUT"
  else
    echo "$(date -u +%FT%TZ) browser test failed: $(tail -n3 /tmp/wc_browser_test.err)"
  fi
  sleep 3600
done
