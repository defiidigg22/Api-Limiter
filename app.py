from flask import Flask, jsonify, request
import redis
import time
import os

# --- Mock User Database ---
# In a real app, this would be a real database.
# Maps an API Key to a user plan.
USER_PLANS = {
    "free_user_key_123": "FREE",
    "pro_user_key_456": "PRO"
}

# --- Configuration Class ---
class Config:
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = 6379
    
    # Tiered rate limits
    TIERS = {
        "FREE": {"limit": 5, "window": 10},      # 5 requests per 10 seconds
        "PRO": {"limit": 50, "window": 10}       # 50 requests per 10 seconds
    }
    DEFAULT_TIER = "FREE" # Tier for users without a valid key

app = Flask(__name__)
app.config.from_object(Config)

# --- Redis Connection ---
try:
    r = redis.Redis(
        host=app.config["REDIS_HOST"],
        port=app.config["REDIS_PORT"],
        decode_responses=True
    )
    r.ping()
    print("Connected to Redis successfully!")
except redis.exceptions.ConnectionError as e:
    print(f"Could not connect to Redis: {e}")
    r = None

# --- Rate Limiter Middleware ---
@app.before_request
def rate_limiter():
    if r is None:
        return

    # 1. Determine the user's plan from their API Key
    api_key = request.headers.get("X-API-Key")
    plan = USER_PLANS.get(api_key, app.config["DEFAULT_TIER"])
    
    # 2. Get the specific limits for the user's plan
    tier_config = app.config["TIERS"][plan]
    limit = tier_config["limit"]
    window = tier_config["window"]

    # 3. Use a unique key for the IP and their plan
    ip_address = request.remote_addr
    key = f"rate_limit:{ip_address}:{plan}"
    current_time = time.time()

    try:
        oldest_allowed_time = current_time - window
        r.zremrangebyscore(key, 0, oldest_allowed_time)
        current_requests = r.zcard(key)

        if current_requests >= limit:
            # Include the current plan in the error message
            error_msg = f"Rate limit for {plan} tier exceeded. Try again later."
            return jsonify({"error": error_msg}), 429

        r.zadd(key, {str(current_time): current_time})
        r.expire(key, window)

    except redis.exceptions.ConnectionError as e:
        print(f"Redis error during request: {e}")
        pass

# --- API Endpoint ---
@app.route("/api/ping")
def ping():
    # Show the user their current plan in the response
    api_key = request.headers.get("X-API-Key")
    plan = USER_PLANS.get(api_key, app.config["DEFAULT_TIER"])
    return jsonify({"message": "pong!", "your_plan": plan})

if __name__ == '__main__':
    app.run(debug=True)