"""Redis-backed sliding-window rate limiting with a local development fallback."""
import threading
import time
import uuid

from services.cache_service import get_redis_client

_FALLBACK_REQUESTS = {}
_FALLBACK_LOCK = threading.Lock()

# The check and insert must happen inside one Redis command.  A pipeline alone
# would let concurrent workers pass the limit at the same time.
_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local cutoff = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
local ttl = tonumber(ARGV[5])

redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
local current = redis.call('ZCARD', key)
if current >= limit then
    redis.call('EXPIRE', key, ttl)
    return 0
end

redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, ttl)
return 1
"""


def _allow_with_memory(key, limit, window_seconds, now):
    """Single-process fallback for local development or a failed Redis node."""
    with _FALLBACK_LOCK:
        # Avoid unbounded key growth in the fallback mode.
        if len(_FALLBACK_REQUESTS) > 10_000:
            cutoff = now - window_seconds
            for stale_key, timestamps in list(_FALLBACK_REQUESTS.items()):
                active = [timestamp for timestamp in timestamps if timestamp > cutoff]
                if active:
                    _FALLBACK_REQUESTS[stale_key] = active
                else:
                    _FALLBACK_REQUESTS.pop(stale_key, None)

        timestamps = [
            timestamp
            for timestamp in _FALLBACK_REQUESTS.get(key, [])
            if now - timestamp < window_seconds
        ]
        if len(timestamps) >= limit:
            _FALLBACK_REQUESTS[key] = timestamps
            return False

        timestamps.append(now)
        _FALLBACK_REQUESTS[key] = timestamps
        return True


def allow_request(scope, client_ip, limit, window_seconds):
    """Return whether a request may proceed.

    Redis makes the decision shared and atomic across workers.  The fallback is
    deliberately local: it keeps development usable, but production should set
    ``REDIS_URL`` for distributed protection.
    """
    now = time.time()
    redis_client = get_redis_client()
    key = f"trendo:rate-limit:{scope}:{client_ip}"

    if redis_client:
        try:
            allowed = redis_client.eval(
                _SLIDING_WINDOW_LUA,
                1,
                key,
                now,
                now - window_seconds,
                limit,
                f"{now}:{uuid.uuid4().hex}",
                max(1, int(window_seconds)),
            )
            return bool(allowed)
        except Exception as exc:
            # Do not fail open: retain the local limiter if Redis is temporarily
            # unavailable.  The warning helps operations notice the degradation.
            print(f"[rate-limit] Redis xatosi, lokal fallback ishlatiladi: {exc}")

    return _allow_with_memory(key, limit, window_seconds, now)
