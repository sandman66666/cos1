"""
Enhanced AI Processing Pipeline - Context-Aware Intelligence
This replaces the scattered AI processing with unified, context-aware analysis
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone, timedelta
import anthropic
from dataclasses import dataclass
import hashlib

from config.settings import settings
from processors.unified_entity_engine import entity_engine, EntityContext
from models.database import Email, Topic, Person, Task, Project, EntityRelationship, IntelligenceInsight

logger = logging.getLogger(__name__)

@dataclass
class ProcessingResult:
    """Result container for AI processing"""
    success: bool
    entities_created: Dict[str, int]  # Type -> count
    entities_updated: Dict[str, int]
    insights_generated: List[str]
    processing_time: float
    error: Optional[str] = None

class EnhancedAIProcessor:
    """
    Context-aware AI processing that builds on existing knowledge.
    This is the brain that turns raw data into intelligent insights.
    """
    
    def __init__(self):
        from config.settings import settings
        
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL  # Now uses Claude 4 Opus from settings
        self.entity_engine = entity_engine
        
    # =====================================================================
    # UNIFIED EMAIL PROCESSING - SINGLE PASS WITH CONTEXT
    # =====================================================================
    
    def process_email_with_context(self, email_data: Dict, user_id: int, existing_context: Dict = None) -> ProcessingResult:
        """
        Process email with full context awareness in a single AI call.
        This replaces multiple separate prompts with one intelligent analysis.
        """
        start_time = datetime.utcnow()
        result = ProcessingResult(
            success=False,
            entities_created={'people': 0, 'topics': 0, 'tasks': 0, 'projects': 0},
            entities_updated={'people': 0, 'topics': 0, 'tasks': 0, 'projects': 0},
            insights_generated=[],
            processing_time=0.0
        )
        
        try:
            # Step 1: Gather existing context for this user
            context = self._gather_user_context(user_id, existing_context)
            
            # Step 2: Prepare comprehensive prompt with existing knowledge
            analysis_prompt = self._prepare_unified_email_prompt(email_data, context)
            
            # Step 3: Single AI analysis call
            claude_response = self._call_claude_unified_analysis(analysis_prompt)
            
            if not claude_response:
                result.error = "Failed to get AI analysis"
                return result
            
            # Step 4: Parse comprehensive response
            analysis = self._parse_unified_analysis(claude_response)
            
            # Step 5: Create/update entities with context
            processing_context = EntityContext(
                source_type='email',
                source_id=email_data.get('id'),
                user_id=user_id,
                confidence=analysis.get('overall_confidence', 0.8)
            )
            
            # Process people (including signature analysis)
            people_result = self._process_people_from_analysis(analysis.get('people', []), processing_context)
            result.entities_created['people'] = people_result['created']
            result.entities_updated['people'] = people_result['updated']
            
            # Process topics (check existing first)
            topics_result = self._process_topics_from_analysis(analysis.get('topics', []), processing_context)
            result.entities_created['topics'] = topics_result['created']
            result.entities_updated['topics'] = topics_result['updated']
            
            # Process tasks (with full context story)
            tasks_result = self._process_tasks_from_analysis(analysis.get('tasks', []), processing_context)
            result.entities_created['tasks'] = tasks_result['created']
            
            # Process projects (check for augmentation)
            projects_result = self._process_projects_from_analysis(analysis.get('projects', []), processing_context)
            result.entities_created['projects'] = projects_result['created']
            result.entities_updated['projects'] = projects_result['updated']
            
            # Create entity relationships
            self._create_entity_relationships(analysis, processing_context)
            
            # Store email intelligence
            self._store_email_intelligence(email_data, analysis, user_id)
            
            # Generate insights
            result.insights_generated = analysis.get('strategic_insights', [])
            
            result.success = True
            result.processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(f"Successfully processed email with context in {result.processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Failed to process email with context: {str(e)}")
            result.error = str(e)
            result.processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return result
    
    # =====================================================================
    # CALENDAR EVENT ENHANCEMENT WITH EMAIL INTELLIGENCE
    # =====================================================================
    
    def enhance_calendar_event_with_intelligence(self, event_data: Dict, user_id: int) -> ProcessingResult:
        """
        Enhance calendar events with email intelligence and create prep tasks.
        This addresses connecting email insights to calendar events.
        """
        start_time = datetime.utcnow()
        result = ProcessingResult(
            success=False,
            entities_created={'tasks': 0, 'people': 0},
            entities_updated={'events': 0, 'people': 0},
            insights_generated=[],
            processing_time=0.0
        )
        
        try:
            # Step 1: Analyze attendees and find existing relationships
            attendee_intelligence = self._analyze_event_attendees(event_data, user_id)
            
            # Step 2: Find related email intelligence for these people
            email_context = self._find_related_email_intelligence(attendee_intelligence, user_id)
            
            # Step 3: Generate enhanced meeting context
            enhancement_prompt = self._prepare_meeting_enhancement_prompt(event_data, attendee_intelligence, email_context)
            
            # Step 4: AI analysis for meeting preparation
            claude_response = self._call_claude_meeting_enhancement(enhancement_prompt)
            
            if claude_response:
                enhancement = self._parse_meeting_enhancement(claude_response)
                
                processing_context = EntityContext(
                    source_type='calendar',
                    source_id=event_data.get('id'),
                    user_id=user_id,
                    confidence=0.8
                )
                
                # Create preparation tasks
                if enhancement.get('prep_tasks'):
                    for task_data in enhancement['prep_tasks']:
                        task = self.entity_engine.create_task_with_full_context(
                            description=task_data['description'],
                            assignee_email=None,  # User's own prep tasks
                            topic_names=task_data.get('topics', []),
                            context=processing_context,
                            priority=task_data.get('priority', 'medium')
                        )
                        if task:
                            result.entities_created['tasks'] += 1
                
                # Update event with business context
                self._update_event_intelligence(event_data, enhancement, user_id)
                result.entities_updated['events'] = 1
                
                result.insights_generated = enhancement.get('insights', [])
                result.success = True
            
            result.processing_time = (datetime.utcnow() - start_time).total_seconds()
            
        except Exception as e:
            logger.error(f"Failed to enhance calendar event: {str(e)}")
            result.error = str(e)
            result.processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        return result
    
    # =====================================================================
    # CONTEXT GATHERING AND PROMPT PREPARATION
    # =====================================================================
    
    def _gather_user_context(self, user_id: int, existing_context: Dict = None) -> Dict:
        """Gather comprehensive user context for AI processing"""
        try:
            from models.database import get_db_manager
            
            context = {
                'existing_people': [],
                'existing_topics': [],
                'active_projects': [],
                'recent_insights': [],
                'communication_patterns': {}
            }
            
            if existing_context:
                context.update(existing_context)
                return context
            
            with get_db_manager().get_session() as session:
                # Get recent people (last 30 days)
                recent_people = session.query(Person).filter(
                    Person.user_id == user_id,
                    Person.last_interaction > datetime.utcnow() - timedelta(days=30)
                ).limit(20).all()
                
                context['existing_people'] = [
                    {
                        'name': p.name,
                        'email': p.email_address,
                        'company': p.company,
                        'relationship': p.relationship_type,
                        'importance': p.importance_level
                    }
                    for p in recent_people
                ]
                
                # Get active topics
                active_topics = session.query(Topic).filter(
                    Topic.user_id == user_id,
                    Topic.total_mentions > 1
                ).order_by(Topic.last_mentioned.desc()).limit(15).all()
                
                context['existing_topics'] = [
                    {
                        'name': t.name,
                        'description': t.description,
                        'keywords': t.keywords,
                        'mentions': t.total_mentions,
                        'is_official': t.is_official
                    }
                    for t in active_topics
                ]
                
                # Get active projects
                active_projects = session.query(Project).filter(
                    Project.user_id == user_id,
                    Project.status == 'active'
                ).limit(10).all()
                
                context['active_projects'] = [
                    {
                        'name': p.name,
                        'description': p.description,
                        'status': p.status,
                        'priority': p.priority
                    }
                    for p in active_projects
                ]
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to gather user context: {str(e)}")
            return {}
    
    def _prepare_unified_email_prompt(self, email_data: Dict, context: Dict) -> str:
        """Prepare comprehensive email analysis prompt with existing context"""
        
        # Format existing context for Claude
        context_summary = self._format_context_for_claude(context)
        
        prompt = f"""You are an AI Chief of Staff analyzing business email communication with access to the user's existing business intelligence context.

