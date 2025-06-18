import asyncio
import hashlib
import hmac
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from enum import Enum
import redis
import ipaddress
from collections import defaultdict
import uuid

logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class SecurityEventType(Enum):
    AUTHENTICATION_FAILURE = "auth_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_EXFILTRATION_ATTEMPT = "data_exfiltration"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    AGENT_ABUSE = "agent_abuse"

@dataclass
class SecurityEvent:
    event_id: str
    user_id: Optional[str]
    ip_address: str
    event_type: SecurityEventType
    threat_level: ThreatLevel
    description: str
    metadata: Dict
    timestamp: datetime
    resolved: bool = False

@dataclass
class RateLimitRule:
    name: str
    endpoint_pattern: str
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_allowance: int
    user_specific: bool = True
    ip_specific: bool = True

class AdvancedSecurityManager:
    """
    Enterprise-grade security manager for AI Chief of Staff
    
    Features:
    - Advanced rate limiting with burst protection
    - Real-time threat detection and response
    - Comprehensive audit logging
    - IP-based and user-based restrictions
    - Anomaly detection for user behavior
    - Agent-specific security controls
    - Data loss prevention (DLP)
    - Compliance monitoring (SOC2, GDPR)
    """
    
    def __init__(self, redis_url: str = None):
        # Redis for rate limiting and session management
        self.redis_client = redis.Redis.from_url(redis_url or 'redis://localhost:6379/0')
        
        # Security event tracking
        self.security_events: List[SecurityEvent] = []
        self.blocked_ips: Set[str] = set()
        self.suspicious_users: Dict[str, Dict] = {}
        
        # Rate limiting configuration
        self.rate_limit_rules = self._initialize_rate_limits()
        self.user_activity_tracker = defaultdict(list)
        self.ip_activity_tracker = defaultdict(list)
        
        # Security thresholds
        self.max_failed_logins = 5
        self.suspicious_activity_threshold = 10
        self.anomaly_detection_window = timedelta(hours=1)
        self.auto_block_duration = timedelta(hours=24)
        
        # Agent-specific security
        self.agent_rate_limits = {
            'autonomous_email': {'per_hour': 20, 'per_day': 100},
            'partnership_workflow': {'per_hour': 5, 'per_day': 20},
            'mcp_connector': {'per_hour': 50, 'per_day': 200},
            'intelligence_analysis': {'per_hour': 30, 'per_day': 150}
        }
        
        # DLP patterns
        self.dlp_patterns = {
            'credit_card': r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'api_key': r'sk-[a-zA-Z0-9]{32,}',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        }
        
        logger.info("🔒 Advanced Security Manager initialized with enterprise controls")

    def _initialize_rate_limits(self) -> List[RateLimitRule]:
        """Initialize rate limiting rules for different endpoints"""
        
        return [
            # Authentication endpoints
            RateLimitRule(
                name="auth_login",
                endpoint_pattern="/auth/*",
                requests_per_minute=10,
                requests_per_hour=30,
                requests_per_day=100,
                burst_allowance=3,
                ip_specific=True,
                user_specific=False
            ),
            
            # Agent endpoints - high security
            RateLimitRule(
                name="agent_autonomous",
                endpoint_pattern="/api/agents/email/process-autonomous",
                requests_per_minute=5,
                requests_per_hour=20,
                requests_per_day=100,
                burst_allowance=2,
                user_specific=True
            ),
            
            RateLimitRule(
                name="agent_intelligence",
                endpoint_pattern="/api/agents/intelligence/*",
                requests_per_minute=10,
                requests_per_hour=30,
                requests_per_day=150,
                burst_allowance=3,
                user_specific=True
            ),
            
            RateLimitRule(
                name="agent_partnership",
                endpoint_pattern="/api/agents/partnership/*",
                requests_per_minute=2,
                requests_per_hour=5,
                requests_per_day=20,
                burst_allowance=1,
                user_specific=True
            ),
            
            # MCP connectors - external data access
            RateLimitRule(
                name="mcp_connectors",
                endpoint_pattern="/api/agents/mcp/*",
                requests_per_minute=15,
                requests_per_hour=50,
                requests_per_day=200,
                burst_allowance=5,
                user_specific=True
            ),
            
            # General API endpoints
            RateLimitRule(
                name="general_api",
                endpoint_pattern="/api/*",
                requests_per_minute=60,
                requests_per_hour=1000,
                requests_per_day=5000,
                burst_allowance=10,
                user_specific=True
            )
        ]

    async def check_rate_limit(self, user_id: str, ip_address: str, endpoint: str) -> Dict[str, any]:
        """
        Check if request is within rate limits using advanced sliding window algorithm
        
        Returns:
            Dict with 'allowed' boolean and rate limit info
        """
        
        try:
            current_time = time.time()
            
            # Find applicable rate limit rule
            rule = self._get_rate_limit_rule(endpoint)
            if not rule:
                return {'allowed': True, 'rule': 'no_limit'}
            
            # Check user-specific limits
            if rule.user_specific and user_id:
                user_key = f"rate_limit:user:{user_id}:{rule.name}"
                user_allowed, user_info = await self._check_sliding_window_limit(
                    user_key, rule, current_time
                )
                if not user_allowed:
                    await self._log_security_event(
                        user_id, ip_address, SecurityEventType.RATE_LIMIT_EXCEEDED,
                        ThreatLevel.MEDIUM, f"User rate limit exceeded for {endpoint}",
                        {'rule': rule.name, 'limit_info': user_info}
                    )
                    return {'allowed': False, 'reason': 'user_rate_limit', 'info': user_info}
            
            # Check IP-specific limits
            if rule.ip_specific:
                ip_key = f"rate_limit:ip:{ip_address}:{rule.name}"
                ip_allowed, ip_info = await self._check_sliding_window_limit(
                    ip_key, rule, current_time
                )
                if not ip_allowed:
                    await self._log_security_event(
                        user_id, ip_address, SecurityEventType.RATE_LIMIT_EXCEEDED,
                        ThreatLevel.HIGH, f"IP rate limit exceeded for {endpoint}",
                        {'rule': rule.name, 'limit_info': ip_info}
                    )
                    return {'allowed': False, 'reason': 'ip_rate_limit', 'info': ip_info}
            
            return {'allowed': True, 'rule': rule.name}
            
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # Fail secure - allow with warning
            return {'allowed': True, 'error': str(e)}

    async def _check_sliding_window_limit(self, key: str, rule: RateLimitRule, current_time: float) -> tuple[bool, Dict]:
        """Check sliding window rate limit with burst protection"""
        
        # Time windows
        minute_window = 60
        hour_window = 3600
        day_window = 86400
        
        # Get request timestamps from Redis
        requests = self.redis_client.zrangebyscore(
            key, current_time - day_window, current_time
        )
        
        # Count requests in each window
        minute_requests = len([r for r in requests if float(r) > current_time - minute_window])
        hour_requests = len([r for r in requests if float(r) > current_time - hour_window])
        day_requests = len(requests)
        
        # Check limits
        limits_exceeded = []
        if minute_requests >= rule.requests_per_minute:
            limits_exceeded.append('per_minute')
        if hour_requests >= rule.requests_per_hour:
            limits_exceeded.append('per_hour')
        if day_requests >= rule.requests_per_day:
            limits_exceeded.append('per_day')
        
        # Check burst allowance
        burst_window = 10  # 10 seconds
        burst_requests = len([r for r in requests if float(r) > current_time - burst_window])
        if burst_requests >= rule.burst_allowance:
            limits_exceeded.append('burst')
        
        allowed = len(limits_exceeded) == 0
        
        if allowed:
            # Add current request to sliding window
            self.redis_client.zadd(key, {str(current_time): current_time})
            # Cleanup old entries
            self.redis_client.zremrangebyscore(key, 0, current_time - day_window)
            # Set expiration
            self.redis_client.expire(key, day_window)
        
        return allowed, {
            'minute_requests': minute_requests,
            'hour_requests': hour_requests,
            'day_requests': day_requests,
            'burst_requests': burst_requests,
            'limits_exceeded': limits_exceeded,
            'rule': rule.name
        }

    def _get_rate_limit_rule(self, endpoint: str) -> Optional[RateLimitRule]:
        """Find the most specific rate limit rule for an endpoint"""
        
        # Sort rules by specificity (more specific patterns first)
        sorted_rules = sorted(self.rate_limit_rules, key=lambda r: len(r.endpoint_pattern), reverse=True)
        
        for rule in sorted_rules:
            if self._matches_pattern(endpoint, rule.endpoint_pattern):
                return rule
        
        return None

    def _matches_pattern(self, endpoint: str, pattern: str) -> bool:
        """Simple pattern matching for endpoints"""
        
        if pattern.endswith('*'):
            return endpoint.startswith(pattern[:-1])
        return endpoint == pattern

    async def detect_suspicious_activity(self, user_id: str, ip_address: str, activity_data: Dict) -> bool:
        """
        Advanced anomaly detection for suspicious user behavior
        
        Returns:
            True if activity is suspicious, False otherwise
        """
        
        try:
            current_time = datetime.now()
            
            # Track user activity patterns
            if user_id not in self.user_activity_tracker:
                self.user_activity_tracker[user_id] = []
            
            self.user_activity_tracker[user_id].append({
                'timestamp': current_time,
                'ip_address': ip_address,
                'activity': activity_data
            })
            
            # Clean old activity data
            cutoff_time = current_time - self.anomaly_detection_window
            self.user_activity_tracker[user_id] = [
                a for a in self.user_activity_tracker[user_id] 
                if a['timestamp'] > cutoff_time
            ]
            
            recent_activity = self.user_activity_tracker[user_id]
            
            # Anomaly detection rules
            suspicious_indicators = []
            
            # 1. Multiple IP addresses in short time
            unique_ips = set(a['ip_address'] for a in recent_activity)
            if len(unique_ips) > 3:
                suspicious_indicators.append('multiple_ips')
            
            # 2. High volume of agent requests
            agent_requests = [a for a in recent_activity if 'agent' in a['activity'].get('endpoint', '')]
            if len(agent_requests) > 20:
                suspicious_indicators.append('high_agent_usage')
            
            # 3. Unusual time patterns (requests outside normal hours)
            unusual_time_requests = [
                a for a in recent_activity 
                if a['timestamp'].hour < 6 or a['timestamp'].hour > 22
            ]
            if len(unusual_time_requests) > 10:
                suspicious_indicators.append('unusual_timing')
            
            # 4. Failed authentication attempts
            auth_failures = [
                a for a in recent_activity 
                if 'auth' in a['activity'].get('endpoint', '') and a['activity'].get('success') is False
            ]
            if len(auth_failures) > 3:
                suspicious_indicators.append('auth_failures')
            
            # 5. Data exfiltration patterns (large responses, bulk queries)
            bulk_queries = [
                a for a in recent_activity 
                if a['activity'].get('response_size', 0) > 100000  # 100KB
            ]
            if len(bulk_queries) > 5:
                suspicious_indicators.append('bulk_data_access')
            
            is_suspicious = len(suspicious_indicators) >= 2
            
            if is_suspicious:
                await self._log_security_event(
                    user_id, ip_address, SecurityEventType.SUSPICIOUS_ACTIVITY,
                    ThreatLevel.HIGH, f"Suspicious activity detected: {suspicious_indicators}",
                    {
                        'indicators': suspicious_indicators,
                        'recent_activity_count': len(recent_activity),
                        'unique_ips': list(unique_ips)
                    }
                )
                
                # Auto-escalation for critical patterns
                if 'bulk_data_access' in suspicious_indicators and 'multiple_ips' in suspicious_indicators:
                    await self._escalate_threat(user_id, ip_address, ThreatLevel.CRITICAL)
            
            return is_suspicious
            
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return False

    async def check_data_loss_prevention(self, content: str, user_id: str) -> Dict[str, any]:
        """
        Scan content for sensitive data patterns (DLP)
        
        Returns:
            Dict with violation details if sensitive data detected
        """
        
        try:
            import re
            violations = []
            
            for pattern_name, pattern in self.dlp_patterns.items():
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    violations.append({
                        'type': pattern_name,
                        'matches': len(matches),
                        'examples': matches[:3]  # First 3 matches for analysis
                    })
            
            if violations:
                await self._log_security_event(
                    user_id, None, SecurityEventType.DATA_EXFILTRATION_ATTEMPT,
                    ThreatLevel.HIGH, f"DLP violation detected: {[v['type'] for v in violations]}",
                    {'violations': violations, 'content_length': len(content)}
                )
                
                return {
                    'blocked': True,
                    'reason': 'dlp_violation',
                    'violations': violations
                }
            
            return {'blocked': False}
            
        except Exception as e:
            logger.error(f"DLP check error: {e}")
            return {'blocked': False, 'error': str(e)}

    async def validate_agent_security(self, user_id: str, agent_type: str, operation: str, data: Dict) -> Dict[str, any]:
        """
        Validate agent operations for security compliance
        
        Returns:
            Dict with validation results and security controls
        """
        
        try:
            violations = []
            
            # Check agent-specific rate limits
            agent_limits = self.agent_rate_limits.get(agent_type, {})
            
            # Check for sensitive operations
            if operation in ['autonomous_email_send', 'external_api_call', 'file_upload']:
                # Require additional validation for high-risk operations
                if not await self._validate_high_risk_operation(user_id, operation, data):
                    violations.append(f'high_risk_operation_{operation}_blocked')
            
            # Check data content for DLP
            content_to_check = json.dumps(data)
            dlp_result = await self.check_data_loss_prevention(content_to_check, user_id)
            if dlp_result.get('blocked'):
                violations.append('dlp_violation')
            
            # Check for agent abuse patterns
            if await self._detect_agent_abuse(user_id, agent_type, operation):
                violations.append('agent_abuse_detected')
            
            is_allowed = len(violations) == 0
            
            if not is_allowed:
                await self._log_security_event(
                    user_id, None, SecurityEventType.AGENT_ABUSE,
                    ThreatLevel.HIGH, f"Agent security validation failed: {violations}",
                    {
                        'agent_type': agent_type,
                        'operation': operation,
                        'violations': violations
                    }
                )
            
            return {
                'allowed': is_allowed,
                'violations': violations,
                'security_controls_applied': True
            }
            
        except Exception as e:
            logger.error(f"Agent security validation error: {e}")
            # Fail secure
            return {'allowed': False, 'error': str(e)}

    async def _validate_high_risk_operation(self, user_id: str, operation: str, data: Dict) -> bool:
        """Validate high-risk operations with additional security checks"""
        
        # This would implement additional validation such as:
        # - Multi-factor authentication for sensitive operations
        # - Administrative approval workflows
        # - Business hours restrictions
        # - Geographic restrictions
        
        # For now, implement basic time-based and volume-based restrictions
        current_hour = datetime.now().hour
        
        # Restrict autonomous operations outside business hours
        if operation == 'autonomous_email_send' and (current_hour < 6 or current_hour > 20):
            return False
        
        # Check daily limits for high-risk operations
        daily_key = f"high_risk:{user_id}:{operation}:{datetime.now().strftime('%Y%m%d')}"
        daily_count = self.redis_client.get(daily_key)
        
        if daily_count and int(daily_count) > 10:  # Max 10 high-risk operations per day
            return False
        
        # Increment counter
        self.redis_client.incr(daily_key)
        self.redis_client.expire(daily_key, 86400)  # 24 hours
        
        return True

    async def _detect_agent_abuse(self, user_id: str, agent_type: str, operation: str) -> bool:
        """Detect potential abuse of agent capabilities"""
        
        # Check for rapid-fire agent requests
        window_key = f"agent_usage:{user_id}:{agent_type}"
        recent_requests = self.redis_client.zrangebyscore(
            window_key, time.time() - 300, time.time()  # Last 5 minutes
        )
        
        if len(recent_requests) > 20:  # More than 20 requests in 5 minutes
            return True
        
        # Add current request
        self.redis_client.zadd(window_key, {str(time.time()): time.time()})
        self.redis_client.expire(window_key, 300)
        
        return False

    async def _log_security_event(self, user_id: str, ip_address: str, event_type: SecurityEventType, 
                                 threat_level: ThreatLevel, description: str, metadata: Dict):
        """Log security event with comprehensive details"""
        
        event = SecurityEvent(
            event_id=str(uuid.uuid4()),
            user_id=user_id,
            ip_address=ip_address,
            event_type=event_type,
            threat_level=threat_level,
            description=description,
            metadata=metadata,
            timestamp=datetime.now()
        )
        
        self.security_events.append(event)
        
        # Log to file/database for persistence
        logger.warning(f"🔒 Security Event [{threat_level.name}]: {description} - User: {user_id}, IP: {ip_address}")
        
        # Auto-response for high/critical threats
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            await self._auto_respond_to_threat(event)

    async def _auto_respond_to_threat(self, event: SecurityEvent):
        """Automated response to security threats"""
        
        if event.threat_level == ThreatLevel.CRITICAL:
            # Immediate blocking for critical threats
            if event.ip_address:
                self.blocked_ips.add(event.ip_address)
            
            if event.user_id:
                # Suspend user session
                await self._suspend_user_session(event.user_id)
        
        elif event.threat_level == ThreatLevel.HIGH:
            # Enhanced monitoring for high threats
            if event.user_id:
                self.suspicious_users[event.user_id] = {
                    'flagged_at': datetime.now(),
                    'threat_count': self.suspicious_users.get(event.user_id, {}).get('threat_count', 0) + 1
                }

    async def _escalate_threat(self, user_id: str, ip_address: str, threat_level: ThreatLevel):
        """Escalate threat to security team and implement additional controls"""
        
        logger.critical(f"🚨 THREAT ESCALATION [{threat_level.name}]: User {user_id} from IP {ip_address}")
        
        # This would integrate with:
        # - Security Information and Event Management (SIEM) systems
        # - Incident response platforms
        # - Notification systems (email, Slack, PagerDuty)
        # - Automated threat response tools

    async def _suspend_user_session(self, user_id: str):
        """Suspend user session for security reasons"""
        
        session_key = f"user_session:{user_id}"
        self.redis_client.delete(session_key)
        logger.warning(f"🔒 User session suspended for security: {user_id}")

    async def get_security_dashboard(self) -> Dict:
        """Get comprehensive security dashboard data"""
        
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        
        recent_events = [e for e in self.security_events if e.timestamp > last_24h]
        
        return {
            'timestamp': now.isoformat(),
            'total_events_24h': len(recent_events),
            'threat_level_breakdown': {
                level.name: len([e for e in recent_events if e.threat_level == level])
                for level in ThreatLevel
            },
            'event_type_breakdown': {
                event_type.value: len([e for e in recent_events if e.event_type == event_type])
                for event_type in SecurityEventType
            },
            'blocked_ips': len(self.blocked_ips),
            'suspicious_users': len(self.suspicious_users),
            'rate_limit_violations': len([
                e for e in recent_events 
                if e.event_type == SecurityEventType.RATE_LIMIT_EXCEEDED
            ]),
            'security_health': 'healthy' if len(recent_events) < 10 else 'concerning'
        }

# Initialize global security manager
security_manager = AdvancedSecurityManager() 