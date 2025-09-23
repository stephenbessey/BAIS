"""
Distributed Tracing Implementation
Provides request tracing across A2A and AP2 protocols for observability
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context variables for tracing
trace_context: ContextVar[Optional['TraceContext']] = ContextVar('trace_context', default=None)
span_context: ContextVar[Optional['Span']] = ContextVar('span_context', default=None)


class TraceStatus(Enum):
    """Trace and span status"""
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class SpanKind(Enum):
    """Type of span in the trace"""
    CLIENT = "client"
    SERVER = "server"
    INTERNAL = "internal"
    PRODUCER = "producer"
    CONSUMER = "consumer"


@dataclass
class TraceContext:
    """Distributed trace context"""
    trace_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)


@dataclass
class Span:
    """Individual span in a distributed trace"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    kind: SpanKind
    start_time: datetime
    end_time: Optional[datetime] = None
    status: TraceStatus = TraceStatus.OK
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    links: List[Dict[str, str]] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class Trace:
    """Complete distributed trace"""
    trace_id: str
    root_span_id: str
    spans: List[Span] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    service_name: str = "bais-service"
    tags: Dict[str, str] = field(default_factory=dict)


class SpanExporter:
    """Interface for exporting spans to external systems"""
    
    async def export_spans(self, spans: List[Span]) -> None:
        """Export spans to external system"""
        raise NotImplementedError


class ConsoleSpanExporter(SpanExporter):
    """Console exporter for development/testing"""
    
    async def export_spans(self, spans: List[Span]) -> None:
        """Export spans to console"""
        for span in spans:
            duration = (span.end_time - span.start_time).total_seconds() * 1000 if span.end_time else 0
            logger.info(
                f"TRACE: {span.trace_id} | SPAN: {span.span_id} | {span.name} | "
                f"{span.status.value} | {duration:.2f}ms | {span.attributes}"
            )


class JaegerSpanExporter(SpanExporter):
    """Jaeger exporter for production tracing"""
    
    def __init__(self, endpoint: str = "http://localhost:14268/api/traces"):
        self.endpoint = endpoint
        self._http_client = None
    
    async def _get_client(self):
        """Get HTTP client for Jaeger"""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient()
        return self._http_client
    
    async def export_spans(self, spans: List[Span]) -> None:
        """Export spans to Jaeger"""
        try:
            client = await self._get_client()
            
            # Convert spans to Jaeger format
            jaeger_spans = []
            for span in spans:
                jaeger_span = {
                    "traceId": span.trace_id,
                    "spanId": span.span_id,
                    "parentSpanId": span.parent_span_id,
                    "operationName": span.name,
                    "startTime": int(span.start_time.timestamp() * 1000000),  # microseconds
                    "duration": int((span.end_time - span.start_time).total_seconds() * 1000000) if span.end_time else 0,
                    "tags": [
                        {"key": "span.kind", "value": span.kind.value, "type": "string"},
                        {"key": "status.code", "value": span.status.value, "type": "string"}
                    ],
                    "logs": []
                }
                
                # Add attributes as tags
                for key, value in span.attributes.items():
                    jaeger_span["tags"].append({
                        "key": key,
                        "value": str(value),
                        "type": "string"
                    })
                
                # Add events as logs
                for event in span.events:
                    jaeger_span["logs"].append({
                        "timestamp": int(event["timestamp"].timestamp() * 1000000),
                        "fields": [{"key": "event", "value": event["name"], "type": "string"}]
                    })
                
                jaeger_spans.append(jaeger_span)
            
            # Send to Jaeger
            payload = {"spans": jaeger_spans}
            await client.post(self.endpoint, json=payload)
            
        except Exception as e:
            logger.error(f"Failed to export spans to Jaeger: {e}")


