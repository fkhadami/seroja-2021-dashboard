#!/usr/bin/env bash
# Menjalankan langkah pipeline berurutan. Langkah yang gagal tidak menghentikan langkah lain.
set -u
mkdir -p data/derived data/raw data/raw_small
for s in $(cat scripts/STEPS); do
  echo "===== $s ====="
  start=$(date +%s)
  python "scripts/$s" || echo "!!!!! $s GAGAL"
  echo "===== $s selesai dalam $(( $(date +%s) - start )) s ====="
done
