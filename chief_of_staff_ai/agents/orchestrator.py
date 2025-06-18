import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid
from anthropic import AsyncAnthropic
from config.settings import settings
import time

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"
    COMPLETED = "completed"
    ERROR = "error"
    WAITING_APPROVAL = "waiting_approval"

class WorkflowPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4

@dataclass
class AgentTask:
    task_id: str
    agent_type: str
    task_data: Dict
    priority: WorkflowPriority
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: AgentStatus = AgentStatus.IDLE
    result: Optional[Dict] = None
    error: Optional[str] = None
    dependencies: List[str] = None
    estimated_duration: Optional[int] = None  # seconds

@dataclass
class AgentCapability:
    agent_type: str
    current_load: int
    max_concurrent: int
    average_response_time: float
    success_rate: float
    last_health_check: datetime
    status: AgentStatus

class AgentOrchestrator:
    """
    Advanced Agent Orchestrator for coordinating multiple Claude 4 Opus agents
    
    Features:
    - Real-time multi-agent coordination
    - Intelligent task scheduling and load balancing
    - Dynamic workflow optimization
    - Cross-agent data sharing via Files API
    - Advanced monitoring and analytics
    - Autonomous decision making with safety controls
    """
    
    def __init__(self, api_key: str = None):
        self.claude = AsyncAnthropic(api_key=api_key or settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL
        
        # Task management
        self.active_tasks: Dict[str, AgentTask] = {}
        self.completed_tasks: Dict[str, AgentTask] = {}
        self.task_queue: List[AgentTask] = []
        
        # Agent registry and capabilities
        self.agent_capabilities: Dict[str, AgentCapability] = {}
        self.agent_instances: Dict[str, object] = {}
        
        # Orchestration settings
        self.max_concurrent_tasks = 10
        self.task_timeout = 300  # 5 minutes
        self.health_check_interval = 60  # 1 minute
        
        # Performance tracking
        self.metrics = {
            'total_tasks': 0,
            'successful_tasks': 0,
            'failed_tasks': 0,
            'average_completion_time': 0,
            'agent_utilization': {},
            'workflow_success_rate': 0
        }
        
        # Real-time monitoring
        self.websocket_connections = set()
        self.last_status_broadcast = datetime.now()
        
        # Initialize agent registry
        self._initialize_agent_registry()
        
        logger.info("🎭 Agent Orchestrator initialized with advanced coordination capabilities")

    def _initialize_agent_registry(self):
        """Initialize registry of available agents and their capabilities"""
        
        # Import agents dynamically
        try:
            from . import (
                IntelligenceAgent, AutonomousEmailAgent, PartnershipWorkflowAgent,
                InvestorRelationshipAgent, GoalAchievementAgent, MCPConnectorAgent
            )
            
            # Register agent capabilities
            self.agent_capabilities = {
                'intelligence': AgentCapability(
                    agent_type='intelligence',
                    current_load=0,
                    max_concurrent=3,
                    average_response_time=15.0,
                    success_rate=0.95,
                    last_health_check=datetime.now(),
                    status=AgentStatus.IDLE
                ),
                'email': AgentCapability(
                    agent_type='email',
                    current_load=0,
                    max_concurrent=5,
                    average_response_time=8.0,
                    success_rate=0.92,
                    last_health_check=datetime.now(),
                    status=AgentStatus.IDLE
                ),
                'partnership': AgentCapability(
                    agent_type='partnership',
                    current_load=0,
                    max_concurrent=2,
                    average_response_time=45.0,
                    success_rate=0.88,
                    last_health_check=datetime.now(),
                    status=AgentStatus.IDLE
                ),
                'investor': AgentCapability(
                    agent_type='investor',
                    current_load=0,
                    max_concurrent=2,
                    average_response_time=30.0,
                    success_rate=0.90,
                    last_health_check=datetime.now(),
                    status=AgentStatus.IDLE
                ),
                'goal': AgentCapability(
                    agent_type='goal',
                    current_load=0,
                    max_concurrent=3,
                    average_response_time=20.0,
                    success_rate=0.93,
                    last_health_check=datetime.now(),
                    status=AgentStatus.IDLE
                ),
                'mcp': AgentCapability(
                    agent_type='mcp',
                    current_load=0,
                    max_concurrent=4,
                    average_response_time=12.0,
                    success_rate=0.85,
                    last_health_check=datetime.now(),
                    status=AgentStatus.IDLE
                )
            }
            
            # Initialize agent instances
            self.agent_instances = {
                'intelligence': IntelligenceAgent(),
                'email': AutonomousEmailAgent(),
                'partnership': PartnershipWorkflowAgent(),
                'investor': InvestorRelationshipAgent(),
                'goal': GoalAchievementAgent(),
                'mcp': MCPConnectorAgent()
            }
            
            logger.info(f"✅ Registered {len(self.agent_capabilities)} agents with orchestration capabilities")
            
        except ImportError as e:
            logger.error(f"Failed to import agents for orchestration: {e}")

    async def execute_multi_agent_workflow(self, workflow_definition: Dict) -> str:
        """
        Execute complex multi-agent workflow with intelligent coordination
        
        Args:
            workflow_definition: Dictionary defining the workflow steps and dependencies
            
        Returns:
            workflow_id: Unique identifier for tracking workflow progress
        """
        
        workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"🎭 Starting multi-agent workflow: {workflow_id}")
        
        try:
            # Parse workflow definition
            workflow_steps = workflow_definition.get('steps', [])
            workflow_priority = WorkflowPriority(workflow_definition.get('priority', 3))
            
            # Create tasks for each step
            tasks = []
            for step in workflow_steps:
                task = AgentTask(
                    task_id=f"{workflow_id}_{step['agent']}_{len(tasks)}",
                    agent_type=step['agent'],
                    task_data=step['data'],
                    priority=workflow_priority,
                    created_at=datetime.now(),
                    dependencies=step.get('dependencies', []),
                    estimated_duration=step.get('estimated_duration', 30)
                )
                tasks.append(task)
                self.task_queue.append(task)
            
            # Start workflow execution
            asyncio.create_task(self._execute_workflow_tasks(workflow_id, tasks))
            
            # Broadcast workflow started
            await self._broadcast_status_update({
                'type': 'workflow_started',
                'workflow_id': workflow_id,
                'total_tasks': len(tasks),
                'estimated_completion': (datetime.now() + timedelta(seconds=sum(t.estimated_duration for t in tasks))).isoformat()
            })
            
            return workflow_id
            
        except Exception as e:
            logger.error(f"Failed to start workflow {workflow_id}: {e}")
            raise

    async def _execute_workflow_tasks(self, workflow_id: str, tasks: List[AgentTask]):
        """Execute workflow tasks with dependency management and optimization"""
        
        try:
            completed_tasks = set()
            running_tasks = {}
            
            while len(completed_tasks) < len(tasks):
                # Find tasks ready to execute (dependencies satisfied)
                ready_tasks = []
                for task in tasks:
                    if (task.task_id not in completed_tasks and 
                        task.task_id not in running_tasks and
                        all(dep in completed_tasks for dep in (task.dependencies or []))):
                        ready_tasks.append(task)
                
                # Execute ready tasks with load balancing
                for task in ready_tasks:
                    if self._can_execute_task(task):
                        running_tasks[task.task_id] = asyncio.create_task(
                            self._execute_single_task(task)
                        )
                        task.status = AgentStatus.WORKING
                        task.started_at = datetime.now()
                        
                        # Update agent load
                        self.agent_capabilities[task.agent_type].current_load += 1
                
                # Wait for any task to complete
                if running_tasks:
                    done, pending = await asyncio.wait(
                        running_tasks.values(), 
                        return_when=asyncio.FIRST_COMPLETED,
                        timeout=self.task_timeout
                    )
                    
                    # Process completed tasks
                    for completed_task in done:
                        task_id = None
                        for tid, t in running_tasks.items():
                            if t == completed_task:
                                task_id = tid
                                break
                        
                        if task_id:
                            task = next(t for t in tasks if t.task_id == task_id)
                            try:
                                result = await completed_task
                                task.result = result
                                task.status = AgentStatus.COMPLETED
                                task.completed_at = datetime.now()
                                completed_tasks.add(task_id)
                                
                                # Update metrics
                                self._update_task_metrics(task, success=True)
                                
                            except Exception as e:
                                task.error = str(e)
                                task.status = AgentStatus.ERROR
                                task.completed_at = datetime.now()
                                completed_tasks.add(task_id)  # Mark as done even if failed
                                
                                # Update metrics
                                self._update_task_metrics(task, success=False)
                                logger.error(f"Task {task_id} failed: {e}")
                            
                            finally:
                                # Update agent load
                                self.agent_capabilities[task.agent_type].current_load -= 1
                                del running_tasks[task_id]
                
                # Broadcast progress update
                progress = len(completed_tasks) / len(tasks)
                await self._broadcast_status_update({
                    'type': 'workflow_progress',
                    'workflow_id': workflow_id,
                    'progress': progress,
                    'completed_tasks': len(completed_tasks),
                    'total_tasks': len(tasks),
                    'running_tasks': len(running_tasks)
                })
                
                # Short delay to prevent tight loop
                await asyncio.sleep(0.5)
            
            # Workflow completed
            success_rate = len([t for t in tasks if t.status == AgentStatus.COMPLETED]) / len(tasks)
            
            await self._broadcast_status_update({
                'type': 'workflow_completed',
                'workflow_id': workflow_id,
                'success_rate': success_rate,
                'total_tasks': len(tasks),
                'completion_time': datetime.now().isoformat()
            })
            
            logger.info(f"🎉 Workflow {workflow_id} completed with {success_rate:.2%} success rate")
            
        except Exception as e:
            logger.error(f"Workflow execution failed for {workflow_id}: {e}")
            await self._broadcast_status_update({
                'type': 'workflow_failed',
                'workflow_id': workflow_id,
                'error': str(e)
            })

    def _can_execute_task(self, task: AgentTask) -> bool:
        """Check if a task can be executed based on agent capacity"""
        
        agent_cap = self.agent_capabilities.get(task.agent_type)
        if not agent_cap:
            return False
        
        return agent_cap.current_load < agent_cap.max_concurrent

    async def _execute_single_task(self, task: AgentTask) -> Dict:
        """Execute a single agent task with error handling and monitoring"""
        
        try:
            start_time = time.time()
            
            # Get the appropriate agent
            agent = self.agent_instances.get(task.agent_type)
            if not agent:
                raise Exception(f"Agent {task.agent_type} not available")
            
            # Execute task based on agent type
            result = await self._route_task_to_agent(agent, task)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Update agent performance metrics
            agent_cap = self.agent_capabilities[task.agent_type]
            agent_cap.average_response_time = (
                agent_cap.average_response_time * 0.8 + execution_time * 0.2
            )
            
            return {
                'success': True,
                'result': result,
                'execution_time': execution_time,
                'agent_type': task.agent_type
            }
            
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'agent_type': task.agent_type
            }

    async def _route_task_to_agent(self, agent, task: AgentTask) -> Dict:
        """Route task to appropriate agent method based on task type"""
        
        task_data = task.task_data
        task_type = task_data.get('type')
        
        # Intelligence Agent routing
        if task.agent_type == 'intelligence':
            if task_type == 'relationship_analysis':
                return await agent.analyze_relationship_intelligence_with_data(
                    task_data['person_data'], 
                    task_data['email_history']
                )
            elif task_type == 'market_intelligence':
                return await agent.generate_strategic_market_intelligence(
                    task_data['business_context'],
                    task_data['goals']
                )
        
        # Email Agent routing
        elif task.agent_type == 'email':
            if task_type == 'process_autonomous':
                return await agent.process_incoming_email_autonomously(
                    task_data['email_data'],
                    task_data['user_context']
                )
        
        # Add routing for other agents...
        
        raise Exception(f"Unknown task type {task_type} for agent {task.agent_type}")

    async def get_real_time_status(self) -> Dict:
        """Get comprehensive real-time status of all agents and workflows"""
        
        try:
            status = {
                'timestamp': datetime.now().isoformat(),
                'orchestrator_health': 'healthy',
                'agents': {},
                'active_workflows': len(self.active_tasks),
                'total_metrics': self.metrics,
                'system_load': self._calculate_system_load()
            }
            
            # Get status for each agent
            for agent_type, capability in self.agent_capabilities.items():
                status['agents'][agent_type] = {
                    'status': capability.status.value,
                    'current_load': capability.current_load,
                    'max_concurrent': capability.max_concurrent,
                    'utilization': capability.current_load / capability.max_concurrent,
                    'average_response_time': capability.average_response_time,
                    'success_rate': capability.success_rate,
                    'last_health_check': capability.last_health_check.isoformat()
                }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting orchestrator status: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'orchestrator_health': 'error',
                'error': str(e)
            }

    def _calculate_system_load(self) -> float:
        """Calculate overall system load across all agents"""
        
        total_capacity = sum(cap.max_concurrent for cap in self.agent_capabilities.values())
        current_load = sum(cap.current_load for cap in self.agent_capabilities.values())
        
        return current_load / total_capacity if total_capacity > 0 else 0

    def _update_task_metrics(self, task: AgentTask, success: bool):
        """Update performance metrics after task completion"""
        
        self.metrics['total_tasks'] += 1
        
        if success:
            self.metrics['successful_tasks'] += 1
        else:
            self.metrics['failed_tasks'] += 1
        
        # Update success rate
        self.metrics['workflow_success_rate'] = (
            self.metrics['successful_tasks'] / self.metrics['total_tasks']
        )
        
        # Update completion time
        if task.completed_at and task.started_at:
            completion_time = (task.completed_at - task.started_at).total_seconds()
            current_avg = self.metrics['average_completion_time']
            total_tasks = self.metrics['total_tasks']
            
            self.metrics['average_completion_time'] = (
                (current_avg * (total_tasks - 1) + completion_time) / total_tasks
            )

    async def _broadcast_status_update(self, update: Dict):
        """Broadcast status update to connected WebSocket clients"""
        
        try:
            update['timestamp'] = datetime.now().isoformat()
            message = json.dumps(update)
            
            # This would integrate with WebSocket server
            # For now, just log the update
            logger.info(f"📡 Broadcasting: {update['type']}")
            
        except Exception as e:
            logger.error(f"Error broadcasting update: {e}")

    async def schedule_autonomous_workflow(self, trigger_condition: str, workflow_definition: Dict) -> str:
        """Schedule autonomous workflow execution based on triggers"""
        
        # This would implement intelligent scheduling based on:
        # - Time-based triggers
        # - Event-based triggers
        # - Performance metrics
        # - User behavior patterns
        
        logger.info(f"📅 Scheduled autonomous workflow with trigger: {trigger_condition}")
        return await self.execute_multi_agent_workflow(workflow_definition)

    async def optimize_agent_allocation(self):
        """Dynamically optimize agent allocation based on performance data"""
        
        # This would implement ML-based optimization of:
        # - Task routing
        # - Load balancing
        # - Resource allocation
        # - Performance tuning
        
        logger.info("🔧 Optimizing agent allocation based on performance data") 