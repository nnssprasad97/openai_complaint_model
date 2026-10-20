"""
Automated Verification Suite implementing each requirement phase walkthrough.
Matches the evaluable contracts and worked example input/output shape.
"""
import os
import sys
import json
import yaml
import subprocess
import requests
from openapi_spec_validator import validate

def verify_req_1_openapi_spec(workspace: str) -> None:
    spec_file = os.path.join(workspace, "openapi.yaml")
    if not os.path.exists(spec_file):
        raise FileNotFoundError(f"req-1-openapi-spec: missing openapi.yaml at {spec_file}")
    
    with open(spec_file, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    
    validate(spec)
    if not spec.get("openapi", "").startswith("3.0"):
        raise ValueError(f"req-1-openapi-spec: OpenAPI version must be 3.0.x, found {spec.get('openapi')}")
    
    paths = spec.get("paths", {})
    if "/v1/predict" not in paths:
        raise KeyError("req-1-openapi-spec: missing '/v1/predict' path")
    
    predict_post = paths["/v1/predict"].get("post")
    if not predict_post:
        raise KeyError("req-1-openapi-spec: missing POST operation for /v1/predict")
    
    req_body = predict_post.get("requestBody", {})
    content = req_body.get("content", {}).get("application/json", {})
    schema = content.get("schema", {})
    properties = schema.get("properties", {})
    
    if "text" not in properties:
        raise KeyError("req-1-openapi-spec: 'text' property required in request schema")
    if properties["text"].get("type") != "string":
        raise TypeError("req-1-openapi-spec: 'text' property must be a string")
    if "text" not in schema.get("required", []):
        raise ValueError("req-1-openapi-spec: 'text' property must be marked required")
        
    responses = predict_post.get("responses", {})
    if "200" not in responses:
        raise KeyError("req-1-openapi-spec: missing 200 response definition in /v1/predict")
    
    resp_200 = responses["200"].get("content", {}).get("application/json", {}).get("schema", {})
    resp_props = resp_200.get("properties", {})
    if "label" not in resp_props or resp_props["label"].get("type") != "string":
        raise TypeError("req-1-openapi-spec: 200 response must include 'label' string")
    if "score" not in resp_props or resp_props["score"].get("type") not in ["number", "float"]:
        raise TypeError("req-1-openapi-spec: 200 response must include 'score' float/number")

def verify_req_2_docker_compose_setup(workspace: str) -> None:
    dc_file = os.path.join(workspace, "docker-compose.yml")
    if not os.path.exists(dc_file):
        raise FileNotFoundError(f"req-2-docker-compose-setup: missing docker-compose.yml at {dc_file}")
    
    with open(dc_file, "r", encoding="utf-8") as f:
        dc = yaml.safe_load(f)
    
    services = dc.get("services", {})
    if "api" not in services or "nginx" not in services:
        raise KeyError("req-2-docker-compose-setup: must define both 'api' and 'nginx' services")
    
    if "healthcheck" not in services["api"]:
        raise KeyError("req-2-docker-compose-setup: 'api' service must declare a healthcheck")
    
    nginx_deps = services["nginx"].get("depends_on", {})
    if "api" not in nginx_deps or nginx_deps["api"].get("condition") != "service_healthy":
        raise ValueError("req-2-docker-compose-setup: nginx must depend on api with condition: service_healthy")

def verify_req_3_network_isolation(workspace: str) -> None:
    dc_file = os.path.join(workspace, "docker-compose.yml")
    with open(dc_file, "r", encoding="utf-8") as f:
        dc = yaml.safe_load(f)
    
    api_service = dc.get("services", {}).get("api", {})
    if "ports" in api_service:
        raise ValueError("req-3-network-isolation: 'api' service must NOT publish ports to host")
    if "expose" not in api_service or "8000" not in [str(p) for p in api_service["expose"]]:
        raise ValueError("req-3-network-isolation: 'api' service must use internal 'expose: 8000'")
    
    # Assert connection refused on direct localhost:8000
    try:
        requests.get("http://localhost:8000/health", timeout=2)
        raise ConnectionError("req-3-network-isolation: direct host access to localhost:8000 succeeded, expected connection refused")
    except requests.exceptions.RequestException:
        pass

def verify_req_4_health_endpoint(workspace: str) -> None:
    r = requests.get("http://localhost:8080/health", timeout=5)
    if r.status_code != 200:
        raise AssertionError(f"req-4-health-endpoint: expected status 200, got {r.status_code}")
    data = r.json()
    if data.get("status") != "ok":
        raise AssertionError(f"req-4-health-endpoint: expected status 'ok', got {data}")

def verify_req_5_inference_endpoint(workspace: str) -> None:
    payload = {"text": "This product works exceptionally well!"}
    r = requests.post("http://localhost:8080/v1/predict", json=payload, timeout=5)
    if r.status_code != 200:
        raise AssertionError(f"req-5-inference-endpoint: expected status 200, got {r.status_code}")
    data = r.json()
    if not isinstance(data.get("label"), str) or not isinstance(data.get("score"), (float, int)):
        raise TypeError(f"req-5-inference-endpoint: response did not match schema: {data}")

def verify_req_6_input_validation(workspace: str) -> None:
    # Empty payload missing text
    r1 = requests.post("http://localhost:8080/v1/predict", json={}, timeout=5)
    if r1.status_code not in [400, 422]:
        raise AssertionError(f"req-6-input-validation: expected 400 or 422 for empty payload, got {r1.status_code}")
    
    # Non-JSON content type
    r2 = requests.post("http://localhost:8080/v1/predict", data="plain text data", headers={"Content-Type": "text/plain"}, timeout=5)
    if r2.status_code not in [400, 415, 422]:
        raise AssertionError(f"req-6-input-validation: expected 400, 415, or 422 for plain text, got {r2.status_code}")

def verify_req_7_security_headers(workspace: str) -> None:
    r = requests.head("http://localhost:8080/v1/predict", timeout=5)
    header = r.headers.get("X-Content-Type-Options", "").lower()
    if header != "nosniff":
        raise AssertionError(f"req-7-security-headers: expected X-Content-Type-Options: nosniff, got '{header}'")

def verify_req_8_rate_limiting(workspace: str) -> None:
    nginx_conf = os.path.join(workspace, "nginx.conf")
    with open(nginx_conf, "r", encoding="utf-8") as f:
        conf = f.read()
    if "limit_req_zone" not in conf:
        raise KeyError("req-8-rate-limiting: missing 'limit_req_zone' in nginx.conf")
    if "limit_req " not in conf:
        raise KeyError("req-8-rate-limiting: missing 'limit_req' in nginx.conf")

def verify_req_9_proxy_forwarding(workspace: str) -> None:
    nginx_conf = os.path.join(workspace, "nginx.conf")
    with open(nginx_conf, "r", encoding="utf-8") as f:
        conf = f.read()
    if "proxy_set_header X-Real-IP" not in conf:
        raise KeyError("req-9-proxy-forwarding: missing X-Real-IP header forward")
    if "proxy_set_header X-Forwarded-For" not in conf:
        raise KeyError("req-9-proxy-forwarding: missing X-Forwarded-For header forward")

def verify_req_10_nginx_config_validation(workspace: str) -> None:
    res = subprocess.run(["docker", "compose", "exec", "nginx", "nginx", "-t"], capture_output=True, text=True)
    out = (res.stdout + res.stderr).lower()
    if res.returncode != 0 or ("syntax is ok" not in out and "test is successful" not in out):
        raise AssertionError(f"req-10-nginx-config-validation: nginx -t failed: {out}")

def run_all_checks(workspace: str = "."):
    check_functions = [
        ("req-1-openapi-spec", verify_req_1_openapi_spec),
        ("req-2-docker-compose-setup", verify_req_2_docker_compose_setup),
        ("req-3-network-isolation", verify_req_3_network_isolation),
        ("req-4-health-endpoint", verify_req_4_health_endpoint),
        ("req-5-inference-endpoint", verify_req_5_inference_endpoint),
        ("req-6-input-validation", verify_req_6_input_validation),
        ("req-7-security-headers", verify_req_7_security_headers),
        ("req-8-rate-limiting", verify_req_8_rate_limiting),
        ("req-9-proxy-forwarding", verify_req_9_proxy_forwarding),
        ("req-10-nginx-config-validation", verify_req_10_nginx_config_validation),
    ]
    checked = []
    warnings = []
    
    for req_id, fn in check_functions:
        try:
            fn(workspace)
            checked.append(req_id)
        except Exception as e:
            warnings.append(f"{req_id} failed: {str(e)}")
            
    status = "pass" if len(warnings) == 0 else "fail"
    output = {
        "status": status,
        "checked": checked,
        "metrics": {"primary": "see report.md"},
        "warnings": warnings
    }
    return output

if __name__ == "__main__":
    result = run_all_checks(os.getcwd())
    print(json.dumps(result, indent=2))
    if result["status"] != "pass":
        sys.exit(1)
    sys.exit(0)
