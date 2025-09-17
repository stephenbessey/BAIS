"""
Custom Prometheus Metrics for BAIS AP2 Integration
"""

from prometheus_client import Counter, Histogram, Gauge, Info
import time
from functools import wraps
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)

# Payment Workflow Metrics
payment_workflows_initiated = Counter(
    'bais_payment_workflows_initiated_total',
    'Total number of AP2 payment workflows initiated',
    ['business_id', 'payment_method_type']
)

payment_workflows_completed = Counter(
    'bais_payment_workflows_completed_total',
    'Total number of AP2 payment workflows completed successfully',
    ['business_id', 'payment_method_type']
)

payment_workflows_failed = Counter(
    'bais_payment_workflows_failed_total',
    'Total number of AP2 payment workflows that failed',
    ['business_id', 'failure_reason']
)

payment_workflow_duration = Histogram(
    'bais_payment_workflow_duration_seconds',
    'Time taken to complete payment workflows',
    ['business_id', 'workflow_step'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120]
)

# AP2 Mandate Metrics
ap2_mandates_created = Counter(
    'bais_ap2_mandates_created_total',
    'Total number of AP2 mandates created',
    ['mandate_type', 'business_id']
)

ap2_mandates_expired = Counter(
    'bais_ap2_mandates_expired_total',
    'Total number of AP2 mandates that expired',
    ['mandate_type', 'business_id']
)

# Webhook Processing Metrics
ap2_webhooks_received = Counter(
    'bais_ap2_webhooks_received_total',
    'Total number of AP2 webhooks received',
    ['event_type']
)

ap2_webhooks_processed = Counter(
    'bais_ap2_webhooks_processed_total',
    'Total number of AP2 webhooks processed successfully',
    ['event_type']
)

ap2_webhooks_failed = Counter(
    'bais_ap2_webhooks_failed_total',
    'Total number of AP2 webhooks that failed processing',
    ['event_type', 'failure_reason']
)

ap2_webhook_processing_duration = Histogram(
    'bais_ap2_webhook_processing_duration_seconds',
    'Time taken to process AP2 webhooks',
    ['event_type'],
    buckets=[0.01, 0.1, 0.5, 1, 2, 5]
)

ap2_webhook_queue_size = Gauge(
    'bais_ap2_webhook_queue_size',
    'Number of AP2 webhooks waiting to be processed'
)

# Security Metrics
auth_failures = Counter(
    'bais_auth_failures_total',
    'Total number of authentication failures',
    ['auth_type', 'failure_reason']
)

ap2_webhook_signature_failures = Counter(
    'bais_ap2_webhook_signature_failures_total',
    'Total number of AP2 webhook signature validation failures'
)

# Business Metrics
active_businesses = Gauge(
    'bais_active_businesses_total',
    'Total number of active businesses in the system'
)

ap2_enabled_businesses = Gauge(
    'bais_ap2_enabled_businesses_total',
    'Total number of businesses with AP2 enabled'
)

# API Performance Metrics
api_request_duration = Histogram(
    'bais_api_request_duration_seconds',
    'Time taken to process API requests',
    ['method', 'endpoint', 'status_code'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
)

api_requests_total = Counter(
    'bais_api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status_code']
)

# System Information
system_info = Info(
    'bais_system_info',
    'System information for BAIS with AP2 integration'
)

# Set system information
system_info.info({
    'version': '1.0.0',
    'ap2_enabled': 'true',
    'environment': 'production'
})


def track_payment_workflow(business_id: str, payment_method_type: str = "unknown"):
    """Decorator to track payment workflow metrics"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Increment initiated counter
            payment_workflows_initiated.labels(
                business_id=business_id,
                payment_method_type=payment_method_type
            ).inc()
            
            try:
                result = await func(*args, **kwargs)
                
                # Increment completed counter
                payment_workflows_completed.labels(
                    business_id=business_id,
                    payment_method_type=payment_method_type
                ).inc()
                
                return result
                
            except Exception as e:
                # Increment failed counter
                failure_reason = type(e).__name__
                payment_workflows_failed.labels(
                    business_id=business_id,
                    failure_reason=failure_reason
                ).inc()
                
                logger.error(f"Payment workflow failed: {str(e)}", exc_info=True)
                raise
                
            finally:
                # Track duration
                duration = time.time() - start_time
                payment_workflow_duration.labels(
                    business_id=business_id,
                    workflow_step="complete"
                ).observe(duration)
        
        return wrapper
    return decorator


def track_webhook_processing(event_type: str):
    """Decorator to track webhook processing metrics"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Increment received counter
            ap2_webhooks_received.labels(event_type=event_type).inc()
            
            try:
                result = await func(*args, **kwargs)
                
                # Increment processed counter
                ap2_webhooks_processed.labels(event_type=event_type).inc()
                
                return result
                
            except Exception as e:
                # Increment failed counter
                failure_reason = type(e).__name__
                ap2_webhooks_failed.labels(
                    event_type=event_type,
                    failure_reason=failure_reason
                ).inc()
                
                logger.error(f"Webhook processing failed: {str(e)}", exc_info=True)
                raise
                
            finally:
                # Track processing duration
                duration = time.time() - start_time
                ap2_webhook_processing_duration.labels(
                    event_type=event_type
                ).observe(duration)
        
        return wrapper
    return decorator


def track_api_request(method: str, endpoint: str):
    """Decorator to track API request metrics"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            status_code = "500"  # Default to error
            
            try:
                result = await func(*args, **kwargs)
                status_code = "200"  # Success
                return result
                
            except Exception as e:
                if hasattr(e, 'status_code'):
                    status_code = str(e.status_code)
                raise
                
            finally:
                # Track request count and duration
                api_requests_total.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).inc()
                
                duration = time.time() - start_time
                api_request_duration.labels(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code
                ).observe(duration)
        
        return wrapper
    return decorator


class MetricsCollector:
    """Utility class for collecting and updating metrics"""
    
    @staticmethod
    def update_business_counts(active_count: int, ap2_enabled_count: int):
        """Update business count metrics"""
        active_businesses.set(active_count)
        ap2_enabled_businesses.set(ap2_enabled_count)
    
    @staticmethod
    def update_webhook_queue_size(size: int):
        """Update webhook queue size metric"""
        ap2_webhook_queue_size.set(size)
    
    @staticmethod
    def record_auth_failure(auth_type: str, reason: str):
        """Record authentication failure"""
        auth_failures.labels(auth_type=auth_type, failure_reason=reason).inc()
    
    @staticmethod
    def record_webhook_signature_failure():
        """Record webhook signature validation failure"""
        ap2_webhook_signature_failures.inc()
