import os
import time
import random

#from api import init_api
from flask import Flask, Response, request, jsonify, g
from collections import deque
from prometheus_client import Gauge, generate_latest
from functools import lru_cache

app = Flask(__name__)


#init_api(app)


is_ready = True

NAMESPACE = os.getenv('POD_NAMESPACE', 'default')
POD_NAME = os.getenv('POD_NAME', 'unknown')

requests_per_second = Gauge('requests_per_second', 'The number of requests per second.', ['namespace', 'pod'])
request_duration = Gauge('request_duration_seconds', 'The duration of HTTP requests.', ['namespace', 'pod', 'method', 'endpoint'])
average_request_duration = Gauge('average_request_duration_seconds', 'Average duration of HTTP requests in the last minute.', ['namespace', 'pod'])

request_times = deque()
request_durations = deque()

@app.before_request
def before_request():
    g.start_time = time.time()

@app.after_request
def after_request(response):
    request_time = time.time() - g.start_time
    request_duration.labels(namespace=NAMESPACE, pod=POD_NAME, method=request.method, endpoint=request.path).set(request_time)
    return response

# Probes section
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify(status='OK'), 200


@app.route('/ready', methods=['GET'])
def readiness_probe():
    global is_ready
    if is_ready:
        return jsonify(status='OK'), 200
    else:
        return jsonify(status='Service unavailable'), 503


@app.route('/ready/enable', methods=['GET'])
def enable_readiness():
    global is_ready
    is_ready = True
    return 'Readiness enabled', 202


@app.route('/ready/disable', methods=['GET'])
def disable_readiness():
    global is_ready
    is_ready = False
    return 'Readiness disabled', 202

@app.route('/payload', methods=['GET'])
def payload():
    n = random.randint(1, 10000)
    fib = fibonacci(n)
    return jsonify(n=n, fib=fib)

@app.route('/metrics', methods=['GET'])
def metrics():
    rps_count = update_request_metrics()
    avg_duration = update_average_duration()
    requests_per_second.labels(namespace=NAMESPACE, pod=POD_NAME).set(rps_count)
    average_request_duration.labels(namespace=NAMESPACE, pod=POD_NAME).set(avg_duration)
    return Response(generate_latest(), mimetype='text/plain')

def update_request_metrics():
    now = time.time()
    request_times.append(now)
    while request_times and request_times[0] < now - 1:
        request_times.popleft()
    return len(request_times)

def update_average_duration():
    now = time.time()
    while request_durations and request_durations[0][0] < now - 60:
        request_durations.popleft()
    if request_durations:
        total_duration = sum(duration for _, duration in request_durations)
        return total_duration / len(request_durations)
    return 0.0

def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
