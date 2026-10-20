# Verification Checklist (VERIFY.md)

- [x] **req-1-openapi-spec**: The repository contains a valid OpenAPI 3.0 specification in `openapi.yaml` defining `POST /v1/predict` (requiring string `text`, returning string `label` and float `score`), 400/422 responses, and `GET /health`. Validated using `openapi_spec_validator`.
- [x] **req-2-docker-compose-setup**: `docker-compose.yml` orchestrates the frontend proxy (`nginx`) and the backend application (`api`). The `api` service defines a healthcheck with `curl -f http://localhost:8000/health` and `nginx` waits with `condition: service_healthy`.
- [x] **req-3-network-isolation**: The `api` backend uses `expose: - "8000"` and does NOT publish ports to host (`ports` mapping is omitted). Direct host connections to `localhost:8000` are refused.
- [x] **req-4-health-endpoint**: `GET http://localhost:8080/health` routed through Nginx returns HTTP 200 with `{"status": "ok"}`.
- [x] **req-5-inference-endpoint**: `POST http://localhost:8080/v1/predict` accepts JSON `{"text": "..."}` and returns HTTP 200 with schema `{"label": "...", "score": 0.xx}`.
- [x] **req-6-input-validation**: Missing `text` field, malformed JSON, and wrong `Content-Type` are rejected with HTTP 400 or 422.
- [x] **req-7-security-headers**: Nginx attaches `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` to responses.
- [x] **req-8-rate-limiting**: `nginx.conf` declares a rate limiting zone `limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;` and applies it with `limit_req zone=api_limit burst=20 nodelay;`.
- [x] **req-9-proxy-forwarding**: `nginx.conf` forwards client metadata using `proxy_set_header X-Real-IP $remote_addr;` and `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`.
- [x] **req-10-nginx-config-validation**: `docker-compose exec nginx nginx -t` parses `nginx.conf` with 0 errors and reports `test is successful`.