class Tracer:
    """Main tracer for creating and managing spans"""
    
    def __init__(self, service_name: str = "bais-service", exporter: SpanExporter = None):
        self.service_name = service_name
        self.exporter = exporter or ConsoleSpanExporter()
        self._active_spans: Dict[str, Span] = {}
        self._completed_traces: List[Trace] = []
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """Start a new span"""
        # Get current trace context
        trace_ctx = trace_context.get()
        if not trace_ctx:
            # Create new trace
            trace_id = self._generate_trace_id()
            trace_ctx = TraceContext(trace_id=trace_id)
            trace_context.set(trace_ctx)
        else:
            trace_id = trace_ctx.trace_id
        
        # Generate span ID
        span_id = self._generate_span_id()
        
        # Create span
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id or trace_ctx.parent_span_id,
            name=name,
            kind=kind,
            start_time=datetime.utcnow(),
            attributes=attributes or {}
        )
        
        # Store active span
        self._active_spans[span_id] = span
        
        # Set span context
        span_context.set(span)
        
        return span
    
    def end_span(self, span_id: str, status: TraceStatus = TraceStatus.OK, error_message: Optional[str] = None):
        """End a span"""
        span = self._active_spans.get(span_id)
        if not span:
            logger.warning(f"Span {span_id} not found")
            return
        
        span.end_time = datetime.utcnow()
        span.status = status
        if error_message:
            span.error_message = error_message
        
        # Remove from active spans
        del self._active_spans[span_id]
        
        # Add to completed traces
        await self._add_span_to_trace(span)
    
    async def _add_span_to_trace(self, span: Span):
        """Add completed span to trace"""
        # Find existing trace or create new one
        trace = None
        for t in self._completed_traces:
            if t.trace_id == span.trace_id:
                trace = t
                break
        
        if not trace:
            trace = Trace(
                trace_id=span.trace_id,
                root_span_id=span.span_id,
                service_name=self.service_name
            )
            self._completed_traces.append(trace)
        
        trace.spans.append(span)
        
        # If this is the root span, mark trace as complete
        if span.span_id == trace.root_span_id and span.end_time:
            trace.end_time = span.end_time
            await self._export_trace(trace)
    
    async def _export_trace(self, trace: Trace):
        """Export completed trace"""
        try:
            await self.exporter.export_spans(trace.spans)
        except Exception as e:
            logger.error(f"Failed to export trace {trace.trace_id}: {e}")
    
    def add_span_event(self, span_id: str, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to a span"""
        span = self._active_spans.get(span_id)
        if not span:
            logger.warning(f"Span {span_id} not found")
            return
        
        event = {
            "name": name,
            "timestamp": datetime.utcnow(),
            "attributes": attributes or {}
        }
        span.events.append(event)
    
    def set_span_attribute(self, span_id: str, key: str, value: Any):
        """Set an attribute on a span"""
        span = self._active_spans.get(span_id)
        if not span:
            logger.warning(f"Span {span_id} not found")
            return
        
        span.attributes[key] = value
    
    def _generate_trace_id(self) -> str:
        """Generate a unique trace ID"""
        return str(uuid.uuid4()).replace('-', '')
    
    def _generate_span_id(self) -> str:
        """Generate a unique span ID"""
        return str(uuid.uuid4()).replace('-', '')
    
    def get_current_span(self) -> Optional[Span]:
        """Get the current active span"""
        return span_context.get()
    
    def get_current_trace_id(self) -> Optional[str]:
        """Get the current trace ID"""
        ctx = trace_context.get()
        return ctx.trace_id if ctx else None


# Global tracer instance
_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """Get the global tracer instance"""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer


def set_tracer(tracer: Tracer):
    """Set the global tracer instance"""
    global _tracer
    _tracer = tracer


# Context managers for tracing
class trace_span:
    """Context manager for creating and managing spans"""
    
    def __init__(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.kind = kind
        self.attributes = attributes
        self.span = None
        self.tracer = get_tracer()
    
    async def __aenter__(self):
        self.span = self.tracer.start_span(
            name=self.name,
            kind=self.kind,
            attributes=self.attributes
        )
        return self.span
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.span:
            status = TraceStatus.ERROR if exc_type else TraceStatus.OK
            error_message = str(exc_val) if exc_val else None
            self.tracer.end_span(self.span.span_id, status, error_message)


# Protocol-specific tracing utilities
class A2ATracer:
    """A2A protocol specific tracing utilities"""
    
    @staticmethod
    async def trace_agent_discovery(capabilities: List[str], location: str = None):
        """Trace agent discovery operations"""
        attributes = {
            "a2a.operation": "agent_discovery",
            "a2a.capabilities": capabilities,
            "a2a.location": location
        }
        return trace_span("a2a.agent_discovery", SpanKind.CLIENT, attributes)
    
    @staticmethod
    async def trace_task_execution(task_id: str, capability: str):
        """Trace A2A task execution"""
        attributes = {
            "a2a.operation": "task_execution",
            "a2a.task_id": task_id,
            "a2a.capability": capability
        }
        return trace_span("a2a.task_execution", SpanKind.SERVER, attributes)


class AP2Tracer:
    """AP2 protocol specific tracing utilities"""
    
    @staticmethod
    async def trace_payment_workflow(workflow_id: str, business_id: str, amount: float):
        """Trace AP2 payment workflow"""
        attributes = {
            "ap2.operation": "payment_workflow",
            "ap2.workflow_id": workflow_id,
            "ap2.business_id": business_id,
            "ap2.amount": amount
        }
        return trace_span("ap2.payment_workflow", SpanKind.INTERNAL, attributes)
    
    @staticmethod
    async def trace_mandate_creation(mandate_type: str, user_id: str, business_id: str):
        """Trace AP2 mandate creation"""
        attributes = {
            "ap2.operation": "mandate_creation",
            "ap2.mandate_type": mandate_type,
            "ap2.user_id": user_id,
            "ap2.business_id": business_id
        }
        return trace_span("ap2.mandate_creation", SpanKind.CLIENT, attributes)
