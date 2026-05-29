"""Rate limiter for OpenRouter API calls.

Implements token bucket algorithm with per-minute and per-day limits
to comply with OpenRouter's rate limiting policies.
"""

import logging
import time
from collections import deque
from threading import Lock
from typing import Literal

logger = logging.getLogger(__name__)


class RateLimiter:
    """Thread-safe rate limiter with per-minute and per-day limits.

    Implements token bucket algorithm for RPM (requests per minute) and
    sliding window for daily request tracking.

    # #CRITICAL: Thread Safety: Multiple threads may call API concurrently
    # #VERIFY: Must use locks to prevent race conditions

    # #CRITICAL: Rate Limit Compliance: Must not exceed OpenRouter limits
    # #VERIFY: 20 RPM for free models, daily limits based on tier
    """

    def __init__(
        self,
        rpm_limit: int = 20,
        daily_limit: int = 50,
        tier: Literal["free", "paid"] = "free",
    ) -> None:
        """Initialize rate limiter.

        Args:
            rpm_limit: Requests per minute limit (default: 20 for OpenRouter)
            daily_limit: Daily request limit (default: 50 for free tier)
            tier: Account tier ("free" or "paid") - affects daily limits
        """
        self.rpm_limit = rpm_limit
        self.daily_limit = daily_limit
        self.tier = tier

        # Per-minute tracking (sliding window)
        self._minute_requests: deque[float] = deque()
        self._minute_lock = Lock()

        # Per-day tracking (sliding window)
        self._daily_requests: deque[float] = deque()
        self._daily_lock = Lock()

        # Statistics
        self._total_requests = 0
        self._total_waits = 0
        self._total_wait_time = 0.0

        logger.info(
            f"RateLimiter initialized: {rpm_limit} RPM, {daily_limit}/day ({tier} tier)",
        )

    def acquire(self, timeout: float | None = None) -> bool:
        """Acquire permission to make an API request.

        Blocks until a request slot is available or timeout is reached.

        # #CRITICAL: Deadlock Prevention: Must not block indefinitely
        # #VERIFY: Implement timeout and periodic checks

        Args:
            timeout: Maximum time to wait in seconds (None = wait indefinitely)

        Returns:
            True if permission granted, False if timeout reached

        Raises:
            ValueError: If daily limit would be exceeded
        """
        start_time = time.time()

        # Check daily limit first (non-blocking check)
        with self._daily_lock:
            self._cleanup_daily_window()
            if len(self._daily_requests) >= self.daily_limit:
                # Calculate when oldest request will expire
                if self._daily_requests:
                    oldest = self._daily_requests[0]
                    reset_time = oldest + 86400  # 24 hours in seconds
                    wait_seconds = reset_time - time.time()

                    raise ValueError(
                        f"Daily limit ({self.daily_limit}) exceeded. "
                        f"Resets in {wait_seconds/3600:.1f} hours. "
                        f"Consider upgrading to paid tier ($10+) for 1000/day limit.",
                    )

        # Wait for RPM slot
        while True:
            with self._minute_lock:
                self._cleanup_minute_window()

                # Check if we can proceed
                if len(self._minute_requests) < self.rpm_limit:
                    # Grant permission
                    current_time = time.time()
                    self._minute_requests.append(current_time)

                    with self._daily_lock:
                        self._daily_requests.append(current_time)

                    self._total_requests += 1

                    # Log wait time if we waited
                    elapsed = time.time() - start_time
                    if elapsed > 0.1:  # Only log if we waited > 100ms
                        self._total_waits += 1
                        self._total_wait_time += elapsed
                        logger.info(f"Rate limiter: waited {elapsed:.2f}s for slot")

                    return True

            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.warning(f"Rate limiter: timeout after {elapsed:.2f}s")
                    return False

            # Calculate sleep time until next slot
            with self._minute_lock:
                if self._minute_requests:
                    # Sleep until oldest request expires (60 seconds old)
                    oldest = self._minute_requests[0]
                    sleep_time = max(0.1, 60 - (time.time() - oldest))
                else:
                    sleep_time = 0.1

            # Sleep briefly to avoid busy waiting
            time.sleep(min(sleep_time, 1.0))

    def _cleanup_minute_window(self) -> None:
        """Remove requests older than 60 seconds from minute window."""
        cutoff = time.time() - 60
        while self._minute_requests and self._minute_requests[0] < cutoff:
            self._minute_requests.popleft()

    def _cleanup_daily_window(self) -> None:
        """Remove requests older than 24 hours from daily window."""
        cutoff = time.time() - 86400  # 24 hours in seconds
        while self._daily_requests and self._daily_requests[0] < cutoff:
            self._daily_requests.popleft()

    def get_stats(self) -> dict[str, int | float]:
        """Get rate limiter statistics.

        Returns:
            Dictionary with statistics
        """
        with self._minute_lock:
            self._cleanup_minute_window()
            current_rpm = len(self._minute_requests)

        with self._daily_lock:
            self._cleanup_daily_window()
            current_daily = len(self._daily_requests)

        return {
            "total_requests": self._total_requests,
            "total_waits": self._total_waits,
            "total_wait_time": self._total_wait_time,
            "avg_wait_time": (self._total_wait_time / self._total_waits if self._total_waits > 0 else 0),
            "current_rpm": current_rpm,
            "rpm_limit": self.rpm_limit,
            "rpm_utilization": current_rpm / self.rpm_limit if self.rpm_limit > 0 else 0,
            "current_daily": current_daily,
            "daily_limit": self.daily_limit,
            "daily_utilization": (current_daily / self.daily_limit if self.daily_limit > 0 else 0),
        }

    def reset(self) -> None:
        """Reset all request tracking (for testing)."""
        with self._minute_lock:
            self._minute_requests.clear()

        with self._daily_lock:
            self._daily_requests.clear()

        self._total_requests = 0
        self._total_waits = 0
        self._total_wait_time = 0.0

    def get_wait_time(self) -> float:
        """Get estimated wait time until next request slot is available.

        Returns:
            Estimated wait time in seconds (0 if slot immediately available)
        """
        with self._minute_lock:
            self._cleanup_minute_window()

            # Check if slot available
            if len(self._minute_requests) < self.rpm_limit:
                return 0.0

            # Calculate when oldest request will be 60 seconds old
            if self._minute_requests:
                oldest = self._minute_requests[0]
                return max(0.0, 60 - (time.time() - oldest))

        return 0.0


