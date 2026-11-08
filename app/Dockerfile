FROM python:3.11-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Tạo non-root user (appuser UID=10001) để tuân thủ securityContext
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/sh -m appuser

# Cài đặt dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn ứng dụng
COPY main.py .

# Build arguments cho các kịch bản thử nghiệm
ARG APP_VERSION=v1
ARG BROKEN=false

ENV APP_VERSION=${APP_VERSION}
ENV BROKEN=${BROKEN}
ENV PORT=8000

# Chuyển sang non-root user
USER 10001

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

