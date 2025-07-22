# Enhanced Email Processor - Entity-Centric Email Intelligence
# This replaces the old email_intelligence.py with unified entity engine integration

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import json
import re

from processors.unified_entity_engine import entity_engine, EntityContext
from processors.enhanced_ai_pipeline import enhanced_ai_processor
from processors.realtime_processor import realtime_processor
from models.enhanced_models import Email, Person, Topic, Task, CalendarEvent

logger = logging.getLogger(__name__)

class EnhancedEmailProcessor:
    """
    Enhanced email processor that leverages the unified entity engine and real-time processing.
    This replaces the old email_intelligence.py with context-aware, entity-integrated email analysis.
    """
    
    def __init__(self):
        self.entity_engine = entity_engine
        self.ai_processor = enhanced_ai_processor
        self.realtime_processor = realtime_processor
        
    # =====================================================================
    # MAIN EMAIL PROCESSING METHODS
    # =====================================================================
    
    def process_email_comprehensive(self, email_data: Dict, user_id: int, 
                                   real_time: bool = True) -> Dict[str, Any]:
        """
        Comprehensive email processing with entity creation and relationship building.
        This is the main entry point that replaces old email processing.
        """
        try:
            logger.info(f"Processing email comprehensively for user {user_id}")
            
            # Step 1: Normalize email data
            normalized_email = self._normalize_email_data(email_data)
            
            # Step 2: Check for duplicates
            if self._is_duplicate_email(normalized_email, user_id):
                logger.info(f"Duplicate email detected, skipping processing")
                return {'success': True, 'result': {'status': 'duplicate', 'processed': False}}
            
            # Step 3: Use enhanced AI pipeline for comprehensive processing
            if real_time:
                # Queue for real-time processing
                self.realtime_processor.process_new_email(normalized_email, user_id, priority=5)
                
                return {
                    'success': True, 
                    'result': {
                        'status': 'queued_for_realtime',
                        'processed': True,
                        'message': 'Email queued for real-time intelligence processing'
                    }
                }
            else:
                # Process immediately
                result = self.ai_processor.process_email_with_context(normalized_email, user_id)
                
                if result.success:
                    # Extract comprehensive processing summary
                    summary = {
                        'email_id': normalized_email.get('gmail_id'),
                        'processing_summary': {
                            'entities_created': result.entities_created,
                            'entities_updated': result.entities_updated,
                            'processing_time': result.processing_time,
                            'insights_generated': len(result.insights_generated)
                        },
                        'intelligence_summary': self._create_intelligence_summary(result, normalized_email),
                        'entity_relationships': self._extract_entity_relationships(result),
                        'action_items': self._extract_action_items(result),
                        'strategic_insights': result.insights_generated
                    }
                    
                    logger.info(f"Successfully processed email: {summary['processing_summary']}")
                    return {'success': True, 'result': summary}
                else:
                    logger.error(f"Failed to process email: {result.error}")
                    return {'success': False, 'error': result.error}
                    
        except Exception as e:
            logger.error(f"Error in comprehensive email processing: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def process_email_batch(self, email_list: List[Dict], user_id: int, 
                           batch_size: int = 10) -> Dict[str, Any]:
        """
        Process multiple emails in batches with efficiency optimizations.
        """
        try:
            logger.info(f"Processing batch of {len(email_list)} emails for user {user_id}")
            
            # Get user context once for the entire batch
            user_context = self.ai_processor._gather_user_context(user_id)
            
            results = {
                'total_emails': len(email_list),
                'processed': 0,
                'failed': 0,
                'duplicates': 0,
                'batch_summary': {
                    'total_entities_created': {'people': 0, 'topics': 0, 'tasks': 0, 'projects': 0},
                    'total_insights': 0,
                    'processing_time': 0.0
                },
                'individual_results': []
            }
            
            # Process in batches
            for i in range(0, len(email_list), batch_size):
                batch = email_list[i:i + batch_size]
                batch_results = self._process_email_batch_chunk(batch, user_id, user_context)
                
                # Aggregate results
                for result in batch_results:
                    results['individual_results'].append(result)
                    
                    if result['success']:
                        if result['result'].get('status') == 'duplicate':
                            results['duplicates'] += 1
                        else:
                            results['processed'] += 1
                            # Aggregate batch summary
                            processing_summary = result['result'].get('processing_summary', {})
                            entities_created = processing_summary.get('entities_created', {})
                            
                            for entity_type, count in entities_created.items():
                                results['batch_summary']['total_entities_created'][entity_type] += count
                                
                            results['batch_summary']['total_insights'] += processing_summary.get('insights_generated', 0)
                            results['batch_summary']['processing_time'] += processing_summary.get('processing_time', 0)
                    else:
                        results['failed'] += 1
            
            logger.info(f"Batch processing complete: {results['processed']} processed, "
                       f"{results['failed']} failed, {results['duplicates']} duplicates")
            
            return {'success': True, 'result': results}
            
        except Exception as e:
            logger.error(f"Error in batch email processing: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def analyze_email_patterns(self, user_id: int, days_back: int = 30) -> Dict[str, Any]:
        """
        Analyze email communication patterns and generate insights.
        """
        try:
            from chief_of_staff_ai.models.database import get_db_manager
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            
            with get_db_manager().get_session() as session:
                emails = session.query(Email).filter(
                    Email.user_id == user_id,
                    Email.email_date > cutoff_date
                ).all()
                
                patterns = {
                    'total_emails': len(emails),
                    'communication_patterns': self._analyze_communication_patterns(emails),
                    'topic_trends': self._analyze_topic_trends(emails, user_id),
                    'relationship_activity': self._analyze_relationship_activity(emails, user_id),
                    'business_intelligence': self._generate_business_intelligence(emails, user_id),
                    'productivity_insights': self._generate_productivity_insights_from_emails(emails),
                    'strategic_recommendations': self._generate_strategic_recommendations(emails, user_id)
                }
                
                return {'success': True, 'result': patterns}
                
        except Exception as e:
            logger.error(f"Error analyzing email patterns: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # =====================================================================
    # EMAIL INTELLIGENCE EXTRACTION
    # =====================================================================
    
    def extract_meeting_requests(self, email_data: Dict, user_id: int) -> Dict[str, Any]:
        """
        Extract meeting requests and create calendar preparation tasks.
        """
        try:
            # Check if email contains meeting-related content
            email_content = email_data.get('body_clean', '')
            subject = email_data.get('subject', '')
            
            meeting_indicators = [
                'meeting', 'call', 'discussion', 'catch up', 'sync',
                'available', 'schedule', 'calendar', 'time', 'when'
            ]
            
            has_meeting_content = any(indicator in email_content.lower() or 
                                    indicator in subject.lower() 
                                    for indicator in meeting_indicators)
            
            if not has_meeting_content:
                return {'success': True, 'result': {'has_meeting_request': False}}
            
            # Use AI to extract meeting details
            meeting_extraction_prompt = self._create_meeting_extraction_prompt(email_data)
            
            # This would call Claude to extract meeting details
            # For now, return a structured response
            meeting_info = {
                'has_meeting_request': True,
                'meeting_type': 'discussion',
                'suggested_participants': [email_data.get('sender')],
                'topic_hints': self._extract_topic_hints_from_content(email_content),
                'urgency_level': self._assess_meeting_urgency(email_content, subject),
                'preparation_tasks': self._generate_meeting_prep_tasks(email_data, user_id)
            }
            
            return {'success': True, 'result': meeting_info}
            
        except Exception as e:
            logger.error(f"Error extracting meeting requests: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def extract_business_context(self, email_data: Dict, user_id: int) -> Dict[str, Any]:
        """
        Extract business context and strategic intelligence from email.
        """
        try:
            # Get user context for enhanced analysis
            user_context = self.ai_processor._gather_user_context(user_id)
            
            context_analysis = {
                'business_category': self._categorize_business_content(email_data),
                'strategic_importance': self._assess_strategic_importance(email_data, user_context),
                'stakeholder_analysis': self._analyze_stakeholders(email_data, user_id),
                'project_connections': self._identify_project_connections(email_data, user_context),
                'decision_points': self._extract_decision_points(email_data),
                'follow_up_requirements': self._identify_follow_up_requirements(email_data),
                'competitive_intelligence': self._extract_competitive_intelligence(email_data),
                'opportunity_signals': self._detect_opportunity_signals(email_data, user_context)
            }
            
            return {'success': True, 'result': context_analysis}
            
        except Exception as e:
            logger.error(f"Error extracting business context: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def enhance_with_historical_context(self, email_data: Dict, user_id: int) -> Dict[str, Any]:
        """
        Enhance email analysis with historical communication context.
        """
        try:
            sender_email = email_data.get('sender', '')
            if not sender_email:
                return {'success': True, 'result': {'has_history': False}}
            
            # Get historical communication with this sender
            historical_context = self._get_sender_history(sender_email, user_id)
            
            if not historical_context:
                return {'success': True, 'result': {'has_history': False}}
            
            # Analyze communication patterns
            enhancement = {
                'has_history': True,
                'communication_frequency': historical_context['frequency'],
                'relationship_strength': historical_context['strength'],
                'common_topics': historical_context['topics'],
                'interaction_patterns': historical_context['patterns'],
                'relationship_trajectory': self._analyze_relationship_trajectory(historical_context),
                'contextual_insights': self._generate_contextual_insights(email_data, historical_context),
                'recommended_response_tone': self._recommend_response_tone(historical_context),
                'priority_adjustment': self._adjust_priority_with_history(email_data, historical_context)
            }
            
            return {'success': True, 'result': enhancement}
            
        except Exception as e:
            logger.error(f"Error enhancing with historical context: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    # =====================================================================
    # HELPER METHODS
    # =====================================================================
    
    def _normalize_email_data(self, email_data: Dict) -> Dict:
        """Normalize email data for consistent processing"""
        normalized = email_data.copy()
        
        # Ensure required fields exist
        required_fields = ['gmail_id', 'subject', 'sender', 'body_clean', 'email_date']
        for field in required_fields:
            if field not in normalized:
                normalized[field] = ''
        
        # Clean and normalize text fields
        if normalized.get('subject'):
            normalized['subject'] = self._clean_text(normalized['subject'])
        
        if normalized.get('body_clean'):
            normalized['body_clean'] = self._clean_text(normalized['body_clean'])
        
        # Normalize sender email
        if normalized.get('sender'):
            normalized['sender'] = normalized['sender'].lower().strip()
        
        return normalized
    
    def _is_duplicate_email(self, email_data: Dict, user_id: int) -> bool:
        """Check if email has already been processed with AI"""
        try:
            from chief_of_staff_ai.models.database import get_db_manager
            
            gmail_id = email_data.get('gmail_id')
            if not gmail_id:
                return False
            
            with get_db_manager().get_session() as session:
                existing = session.query(Email).filter(
                    Email.user_id == user_id,
                    Email.gmail_id == gmail_id,
                    Email.ai_summary.isnot(None)  # Only consider it duplicate if AI-processed
                ).first()
                
                return existing is not None
                
        except Exception as e:
            logger.error(f"Error checking for duplicate email: {str(e)}")
            return False
    
    def _process_email_batch_chunk(self, email_batch: List[Dict], user_id: int, user_context: Dict) -> List[Dict]:
        """Process a chunk of emails in a batch"""
        results = []
        
        for email_data in email_batch:
            try:
                # Use cached context for efficiency
                result = self.ai_processor.process_email_with_context(
                    email_data, user_id, user_context
                )
                
                if result.success:
                    summary = {
                        'email_id': email_data.get('gmail_id'),
                        'processing_summary': {
                            'entities_created': result.entities_created,
                            'entities_updated': result.entities_updated,
                            'processing_time': result.processing_time,
                            'insights_generated': len(result.insights_generated)
                        }
                    }
                    results.append({'success': True, 'result': summary})
                else:
                    results.append({'success': False, 'error': result.error})
                    
            except Exception as e:
                results.append({'success': False, 'error': str(e)})
        
        return results
    
    def _create_intelligence_summary(self, result: Any, email_data: Dict) -> Dict:
        """Create intelligence summary from processing result"""
        return {
            'business_summary': 'Email processed with entity-centric intelligence',
            'key_entities': {
                'people_mentioned': result.entities_created.get('people', 0),
                'topics_discussed': result.entities_created.get('topics', 0),
                'tasks_extracted': result.entities_created.get('tasks', 0),
                'projects_referenced': result.entities_created.get('projects', 0)
            },
            'strategic_value': 'Medium',  # This would be calculated
            'follow_up_required': result.entities_created.get('tasks', 0) > 0
        }
    
    def _extract_entity_relationships(self, result: Any) -> List[Dict]:
        """Extract entity relationships from processing result"""
        # This would extract actual relationships
        # For now return placeholder
        return [
            {
                'relationship_type': 'person_discusses_topic',
                'entities': ['person:1', 'topic:2'],
                'strength': 0.8
            }
        ]
    
    def _extract_action_items(self, result: Any) -> List[Dict]:
        """Extract action items from processing result"""
        action_items = []
        
        # Tasks created are action items
        if result.entities_created.get('tasks', 0) > 0:
            action_items.append({
                'type': 'tasks_created',
                'count': result.entities_created['tasks'],
                'description': f"Created {result.entities_created['tasks']} tasks from email analysis"
            })
        
        # People to follow up with
        if result.entities_created.get('people', 0) > 0:
            action_items.append({
                'type': 'relationship_update',
                'count': result.entities_created['people'],
                'description': f"Updated {result.entities_created['people']} person profiles"
            })
        
        return action_items
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ''
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove HTML entities
        text = re.sub(r'&[a-zA-Z0-9#]+;', '', text)
        
        return text.strip()
    
    # =====================================================================
    # ANALYSIS METHODS
    # =====================================================================
    
    def _analyze_communication_patterns(self, emails: List[Email]) -> Dict:
        """Analyze communication patterns from emails"""
        patterns = {
            'emails_per_day': len(emails) / 30,  # Assuming 30-day period
            'top_senders': self._get_top_senders(emails),
            'response_time_analysis': self._analyze_response_times(emails),
            'communication_times': self._analyze_communication_times(emails),
            'email_categories': self._categorize_emails(emails)
        }
        return patterns
    
    def _analyze_topic_trends(self, emails: List[Email], user_id: int) -> Dict:
        """Analyze topic trends from email communications"""
        try:
            from chief_of_staff_ai.models.database import get_db_manager
            
            with get_db_manager().get_session() as session:
                # Get topics mentioned in recent emails
                topic_mentions = {}
                
                for email in emails:
                    if hasattr(email, 'primary_topic') and email.primary_topic:
                        topic_name = email.primary_topic.name
                        if topic_name not in topic_mentions:
                            topic_mentions[topic_name] = 0
                        topic_mentions[topic_name] += 1
                
                # Sort by frequency
                trending_topics = sorted(topic_mentions.items(), key=lambda x: x[1], reverse=True)
                
                return {
                    'trending_topics': trending_topics[:10],
                    'total_topics_discussed': len(topic_mentions),
                    'topic_distribution': topic_mentions
                }
                
        except Exception as e:
            logger.error(f"Error analyzing topic trends: {str(e)}")
            return {}
    
    def _analyze_relationship_activity(self, emails: List[Email], user_id: int) -> Dict:
        """Analyze relationship activity from emails"""
        sender_activity = {}
        
        for email in emails:
            sender = email.sender
            if sender not in sender_activity:
                sender_activity[sender] = {
                    'email_count': 0,
                    'last_contact': None,
                    'avg_importance': 0
                }
            
            sender_activity[sender]['email_count'] += 1
            sender_activity[sender]['last_contact'] = email.email_date
            
            if email.strategic_importance:
                current_avg = sender_activity[sender]['avg_importance']
                count = sender_activity[sender]['email_count']
                sender_activity[sender]['avg_importance'] = (
                    (current_avg * (count - 1) + email.strategic_importance) / count
                )
        
        # Sort by activity level
        active_relationships = sorted(
            sender_activity.items(), 
            key=lambda x: x[1]['email_count'], 
            reverse=True
        )
        
        return {
            'most_active_contacts': active_relationships[:10],
            'total_unique_contacts': len(sender_activity),
            'relationship_distribution': sender_activity
        }
    
    def _generate_business_intelligence(self, emails: List[Email], user_id: int) -> Dict:
        """Generate business intelligence from email patterns"""
        intelligence = {
            'communication_health': self._assess_communication_health(emails),
            'business_momentum': self._assess_business_momentum(emails),
            'opportunity_indicators': self._detect_opportunity_indicators(emails),
            'risk_signals': self._detect_risk_signals(emails),
            'strategic_priorities': self._identify_strategic_priorities(emails)
        }
        return intelligence
    
    def _generate_productivity_insights_from_emails(self, emails: List[Email]) -> List[str]:
        """Generate productivity insights from email analysis"""
        insights = []
        
        # Email volume analysis
        daily_average = len(emails) / 30
        if daily_average > 50:
            insights.append("High email volume detected. Consider email management strategies.")
        elif daily_average < 10:
            insights.append("Low email volume. Good email management or potential communication gaps.")
        
        # Response time analysis
        urgent_emails = [e for e in emails if e.urgency_score and e.urgency_score > 0.7]
        if urgent_emails:
            insights.append(f"{len(urgent_emails)} urgent emails detected. Prioritize timely responses.")
        
        return insights
    
    def _generate_strategic_recommendations(self, emails: List[Email], user_id: int) -> List[str]:
        """Generate strategic recommendations from email analysis"""
        recommendations = []
        
        # Analyze communication patterns for recommendations
        high_importance_emails = [e for e in emails if e.strategic_importance and e.strategic_importance > 0.7]
        
        if high_importance_emails:
            recommendations.append(
                f"Focus on {len(high_importance_emails)} high-importance communications for strategic impact."
            )
        
        # Analyze relationship building opportunities
        unique_senders = len(set(e.sender for e in emails))
        if unique_senders > 20:
            recommendations.append(
                "Consider consolidating communications or delegating to manage relationship bandwidth."
            )
        
        return recommendations
    
    # =====================================================================
    # UTILITY METHODS
    # =====================================================================
    
    def _get_top_senders(self, emails: List[Email]) -> List[Dict]:
        """Get top email senders by frequency"""
        sender_counts = {}
        for email in emails:
            sender = email.sender
            if sender not in sender_counts:
                sender_counts[sender] = 0
            sender_counts[sender] += 1
        
        sorted_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)
        return [{'sender': sender, 'count': count} for sender, count in sorted_senders[:10]]
    
    def _analyze_response_times(self, emails: List[Email]) -> Dict:
        """Analyze email response time patterns"""
        # This would analyze response times between emails in threads
        return {
            'avg_response_time_hours': 4.5,
            'fastest_response_minutes': 15,
            'slowest_response_days': 3
        }
    
    def _analyze_communication_times(self, emails: List[Email]) -> Dict:
        """Analyze when communications typically happen"""
        hour_distribution = {}
        
        for email in emails:
            if email.email_date:
                hour = email.email_date.hour
                if hour not in hour_distribution:
                    hour_distribution[hour] = 0
                hour_distribution[hour] += 1
        
        return {
            'peak_hours': sorted(hour_distribution.items(), key=lambda x: x[1], reverse=True)[:3],
            'hourly_distribution': hour_distribution
        }
    
    def _categorize_emails(self, emails: List[Email]) -> Dict:
        """Categorize emails by business type"""
        categories = {}
        
        for email in emails:
            category = email.business_category or 'uncategorized'
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
        
        return categories
    
    def _assess_communication_health(self, emails: List[Email]) -> str:
        """Assess overall communication health"""
        if len(emails) > 100:
            return "High activity"
        elif len(emails) > 50:
            return "Moderate activity"
        else:
            return "Low activity"
    
    def _assess_business_momentum(self, emails: List[Email]) -> str:
        """Assess business momentum from email patterns"""
        high_importance_count = len([e for e in emails if e.strategic_importance and e.strategic_importance > 0.7])
        
        if high_importance_count > 20:
            return "High momentum"
        elif high_importance_count > 10:
            return "Moderate momentum"
        else:
            return "Low momentum"
    
    def _detect_opportunity_indicators(self, emails: List[Email]) -> List[str]:
        """Detect opportunity indicators from emails"""
        indicators = []
        
        # Look for specific keywords or patterns
        opportunity_keywords = ['opportunity', 'partnership', 'proposal', 'deal', 'collaboration']
        
        for email in emails:
            content = (email.ai_summary or '').lower()
            for keyword in opportunity_keywords:
                if keyword in content:
                    indicators.append(f"Opportunity signal: {keyword} mentioned")
                    break
        
        return indicators[:5]  # Limit to top 5
    
    def _detect_risk_signals(self, emails: List[Email]) -> List[str]:
        """Detect risk signals from emails"""
        signals = []
        
        risk_keywords = ['concern', 'issue', 'problem', 'delay', 'budget', 'urgent']
        
        for email in emails:
            content = (email.ai_summary or '').lower()
            for keyword in risk_keywords:
                if keyword in content:
                    signals.append(f"Risk signal: {keyword} mentioned")
                    break
        
        return signals[:5]  # Limit to top 5
    
    def _identify_strategic_priorities(self, emails: List[Email]) -> List[str]:
        """Identify strategic priorities from email patterns"""
        priorities = []
        
        # Analyze high-importance topics
        high_importance_emails = [e for e in emails if e.strategic_importance and e.strategic_importance > 0.7]
        
        if high_importance_emails:
            priorities.append(f"Focus on {len(high_importance_emails)} high-strategic-value communications")
        
        return priorities

# Global instance for easy import
enhanced_email_processor = EnhancedEmailProcessor() 