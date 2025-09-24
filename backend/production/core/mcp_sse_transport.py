"""
MCP Server-Sent Events (SSE) Transport Implementation
Implements SSE transport for MCP protocol following best practices
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator, List, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sse_starlette import EventSourceResponse
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class MCPTransportType(Enum):
    """MCP transport types following protocol specification"""
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"


@dataclass
class MCPSSEEvent:
    """SSE event structure for MCP protocol"""
    event_type: str
    data: Dict[str, Any]
    id: Optional[str] = None
    retry: Optional[int] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_sse_format(self) -> str:
        """Convert to SSE format string"""
        lines = []
        
        if self.id:
            lines.append(f"id: {self.id}")
        
        if self.retry:
            lines.append(f"retry: {self.retry}")
        
        lines.append(f"event: {self.event_type}")
        lines.append(f"data: {json.dumps(self.data)}")
        lines.append("")  # Empty line to end event
        
        return "\n".join(lines)


@dataclass
class MCPSSEClient:
    """SSE client connection information"""
    client_id: str
    client_info: Dict[str, Any]
    connected_at: datetime = field(default_factory=datetime.now)
    last_ping: datetime = field(default_factory=datetime.now)
    subscriptions: Set[str] = field(default_factory=set)
    is_active: bool = True


class MCPSSETransportManager:
    """SSE transport manager following best practices"""
    
    def __init__(self, ping_interval_seconds: int = None, client_timeout_seconds: int = None):
        from .constants import SSEConnectionLimits
        self._ping_interval = ping_interval_seconds or SSEConnectionLimits.PING_INTERVAL_SECONDS
        self._client_timeout = client_timeout_seconds or SSEConnectionLimits.CLIENT_TIMEOUT_SECONDS
        self._clients: Dict[str, MCPSSEClient] = {}
        self._client_queues: Dict[str, asyncio.Queue] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the SSE transport manager"""
        self._cleanup_task = asyncio.create_task(self._cleanup_inactive_clients())
        logger.info("MCP SSE transport manager started")
    
    async def stop(self):
        """Stop the SSE transport manager"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all client connections
        async with self._lock:
            for client_id in list(self._clients.keys()):
                await self._disconnect_client(client_id)
        
        logger.info("MCP SSE transport manager stopped")
    
    async def connect_client(self, client_id: str, client_info: Dict[str, Any]) -> asyncio.Queue:
        """Connect a new SSE client"""
        async with self._lock:
            if client_id in self._clients:
                await self._disconnect_client(client_id)
            
            client = MCPSSEClient(
                client_id=client_id,
                client_info=client_info
            )
            
            from .constants import SSEConnectionLimits
            queue = asyncio.Queue(maxsize=SSEConnectionLimits.MAX_QUEUE_SIZE)  # Prevent memory issues
            
            self._clients[client_id] = client
            self._client_queues[client_id] = queue
            
            logger.info(f"SSE client connected: {client_id}")
            
            # Send connection confirmation
            await self._send_to_client(client_id, MCPSSEEvent(
                event_type="connected",
                data={
                    "client_id": client_id,
                    "server_time": datetime.now().isoformat(),
                    "protocol_version": "2025-06-18"
                },
                id=str(uuid.uuid4())
            ))
            
            return queue
    
    async def disconnect_client(self, client_id: str):
        """Disconnect an SSE client"""
        async with self._lock:
            await self._disconnect_client(client_id)
    
    async def _disconnect_client(self, client_id: str):
        """Internal method to disconnect client"""
        if client_id in self._clients:
            client = self._clients[client_id]
            client.is_active = False
            
            # Close the queue
            if client_id in self._client_queues:
                queue = self._client_queues[client_id]
                # Put a sentinel value to signal end
                try:
                    queue.put_nowait(None)
                except asyncio.QueueFull:
                    pass
                del self._client_queues[client_id]
            
            del self._clients[client_id]
            logger.info(f"SSE client disconnected: {client_id}")
    
    async def subscribe_client(self, client_id: str, subscription_type: str):
        """Subscribe client to specific event types"""
        async with self._lock:
            if client_id in self._clients:
                self._clients[client_id].subscriptions.add(subscription_type)
                logger.info(f"Client {client_id} subscribed to {subscription_type}")
    
    async def unsubscribe_client(self, client_id: str, subscription_type: str):
        """Unsubscribe client from specific event types"""
        async with self._lock:
            if client_id in self._clients:
                self._clients[client_id].subscriptions.discard(subscription_type)
                logger.info(f"Client {client_id} unsubscribed from {subscription_type}")
    
    async def broadcast_event(self, event: MCPSSEEvent, subscription_type: str = None):
        """Broadcast event to all subscribed clients"""
        async with self._lock:
            for client_id, client in self._clients.items():
                if not client.is_active:
                    continue
                
                # Check subscription filter
                if subscription_type and subscription_type not in client.subscriptions:
                    continue
                
                await self._send_to_client(client_id, event)
    
    async def send_to_client(self, client_id: str, event: MCPSSEEvent):
        """Send event to specific client"""
        async with self._lock:
            await self._send_to_client(client_id, event)
    
    async def _send_to_client(self, client_id: str, event: MCPSSEEvent):
        """Internal method to send event to client"""
        if client_id not in self._clients or not self._clients[client_id].is_active:
            return
        
        if client_id in self._client_queues:
            queue = self._client_queues[client_id]
            try:
                queue.put_nowait(event)
                self._clients[client_id].last_ping = datetime.now()
            except asyncio.QueueFull:
                logger.warning(f"Client {client_id} queue full, dropping event")
    
    async def get_client_info(self, client_id: str) -> Optional[MCPSSEClient]:
        """Get client information"""
        async with self._lock:
            return self._clients.get(client_id)
    
    async def get_active_clients_count(self) -> int:
        """Get count of active clients"""
        async with self._lock:
            return sum(1 for client in self._clients.values() if client.is_active)
    
    async def _cleanup_inactive_clients(self):
        """Background task to cleanup inactive clients"""
        while True:
            try:
                await asyncio.sleep(self._ping_interval)
                
                cutoff_time = datetime.now() - timedelta(seconds=self._client_timeout)
                inactive_clients = []
                
                async with self._lock:
                    for client_id, client in self._clients.items():
                        if client.last_ping < cutoff_time:
                            inactive_clients.append(client_id)
                
                for client_id in inactive_clients:
                    await self._disconnect_client(client_id)
                    logger.info(f"Cleaned up inactive client: {client_id}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in client cleanup task: {e}")


class MCPSSEHandler:
    """SSE handler for MCP protocol endpoints"""
    
    def __init__(self, transport_manager: MCPSSETransportManager):
        self._transport_manager = transport_manager
    
    async def handle_sse_connection(
        self, 
        request: Request, 
        client_id: str = None,
        subscriptions: List[str] = None
    ) -> EventSourceResponse:
        """Handle SSE connection request"""
        
        # Generate client ID if not provided
        if not client_id:
            client_id = str(uuid.uuid4())
        
        # Extract client info from request
        client_info = {
            "user_agent": request.headers.get("user-agent", ""),
            "remote_addr": request.client.host if request.client else "unknown",
            "subscriptions": subscriptions or []
        }
        
        # Connect client
        queue = await self._transport_manager.connect_client(client_id, client_info)
        
        # Subscribe to requested event types
        for subscription_type in (subscriptions or []):
            await self._transport_manager.subscribe_client(client_id, subscription_type)
        
        # Create SSE response
        async def event_generator():
            """Generate SSE events for the client"""
            try:
                # Send initial connection event
                yield MCPSSEEvent(
                    event_type="connected",
                    data={
                        "client_id": client_id,
                        "message": "Connected to MCP SSE transport",
                        "timestamp": datetime.now().isoformat()
                    },
                    id=str(uuid.uuid4())
                ).to_sse_format()
                
                # Process events from queue
                while True:
                    try:
                        # Wait for event with timeout
                        event = await asyncio.wait_for(queue.get(), timeout=30.0)
                        
                        # None indicates connection should close
                        if event is None:
                            break
                        
                        yield event.to_sse_format()
                        
                        # Mark task as done
                        queue.task_done()
                        
                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        yield MCPSSEEvent(
                            event_type="ping",
                            data={"timestamp": datetime.now().isoformat()},
                            id=str(uuid.uuid4())
                        ).to_sse_format()
                        
                    except Exception as e:
                        logger.error(f"Error in SSE event generator: {e}")
                        yield MCPSSEEvent(
                            event_type="error",
                            data={"error": str(e)},
                            id=str(uuid.uuid4())
                        ).to_sse_format()
                        break
            
            finally:
                # Cleanup on disconnect
                await self._transport_manager.disconnect_client(client_id)
        
        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
    
    async def handle_subscription_request(
        self, 
        client_id: str, 
        subscription_type: str, 
        action: str
    ) -> Dict[str, Any]:
        """Handle subscription request"""
        
        if action == "subscribe":
            await self._transport_manager.subscribe_client(client_id, subscription_type)
            return {
                "success": True,
                "message": f"Subscribed to {subscription_type}",
                "client_id": client_id
            }
        elif action == "unsubscribe":
            await self._transport_manager.unsubscribe_client(client_id, subscription_type)
            return {
                "success": True,
                "message": f"Unsubscribed from {subscription_type}",
                "client_id": client_id
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'subscribe' or 'unsubscribe'")


class MCPSSEIntegration:
    """Integration layer for MCP SSE with other protocols"""
    
    def __init__(self, transport_manager: MCPSSETransportManager):
        self._transport_manager = transport_manager
    
    async def notify_resource_update(self, resource_uri: str, update_data: Dict[str, Any]):
        """Notify clients of resource updates"""
        event = MCPSSEEvent(
            event_type="resource_updated",
            data={
                "resource_uri": resource_uri,
                "update_data": update_data,
                "timestamp": datetime.now().isoformat()
            },
            id=str(uuid.uuid4())
        )
        
        await self._transport_manager.broadcast_event(event, "resources")
    
    async def notify_tool_execution(self, tool_name: str, execution_result: Dict[str, Any]):
        """Notify clients of tool execution results"""
        event = MCPSSEEvent(
            event_type="tool_executed",
            data={
                "tool_name": tool_name,
                "execution_result": execution_result,
                "timestamp": datetime.now().isoformat()
            },
            id=str(uuid.uuid4())
        )
        
        await self._transport_manager.broadcast_event(event, "tools")
    
    async def notify_prompt_update(self, prompt_name: str, update_data: Dict[str, Any]):
        """Notify clients of prompt updates"""
        event = MCPSSEEvent(
            event_type="prompt_updated",
            data={
                "prompt_name": prompt_name,
                "update_data": update_data,
                "timestamp": datetime.now().isoformat()
            },
            id=str(uuid.uuid4())
        )
        
        await self._transport_manager.broadcast_event(event, "prompts")
    
    async def notify_a2a_task_update(self, task_id: str, task_status: str, task_data: Dict[str, Any]):
        """Notify clients of A2A task updates"""
        event = MCPSSEEvent(
            event_type="a2a_task_update",
            data={
                "task_id": task_id,
                "task_status": task_status,
                "task_data": task_data,
                "timestamp": datetime.now().isoformat()
            },
            id=str(uuid.uuid4())
        )
        
        await self._transport_manager.broadcast_event(event, "a2a_tasks")
    
    async def notify_ap2_payment_update(self, payment_id: str, payment_status: str, payment_data: Dict[str, Any]):
        """Notify clients of AP2 payment updates"""
        event = MCPSSEEvent(
            event_type="ap2_payment_update",
            data={
                "payment_id": payment_id,
                "payment_status": payment_status,
                "payment_data": payment_data,
                "timestamp": datetime.now().isoformat()
            },
            id=str(uuid.uuid4())
        )
        
        await self._transport_manager.broadcast_event(event, "ap2_payments")


def create_mcp_sse_routes(app: FastAPI, transport_manager: MCPSSETransportManager):
    """Create MCP SSE routes for FastAPI application"""
    
    sse_handler = MCPSSEHandler(transport_manager)
    sse_integration = MCPSSEIntegration(transport_manager)
    
    @app.get("/mcp/sse/connect")
    async def connect_sse(
        request: Request,
        subscriptions: str = None
    ):
        """Connect to MCP SSE transport"""
        subscription_list = subscriptions.split(",") if subscriptions else []
        return await sse_handler.handle_sse_connection(request, subscriptions=subscription_list)
    
    @app.post("/mcp/sse/subscribe")
    async def subscribe_to_events(
        client_id: str,
        subscription_type: str,
        action: str = "subscribe"
    ):
        """Subscribe/unsubscribe to specific event types"""
        return await sse_handler.handle_subscription_request(client_id, subscription_type, action)
    
    @app.get("/mcp/sse/clients")
    async def get_active_clients():
        """Get information about active SSE clients"""
        return {
            "active_clients": await transport_manager.get_active_clients_count(),
            "timestamp": datetime.now().isoformat()
        }
    
    @app.post("/mcp/sse/broadcast")
    async def broadcast_event(
        event_type: str,
        data: Dict[str, Any],
        subscription_type: str = None
    ):
        """Broadcast event to all subscribed clients (admin endpoint)"""
        event = MCPSSEEvent(
            event_type=event_type,
            data=data,
            id=str(uuid.uuid4())
        )
        
        await transport_manager.broadcast_event(event, subscription_type)
        
        return {
            "success": True,
            "message": f"Event {event_type} broadcasted",
            "event_id": event.id
        }
    
    return sse_integration


# Global SSE transport manager instance
_sse_transport_manager: Optional[MCPSSETransportManager] = None


def get_sse_transport_manager() -> MCPSSETransportManager:
    """Get global SSE transport manager instance"""
    global _sse_transport_manager
    if _sse_transport_manager is None:
        _sse_transport_manager = MCPSSETransportManager()
    return _sse_transport_manager


@asynccontextmanager
async def sse_transport_lifecycle():
    """Context manager for SSE transport lifecycle"""
    manager = get_sse_transport_manager()
    await manager.start()
    
    try:
        yield manager
    finally:
        await manager.stop()


if __name__ == "__main__":
    # Example usage
    async def main():
        from fastapi import FastAPI
        
        app = FastAPI()
        manager = get_sse_transport_manager()
        
        # Create SSE routes
        sse_integration = create_mcp_sse_routes(app, manager)
        
        # Start transport manager
        await manager.start()
        
        # Simulate some events
        await asyncio.sleep(1)
        
        # Broadcast test event
        await manager.broadcast_event(MCPSSEEvent(
            event_type="test",
            data={"message": "Hello from MCP SSE!"},
            id=str(uuid.uuid4())
        ))
        
        # Wait a bit then stop
        await asyncio.sleep(5)
        await manager.stop()
        
        print("SSE transport example completed")
    
    asyncio.run(main())
