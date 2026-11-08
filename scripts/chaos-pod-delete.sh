#!/usr/bin/env bash
# Kịch bản kiểm thử Chaos: Xóa Pod ngẫu nhiên hoặc Drain Worker Node

set -euo pipefail

MODE="${1:-pod}"
NAMESPACE="default"
DEPLOYMENT_NAME="selfhealing-demo"

if [ "$MODE" = "pod" ]; then
    echo "=================================================="
    echo " [CHAOS] Chọn ngẫu nhiên 1 pod để xóa..."
    echo "=================================================="
    
    POD_NAME=$(kubectl get pods -n "$NAMESPACE" -l app="$DEPLOYMENT_NAME" -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$POD_NAME" ]; then
        echo "[ERROR] Không tìm thấy pod nào của deployment $DEPLOYMENT_NAME!"
        exit 1
    fi
    
    echo "[ACTION] Đang xóa pod: $POD_NAME"
    START_TIME=$(date +%s)
    kubectl delete pod "$POD_NAME" -n "$NAMESPACE" --now
    
    echo "[WAIT] Đang đợi ReplicaSet phục hồi đủ pod Ready..."
    kubectl wait --namespace "$NAMESPACE" --for=condition=ready pod -l app="$DEPLOYMENT_NAME" --timeout=60s
    END_TIME=$(date +%s)
    
    DURATION=$((END_TIME - START_TIME))
    echo "[SUCCESS] Cụm đã tự phục hồi về trạng thái Ready sau $DURATION giây!"

elif [ "$MODE" = "drain" ]; then
    echo "=================================================="
    echo " [CHAOS] Kiểm thử Drain Node worker..."
    echo "=================================================="
    
    WORKER_NODE=$(kubectl get nodes --selector='!node-role.kubernetes.io/control-plane' -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$WORKER_NODE" ]; then
        echo "[ERROR] Không tìm thấy worker node nào!"
        exit 1
    fi
    
    echo "[ACTION] Đang drain node: $WORKER_NODE (PDB sẽ bảo vệ ít nhất 1 pod sống)..."
    kubectl drain "$WORKER_NODE" --ignore-daemonsets --delete-emptydir-data --force
    
    echo "[VERIFY] Kiểm tra trạng thái các Pod..."
    kubectl get pods -o wide -l app="$DEPLOYMENT_NAME"
    
    echo "[RECOVER] Uncordon lại worker node để phục hồi cụm..."
    kubectl uncordon "$WORKER_NODE"
    echo "[SUCCESS] Đã uncordon node $WORKER_NODE thành công!"
else
    echo "Cách dùng: $0 [pod|drain]"
    exit 1
fi

