import httpx
import pytest
import asyncio
import time
from statistics import mean, median, stdev
from config import REQUEST_TIMEOUT, RUN_LARGE_PAYLOAD_TESTS


@pytest.mark.skipif(not RUN_LARGE_PAYLOAD_TESTS, reason="Large payload tests disabled by default")
class TestLargePayloadConcurrent:    
    def test_concurrent_large_payloads(self, base_url, server):
        payload_size = 1024 * 1024  # 1 MB
        num_requests = 10
        
        print(f"\n[TEST] Sending {num_requests} concurrent large requests ({payload_size} bytes each!)")
        
        payloads = [f"Data-{i}-" + "X" * (payload_size - len(f"Data-{i}-")) for i in range(num_requests)]
        
        timings = []
        responses_data = []
        
        with httpx.Client(timeout=REQUEST_TIMEOUT * 3) as client:
            start_total = time.perf_counter()
            
            for i, payload in enumerate(payloads):
                start = time.perf_counter()
                
                response = client.post(
                    base_url,
                    content=payload,
                )
                
                elapsed = time.perf_counter() - start
                timings.append(elapsed)
                responses_data.append((i, response, elapsed))
                
                print(f"[TEST] Request {i}: {response.status_code}, {len(response.text)} bytes, {elapsed:.4f}s")
            
            total_time = time.perf_counter() - start_total
        
        for i, response, elapsed in responses_data:
            assert response.status_code == 200, f"Request {i} failed with status {response.status_code}"
            assert response.text == f"Echo: {payloads[i]}", f"Request {i} returned wrong content"
        
        # Статистика
        print("\n" + "="*60)
        print("Statistics for concurrent large payload requests")
        print("="*60)
        print(f"Total requests: {num_requests}")
        print(f"Size of each payload: {payload_size:,} bytes ({payload_size / 1024 / 1024:.2f} MB)")
        print(f"Total time: {total_time:.4f}s")
        print(f"Average time per request: {mean(timings):.4f}s")
        print(f"Median time: {median(timings):.4f}s")
        if len(timings) > 1:
            print(f"Standard deviation: {stdev(timings):.4f}s")
        print(f"Minimum time: {min(timings):.4f}s")
        print(f"Maximum time: {max(timings):.4f}s")
        print(f"Throughput: {(payload_size * num_requests / 1024 / 1024) / total_time:.2f} MB/s")
        print("="*60)
    
    def test_concurrent_large_payloads_async(self, base_url, server):
        asyncio.run(self._async_concurrent_test(base_url))
    
    async def _async_concurrent_test(self, base_url):
        payload_size = 512 * 1024  # 512 KB
        num_requests = 20
        
        print(f"\n[TEST] Asynchronous sending of {num_requests} concurrent requests ({payload_size} bytes each)")
        
        payloads = [f"Async-{i}-" + "Y" * (payload_size - len(f"Async-{i}-")) for i in range(num_requests)]
        
        async def send_request(client, i, payload):
            start = time.perf_counter()
            response = await client.post(
                base_url,
                content=payload,
            )
            elapsed = time.perf_counter() - start
            return i, response, elapsed
        
        start_total = time.perf_counter()
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT * 3) as client:
            tasks = [send_request(client, i, payload) for i, payload in enumerate(payloads)]
            results = await asyncio.gather(*tasks)
        
        total_time = time.perf_counter() - start_total
        
        timings = [elapsed for _, _, elapsed in results]
        
        for i, response, elapsed in results:
            print(f"[TEST] Async Request {i}: {response.status_code}, {len(response.text)} bytes, {elapsed:.4f}s")
            assert response.status_code == 200, f"Async request {i} failed with status {response.status_code}"
            assert response.text == f"Echo: {payloads[i]}", f"Async request {i} returned wrong content"
        
        print("\n" + "="*60)
        print("Statistics for asynchronous execution")
        print("="*60)
        print(f"Total requests: {num_requests}")
        print(f"Size of each payload: {payload_size:,} bytes ({payload_size / 1024:.2f} KB)")
        print(f"Total time: {total_time:.4f}s")
        print(f"Average time per request: {mean(timings):.4f}s")
        print(f"Median time: {median(timings):.4f}s")
        if len(timings) > 1:
            print(f"Standard deviation: {stdev(timings):.4f}s")
        print(f"Minimum time: {min(timings):.4f}s")
        print(f"Maximum time: {max(timings):.4f}s")
        print(f"Throughput: {(payload_size * num_requests / 1024 / 1024) / total_time:.2f} MB/s")
        print(f"Actual concurrency: {num_requests / total_time:.2f} req/s")
        print("="*60)
    
    @pytest.mark.parametrize("payload_size_kb", [100, 500, 1000, 5000])
    def test_various_payload_sizes(self, base_url, server, payload_size_kb):
        """Test with various payload sizes"""
        payload_size = payload_size_kb * 1024
        num_requests = 5
        
        print(f"\n[TEST] Sending {num_requests} requests with {payload_size_kb} KB each")
        
        payloads = ["Z" * payload_size for _ in range(num_requests)]
        timings = []
        
        with httpx.Client(timeout=REQUEST_TIMEOUT * 3) as client:
            for i, payload in enumerate(payloads):
                start = time.perf_counter()
                response = client.post(base_url, content=payload)
                elapsed = time.perf_counter() - start
                timings.append(elapsed)
                
                assert response.status_code == 200
                print(f"[TEST] Request {i}: {elapsed:.4f}s")
        
        print(f"[STATS] {payload_size_kb} KB - Среднее время: {mean(timings):.4f}s")
