# Enhanced Intelligence Engine - The Core That Makes Everything Useful
# This generates meaningful meeting preparation, attendee intelligence, and proactive insights

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import anthropic
from dataclasses import dataclass

from config.settings import settings
from chief_of_staff_ai.models.database import get_db_manager, Calendar, Person, Email, Task, IntelligenceInsight, EntityRelationship

logger = logging.getLogger(__name__)

@dataclass
class AttendeeIntelligence:
    """Rich intelligence about meeting attendees"""
    name: str
    email: str
    relationship_score: float
    recent_communications: List[Dict]
    business_context: str
    preparation_notes: str
    conversation_starters: List[str]

@dataclass
class MeetingIntelligence:
    """Comprehensive meeting intelligence"""
    meeting_title: str
    business_context: str
    attendee_intelligence: List[AttendeeIntelligence]
    preparation_tasks: List[Dict]
    discussion_topics: List[Dict]
    strategic_importance: float
    success_probability: float
    outcome_predictions: List[str]

class IntelligenceEngine:
    """The core intelligence engine that makes everything useful"""
    
    def __init__(self):
        from config.settings import settings
        
        self.claude_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL  # Now uses Claude 4 Opus from settings
        
    def generate_meeting_intelligence(self, user_id: int, event: Calendar) -> Optional[MeetingIntelligence]:
        """Generate comprehensive meeting intelligence with preparation tasks"""
        try:
            logger.info(f"Generating meeting intelligence for: {event.title}")
            
            # Step 1: Gather attendee intelligence
            attendee_intelligence = self._gather_attendee_intelligence(user_id, event)
            
            # Step 2: Find related email context
            email_context = self._find_meeting_email_context(user_id, event, attendee_intelligence)
            
            # Step 3: Generate AI-powered meeting analysis
            meeting_analysis = self._generate_ai_meeting_analysis(event, attendee_intelligence, email_context)
            
            if not meeting_analysis:
                return None
                
            # Step 4: Create preparation tasks based on analysis
            prep_tasks = self._create_preparation_tasks(user_id, event, meeting_analysis, attendee_intelligence)
            
            # Step 5: Generate proactive insights
            self._create_meeting_insights(user_id, event, meeting_analysis, attendee_intelligence)
            
            return MeetingIntelligence(
                meeting_title=event.title or "Unknown Meeting",
                business_context=meeting_analysis.get('business_context', ''),
                attendee_intelligence=attendee_intelligence,
                preparation_tasks=prep_tasks,
                discussion_topics=meeting_analysis.get('discussion_topics', []),
                strategic_importance=meeting_analysis.get('strategic_importance', 0.5),
                success_probability=meeting_analysis.get('success_probability', 0.5),
                outcome_predictions=meeting_analysis.get('outcome_predictions', [])
            )
            
        except Exception as e:
            logger.error(f"Failed to generate meeting intelligence: {str(e)}")
            return None
    
    def _gather_attendee_intelligence(self, user_id: int, event: Calendar) -> List[AttendeeIntelligence]:
        """Gather rich intelligence about meeting attendees"""
        attendees = []
        
        if not event.attendee_emails:
            return attendees
            
        db_manager = get_db_manager()
        
        for email in event.attendee_emails:
            if not email:
                continue
                
            # Find person in database
            person = db_manager.find_person_by_email(user_id, email)
            
            if person:
                # Get recent communications
                recent_comms = self._get_recent_communications(user_id, email)
                
                # Calculate relationship score
                relationship_score = self._calculate_relationship_score(person, recent_comms)
                
                # Generate business context
                business_context = self._generate_person_business_context(person, recent_comms)
                
                # Generate preparation notes
                prep_notes = self._generate_preparation_notes(person, recent_comms, event)
                
                # Generate conversation starters
                conversation_starters = self._generate_conversation_starters(person, recent_comms)
                
                attendee_intel = AttendeeIntelligence(
                    name=person.name,
                    email=email,
                    relationship_score=relationship_score,
                    recent_communications=recent_comms,
                    business_context=business_context,
                    preparation_notes=prep_notes,
                    conversation_starters=conversation_starters
                )
                attendees.append(attendee_intel)
            else:
                # Unknown attendee - still provide basic intelligence
                attendee_intel = AttendeeIntelligence(
                    name=email.split('@')[0].replace('.', ' ').title(),
                    email=email,
                    relationship_score=0.1,
                    recent_communications=[],
                    business_context=f"New contact from {email.split('@')[1]}",
                    preparation_notes=f"First meeting with {email} - opportunity to build new relationship",
                    conversation_starters=[f"How did you get involved with this project?", "What's your role at {email.split('@')[1]}?"]
                )
                attendees.append(attendee_intel)
        
        return attendees
    
    def _find_meeting_email_context(self, user_id: int, event: Calendar, attendees: List[AttendeeIntelligence]) -> Dict:
        """Find email context related to this meeting"""
        db_manager = get_db_manager()
        
        with db_manager.get_session() as session:
            # Look for emails mentioning meeting topics or from attendees
            attendee_emails = [a.email for a in attendees]
            
            # Get emails from attendees in the last 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            related_emails = session.query(Email).filter(
                Email.user_id == user_id,
                Email.sender.in_(attendee_emails),
                Email.email_date > cutoff_date
            ).order_by(Email.email_date.desc()).limit(10).all()
            
            # Also look for emails mentioning meeting title keywords
            if event.title:
                title_keywords = [word.lower() for word in event.title.split() if len(word) > 3]
                if title_keywords:
                    keyword_emails = session.query(Email).filter(
                        Email.user_id == user_id,
                        Email.email_date > cutoff_date
                    ).all()
                    
                    # Filter by keyword matching
                    keyword_matches = []
                    for email in keyword_emails:
                        content = f"{email.subject or ''} {email.ai_summary or ''}".lower()
                        if any(keyword in content for keyword in title_keywords):
                            keyword_matches.append(email)
                    
                    related_emails.extend(keyword_matches[:5])  # Add top 5 keyword matches
            
            session.expunge_all()
            
            return {
                'related_emails': related_emails,
                'attendee_communications': len(related_emails),
                'recent_topics': self._extract_topics_from_emails(related_emails),
                'key_decisions': self._extract_decisions_from_emails(related_emails),
                'shared_context': self._extract_shared_context(related_emails)
            }
    
    def _generate_ai_meeting_analysis(self, event: Calendar, attendees: List[AttendeeIntelligence], email_context: Dict) -> Optional[Dict]:
        """Generate AI-powered meeting analysis"""
        try:
            # Prepare context for Claude
            meeting_context = self._prepare_meeting_context(event, attendees, email_context)
            
            system_prompt = """You are an expert executive assistant AI that specializes in meeting preparation and business intelligence. Your goal is to generate actionable meeting intelligence that will help the user have more effective, productive meetings.

Analyze the meeting and attendee information to provide:

1. **Business Context**: What is this meeting really about? What are the underlying business objectives?
2. **Strategic Importance**: How important is this meeting to business success?
3. **Preparation Tasks**: Specific, actionable tasks the user should complete before the meeting
4. **Discussion Topics**: Key topics to discuss based on recent communications and relationships
5. **Success Probability**: Likelihood this meeting will achieve its objectives
6. **Outcome Predictions**: Likely outcomes and next steps from this meeting

Focus on being practical and actionable. Generate insights that will actually help the user succeed in this meeting.

Return a JSON object with this structure:
{
    "business_context": "Detailed explanation of what this meeting is really about and why it matters",
    "strategic_importance": 0.8,
    "preparation_tasks": [
        {
            "task": "Specific preparation task",
            "rationale": "Why this is important",
            "priority": "high|medium|low",
            "time_needed": "15 minutes",
            "category": "research|review|prepare_materials|contact_followup"
        }
    ],
    "discussion_topics": [
        {
            "topic": "Key discussion topic",
            "context": "Background based on recent communications",
            "talking_points": ["Specific point 1", "Specific point 2"],
            "priority": "high|medium|low"
        }
    ],
    "success_probability": 0.7,
    "outcome_predictions": [
        "Likely outcome 1 based on context",
        "Potential challenge to prepare for"
    ],
    "attendee_dynamics": "Analysis of how attendees might interact",
    "key_opportunities": ["Opportunity 1", "Opportunity 2"],
    "potential_obstacles": ["Challenge 1", "Challenge 2"]
}"""

            user_prompt = f"""Analyze this meeting and generate comprehensive preparation intelligence:

{meeting_context}

Focus on generating actionable preparation tasks and discussion topics that will help make this meeting successful. Be specific and practical."""

            message = self.claude_client.messages.create(
                model=self.model,
                max_tokens=3000,
                temperature=0.1,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            
            response_text = message.content[0].text.strip()
            
            # Parse JSON response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                return json.loads(json_text)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to generate AI meeting analysis: {str(e)}")
            return None
    
    def _create_preparation_tasks(self, user_id: int, event: Calendar, analysis: Dict, attendees: List[AttendeeIntelligence]) -> List[Dict]:
        """Create specific preparation tasks based on meeting analysis"""
        db_manager = get_db_manager()
        created_tasks = []
        
        # Get preparation tasks from AI analysis
        prep_tasks = analysis.get('preparation_tasks', [])
        
        for task_info in prep_tasks:
            # Calculate due date (before meeting)
            meeting_time = event.start_time
            if meeting_time:
                # Tasks should be completed 1-2 hours before meeting
                due_time = meeting_time - timedelta(hours=2)
            else:
                due_time = datetime.utcnow() + timedelta(hours=24)
            
            task_data = {
                'description': task_info.get('task', 'Meeting preparation task'),
                'category': 'meeting_prep',
                'priority': task_info.get('priority', 'medium'),
                'due_date': due_time,
                'due_date_text': f"Before {event.title}",
                'source_text': f"AI-generated preparation for: {event.title}",
                'context': f"{task_info.get('rationale', '')} | Time needed: {task_info.get('time_needed', '15 minutes')}",
                'confidence': 0.9,
                'comprehensive_context_story': self._generate_task_context_story(task_info, event, attendees),
                'detailed_task_meaning': self._generate_task_meaning(task_info, event),
                'comprehensive_importance_analysis': self._generate_task_importance(task_info, event, analysis),
                'comprehensive_origin_details': f"Generated by AI for meeting '{event.title}' scheduled for {event.start_time}"
            }
            
            task = db_manager.create_or_update_task(user_id, task_data)
            if task:
                created_tasks.append(task.to_dict())
        
        return created_tasks
    
    def _create_meeting_insights(self, user_id: int, event: Calendar, analysis: Dict, attendees: List[AttendeeIntelligence]):
        """Create proactive insights about the meeting"""
        db_manager = get_db_manager()
        
        # Meeting preparation insight
        if analysis.get('strategic_importance', 0) > 0.6:
            insight_data = {
                'insight_type': 'meeting_prep',
                'title': f"High-value meeting preparation needed: {event.title}",
                'description': f"This meeting has high strategic importance ({analysis.get('strategic_importance', 0):.1f}/1.0). {analysis.get('business_context', '')}",
                'priority': 'high' if analysis.get('strategic_importance', 0) > 0.8 else 'medium',
                'confidence': 0.9,
                'related_entity_type': 'event',
                'related_entity_id': event.id,
                'action_required': True,
                'action_due_date': event.start_time - timedelta(hours=2) if event.start_time else None,
                'expires_at': event.start_time
            }
            db_manager.create_intelligence_insight(user_id, insight_data)
        
        # Relationship insights
        for attendee in attendees:
            if attendee.relationship_score > 0.7:
                insight_data = {
                    'insight_type': 'relationship_opportunity',
                    'title': f"Strong relationship opportunity with {attendee.name}",
                    'description': f"You have a strong relationship with {attendee.name} (score: {attendee.relationship_score:.1f}). {attendee.preparation_notes}",
                    'priority': 'medium',
                    'confidence': 0.8,
                    'related_entity_type': 'person',
                    'expires_at': event.start_time + timedelta(days=1)
                }
                db_manager.create_intelligence_insight(user_id, insight_data)
    
    def generate_proactive_insights(self, user_id: int) -> List[IntelligenceInsight]:
        """Generate proactive business insights"""
        db_manager = get_db_manager()
        insights = []
        
        # Check for upcoming meetings needing preparation
        upcoming_meetings = db_manager.get_upcoming_meetings_needing_prep(user_id, 48)
        
        for meeting in upcoming_meetings:
            hours_until = (meeting.start_time - datetime.utcnow()).total_seconds() / 3600
            
            if hours_until > 0 and hours_until < 24:
                insight_data = {
                    'insight_type': 'meeting_prep',
                    'title': f"Meeting preparation needed: {meeting.title}",
                    'description': f"Meeting in {hours_until:.1f} hours. Preparation recommended based on meeting importance and attendees.",
                    'priority': 'high' if hours_until < 4 else 'medium',
                    'confidence': 0.9,
                    'related_entity_type': 'event',
                    'related_entity_id': meeting.id,
                    'action_required': True,
                    'action_due_date': meeting.start_time - timedelta(hours=1),
                    'expires_at': meeting.start_time
                }
                insight = db_manager.create_intelligence_insight(user_id, insight_data)
                insights.append(insight)
        
        # Check for relationship maintenance opportunities
        self._generate_relationship_insights(user_id, insights)
        
        # Check for topic momentum opportunities
        self._generate_topic_insights(user_id, insights)
        
        return insights
    
    def _generate_relationship_insights(self, user_id: int, insights: List[IntelligenceInsight]):
        """Generate relationship maintenance insights"""
        db_manager = get_db_manager()
        
        # Find people who haven't been contacted recently but have high engagement
        with db_manager.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=14)
            
            inactive_relationships = session.query(Person).filter(
                Person.user_id == user_id,
                Person.importance_level > 0.7,
                Person.last_interaction < cutoff_date
            ).limit(5).all()
            
            for person in inactive_relationships:
                days_since = (datetime.utcnow() - person.last_interaction).days
                
                insight_data = {
                    'insight_type': 'relationship_maintenance',
                    'title': f"Reconnect with {person.name}",
                    'description': f"It's been {days_since} days since your last interaction with {person.name} ({person.company or 'important contact'}). Consider reaching out to maintain this valuable relationship.",
                    'priority': 'medium',
                    'confidence': 0.7,
                    'related_entity_type': 'person',
                    'related_entity_id': person.id,
                    'action_required': True
                }
                insight = db_manager.create_intelligence_insight(user_id, insight_data)
                insights.append(insight)
    
    def _generate_topic_insights(self, user_id: int, insights: List[IntelligenceInsight]):
        """Generate topic momentum insights"""
        db_manager = get_db_manager()
        
        # Find topics with recent momentum
        with db_manager.get_session() as session:
            recent_date = datetime.utcnow() - timedelta(days=7)
            
            # Get recent emails with topics
            recent_emails = session.query(Email).filter(
                Email.user_id == user_id,
                Email.email_date > recent_date,
                Email.topics.isnot(None)
            ).all()
            
            # Count topic mentions
            topic_counts = {}
            for email in recent_emails:
                if email.topics:
                    for topic in email.topics:
                        topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            # Find trending topics
            for topic, count in topic_counts.items():
                if count >= 3:  # Mentioned in 3+ emails this week
                    insight_data = {
                        'insight_type': 'topic_momentum',
                        'title': f"Trending topic: {topic}",
                        'description': f"'{topic}' has been mentioned in {count} recent communications. This might be a good time to take action or follow up on this topic.",
                        'priority': 'medium',
                        'confidence': 0.6,
                        'action_required': False
                    }
                    insight = db_manager.create_intelligence_insight(user_id, insight_data)
                    insights.append(insight)
    
    # Helper methods for context generation
    def _prepare_meeting_context(self, event: Calendar, attendees: List[AttendeeIntelligence], email_context: Dict) -> str:
        """Prepare meeting context for AI analysis"""
        context = f"""MEETING ANALYSIS REQUEST

Meeting Details:
- Title: {event.title or 'Unknown'}
- Date/Time: {event.start_time}
- Duration: {(event.end_time - event.start_time).total_seconds() / 3600:.1f} hours
- Location: {event.location or 'Not specified'}
- Description: {event.description or 'No description'}

Attendees ({len(attendees)} people):"""

        for attendee in attendees:
            context += f"\n- {attendee.name} ({attendee.email})"
            context += f"\n  * Relationship Score: {attendee.relationship_score:.1f}/1.0"
            context += f"\n  * Business Context: {attendee.business_context}"
            if attendee.recent_communications:
                context += f"\n  * Recent Communications: {len(attendee.recent_communications)} emails"

        context += f"\n\nEmail Context:"
        context += f"\n- Related emails found: {email_context.get('attendee_communications', 0)}"
        if email_context.get('recent_topics'):
            context += f"\n- Recent topics: {', '.join(email_context['recent_topics'][:5])}"
        if email_context.get('key_decisions'):
            context += f"\n- Key decisions mentioned: {', '.join(email_context['key_decisions'][:3])}"

        return context
    
    def _get_recent_communications(self, user_id: int, email: str) -> List[Dict]:
        """Get recent communications with a person"""
        db_manager = get_db_manager()
        
        with db_manager.get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            emails = session.query(Email).filter(
                Email.user_id == user_id,
                Email.sender == email,
                Email.email_date > cutoff_date
            ).order_by(Email.email_date.desc()).limit(5).all()
            
            return [
                {
                    'subject': email.subject,
                    'date': email.email_date,
                    'summary': email.ai_summary,
                    'strategic_importance': email.strategic_importance or 0.5
                }
                for email in emails
            ]
    
    def _calculate_relationship_score(self, person: Person, recent_comms: List[Dict]) -> float:
        """Calculate relationship strength score"""
        base_score = person.importance_level or 0.5
        
        # Boost for recent communications
        comm_boost = min(0.3, len(recent_comms) * 0.1)
        
        # Boost for strategic communications
        strategic_boost = 0
        for comm in recent_comms:
            if comm.get('strategic_importance', 0) > 0.7:
                strategic_boost += 0.1
        
        return min(1.0, base_score + comm_boost + strategic_boost)
    
    def _generate_person_business_context(self, person: Person, recent_comms: List[Dict]) -> str:
        """Generate business context for a person"""
        context_parts = []
        
        if person.title and person.company:
            context_parts.append(f"{person.title} at {person.company}")
        elif person.company:
            context_parts.append(f"Works at {person.company}")
        elif person.title:
            context_parts.append(f"{person.title}")
        
        if person.relationship_type:
            context_parts.append(f"Relationship: {person.relationship_type}")
        
        if recent_comms:
            recent_topics = []
            for comm in recent_comms[:2]:
                if comm.get('summary'):
                    recent_topics.append(comm['summary'][:100])
            if recent_topics:
                context_parts.append(f"Recent discussions: {'; '.join(recent_topics)}")
        
        return '. '.join(context_parts) if context_parts else "Professional contact"
    
    def _generate_preparation_notes(self, person: Person, recent_comms: List[Dict], event: Calendar) -> str:
        """Generate preparation notes for meeting with this person"""
        notes = []
        
        if recent_comms:
            notes.append(f"Recent context: {recent_comms[0].get('summary', 'Previous communication')}")
        
        if person.key_topics:
            topics = person.key_topics[:3] if isinstance(person.key_topics, list) else [str(person.key_topics)]
            notes.append(f"Key interests: {', '.join(topics)}")
        
        if person.notes:
            notes.append(f"Background: {person.notes[:150]}")
        
        return '. '.join(notes) if notes else f"First documented meeting with {person.name}"
    
    def _generate_conversation_starters(self, person: Person, recent_comms: List[Dict]) -> List[str]:
        """Generate conversation starters"""
        starters = ["How has your week been?"]
        
        if recent_comms and recent_comms[0].get('summary'):
            starters.append(f"Following up on {recent_comms[0]['summary'][:50]}...")
        
        if person.company:
            starters.append(f"How are things going at {person.company}?")
        
        if person.key_topics and isinstance(person.key_topics, list):
            if person.key_topics:
                starters.append(f"Any updates on {person.key_topics[0]}?")
        
        return starters[:3]
    
    def _extract_topics_from_emails(self, emails: List[Email]) -> List[str]:
        """Extract topics from emails"""
        topics = set()
        for email in emails:
            if email.topics and isinstance(email.topics, list):
                topics.update(email.topics[:3])
        return list(topics)[:5]
    
    def _extract_decisions_from_emails(self, emails: List[Email]) -> List[str]:
        """Extract key decisions from emails"""
        decisions = []
        for email in emails:
            if email.key_insights and isinstance(email.key_insights, dict):
                email_decisions = email.key_insights.get('key_decisions', [])
                if isinstance(email_decisions, list):
                    decisions.extend(email_decisions[:2])
        return decisions[:3]
    
    def _extract_shared_context(self, emails: List[Email]) -> str:
        """Extract shared context from emails"""
        if not emails:
            return "No recent shared context found"
        
        summaries = [email.ai_summary for email in emails[:3] if email.ai_summary]
        if summaries:
            return f"Recent shared discussions: {' | '.join(summaries[:2])}"
        
        return "Recent communications available"
    
    def _generate_task_context_story(self, task_info: Dict, event: Calendar, attendees: List[AttendeeIntelligence]) -> str:
        """Generate comprehensive context story for preparation task"""
        story_parts = []
        
        story_parts.append(f"📅 **Meeting Preparation Task for:** {event.title}")
        story_parts.append(f"⏰ **Meeting Time:** {event.start_time.strftime('%A, %B %d at %I:%M %p')}")
        
        if attendees:
            attendee_names = [a.name for a in attendees[:3]]
            story_parts.append(f"👥 **Key Attendees:** {', '.join(attendee_names)}")
        
        story_parts.append(f"🎯 **Task Purpose:** {task_info.get('rationale', 'Meeting preparation')}")
        story_parts.append(f"⏱️ **Time Investment:** {task_info.get('time_needed', '15 minutes')}")
        
        return "\n".join(story_parts)
    
    def _generate_task_meaning(self, task_info: Dict, event: Calendar) -> str:
        """Generate detailed task meaning"""
        meaning_parts = []
        
        meaning_parts.append(f"📋 **What You Need to Do:** {task_info.get('task', 'Complete preparation task')}")
        meaning_parts.append(f"🎯 **Why This Matters:** {task_info.get('rationale', 'This preparation will help ensure meeting success')}")
        meaning_parts.append(f"📅 **Context:** This task should be completed before your meeting '{event.title}'")
        
        category = task_info.get('category', 'general')
        if category == 'research':
            meaning_parts.append("🔍 **Action Type:** Research and information gathering")
        elif category == 'review':
            meaning_parts.append("📖 **Action Type:** Review and analysis of existing materials")
        elif category == 'prepare_materials':
            meaning_parts.append("📁 **Action Type:** Prepare documents or presentation materials")
        elif category == 'contact_followup':
            meaning_parts.append("📞 **Action Type:** Reach out to contacts for information or confirmation")
        
        return "\n".join(meaning_parts)
    
    def _generate_task_importance(self, task_info: Dict, event: Calendar, analysis: Dict) -> str:
        """Generate comprehensive importance analysis"""
        importance_parts = []
        
        priority = task_info.get('priority', 'medium')
        if priority == 'high':
            importance_parts.append("🚨 **Priority Level:** HIGH - This task is critical for meeting success")
        elif priority == 'medium':
            importance_parts.append("⚠️ **Priority Level:** MEDIUM - This task will significantly improve meeting outcomes")
        else:
            importance_parts.append("📝 **Priority Level:** Standard preparation task")
        
        strategic_importance = analysis.get('strategic_importance', 0.5)
        if strategic_importance > 0.8:
            importance_parts.append("⭐ **Strategic Value:** This meeting has very high strategic importance")
        elif strategic_importance > 0.6:
            importance_parts.append("⭐ **Strategic Value:** This meeting has significant strategic value")
        
        importance_parts.append(f"💼 **Business Impact:** {analysis.get('business_context', 'Important for business relationships and outcomes')}")
        
        return "\n".join(importance_parts)

# Global intelligence engine instance
intelligence_engine = IntelligenceEngine() 