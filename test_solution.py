"""
Comprehensive Test and Verification Suite for:
Deploy an OpenAPI-Compliant Model Inference Service with Nginx and Python
Checks all 10 Core Requirements defined by the evaluation rubric.
"""
import os
import sys
import yaml
import subprocess
import requests
from openapi_spec_validator import validate

def test_req_1_openapi_spec():
    print("Testing Requirement 1: OpenAPI 3.0 specification...")
    spec_path = "openapi.yaml"
    assert os.path.exists(spec_path), "openapi.yaml not found in root directory!"
    with open(spec_path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    
    # Validate against OpenAPI spec
    validate(spec)
    assert spec.get("openapi", "").startswith("3.0"), f"OpenAPI version must be 3.0.x, found {spec.get('openapi')}"
    
    paths = spec.get("paths", {})
    assert "/v1/predict" in paths, "Missing '/v1/predict' path in openapi.yaml"
    predict_op = paths["/v1/predict"].get("post")
    assert predict_op is not None, "Missing 'post' operation for /v1/predict"
    
    req_body = predict_op.get("requestBody", {})
    content = req_body.get("content", {}).get("application/json", {})
    schema = content.get("schema", {})
    assert "text" in schema.get("properties", {}), "Request schema must define 'text' property"
    assert schema["properties"]["text"].get("type") == "string", "'text' must be a string"
    assert "text" in schema.get("required", []), "'text' must be a required property"
    
    responses = predict_op.get("responses", {})
    assert "200" in responses, "Missing 200 response definition in /v1/predict"
    resp_200 = responses["200"].get("content", {}).get("application/json", {}).get("schema", {})
    props = resp_200.get("properties", {})
    assert "label" in props, "Response schema must define 'label' property"
    assert props["label"].get("type") == "string", "'label' must be of type string"
    assert "score" in props, "Response schema must define 'score' property"
    assert props["score"].get("type") in ["number", "float"], "'score' must be number or float"
    assert "label" in resp_200.get("required", []) and "score" in resp_200.get("required", []), "label and score must be required"
    print(" [PASS] Requirement 1 passed!")

def test_req_2_docker_compose_setup():
    print("Testing Requirement 2: Docker Compose orchestration & healthchecks...")
    dc_path = "docker-compose.yml"
    assert os.path.exists(dc_path), "docker-compose.yml not found!"
    with open(dc_path, "r", encoding="utf-8") as f:
        dc = yaml.safe_load(f)
    
    services = dc.get("services", {})
    assert "nginx" in services, "'nginx' service missing from docker-compose.yml"
    assert "api" in services, "'api' service missing from docker-compose.yml"
    
    api_service = services["api"]
    assert "healthcheck" in api_service, "'api' service must define a healthcheck"
    
    nginx_service = services["nginx"]
    depends_on = nginx_service.get("depends_on", {})
    assert "api" in depends_on, "nginx must depend on api"
    assert depends_on["api"].get("condition") == "service_healthy", "nginx must depend on api with condition: service_healthy"
    
    # Check port mappings for nginx
    ports = nginx_service.get("ports", [])
    has_8080 = any("8080:80" in str(p) or "80:80" in str(p) for p in ports)
    assert has_8080, "nginx service must expose port 8080 (or 80)"
    print(" [PASS] Requirement 2 passed!")

def test_req_3_network_isolation():
    print("Testing Requirement 3: Network isolation...")
    with open("docker-compose.yml", "r", encoding="utf-8") as f:
        dc = yaml.safe_load(f)
    
    api_service = dc.get("services", {}).get("api", {})
    assert "ports" not in api_service, "CRITICAL: 'api' service must NOT contain 'ports' mapping!"
    assert "expose" in api_service, "'api' service should use 'expose' to make port available internally"
    assert "8000" in [str(p) for p in api_service["expose"]], "Port 8000 should be in expose list"
    
    # Verify direct host connection to port 8000 fails
    try:
        r = requests.get("http://localhost:8000/health", timeout=2)
        assert False, f"Direct connection to localhost:8000 succeeded with status {r.status_code}, expected connection failure!"
    except requests.exceptions.RequestException:
        # Expected: connection refused or timeout
        pass
    print(" [PASS] Requirement 3 passed!")

def test_req_4_health_endpoint():
    print("Testing Requirement 4: Health endpoint via proxy...")
    r = requests.get("http://localhost:8080/health", timeout=5)
    assert r.status_code == 200, f"Expected status 200, got {r.status_code}"
    data = r.json()
    assert data.get("status") == "ok", f"Expected {{'status': 'ok'}}, got {data}"
    print(" [PASS] Requirement 4 passed!")

def test_req_5_inference_endpoint():
    print("Testing Requirement 5: Model inference endpoint...")
    payload = {"text": "This model service is fantastic and works perfectly!"}
    r = requests.post("http://localhost:8080/v1/predict", json=payload, timeout=5)
    assert r.status_code == 200, f"Expected status 200, got {r.status_code}"
    data = r.json()
    assert "label" in data and isinstance(data["label"], str), f"Missing or invalid 'label' in response: {data}"
    assert "score" in data and isinstance(data["score"], (float, int)), f"Missing or invalid 'score' in response: {data}"
    assert data["label"] == "positive"
    print(" [PASS] Requirement 5 passed!")

def test_req_6_input_validation():
    print("Testing Requirement 6: Input validation & rejection...")
    # Missing 'text' property in JSON
    r_empty = requests.post("http://localhost:8080/v1/predict", json={}, timeout=5)
    assert r_empty.status_code in [400, 422], f"Expected 400 or 422 for empty payload, got {r_empty.status_code}"
    
    # Plain text / wrong content type
    r_plain = requests.post(
        "http://localhost:8080/v1/predict",
        data="raw plain text without json",
        headers={"Content-Type": "text/plain"},
        timeout=5
    )
    assert r_plain.status_code in [400, 415, 422], f"Expected 400, 415, or 422 for wrong content type, got {r_plain.status_code}"
    print(" [PASS] Requirement 6 passed!")

def test_req_7_security_headers():
    print("Testing Requirement 7: HTTP security hardening headers...")
    r = requests.head("http://localhost:8080/v1/predict", timeout=5)
    assert "x-content-type-options" in r.headers, f"Missing X-Content-Type-Options header: {r.headers}"
    assert r.headers["x-content-type-options"].lower() == "nosniff", f"Expected 'nosniff', got {r.headers['x-content-type-options']}"
    print(" [PASS] Requirement 7 passed!")

def test_req_8_rate_limiting():
    print("Testing Requirement 8: Rate limiting directives...")
    with open("nginx.conf", "r", encoding="utf-8") as f:
        conf = f.read()
    assert "limit_req_zone" in conf, "Missing 'limit_req_zone' directive in nginx.conf"
    assert "limit_req " in conf, "Missing 'limit_req' directive in nginx.conf"
    print(" [PASS] Requirement 8 passed!")

def test_req_9_proxy_forwarding():
    print("Testing Requirement 9: Request metadata proxy forwarding...")
    with open("nginx.conf", "r", encoding="utf-8") as f:
        conf = f.read()
    assert "proxy_set_header X-Real-IP" in conf, "Missing proxy_set_header X-Real-IP in nginx.conf"
    assert "proxy_set_header X-Forwarded-For" in conf, "Missing proxy_set_header X-Forwarded-For in nginx.conf"
    print(" [PASS] Requirement 9 passed!")

def test_req_10_nginx_config_validation():
    print("Testing Requirement 10: Nginx configuration syntax check...")
    res = subprocess.run(
        ["docker", "compose", "exec", "nginx", "nginx", "-t"],
        capture_output=True,
        text=True
    )
    output = (res.stdout + res.stderr).lower()
    assert res.returncode == 0, f"nginx -t failed with exit code {res.returncode}: {output}"
    assert "syntax is ok" in output or "test is successful" in output, f"Unexpected nginx -t output: {output}"
    print(" [PASS] Requirement 10 passed!")

if __name__ == "__main__":
    tests = [
        test_req_1_openapi_spec,
        test_req_2_docker_compose_setup,
        test_req_3_network_isolation,
        test_req_4_health_endpoint,
        test_req_5_inference_endpoint,
        test_req_6_input_validation,
        test_req_7_security_headers,
        test_req_8_rate_limiting,
        test_req_9_proxy_forwarding,
        test_req_10_nginx_config_validation,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f" [FAIL] {t.__name__} failed: {e}")
            failed += 1
    
    if failed == 0:
        print("\n ALL 10 REQUIREMENTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print(f"\n {failed} tests failed.")
        sys.exit(1)