EXISTING BUSINESS CONTEXT:
{context_summary}

EMAIL TO ANALYZE:
From: {email_data.get('sender_name', '')} <{email_data.get('sender', '')}>
Subject: {email_data.get('subject', '')}
Date: {email_data.get('email_date', '')}

Content:
{email_data.get('body_text', email_data.get('body_clean', ''))}

ANALYSIS INSTRUCTIONS:
Provide comprehensive analysis in the following JSON format. Use the existing context to:
1. Match people to existing contacts (avoid duplicates)
2. Connect topics to existing business themes
3. Identify project connections and updates
4. Generate contextual tasks with business rationale
5. Extract strategic insights based on patterns

{{
    "overall_confidence": 0.0-1.0,
    "business_summary": "Concise business-focused summary for display",
    "category": "meeting|project|decision|information|relationship",
    "sentiment": "positive|neutral|negative|urgent",
    "strategic_importance": 0.0-1.0,
    
    "people": [
        {{
            "email": "required",
            "name": "extracted or inferred name",
            "is_existing": true/false,
            "existing_person_match": "name if matched to existing context",
            "role_in_email": "sender|recipient|mentioned",
            "professional_context": "title, company, relationship insights",
            "signature_data": "extracted title, company, phone, etc if available",
            "importance_level": 0.0-1.0
        }}
    ],
    
    "topics": [
        {{
            "name": "topic name",
            "is_existing": true/false,
            "existing_topic_match": "name if matched to existing",
            "description": "what this topic covers",
            "keywords": ["keyword1", "keyword2"],
            "strategic_importance": 0.0-1.0,
            "new_information": "what's new about this topic from this email"
        }}
    ],
    
    "tasks": [
        {{
            "description": "clear actionable task",
            "assignee_email": "who should do this or null for user",
            "context_rationale": "WHY this task exists - business context",
            "related_topics": ["topic names"],
            "related_people": ["email addresses"],
            "priority": "high|medium|low",
            "due_date_hint": "extracted date or timing hint",
            "confidence": 0.0-1.0
        }}
    ],
    
    "projects": [
        {{
            "name": "project name",
            "is_existing": true/false,
            "existing_project_match": "name if matched",
            "description": "project description",
            "new_information": "what's new about this project",
            "stakeholders": ["email addresses of involved people"],
            "status_update": "current status or progress",
            "priority": "high|medium|low"
        }}
    ],
    
    "strategic_insights": [
        "Key business insights that connect to existing context or reveal new patterns"
    ],
    
    "entity_relationships": [
        {{
            "entity_a": {{"type": "person|topic|project", "identifier": "email or name"}},
            "entity_b": {{"type": "person|topic|project", "identifier": "email or name"}},
            "relationship_type": "collaborates_on|discusses|leads|reports_to",
            "strength": 0.0-1.0
        }}
    ]
}}

