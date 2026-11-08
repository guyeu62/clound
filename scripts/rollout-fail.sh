#!/usr/bin/env bash
# Kịch bản kiểm thử: Phát hành phiên bản lỗi (v2-bad) và Tự động Rollback

set -euo pipefail

NAMESPACE="default"
DEPLOYMENT_NAME="selfhealing-demo"
BAD_IMAGE="selfhealing-demo:v2-bad"

echo "=================================================="
echo " 1. Cập nhật Deployment sang phiên bản lỗi: $BAD_IMAGE"
echo "=================================================="
kubectl set image deployment/"$DEPLOYMENT_NAME" app="$BAD_IMAGE" -n "$NAMESPACE"

echo ""
echo "[INFO] Đang theo dõi tiến trình rollout (chờ 30s để chứng minh Pod mới không bao giờ Ready)..."
if ! kubectl rollout status deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE" --timeout=30s; then
    echo ""
    echo "[PHÁT HIỆN] Rollout bị nghẽn do readinessProbe thất bại trên bản v2-bad!"
    echo "[XÁC NHẬN] Các pod phiên bản cũ vẫn đang phục vụ traffic mà không bị gián đoạn."
fi

echo ""
echo "=================================================="
echo " 2. Kiểm tra lưu lượng qua Ingress (phải 100% thành công và trả về v1)"
echo "=================================================="
RESPONSE=$(curl -s -H "Host: selfhealing.local" http://localhost/version || echo "FAILED")
echo "Response nhận được: $RESPONSE"

echo ""
echo "=================================================="
echo " 3. Tiến hành Rollback về phiên bản ổn định trước đó..."
echo "=================================================="
START_ROLLBACK=$(date +%s)
kubectl rollout undo deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE"
kubectl rollout status deployment/"$DEPLOYMENT_NAME" -n "$NAMESPACE" --timeout=60s
END_ROLLBACK=$(date +%s)

ROLLBACK_DURATION=$((END_ROLLBACK - START_ROLLBACK))
echo "[SUCCESS] Rollback hoàn tất thành công trong $ROLLBACK_DURATION giây!"

