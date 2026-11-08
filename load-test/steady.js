import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Đo lường tỷ lệ lỗi
export const errorRate = new Rate('errors');

export const options = {
  // Giữ tải nền ổn định 20 VUs trong 10 phút để thực hiện các bài test chaos / rollout
  vus: 20,
  duration: '10m',
  thresholds: {
    // Tỷ lệ lỗi cho phép < 1% (availability >= 99%)
    errors: ['rate<0.01'],
    // 95% request phải hoàn thành dưới 500ms
    http_req_duration: ['p(95)<500'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost/version';

export default function () {
  const params = {
    headers: {
      'Host': 'selfhealing.local',
    },
    timeout: '3s',
  };

  const res = http.get(BASE_URL, params);
  const success = check(res, {
    'status is 200': (r) => r.status === 200,
  });

  errorRate.add(!success);
  sleep(0.1); // Khoảng nghỉ ngắn giữa các request
}

