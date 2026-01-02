import httpx
import pytest
from config import REQUEST_TIMEOUT


@pytest.mark.parametrize("request_num", range(10))
def test_multiple_requests(base_url, server, request_num):
    print(f"\n[TEST] Multiple request #{request_num}")
    response = httpx.post(
        base_url,
        content=f"Request {request_num}",
        timeout=REQUEST_TIMEOUT
    )
    print(f"[TEST] Response: {response.status_code} - {response.text}")
    assert response.status_code == 200
    assert response.text == f"Echo: Request {request_num}"


def test_concurrent_requests(base_url, server):
    print(f"\n[TEST] Sending 5 concurrent requests")
    with httpx.Client() as client:
        responses = []
        for i in range(5):
            response = client.post(
                base_url,
                content=f"Concurrent {i}",
                timeout=REQUEST_TIMEOUT
            )
            responses.append(response)
            print(f"[TEST] Request {i}: {response.status_code}")
        
        for i, response in enumerate(responses):
            assert response.status_code == 200
            assert response.text == f"Echo: Concurrent {i}"
