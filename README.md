# OpenAPI-Compliant Model Inference Service with Nginx and Python

A contract-first machine learning inference service built with FastAPI, secured behind an Nginx reverse proxy, and containerized using Docker Compose. The architecture enforces network isolation to ensure backend application servers are never exposed directly to external traffic.

---

## Architecture Overview

```
                           +---------------------------+
                           |  Client / External Caller |
                           +-------------+-------------+
                                         |
                                         | HTTP (Port 8080)
                                         v
+---------------------------------------------------------------------------------+
| Docker Internal Network (Isolated)                                              |
|                                                                                 |
|   +-------------------------------------------------------------------------+   |
|   |                           Nginx Reverse Proxy                           |   |
|   | - Listens on internal port 80 (Published to host 8080:80)               |   |
|   | - Applies Rate Limiting: 10r/s (zone=api_limit, burst=20, nodelay)     |   |
|   | - Injects Security Headers: X-Content-Type-Options: nosniff             |   |
|   | - Forwards Client Metadata: Host, X-Real-IP, X-Forwarded-For            |   |
|   | - Routes traffic to http://api:8000                                     |   |
|   +------------------------------------+------------------------------------+   |
|                                        |                                        |
|                                        | proxy_pass http://api:8000             |
|                                        v                                        |
|   +-------------------------------------------------------------------------+   |
|   |                           Python Inference API                          |   |
|   | - FastAPI / Uvicorn listening on port 8000                              |   |
|   | - NOT published to host (unreachable via localhost:8000 directly)       |   |
|   | - Endpoints: POST /v1/predict, GET /health                              |   |
|   | - Healthcheck: curl -f http://localhost:8000/health                     |   |
|   +-------------------------------------------------------------------------+   |
+---------------------------------------------------------------------------------+
```

---

## Project Structure

```
.
├── docker-compose.yml   # Multi-container orchestration & network isolation
├── Dockerfile           # Builds the Python FastAPI backend container
├── nginx.conf           # Reverse proxy, rate limiting, and security headers
├── openapi.yaml         # OpenAPI 3.0 specification contract
├── requirements.txt     # Python backend dependencies
├── app.py               # FastAPI application implementation
└── README.md            # Setup instructions and verification guide
```

---

## One-Command Setup

Start the entire stack in detached mode:

```bash
docker-compose up -d --build
```
*(or `docker compose up -d --build`)*

To view real-time logs:
```bash
docker-compose logs -f
```

To stop and remove containers:
```bash
docker-compose down
```

---

## Verification & Testing Guide

### 1. Verify Health Endpoint (via Proxy)
```bash
curl -i http://localhost:8080/health
```
**Expected Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json
X-Content-Type-Options: nosniff
X-Frame-Options: DENY

{"status":"ok"}
```

### 2. Verify Model Inference Contract (POST /v1/predict)
```bash
curl -X POST http://localhost:8080/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "This product is fantastic and exceeded all my expectations!"}'
```
**Expected Response:**
```json
{
  "label": "positive",
  "score": 0.95
}
```

```bash
curl -X POST http://localhost:8080/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "The delivery was terrible and customer service was poor."}'
```
**Expected Response:**
```json
{
  "label": "negative",
  "score": 0.88
}
```

### 3. Verify Security Hardening Headers
Inspect headers on requests to `/v1/predict`:
```bash
curl -I http://localhost:8080/v1/predict
```
**Expected Headers:**
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
```

### 4. Verify Network Isolation (Backend NOT Exposed to Host)
Attempt to reach the backend application directly on port 8000:
```bash
curl -v http://localhost:8000/health
```
**Expected Behavior:** Connection refused or timeout (the port is NOT published to the host).

### 5. Verify Input Validation & Rejection

#### Missing Required `text` Field:
```bash
curl -X POST http://localhost:8080/v1/predict \
  -H "Content-Type: application/json" \
  -d '{}'
```
**Expected Response:** `422 Unprocessable Entity`

#### Invalid / Non-JSON Payload:
```bash
curl -X POST http://localhost:8080/v1/predict \
  -H "Content-Type: text/plain" \
  -d "plain text data"
```
**Expected Response:** `422 Unprocessable Entity` or `400 Bad Request`

#### Empty String `text`:
```bash
curl -X POST http://localhost:8080/v1/predict \
  -H "Content-Type: application/json" \
  -d '{"text": ""}'
```
**Expected Response:** `422 Unprocessable Entity`

### 6. Verify Nginx Configuration Syntax
```bash
docker-compose exec nginx nginx -t
```
**Expected Output:**
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 7. Validate OpenAPI 3.0 Specification
Validate the contract against OpenAPI 3.0 standards:
```bash
python -c "import yaml; from openapi_spec_validator import validate; validate(yaml.safe_load(open('openapi.yaml'))); print('Valid OpenAPI 3.0 specification!')"
```
