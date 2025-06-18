import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional
import websockets
import ssl
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import time
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

class EventType(Enum):
    AGENT_STATUS_UPDATE = "agent_status_update"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_PROGRESS = "workflow_progress"
    WORKFLOW_COMPLETED = "workflow_completed"
    SECURITY_ALERT = "security_alert"
    PERFORMANCE_METRIC = "performance_metric"
    SYSTEM_HEALTH = "system_health"
    USER_ACTIVITY = "user_activity"
    ERROR_OCCURRED = "error_occurred"

@dataclass
class RealtimeEvent:
    event_id: str
    event_type: EventType
    timestamp: datetime
    data: Dict
    user_id: Optional[str] = None
    agent_type: Optional[str] = None
    priority: int = 1  # 1=low, 5=critical

class RealtimeConnection:
    """Represents a WebSocket connection with subscription preferences"""
    
    def __init__(self, websocket, user_id: str):
        self.websocket = websocket
        self.user_id = user_id
        self.connection_id = str(uuid.uuid4())
        self.connected_at = datetime.now()
        self.last_ping = datetime.now()
        self.subscriptions: Set[EventType] = set()
        self.is_admin = False
        self.rate_limit_counter = 0
        self.last_rate_limit_reset = time.time()

class RealtimeMonitoringServer:
    """
    Advanced real-time monitoring server for AI Chief of Staff
    
    Features:
    - Real-time WebSocket connections for all agent activities
    - Multi-channel subscriptions with filtering
    - Advanced performance monitoring and analytics
    - Security event streaming
    - Auto-scaling WebSocket management
    - Historical data streaming
    - Rate limiting and abuse protection
    - Admin dashboard streaming
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.connections: Dict[str, RealtimeConnection] = {}
        self.event_history: List[RealtimeEvent] = []
        self.event_queue = asyncio.Queue()
        
        # Performance metrics
        self.metrics = {
            'total_connections': 0,
            'active_connections': 0,
            'events_sent': 0,
            'events_per_second': 0,
            'data_throughput': 0,
            'connection_errors': 0,
            'last_metric_reset': time.time()
        }
        
        # Rate limiting
        self.max_events_per_second_per_user = 50
        self.max_connections_per_user = 5
        
        # Event filtering and aggregation
        self.event_aggregators = defaultdict(list)
        self.batch_size = 10
        self.batch_timeout = 1.0  # seconds
        
        # Health monitoring
        self.server_health = {
            'status': 'starting',
            'uptime': 0,
            'memory_usage': 0,
            'cpu_usage': 0,
            'connection_quality': 'good'
        }
        
        # Background tasks
        self.cleanup_task = None
        self.metrics_task = None
        self.health_task = None
        
        logger.info(f"🔴 Real-time Monitoring Server initializing on {host}:{port}")

    async def start_server(self):
        """Start the WebSocket server with production configurations"""
        
        try:
            # SSL configuration for production
            ssl_context = None
            if hasattr(self, 'ssl_cert_path') and hasattr(self, 'ssl_key_path'):
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(self.ssl_cert_path, self.ssl_key_path)
            
            # Start WebSocket server
            server = await websockets.serve(
                self.handle_connection,
                self.host,
                self.port,
                ssl=ssl_context,
                ping_interval=30,
                ping_timeout=10,
                max_size=10**6,  # 1MB max message size
                max_queue=100,   # Max queued messages
                compression="deflate"
            )
            
            # Start background tasks
            self.cleanup_task = asyncio.create_task(self.cleanup_connections())
            self.metrics_task = asyncio.create_task(self.update_metrics())
            self.health_task = asyncio.create_task(self.monitor_health())
            
            # Start event processing
            asyncio.create_task(self.process_event_queue())
            
            self.server_health['status'] = 'running'
            logger.info(f"🔴 Real-time Monitoring Server started on {self.host}:{self.port}")
            
            # Keep server running
            await server.wait_closed()
            
        except Exception as e:
            logger.error(f"Failed to start real-time server: {e}")
            self.server_health['status'] = 'error'
            raise

    async def handle_connection(self, websocket, path):
        """Handle new WebSocket connection with authentication and setup"""
        
        connection_id = None
        try:
            # Extract authentication from query params or headers
            user_id = await self.authenticate_connection(websocket, path)
            if not user_id:
                await websocket.close(4001, "Authentication required")
                return
            
            # Check connection limits
            user_connections = [c for c in self.connections.values() if c.user_id == user_id]
            if len(user_connections) >= self.max_connections_per_user:
                await websocket.close(4002, "Connection limit exceeded")
                return
            
            # Create connection object
            connection = RealtimeConnection(websocket, user_id)
            connection_id = connection.connection_id
            self.connections[connection_id] = connection
            self.metrics['total_connections'] += 1
            self.metrics['active_connections'] += 1
            
            logger.info(f"🔗 New real-time connection: {user_id} ({connection_id})")
            
            # Send welcome message with capabilities
            await self.send_to_connection(connection, {
                'type': 'connection_established',
                'connection_id': connection_id,
                'server_capabilities': {
                    'event_types': [e.value for e in EventType],
                    'max_rate': self.max_events_per_second_per_user,
                    'batch_support': True,
                    'filtering_support': True
                },
                'server_health': self.server_health
            })
            
            # Handle messages from client
            async for message in websocket:
                await self.handle_client_message(connection, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔗 Connection closed: {connection_id}")
        except Exception as e:
            logger.error(f"Connection error for {connection_id}: {e}")
            self.metrics['connection_errors'] += 1
        finally:
            # Cleanup connection
            if connection_id and connection_id in self.connections:
                del self.connections[connection_id]
                self.metrics['active_connections'] -= 1

    async def authenticate_connection(self, websocket, path) -> Optional[str]:
        """Authenticate WebSocket connection using token or session"""
        
        try:
            # Extract auth token from query parameters
            import urllib.parse
            parsed = urllib.parse.urlparse(path)
            query_params = urllib.parse.parse_qs(parsed.query)
            
            auth_token = query_params.get('token', [None])[0]
            if not auth_token:
                return None
            
            # Validate token (integrate with your auth system)
            user_id = await self.validate_auth_token(auth_token)
            return user_id
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    async def validate_auth_token(self, token: str) -> Optional[str]:
        """Validate authentication token and return user_id"""
        
        # This would integrate with your actual authentication system
        # For now, return a mock user_id if token is valid format
        if token and len(token) > 10:
            return f"user_{token[:8]}"
        return None

    async def handle_client_message(self, connection: RealtimeConnection, message: str):
        """Handle messages from client (subscription management, etc.)"""
        
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'subscribe':
                # Subscribe to specific event types
                event_types = data.get('event_types', [])
                for event_type_str in event_types:
                    try:
                        event_type = EventType(event_type_str)
                        connection.subscriptions.add(event_type)
                    except ValueError:
                        pass
                
                await self.send_to_connection(connection, {
                    'type': 'subscription_confirmed',
                    'subscriptions': [e.value for e in connection.subscriptions]
                })
                
            elif message_type == 'unsubscribe':
                # Unsubscribe from event types
                event_types = data.get('event_types', [])
                for event_type_str in event_types:
                    try:
                        event_type = EventType(event_type_str)
                        connection.subscriptions.discard(event_type)
                    except ValueError:
                        pass
                        
            elif message_type == 'ping':
                # Update last ping time
                connection.last_ping = datetime.now()
                await self.send_to_connection(connection, {'type': 'pong'})
                
            elif message_type == 'get_history':
                # Send recent event history
                hours_back = data.get('hours', 1)
                await self.send_event_history(connection, hours_back)
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from {connection.connection_id}")
        except Exception as e:
            logger.error(f"Error handling client message: {e}")

    async def send_to_connection(self, connection: RealtimeConnection, data: Dict):
        """Send data to a specific connection with rate limiting"""
        
        try:
            # Rate limiting check
            current_time = time.time()
            if current_time - connection.last_rate_limit_reset > 1.0:
                connection.rate_limit_counter = 0
                connection.last_rate_limit_reset = current_time
            
            if connection.rate_limit_counter >= self.max_events_per_second_per_user:
                logger.warning(f"Rate limit exceeded for {connection.user_id}")
                return False
            
            # Send message
            message = json.dumps(data, default=str)
            await connection.websocket.send(message)
            
            connection.rate_limit_counter += 1
            self.metrics['events_sent'] += 1
            self.metrics['data_throughput'] += len(message)
            
            return True
            
        except websockets.exceptions.ConnectionClosed:
            # Connection closed, will be cleaned up by cleanup task
            return False
        except Exception as e:
            logger.error(f"Error sending to connection {connection.connection_id}: {e}")
            return False

    async def broadcast_event(self, event: RealtimeEvent):
        """Broadcast event to all subscribed connections"""
        
        try:
            # Add to event queue for processing
            await self.event_queue.put(event)
            
            # Add to history
            self.event_history.append(event)
            
            # Limit history size
            if len(self.event_history) > 1000:
                self.event_history = self.event_history[-800:]  # Keep last 800 events
                
        except Exception as e:
            logger.error(f"Error broadcasting event: {e}")

    async def process_event_queue(self):
        """Process events from queue and send to subscribers"""
        
        while True:
            try:
                # Batch processing for efficiency
                events = []
                timeout = False
                
                # Collect batch of events or timeout
                try:
                    event = await asyncio.wait_for(self.event_queue.get(), timeout=self.batch_timeout)
                    events.append(event)
                    
                    # Try to get more events for batching
                    for _ in range(self.batch_size - 1):
                        try:
                            event = self.event_queue.get_nowait()
                            events.append(event)
                        except asyncio.QueueEmpty:
                            break
                            
                except asyncio.TimeoutError:
                    timeout = True
                
                if events:
                    await self._send_events_to_subscribers(events)
                    
                # Small delay if no events to prevent tight loop
                if timeout and not events:
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error processing event queue: {e}")
                await asyncio.sleep(1)

    async def _send_events_to_subscribers(self, events: List[RealtimeEvent]):
        """Send events to all subscribed connections"""
        
        for connection in list(self.connections.values()):
            try:
                # Filter events based on subscriptions
                relevant_events = [
                    event for event in events
                    if (not connection.subscriptions or event.event_type in connection.subscriptions)
                    and (connection.is_admin or event.user_id == connection.user_id or event.user_id is None)
                ]
                
                if relevant_events:
                    # Send as batch if multiple events
                    if len(relevant_events) == 1:
                        await self.send_to_connection(connection, {
                            'type': 'event',
                            'event': asdict(relevant_events[0])
                        })
                    else:
                        await self.send_to_connection(connection, {
                            'type': 'event_batch',
                            'events': [asdict(event) for event in relevant_events]
                        })
                        
            except Exception as e:
                logger.error(f"Error sending events to connection {connection.connection_id}: {e}")

    async def send_event_history(self, connection: RealtimeConnection, hours_back: int):
        """Send historical events to a connection"""
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            relevant_events = [
                event for event in self.event_history
                if (event.timestamp > cutoff_time and
                    (not connection.subscriptions or event.event_type in connection.subscriptions) and
                    (connection.is_admin or event.user_id == connection.user_id or event.user_id is None))
            ]
            
            # Send in chunks to avoid overwhelming connection
            chunk_size = 50
            for i in range(0, len(relevant_events), chunk_size):
                chunk = relevant_events[i:i + chunk_size]
                await self.send_to_connection(connection, {
                    'type': 'history_chunk',
                    'events': [asdict(event) for event in chunk],
                    'chunk_info': {
                        'chunk_number': i // chunk_size + 1,
                        'total_chunks': (len(relevant_events) + chunk_size - 1) // chunk_size,
                        'total_events': len(relevant_events)
                    }
                })
                
                # Small delay between chunks
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error sending history to {connection.connection_id}: {e}")

    async def cleanup_connections(self):
        """Periodic cleanup of dead connections"""
        
        while True:
            try:
                current_time = datetime.now()
                dead_connections = []
                
                for connection_id, connection in self.connections.items():
                    # Check for stale connections
                    if (current_time - connection.last_ping).total_seconds() > 60:
                        dead_connections.append(connection_id)
                
                # Remove dead connections
                for connection_id in dead_connections:
                    try:
                        await self.connections[connection_id].websocket.close()
                    except:
                        pass
                    del self.connections[connection_id]
                    self.metrics['active_connections'] -= 1
                    logger.info(f"🔗 Cleaned up dead connection: {connection_id}")
                
                await asyncio.sleep(30)  # Cleanup every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in connection cleanup: {e}")
                await asyncio.sleep(30)

    async def update_metrics(self):
        """Update performance metrics"""
        
        while True:
            try:
                current_time = time.time()
                time_delta = current_time - self.metrics['last_metric_reset']
                
                if time_delta > 0:
                    self.metrics['events_per_second'] = self.metrics['events_sent'] / time_delta
                
                # Reset counters
                self.metrics['events_sent'] = 0
                self.metrics['data_throughput'] = 0
                self.metrics['last_metric_reset'] = current_time
                
                # Broadcast metrics to admin connections
                admin_connections = [c for c in self.connections.values() if c.is_admin]
                if admin_connections:
                    metrics_event = RealtimeEvent(
                        event_id=str(uuid.uuid4()),
                        event_type=EventType.PERFORMANCE_METRIC,
                        timestamp=datetime.now(),
                        data=self.metrics.copy()
                    )
                    
                    for connection in admin_connections:
                        await self.send_to_connection(connection, {
                            'type': 'event',
                            'event': asdict(metrics_event)
                        })
                
                await asyncio.sleep(10)  # Update every 10 seconds
                
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                await asyncio.sleep(10)

    async def monitor_health(self):
        """Monitor server health and broadcast health updates"""
        
        while True:
            try:
                import psutil
                
                # Update health metrics
                self.server_health.update({
                    'status': 'running',
                    'uptime': time.time() - self.metrics['last_metric_reset'],
                    'memory_usage': psutil.virtual_memory().percent,
                    'cpu_usage': psutil.cpu_percent(interval=1),
                    'active_connections': self.metrics['active_connections'],
                    'events_per_second': self.metrics['events_per_second']
                })
                
                # Determine connection quality
                if self.metrics['connection_errors'] > 10:
                    self.server_health['connection_quality'] = 'poor'
                elif self.metrics['connection_errors'] > 5:
                    self.server_health['connection_quality'] = 'fair'
                else:
                    self.server_health['connection_quality'] = 'good'
                
                # Broadcast health update
                health_event = RealtimeEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=EventType.SYSTEM_HEALTH,
                    timestamp=datetime.now(),
                    data=self.server_health.copy()
                )
                
                await self.broadcast_event(health_event)
                
                await asyncio.sleep(30)  # Health check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring health: {e}")
                self.server_health['status'] = 'degraded'
                await asyncio.sleep(30)

    # Event creation helpers for integration with agents
    
    def create_agent_status_event(self, agent_type: str, status: str, data: Dict, user_id: str = None) -> RealtimeEvent:
        """Create agent status update event"""
        return RealtimeEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.AGENT_STATUS_UPDATE,
            timestamp=datetime.now(),
            data={
                'agent_type': agent_type,
                'status': status,
                'details': data
            },
            user_id=user_id,
            agent_type=agent_type
        )

    def create_workflow_event(self, event_type: EventType, workflow_id: str, data: Dict, user_id: str = None) -> RealtimeEvent:
        """Create workflow-related event"""
        return RealtimeEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(),
            data={
                'workflow_id': workflow_id,
                **data
            },
            user_id=user_id
        )

    def create_security_event(self, threat_level: str, description: str, data: Dict, user_id: str = None) -> RealtimeEvent:
        """Create security alert event"""
        return RealtimeEvent(
            event_id=str(uuid.uuid4()),
            event_type=EventType.SECURITY_ALERT,
            timestamp=datetime.now(),
            data={
                'threat_level': threat_level,
                'description': description,
                'details': data
            },
            user_id=user_id,
            priority=5 if threat_level == 'CRITICAL' else 3
        )

    async def get_server_stats(self) -> Dict:
        """Get comprehensive server statistics"""
        
        return {
            'server_health': self.server_health,
            'metrics': self.metrics,
            'connection_stats': {
                'total_connections': len(self.connections),
                'user_distribution': {},
                'subscription_stats': {}
            },
            'event_stats': {
                'total_events_in_history': len(self.event_history),
                'events_by_type': {},
                'queue_size': self.event_queue.qsize()
            }
        }

# Global instance for easy integration
realtime_server = RealtimeMonitoringServer() 