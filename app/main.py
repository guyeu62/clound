import os
import time
import math
import uvicorn
from fastapi import FastAPI, Request, Response, status, HTTPException
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="Self-Healing Demo App")

# Cấu hình từ biến môi trường
APP_VERSION = os.getenv("APP_VERSION", "v1")
BROKEN = os.getenv("BROKEN", "false").lower() in ("true", "1", "yes")

# Trạng thái cờ phục vụ kịch bản thử nghiệm
IS_HEALTHY = True
START_TIME = time.time()

# Prometheus Metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP Requests",
    ["method", "endpoint", "status"]
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP Request Latency in seconds",
    ["method", "endpoint"]
)

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start = time.time()
    endpoint = request.url.path
    method = request.method
    try:
        response = await call_next(request)
        duration = time.time() - start
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=str(response.status_code)).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        return response
    except Exception as exc:
        duration = time.time() - start
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status="500").inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        raise exc

@app.get("/")
def read_root():
    """Trang chủ kiểm tra kết nối cơ bản"""
    return {
        "message": "Kubernetes Self-Healing & Autoscaling Demo",
        "version": APP_VERSION,
        "uptime_seconds": round(time.time() - START_TIME, 2)
    }

@app.get("/version")
def get_version():
    """Endpoint trả về phiên bản ứng dụng (v1, v2, v2-bad)"""
    return {"version": APP_VERSION}

@app.get("/health")
def health_probe():
    """
    Liveness probe:
    Nếu IS_HEALTHY = False (do gọi /fail-health), trả về 500 để kubelet restart container.
    """
    global IS_HEALTHY
    if not IS_HEALTHY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "unhealthy", "reason": "Manually triggered failure via /fail-health"}
        )
    return {"status": "healthy"}

@app.get("/ready")
def readiness_probe():
    """
    Readiness probe:
    Nếu BROKEN = true (bản lỗi v2-bad) hoặc IS_HEALTHY = False, trả về 500.
    Kubernetes sẽ ngắt traffic khỏi pod này mà không restart.
    """
    if BROKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "not_ready", "reason": "Simulated broken release (BROKEN=true)"}
        )
    if not IS_HEALTHY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"status": "not_ready", "reason": "Application is in unhealthy state"}
        )
    return {"status": "ready"}

@app.get("/fail-health")
def trigger_fail_health():
    """Chủ động làm hỏng liveness probe để kiểm thử self-healing"""
    global IS_HEALTHY
    IS_HEALTHY = False
    return {"message": "Health failure triggered! Next /health calls will return 500."}

@app.get("/load")
def compute_load(duration_ms: int = 200):
    """
    Endpoint tạo tải CPU giả lập để kích hoạt HPA scale pod.
    Thực hiện tính toán số học nặng trong khoảng thời gian duration_ms (mặc định 200ms).
    """
    end_time = time.time() + (duration_ms / 1000.0)
    x = 0.0001
    while time.time() < end_time:
        x += math.sqrt(x) + math.sin(x)
    return {"status": "load_simulated", "duration_ms": duration_ms}

@app.get("/metrics")
def get_metrics():
    """Endpoint cho Prometheus scrape"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    # Truyền trực tiếp app instance để chạy được ở mọi thư mục mà không bị lỗi Could not import module
    uvicorn.run(app, host="0.0.0.0", port=port)