Focus on business intelligence that builds on existing context rather than isolated data extraction."""
        
        return prompt
    
    def _format_context_for_claude(self, context: Dict) -> str:
        """Format user context in a readable way for Claude"""
        sections = []
        
        if context.get('existing_people'):
            people_summary = []
            for person in context['existing_people'][:10]:  # Limit for token efficiency
                people_summary.append(f"- {person['name']} ({person['email']}) - {person.get('company', 'Unknown')} - {person.get('relationship', 'contact')}")
            sections.append(f"EXISTING PEOPLE:\n" + "\n".join(people_summary))
        
        if context.get('existing_topics'):
            topics_summary = []
            for topic in context['existing_topics'][:10]:
                status = "OFFICIAL" if topic.get('is_official') else f"{topic.get('mentions', 0)} mentions"
                topics_summary.append(f"- {topic['name']} ({status}) - {topic.get('description', 'No description')}")
            sections.append(f"EXISTING TOPICS:\n" + "\n".join(topics_summary))
        
        if context.get('active_projects'):
            projects_summary = []
            for project in context['active_projects'][:5]:
                projects_summary.append(f"- {project['name']} ({project['status']}) - {project.get('description', '')}")
            sections.append(f"ACTIVE PROJECTS:\n" + "\n".join(projects_summary))
        
        return "\n\n".join(sections) if sections else "No existing context available."
    
    # =====================================================================
    # AI RESPONSE PROCESSING
    # =====================================================================
    
    def _call_claude_unified_analysis(self, prompt: str) -> Optional[str]:
        """Call Claude for unified email analysis"""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=4000,  # Increased for comprehensive analysis
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return message.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Failed to call Claude for unified analysis: {str(e)}")
            return None
    
    def _parse_unified_analysis(self, response: str) -> Dict:
        """Parse Claude's comprehensive analysis response"""
        try:
            # Find JSON in response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.warning("No JSON found in Claude response")
                return {}
            
            json_text = response[json_start:json_end]
            analysis = json.loads(json_text)
            
            logger.info(f"Parsed unified analysis with {len(analysis.get('people', []))} people, "
                       f"{len(analysis.get('topics', []))} topics, {len(analysis.get('tasks', []))} tasks")
            
            return analysis
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude analysis JSON: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Failed to parse Claude analysis: {str(e)}")
            return {}
    
    def _process_people_from_analysis(self, people_data: List[Dict], context: EntityContext) -> Dict:
        """Process people from unified analysis"""
        result = {'created': 0, 'updated': 0}
        
        for person_data in people_data:
            email = person_data.get('email')
            name = person_data.get('name')
            
            if not email:
                continue
            
            # Add signature data to processing metadata
            if person_data.get('signature_data'):
                context.processing_metadata = {'signature': person_data['signature_data']}
            
            person = self.entity_engine.create_or_update_person(email, name, context)
            
            if person:
                if person_data.get('is_existing'):
                    result['updated'] += 1
                else:
                    result['created'] += 1
        
        return result
    
    def _process_topics_from_analysis(self, topics_data: List[Dict], context: EntityContext) -> Dict:
        """Process topics from unified analysis with existing topic checking"""
        result = {'created': 0, 'updated': 0}
        
        for topic_data in topics_data:
            topic_name = topic_data.get('name')
            description = topic_data.get('description')
            keywords = topic_data.get('keywords', [])
            
            if not topic_name:
                continue
            
            topic = self.entity_engine.create_or_update_topic(
                topic_name=topic_name,
                description=description,
                keywords=keywords,
                context=context
            )
            
            if topic:
                if topic_data.get('is_existing'):
                    result['updated'] += 1
                else:
                    result['created'] += 1
        
        return result
    
    def _process_tasks_from_analysis(self, tasks_data: List[Dict], context: EntityContext) -> Dict:
        """Process tasks from unified analysis with full context stories"""
        result = {'created': 0}
        
        for task_data in tasks_data:
            description = task_data.get('description')
            assignee_email = task_data.get('assignee_email')
            related_topics = task_data.get('related_topics', [])
            priority = task_data.get('priority', 'medium')
            
            if not description:
                continue
            
            # Parse due date hint
            due_date = None
            due_date_hint = task_data.get('due_date_hint')
            if due_date_hint:
                due_date = self._parse_due_date_hint(due_date_hint)
            
            # Set confidence from analysis
            context.confidence = task_data.get('confidence', 0.8)
            
            # Add context rationale to processing metadata
            if task_data.get('context_rationale'):
                context.processing_metadata = {
                    'context_rationale': task_data['context_rationale'],
                    'related_people': task_data.get('related_people', [])
                }
            
            task = self.entity_engine.create_task_with_full_context(
                description=description,
                assignee_email=assignee_email,
                topic_names=related_topics,
                context=context,
                due_date=due_date,
                priority=priority
            )
            
            if task:
                result['created'] += 1
        
        return result
    
    def _process_projects_from_analysis(self, projects_data: List[Dict], context: EntityContext) -> Dict:
        """Process projects from unified analysis with augmentation logic"""
        result = {'created': 0, 'updated': 0}
        
        try:
            from models.database import get_db_manager
            
            with get_db_manager().get_session() as session:
                for project_data in projects_data:
                    project_name = project_data.get('name')
                    
                    if not project_name:
                        continue
                    
                    # Check for existing project
                    existing_project = session.query(Project).filter(
                        Project.user_id == context.user_id,
                        Project.name.ilike(f"%{project_name}%")
                    ).first()
                    
                    if existing_project and project_data.get('is_existing'):
                        # Augment existing project
                        updated = self._augment_existing_project(existing_project, project_data, session)
                        if updated:
                            result['updated'] += 1
                    
                    elif not existing_project:
                        # Create new project
                        new_project = self._create_new_project(project_data, context, session)
                        if new_project:
                            result['created'] += 1
                
                session.commit()
        
        except Exception as e:
            logger.error(f"Failed to process projects: {str(e)}")
        
        return result
    
    def _create_entity_relationships(self, analysis: Dict, context: EntityContext):
        """Create relationships between entities based on analysis"""
        relationships = analysis.get('entity_relationships', [])
        
        for rel_data in relationships:
            entity_a = rel_data.get('entity_a', {})
            entity_b = rel_data.get('entity_b', {})
            relationship_type = rel_data.get('relationship_type', 'related')
            
            # Find actual entity IDs
            entity_a_id = self._find_entity_id(entity_a, context.user_id)
            entity_b_id = self._find_entity_id(entity_b, context.user_id)
            
            if entity_a_id and entity_b_id:
                self.entity_engine.create_entity_relationship(
                    entity_a['type'], entity_a_id,
                    entity_b['type'], entity_b_id,
                    relationship_type,
                    context
                )
    
    def _store_email_intelligence(self, email_data: Dict, analysis: Dict, user_id: int):
        """Store processed email intelligence in optimized format"""
        try:
            from models.database import get_db_manager, Email
            import hashlib
            
            # Create content hash for deduplication
            content = email_data.get('body_clean', '')
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            # Store in blob storage (simplified for now - would use S3/GCS in production)
            blob_key = f"emails/{user_id}/{content_hash}.txt"
            
            # Convert sentiment string to float for database storage
            sentiment_value = self._convert_sentiment_to_float(analysis.get('sentiment'))
            
            with get_db_manager().get_session() as session:
                # Check if email already exists
                existing_email = session.query(Email).filter(
                    Email.gmail_id == email_data.get('gmail_id')
                ).first()
                
                if existing_email:
                    # Update existing email with new intelligence
                    existing_email.ai_summary = analysis.get('business_summary')
                    existing_email.business_category = analysis.get('category')
                    existing_email.sentiment = sentiment_value
                    existing_email.strategic_importance = analysis.get('strategic_importance', 0.5)
                    existing_email.processed_at = datetime.utcnow()
                else:
                    # Create new email record
                    email_record = Email(
                        user_id=user_id,
                        gmail_id=email_data.get('gmail_id') or email_data.get('id'),  # Use gmail_id or id
                        subject=email_data.get('subject'),
                        sender=email_data.get('sender'),
                        sender_name=email_data.get('sender_name'),
                        email_date=email_data.get('email_date'),
                        ai_summary=analysis.get('business_summary'),
                        business_category=analysis.get('category'),
                        sentiment=sentiment_value,
                        strategic_importance=analysis.get('strategic_importance', 0.5),
                        content_hash=content_hash,
                        blob_storage_key=blob_key,
                        processed_at=datetime.utcnow(),
                        processing_version="unified_v2.0"
                    )
                    session.add(email_record)
                
                session.commit()
                
        except Exception as e:
            logger.error(f"Failed to store email intelligence: {str(e)}")
    
    def _convert_sentiment_to_float(self, sentiment):
        """Convert sentiment string to float value for database storage"""
        if isinstance(sentiment, (int, float)):
            return float(sentiment)
        
        if isinstance(sentiment, str):
            sentiment_lower = sentiment.lower()
            if sentiment_lower in ['positive', 'good', 'happy']:
                return 0.7
            elif sentiment_lower in ['negative', 'bad', 'sad', 'angry']:
                return -0.7
            elif sentiment_lower in ['neutral', 'mixed', 'balanced']:
                return 0.0
            else:
                # Try to parse as float
                try:
                    return float(sentiment)
                except ValueError:
                    return 0.0
        
        return 0.0  # Default neutral
    
    # =====================================================================
    # MEETING ENHANCEMENT METHODS (simplified for space)
    # =====================================================================
    
    def _analyze_event_attendees(self, event_data: Dict, user_id: int) -> Dict:
        """Analyze meeting attendees and find existing relationships"""
        # Implementation for attendee analysis
        return {'known_attendees': [], 'unknown_attendees': [], 'relationship_strength': 0.0}
    
    def _find_related_email_intelligence(self, attendee_intelligence: Dict, user_id: int) -> Dict:
        """Find email intelligence related to meeting attendees"""
        # Implementation for finding related email context
        return {'recent_communications': [], 'shared_topics': []}
    
    def _prepare_meeting_enhancement_prompt(self, event_data: Dict, attendee_intelligence: Dict, email_context: Dict) -> str:
        """Prepare prompt for meeting enhancement with intelligence"""
        return f"Analyze meeting: {event_data.get('title', '')} with context"
    
    def _call_claude_meeting_enhancement(self, prompt: str) -> Optional[str]:
        """Call Claude for meeting enhancement analysis"""
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=3000,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text.strip()
        except Exception as e:
            logger.error(f"Failed to call Claude for meeting enhancement: {str(e)}")
            return None
    
    def _parse_meeting_enhancement(self, response: str) -> Dict:
        """Parse Claude's meeting enhancement response"""
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > 0:
                return json.loads(response[json_start:json_end])
        except:
            pass
        return {}
    
    def _update_event_intelligence(self, event_data: Dict, enhancement: Dict, user_id: int):
        """Update calendar event with intelligence"""
        # Implementation for updating event intelligence
        pass
    
    # =====================================================================
    # UTILITY METHODS
    # =====================================================================
    
    def _parse_due_date_hint(self, hint: str) -> Optional[datetime]:
        """Parse due date hint into actual datetime"""
        from dateutil import parser as date_parser
        try:
            return date_parser.parse(hint, fuzzy=True)
        except:
            return None
    
    def _find_entity_id(self, entity_info: Dict, user_id: int) -> Optional[int]:
        """Find actual entity ID from analysis data"""
        try:
            from models.database import get_db_manager
            
            entity_type = entity_info.get('type')
            identifier = entity_info.get('identifier')
            
            if not entity_type or not identifier:
                return None
            
            with get_db_manager().get_session() as session:
                if entity_type == 'person':
                    entity = session.query(Person).filter(
                        Person.user_id == user_id,
                        Person.email_address == identifier
                    ).first()
                elif entity_type == 'topic':
                    entity = session.query(Topic).filter(
                        Topic.user_id == user_id,
                        Topic.name == identifier
                    ).first()
                elif entity_type == 'project':
                    entity = session.query(Project).filter(
                        Project.user_id == user_id,
                        Project.name == identifier
                    ).first()
                else:
                    return None
                
                return entity.id if entity else None
                
        except Exception as e:
            logger.error(f"Failed to find entity ID: {str(e)}")
            return None
    
    def _augment_existing_project(self, project: Project, project_data: Dict, session) -> bool:
        """Augment existing project with new information"""
        updated = False
        
        new_info = project_data.get('new_information')
        if new_info:
            if project.description:
                project.description = f"{project.description}. {new_info}"
            else:
                project.description = new_info
            updated = True
        
        status_update = project_data.get('status_update')
        if status_update:
            project.updated_at = datetime.utcnow()
            updated = True
        
        return updated
    
    def _create_new_project(self, project_data: Dict, context: EntityContext, session) -> Optional[Project]:
        """Create new project from analysis"""
        try:
            project = Project(
                user_id=context.user_id,
                name=project_data['name'],
                description=project_data.get('description'),
                status='active',
                priority=project_data.get('priority', 'medium'),
                created_at=datetime.utcnow()
            )
            
            session.add(project)
            return project
            
        except Exception as e:
            logger.error(f"Failed to create new project: {str(e)}")
            return None

# Global instance
enhanced_ai_processor = EnhancedAIProcessor() 