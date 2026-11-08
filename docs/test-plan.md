# Kế hoạch & Tiêu chí Kiểm thử (Test Plan)

Đề tài 26: Triển khai ứng dụng trên Kubernetes với tự phục hồi, co giãn và cập nhật không gián đoạn.

---

## 1. Môi trường kiểm thử

- **Cụm Kubernetes:** Local kind cluster (`k8s/kind-config.yaml` gồm 1 control-plane và 2 worker nodes).
- **Ingress Controller:** Nginx Ingress Controller v1.12.1.
- **Autoscaler:** Metrics Server v0.7.2 + HorizontalPodAutoscaler.
- **Monitoring Stack:** Kube-Prometheus-Stack (Prometheus + Grafana).
- **Công cụ tạo tải:** k6 v0.49+ (kịch bản `steady.js` và `hpa-spike.js`).

---

## 2. Bảng 7 Kịch bản Kiểm thử Chính

> **Quy trình chuẩn:** Mỗi kịch bản chạy **cùng lúc với tải nền k6** (`steady.js` 20 VUs), lặp lại **3 lần** và lấy kết quả trung bình.

| # | Kịch bản | Lệnh thực hiện | Chỉ số quan sát | Tiêu chí đạt (Target Threshold) | Kết quả thực tế (Đạt / Không đạt) |
|---|:---|:---|:---|:---|:---|
| **1** | **Baseline (Chuẩn)** | `k6 run load-test/steady.js` (không can thiệp) | Availability (%), Độ trễ p95 (ms) | Availability ≥ 99.9%, p95 < 200ms | Chờ chạy nghiệm thu |
| **2** | **Xóa Pod ngẫu nhiên** | `bash scripts/chaos-pod-delete.sh pod` | Thời gian về đủ 2 replicas, Tỷ lệ lỗi 5xx | Availability ≥ 99%, phục hồi đủ replica < 30s | Chờ chạy nghiệm thu |
| **3** | **Lỗi Health Endpoint** | `curl -H "Host: selfhealing.local" http://localhost/fail-health` | Số lần container restart, Thời gian kubelet nhận diện | Container tự động restart, restart count tăng +1, pod Ready trở lại | Chờ chạy nghiệm thu |
| **4** | **Drain Worker Node** | `bash scripts/chaos-pod-delete.sh drain` | PodDisruptionBudget (PDB), Tính sẵn sàng | Luôn còn ≥ 1 pod Ready tại node còn lại, Availability ≥ 99% | Chờ chạy nghiệm thu |
| **5** | **Rollout bản tốt (v2)** | `kubectl set image deployment/selfhealing-demo app=selfhealing-demo:v2` | Thời gian cập nhật, Số lỗi request gián đoạn | Lỗi 5xx ≈ 0 (không gián đoạn dịch vụ nhờ `maxUnavailable: 0`) | Chờ chạy nghiệm thu |
| **6** | **Rollout lỗi (v2-bad) & Rollback** | `bash scripts/rollout-fail.sh` | Trạng thái pod mới, Phản hồi của client, Thời gian rollback | Pod mới không bao giờ nhận traffic; Client vẫn nhận bản v1; Rollback hoàn tất < 60s | Chờ chạy nghiệm thu |
| **7** | **Autoscaling (HPA)** | `k6 run load-test/hpa-spike.js` | CPU load %, Số replicas scale up / scale down | Scale up từ 2 lên ≥ 4 pods trong < 3 phút; Scale down sau cửa sổ 60s | Chờ chạy nghiệm thu |

---

## 3. Thử nghiệm Bổ sung

### A. Thử nghiệm Cấu hình Sai (`k8s/experiments/`)

| File kiểm thử | Hành vi cố ý sai | Triệu chứng quan sát | Lệnh chẩn đoán (`kubectl`) |
|:---|:---|:---|:---|
| `bad-liveness.yaml` | Liveness timeout 1s, period 1s, initialDelay 0 | Pod bị restart liên tục (CrashLoopBackOff) | `kubectl describe pod -l app=selfhealing-demo` -> Event: Unhealthy Liveness probe failed |
| `low-memory-limit.yaml` | Cấp giới hạn bộ nhớ chỉ 10Mi | Pod bị Linux OOM killer kill ngay lúc start | `kubectl get pod` -> Status: `OOMKilled` (Exit code 137) |
| `missing-readiness.yaml` | Không khai báo `readinessProbe` | Pod mới sinh ra nhận traffic ngay khi app chưa khởi động xong | `k6 run load-test/steady.js` -> Phát hiện hàng loạt lỗi 502 Bad Gateway / Connection Refused |

### B. Kiểm thử Tính Bền Vững của Dữ liệu (PersistentVolumeClaim)

- **Manifest:** `k8s/base/pvc.yaml` và `k8s/base/storage-demo.yaml`.
- **Cách thực hiện:**
  1. Kiểm tra log của pod `storage-demo` xem timestamp đã ghi: `kubectl logs deployment/storage-demo`.
  2. Xóa pod: `kubectl delete pod -l app=storage-demo`.
  3. Khi pod mới được ReplicaSet tạo lại, kiểm tra log: `kubectl logs deployment/storage-demo`.
- **Tiêu chí đạt:** Pod mới đọc lại được dữ liệu "Existing data found" từ PVC trước đó mà không bị mất dữ liệu.