class OpenRouterRateLimiter:
    """Rate limiter specifically configured for OpenRouter API.

    Manages separate rate limiters for free and paid models.

    # #CRITICAL: Model Routing: Must route to correct rate limiter
    # #VERIFY: Free models use 20 RPM limit, paid models have no limit
    """

    def __init__(self, tier: Literal["free", "paid"] = "free") -> None:
        """Initialize OpenRouter rate limiter.

        Args:
            tier: Account tier ("free" < $10 credits, "paid" >= $10 credits)
        """
        self.tier = tier

        # Free model rate limiter (20 RPM, tier-based daily limit)
        daily_limit = 50 if tier == "free" else 1000
        self.free_limiter = RateLimiter(
            rpm_limit=20,
            daily_limit=daily_limit,
            tier=tier,
        )

        # Paid models have no platform-level rate limits
        # But we still track for monitoring purposes
        self.paid_limiter = RateLimiter(
            rpm_limit=1000,  # Conservative limit for monitoring
            daily_limit=100000,  # Very high limit (no real limit)
            tier=tier,
        )

        logger.info(f"OpenRouterRateLimiter initialized for {tier} tier")

    def acquire(self, model: str, timeout: float | None = None) -> bool:
        """Acquire permission for API request based on model.

        Args:
            model: Model name (e.g., "meta-llama/llama-4-maverick:free")
            timeout: Maximum time to wait in seconds

        Returns:
            True if permission granted, False if timeout reached

        Raises:
            ValueError: If daily limit exceeded
        """
        # Route to appropriate rate limiter
        if model.endswith(":free"):
            logger.debug(f"Using free tier rate limiter for {model}")
            return self.free_limiter.acquire(timeout=timeout)
        logger.debug(f"Using paid tier rate limiter for {model}")
        return self.paid_limiter.acquire(timeout=timeout)

    def get_stats(self, model_type: Literal["free", "paid"] | None = None) -> dict:
        """Get rate limiter statistics.

        Args:
            model_type: "free" or "paid" (None = both)

        Returns:
            Statistics dictionary
        """
        if model_type == "free":
            return {"free_models": self.free_limiter.get_stats()}
        if model_type == "paid":
            return {"paid_models": self.paid_limiter.get_stats()}
        return {
            "free_models": self.free_limiter.get_stats(),
            "paid_models": self.paid_limiter.get_stats(),
        }
