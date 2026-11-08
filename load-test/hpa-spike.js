import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

export const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '30s', target: 10 },  // Khởi động nhẹ
    { duration: '1m',  target: 80 },  // Tăng vọt tải CPU (kích hoạt HPA scale up)
    { duration: '2m',  target: 80 },  // Giữ tải cao để quan sát số lượng pod tăng
    { duration: '30s', target: 5 },   // Hạ tải
    { duration: '2m',  target: 5 },   // Giữ tải thấp để quan sát HPA scale down
  ],
  thresholds: {
    errors: ['rate<0.05'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost/load';

export default function () {
  const params = {
    headers: {
      'Host': 'selfhealing.local',
    },
    timeout: '5s',
  };

  const res = http.get(`${BASE_URL}?duration_ms=150`, params);
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
  });

  errorRate.add(!success);
  sleep(0.05);
}

