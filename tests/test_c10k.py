import httpx
import pytest
import asyncio
import time
from statistics import mean, median, stdev, quantiles
from config import REQUEST_TIMEOUT, RUN_C10K_TESTS

pytestmark = pytest.mark.asyncio


@pytest.mark.skipif(not RUN_C10K_TESTS, reason="C10k tests disabled by default - very resource intensive")
class TestC10kProblem:    
    async def _stress_test(self, base_url, num_connections, payload_size, duration_info=True):        
        payload = "X" * payload_size
        
        async def send_request(client, conn_id):
            start = time.perf_counter()
            try:
                response = await client.post(
                    base_url,
                    content=f"Conn-{conn_id}-{payload}",
                    timeout=REQUEST_TIMEOUT * 2
                )
                elapsed = time.perf_counter() - start
                return {
                    'id': conn_id,
                    'success': response.status_code == 200,
                    'status': response.status_code,
                    'time': elapsed,
                    'error': None
                }
            except Exception as e:
                elapsed = time.perf_counter() - start
                return {
                    'id': conn_id,
                    'success': False,
                    'status': 0,
                    'time': elapsed,
                    'error': str(e)
                }
        
        print(f"\n[C10K TEST] Starting {num_connections} concurrent connections")
        print(f"[C10K TEST] Payload size: {payload_size} bytes")
        
        start_total = time.perf_counter()
        
        limits = httpx.Limits(
            max_keepalive_connections=num_connections,
            max_connections=num_connections,
            keepalive_expiry=30
        )
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT * 2, limits=limits) as client:
            tasks = [send_request(client, i) for i in range(num_connections)]
            results = await asyncio.gather(*tasks)
        
        total_time = time.perf_counter() - start_total
        
        successful = [r for r in results if r['success']]
        failed = [r for r in results if not r['success']]
        timings = [r['time'] for r in successful]
        
        return {
            'total': len(results),
            'successful': len(successful),
            'failed': len(failed),
            'timings': timings,
            'total_time': total_time,
            'results': results,
            'payload_size': payload_size
        }
    
    def _print_statistics(self, stats, test_name):
        print("\n" + "="*70)
        print(f"C10K TEST RESULTS: {test_name}")
        print("="*70)
        print(f"Total connections attempted: {stats['total']}")
        print(f"Successful: {stats['successful']} ({stats['successful']/stats['total']*100:.2f}%)")
        print(f"Failed: {stats['failed']} ({stats['failed']/stats['total']*100:.2f}%)")
        print(f"Total execution time: {stats['total_time']:.4f}s")
        
        if stats['timings']:
            timings = stats['timings']
            print(f"\nResponse Time Statistics:")
            print(f"  Average: {mean(timings):.4f}s")
            print(f"  Median: {median(timings):.4f}s")
            if len(timings) > 1:
                print(f"  Std deviation: {stdev(timings):.4f}s")
            print(f"  Min: {min(timings):.4f}s")
            print(f"  Max: {max(timings):.4f}s")
            
            if len(timings) >= 4:
                percentiles = quantiles(timings, n=100)
                print(f"\nPercentiles:")
                print(f"  50th (median): {percentiles[49]:.4f}s")
                print(f"  90th: {percentiles[89]:.4f}s")
                print(f"  95th: {percentiles[94]:.4f}s")
                print(f"  99th: {percentiles[98]:.4f}s")
            
            total_data = stats['total'] * stats['payload_size'] / 1024 / 1024  # MB
            throughput = total_data / stats['total_time']
            print(f"\nThroughput:")
            print(f"  Data transferred: {total_data:.2f} MB")
            print(f"  Throughput: {throughput:.2f} MB/s")
            print(f"  Requests per second: {stats['successful'] / stats['total_time']:.2f} req/s")
        
        if stats['failed'] > 0:
            print(f"\nErrors encountered:")
            error_types = {}
            for r in stats['results']:
                if not r['success']:
                    error = r['error'] or f"HTTP {r['status']}"
                    error_types[error] = error_types.get(error, 0) + 1
            
            for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                print(f"  {error}: {count} times")
        
        print("="*70)
    
    @pytest.mark.asyncio
    async def test_1k_connections(self, base_url, server):
        stats = await self._stress_test(base_url, 1000, 100)
        self._print_statistics(stats, "1K Connections")
        
        assert stats['successful'] >= stats['total'] * 0.95, \
            f"Too many failed requests: {stats['failed']}/{stats['total']}"
    
    @pytest.mark.asyncio
    async def test_5k_connections(self, base_url, server):
        stats = await self._stress_test(base_url, 5000, 100)
        self._print_statistics(stats, "5K Connections")
        
        assert stats['successful'] >= stats['total'] * 0.90, \
            f"Too many failed requests: {stats['failed']}/{stats['total']}"
    
    @pytest.mark.asyncio
    async def test_10k_connections_small_payload(self, base_url, server):
        stats = await self._stress_test(base_url, 10000, 100)
        self._print_statistics(stats, "10K Connections (Small Payload)")
        
        assert stats['successful'] >= stats['total'] * 0.85, \
            f"Too many failed requests: {stats['failed']}/{stats['total']}"
    
    @pytest.mark.asyncio
    async def test_10k_connections_medium_payload(self, base_url, server):
        stats = await self._stress_test(base_url, 10000, 1024)
        self._print_statistics(stats, "10K Connections (Medium Payload)")
        
        assert stats['successful'] >= stats['total'] * 0.85, \
            f"Too many failed requests: {stats['failed']}/{stats['total']}"
    
    @pytest.mark.asyncio
    async def test_sustained_load(self, base_url, server):
        print("\n[C10K TEST] Sustained load test - 3 waves of 2000 connections each")
        
        wave_stats = []
        for wave in range(3):
            print(f"\n[C10K TEST] Starting wave {wave + 1}/3...")
            stats = await self._stress_test(base_url, 2000, 512)
            wave_stats.append(stats)
            
            if wave < 2:
                await asyncio.sleep(1)
        
        print("\n" + "="*70)
        print("SUSTAINED LOAD TEST - SUMMARY")
        print("="*70)
        
        total_requests = sum(s['total'] for s in wave_stats)
        total_successful = sum(s['successful'] for s in wave_stats)
        total_failed = sum(s['failed'] for s in wave_stats)
        total_time = sum(s['total_time'] for s in wave_stats)
        
        print(f"Total waves: 3")
        print(f"Total requests: {total_requests}")
        print(f"Total successful: {total_successful} ({total_successful/total_requests*100:.2f}%)")
        print(f"Total failed: {total_failed}")
        print(f"Cumulative time: {total_time:.4f}s")
        print(f"Average RPS: {total_successful/total_time:.2f} req/s")
        
        print(f"\nPer-wave breakdown:")
        for i, stats in enumerate(wave_stats, 1):
            avg_time = mean(stats['timings']) if stats['timings'] else 0
            print(f"  Wave {i}: {stats['successful']}/{stats['total']} success, "
                  f"avg time: {avg_time:.4f}s, "
                  f"RPS: {stats['successful']/stats['total_time']:.2f}")
        
        print("="*70)
        
        assert total_successful >= total_requests * 0.90, \
            f"Too many failed requests across all waves: {total_failed}/{total_requests}"
    
    @pytest.mark.asyncio
    async def test_connection_reuse(self, base_url, server):
        print("\n[C10K TEST] Connection reuse test - multiple requests per connection")
        
        num_connections = 1000
        requests_per_connection = 5
        payload = "Y" * 200
        
        async def multiple_requests(client, conn_id):
            timings = []
            for req_num in range(requests_per_connection):
                start = time.perf_counter()
                try:
                    response = await client.post(
                        base_url,
                        content=f"Conn-{conn_id}-Req-{req_num}-{payload}",
                        timeout=REQUEST_TIMEOUT
                    )
                    elapsed = time.perf_counter() - start
                    timings.append({
                        'success': response.status_code == 200,
                        'time': elapsed
                    })
                except Exception as e:
                    elapsed = time.perf_counter() - start
                    timings.append({
                        'success': False,
                        'time': elapsed
                    })
            return timings
        
        start_total = time.perf_counter()
        
        limits = httpx.Limits(
            max_keepalive_connections=num_connections,
            max_connections=num_connections,
            keepalive_expiry=30
        )
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT * 2, limits=limits) as client:
            tasks = [multiple_requests(client, i) for i in range(num_connections)]
            results = await asyncio.gather(*tasks)
        
        total_time = time.perf_counter() - start_total
        
        all_timings = []
        total_requests = 0
        successful_requests = 0
        
        for conn_results in results:
            for req_result in conn_results:
                total_requests += 1
                if req_result['success']:
                    successful_requests += 1
                    all_timings.append(req_result['time'])
        
        print("\n" + "="*70)
        print("CONNECTION REUSE TEST RESULTS")
        print("="*70)
        print(f"Connections: {num_connections}")
        print(f"Requests per connection: {requests_per_connection}")
        print(f"Total requests: {total_requests}")
        print(f"Successful: {successful_requests} ({successful_requests/total_requests*100:.2f}%)")
        print(f"Total time: {total_time:.4f}s")
        print(f"Requests per second: {successful_requests/total_time:.2f} req/s")
        
        if all_timings:
            print(f"\nResponse times:")
            print(f"  Average: {mean(all_timings):.4f}s")
            print(f"  Median: {median(all_timings):.4f}s")
            print(f"  Min: {min(all_timings):.4f}s")
            print(f"  Max: {max(all_timings):.4f}s")
        
        print("="*70)
        
        assert successful_requests >= total_requests * 0.95, \
            f"Too many failed requests: {total_requests - successful_requests}/{total_requests}"
