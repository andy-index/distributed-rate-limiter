local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]

-- 1. Evict entries older than the window
redis.call('ZREMRANGEBYSCORE', key, 0, now - window)

-- 2. Count what's left
local count = redis.call('ZCARD', key)

-- 3. Allow or deny
if count < limit then
    redis.call('ZADD', key, now, member)
    redis.call('EXPIRE', key, window)
    return {1, limit - count - 1}
else
    return {0, 0}
end
