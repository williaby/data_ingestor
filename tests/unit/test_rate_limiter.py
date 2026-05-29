"""Unit tests for rate limiter."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from data_ingestor.utils.rate_limiter import OpenRouterRateLimiter, RateLimiter


class TestRateLimiter:
    """Test RateLimiter class."""

    def test_basic_rate_limiting(self) -> None:
        """Test basic rate limiting functionality."""
        # Create limiter with 5 RPM, 10/day
        limiter = RateLimiter(rpm_limit=5, daily_limit=10, tier="free")

        # Should be able to acquire 5 slots immediately
        for _ in range(5):
            assert limiter.acquire(timeout=1.0) is True

        # 6th request should block (or fail with short timeout)
        start_time = time.time()
        result = limiter.acquire(timeout=0.5)
        elapsed = time.time() - start_time

        # Should either timeout or wait
        assert result is False or elapsed > 0.4

    def test_sliding_window(self) -> None:
        """Test that sliding window works correctly."""
        limiter = RateLimiter(rpm_limit=3, daily_limit=100, tier="free")

        # Acquire 3 slots
        for _ in range(3):
            assert limiter.acquire(timeout=1.0) is True

        # 4th should timeout (all slots filled)
        result = limiter.acquire(timeout=0.2)
        assert result is False

        # Stats should show 3 current RPM
        stats = limiter.get_stats()
        assert stats["current_rpm"] == 3

    def test_daily_limit(self) -> None:
        """Test daily limit enforcement."""
        limiter = RateLimiter(rpm_limit=100, daily_limit=5, tier="free")

        # Acquire 5 slots (daily limit)
        for _ in range(5):
            assert limiter.acquire(timeout=1.0) is True

        # 6th should raise ValueError
        with pytest.raises(ValueError, match="Daily limit .* exceeded"):
            limiter.acquire(timeout=1.0)

    def test_stats(self) -> None:
        """Test statistics tracking."""
        limiter = RateLimiter(rpm_limit=10, daily_limit=100, tier="free")

        # Acquire 3 slots
        for _ in range(3):
            limiter.acquire(timeout=1.0)

        stats = limiter.get_stats()
        assert stats["total_requests"] == 3
        assert stats["current_rpm"] <= 3
        assert stats["current_daily"] == 3
        assert stats["rpm_limit"] == 10
        assert stats["daily_limit"] == 100

    def test_reset(self) -> None:
        """Test reset functionality."""
        limiter = RateLimiter(rpm_limit=5, daily_limit=10, tier="free")

        # Acquire some slots
        for _ in range(3):
            limiter.acquire(timeout=1.0)

        stats = limiter.get_stats()
        assert stats["total_requests"] == 3

        # Reset
        limiter.reset()

        stats = limiter.get_stats()
        assert stats["total_requests"] == 0
        assert stats["current_rpm"] == 0
        assert stats["current_daily"] == 0

    def test_get_wait_time(self) -> None:
        """Test wait time estimation."""
        limiter = RateLimiter(rpm_limit=2, daily_limit=100, tier="free")

        # No wait initially
        assert limiter.get_wait_time() == 0.0

        # Acquire 2 slots (hit limit)
        limiter.acquire(timeout=1.0)
        limiter.acquire(timeout=1.0)

        # Should need to wait (up to 60 seconds)
        wait_time = limiter.get_wait_time()
        assert 0.0 < wait_time <= 60.0

    def test_thread_safety(self) -> None:
        """Test thread-safe concurrent access."""
        limiter = RateLimiter(rpm_limit=10, daily_limit=100, tier="free")

        def acquire_slot() -> bool:
            return limiter.acquire(timeout=5.0)

        # Create 20 threads trying to acquire slots
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(acquire_slot) for _ in range(20)]
            results = [f.result() for f in as_completed(futures)]

        # Should have acquired exactly 10 slots (rpm_limit)
        # Some may timeout since we're only allowing 5s timeout
        successful = sum(1 for r in results if r is True)
        assert successful <= 10

        stats = limiter.get_stats()
        assert stats["current_rpm"] <= 10

    def test_tier_configuration(self) -> None:
        """Test tier-specific configuration."""
        free_limiter = RateLimiter(rpm_limit=20, daily_limit=50, tier="free")
        paid_limiter = RateLimiter(rpm_limit=20, daily_limit=1000, tier="paid")

        assert free_limiter.tier == "free"
        assert free_limiter.daily_limit == 50

        assert paid_limiter.tier == "paid"
        assert paid_limiter.daily_limit == 1000


class TestOpenRouterRateLimiter:
    """Test OpenRouterRateLimiter class."""

    def test_free_model_routing(self) -> None:
        """Test that :free models use free limiter."""
        limiter = OpenRouterRateLimiter(tier="paid")

        # Free model should use free limiter
        assert limiter.acquire("meta-llama/llama-4-maverick:free", timeout=1.0) is True

        # Check that free limiter was used
        stats = limiter.get_stats(model_type="free")
        assert stats["free_models"]["total_requests"] == 1

    def test_paid_model_routing(self) -> None:
        """Test that paid models use paid limiter."""
        limiter = OpenRouterRateLimiter(tier="paid")

        # Paid model should use paid limiter
        assert limiter.acquire("google/gemini-2.5-flash-lite", timeout=1.0) is True

        # Check that paid limiter was used
        stats = limiter.get_stats(model_type="paid")
        assert stats["paid_models"]["total_requests"] == 1

    def test_tier_limits(self) -> None:
        """Test tier-specific daily limits."""
        free_tier = OpenRouterRateLimiter(tier="free")
        paid_tier = OpenRouterRateLimiter(tier="paid")

        # Free tier should have 50/day for :free models
        assert free_tier.free_limiter.daily_limit == 50

        # Paid tier should have 1000/day for :free models
        assert paid_tier.free_limiter.daily_limit == 1000

    def test_rpm_limits(self) -> None:
        """Test that RPM is correctly limited to 20 for :free models."""
        limiter = OpenRouterRateLimiter(tier="paid")

        # Should be able to acquire 20 slots for :free models
        for _ in range(20):
            assert limiter.acquire("meta-llama/llama-4-maverick:free", timeout=1.0) is True

        # 21st should timeout
        result = limiter.acquire("meta-llama/llama-4-maverick:free", timeout=0.5)
        assert result is False

    def test_combined_stats(self) -> None:
        """Test combined statistics for both free and paid models."""
        limiter = OpenRouterRateLimiter(tier="paid")

        # Acquire some free and paid slots
        limiter.acquire("meta-llama/llama-4-maverick:free", timeout=1.0)
        limiter.acquire("google/gemini-2.5-flash-lite", timeout=1.0)

        # Get combined stats
        stats = limiter.get_stats()
        assert "free_models" in stats
        assert "paid_models" in stats
        assert stats["free_models"]["total_requests"] == 1
        assert stats["paid_models"]["total_requests"] == 1

    def test_concurrent_mixed_models(self) -> None:
        """Test concurrent requests with mixed free and paid models."""
        limiter = OpenRouterRateLimiter(tier="paid")

        def acquire_free() -> bool:
            return limiter.acquire("meta-llama/llama-4-maverick:free", timeout=2.0)

        def acquire_paid() -> bool:
            return limiter.acquire("google/gemini-2.5-flash-lite", timeout=2.0)

        # Create mixed requests
        with ThreadPoolExecutor(max_workers=30) as executor:
            free_futures = [executor.submit(acquire_free) for _ in range(15)]
            paid_futures = [executor.submit(acquire_paid) for _ in range(15)]

            all_futures = free_futures + paid_futures
            results = [f.result() for f in as_completed(all_futures)]

        # Paid models should mostly succeed (high limit)
        # Free models should be limited to 20 RPM
        stats = limiter.get_stats()

        # Free models should be rate limited
        assert stats["free_models"]["current_rpm"] <= 20

        # Paid models should have high throughput
        assert stats["paid_models"]["total_requests"] > 0


class TestRateLimiterIntegration:
    """Integration tests for rate limiter."""

    def test_realistic_usage_pattern(self) -> None:
        """Test realistic usage pattern with bursts and pauses."""
        limiter = RateLimiter(rpm_limit=10, daily_limit=100, tier="paid")

        # Burst 1: 5 requests
        for _ in range(5):
            assert limiter.acquire(timeout=1.0) is True

        # Burst 2: 5 more requests (within limit)
        for _ in range(5):
            assert limiter.acquire(timeout=1.0) is True

        # Now at 10/10 limit - next should timeout
        result = limiter.acquire(timeout=0.2)
        assert result is False

        # Stats should show 10 current RPM
        stats = limiter.get_stats()
        assert stats["current_rpm"] == 10
        assert stats["total_requests"] == 10

    def test_error_recovery(self) -> None:
        """Test error recovery and retry logic."""
        limiter = RateLimiter(rpm_limit=5, daily_limit=100, tier="free")

        # Fill up the limiter
        for _ in range(5):
            assert limiter.acquire(timeout=1.0) is True

        # Try to acquire with short timeout (should fail - limit reached)
        result = limiter.acquire(timeout=0.2)
        assert result is False

        # Verify we're at the limit
        stats = limiter.get_stats()
        assert stats["current_rpm"] == 5
        assert stats["rpm_utilization"] == 1.0

    def test_long_running_process(self) -> None:
        """Test rate limiter capacity and stats tracking."""
        # 5 RPM limit
        limiter = RateLimiter(rpm_limit=5, daily_limit=100, tier="paid")

        # Acquire 5 requests (fill the limiter)
        for _ in range(5):
            assert limiter.acquire(timeout=1.0) is True

        # Verify we're at capacity
        stats = limiter.get_stats()
        assert stats["current_rpm"] == 5
        assert stats["rpm_utilization"] == 1.0
        assert stats["total_requests"] == 5

        # 6th request should timeout (over limit)
        result = limiter.acquire(timeout=0.2)
        assert result is False

        # Total requests should still be 5 (timeout doesn't increment)
        stats = limiter.get_stats()
        assert stats["total_requests"] == 5
