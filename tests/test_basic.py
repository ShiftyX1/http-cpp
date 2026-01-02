import httpx
from config import REQUEST_TIMEOUT


def test_server_responds(base_url, server):
    print(f"\n[TEST] Sending request to {base_url}")
    response = httpx.post(
        base_url,
        content="Hello, World!",
        timeout=REQUEST_TIMEOUT
    )
    print(f"[TEST] Response: {response.status_code} - {response.text}")
    assert response.status_code == 200
    assert response.text == "Echo: Hello, World!"


def test_empty_body(base_url, server):
    print(f"\n[TEST] Sending empty body to {base_url}")
    response = httpx.post(
        base_url,
        content="",
        timeout=REQUEST_TIMEOUT
    )
    print(f"[TEST] Response: {response.status_code} - {response.text}")
    assert response.status_code == 200
    assert response.text == "Echo: "


def test_large_body(base_url, server):
    payload = "A" * 10000
    print(f"\n[TEST] Sending large body ({len(payload)} bytes) to {base_url}")
    response = httpx.post(
        base_url,
        content=payload,
        timeout=REQUEST_TIMEOUT
    )
    print(f"[TEST] Response: {response.status_code} - {len(response.text)} bytes")
    assert response.status_code == 200
    assert response.text == f"Echo: {payload}"
