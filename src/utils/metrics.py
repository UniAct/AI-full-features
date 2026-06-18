"""
Middleware and utilities for exposing Prometheus metrics.
"""

from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time

# Define metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP Requests", ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "HTTP Request Latency", ["method", "endpoint"]
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    HTTP middleware that records request latency and count for Prometheus.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Processes each request to record metrics.
        
        Args:
            request (Request): The incoming HTTP request.
            call_next: The next handler in the middleware chain.
            
        Returns:
            Response: The processed HTTP response.
        """
        start_time = time.time()

        # Process the request
        response = await call_next(request)

        # Record metrics after request is processed
        duration = time.time() - start_time
        endpoint = request.url.path

        REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(duration)
        REQUEST_COUNT.labels(
            method=request.method, endpoint=endpoint, status=response.status_code
        ).inc()

        return response


def setup_metrics(app: FastAPI):
    """
    Configures Prometheus metrics middleware and adds a specialized metrics endpoint.
    
    Args:
        app (FastAPI): The FastAPI application instance.
    """
    app.add_middleware(PrometheusMiddleware)

    # Obfuscated metrics endpoint for security
    @app.get("/metrics/stats", include_in_schema=False)
    def metrics():
        """
        Exposes current metrics in Prometheus format.
        """
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

