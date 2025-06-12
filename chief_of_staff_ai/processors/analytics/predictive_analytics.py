"""
Predictive Analytics Engine - Pattern Detection and Future Intelligence
Part of the enhanced AI Chief of Staff refactor implementation
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from collections import defaultdict, Counter
import json

from models.database import get_db_manager
from models.enhanced_models import Topic, Person, Task, Email, CalendarEvent, IntelligenceInsight

logger = logging.getLogger(__name__)

class PredictiveAnalytics:
    """
    Advanced predictive analytics for proactive intelligence generation.
    Detects patterns and predicts future needs based on historical data.
    """
    
    def __init__(self):
        self.db_manager = get_db_manager()
        self.is_running = False
        
    def start(self):
        """Start the predictive analytics engine"""
        self.is_running = True
        logger.info("Predictive Analytics Engine started")
    
    def stop(self):
        """Stop the predictive analytics engine"""
        self.is_running = False
        logger.info("Predictive Analytics Engine stopped")
    
    def analyze_communication_patterns(self, user_id: int) -> Dict:
        """Analyze communication patterns to predict future interactions"""
        try:
            with self.db_manager.get_session() as session:
                # Get recent communication data
                recent_emails = session.query(Email).filter(
                    Email.user_id == user_id,
                    Email.email_date > datetime.utcnow() - timedelta(days=90)
                ).all()
                
                patterns = {
                    'email_frequency': self._analyze_email_frequency(recent_emails),
                    'topic_trends': self._analyze_topic_trends(user_id, session),
                    'relationship_patterns': self._analyze_relationship_patterns(user_id, session),
                    'meeting_patterns': self._analyze_meeting_patterns(user_id, session)
                }
                
                return patterns
                
        except Exception as e:
            logger.error(f"Failed to analyze communication patterns: {str(e)}")
            return {}
    
    def predict_upcoming_needs(self, user_id: int) -> List[Dict]:
        """Predict upcoming needs based on historical patterns"""
        predictions = []
        
        try:
            with self.db_manager.get_session() as session:
                # Predict meeting preparation needs
                meeting_predictions = self._predict_meeting_prep_needs(user_id, session)
                predictions.extend(meeting_predictions)
                
                # Predict follow-up needs
                followup_predictions = self._predict_followup_needs(user_id, session)
                predictions.extend(followup_predictions)
                
                # Predict project attention needs
                project_predictions = self._predict_project_attention(user_id, session)
                predictions.extend(project_predictions)
                
                # Predict relationship maintenance needs
                relationship_predictions = self._predict_relationship_maintenance(user_id, session)
                predictions.extend(relationship_predictions)
                
                logger.info(f"Generated {len(predictions)} predictive insights for user {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to predict upcoming needs: {str(e)}")
        
        return predictions
    
    def detect_anomalies(self, user_id: int) -> List[Dict]:
        """Detect anomalies in user behavior and data patterns"""
        anomalies = []
        
        try:
            with self.db_manager.get_session() as session:
                # Detect unusual email activity
                email_anomalies = self._detect_email_anomalies(user_id, session)
                anomalies.extend(email_anomalies)
                
                # Detect unusual topic activity
                topic_anomalies = self._detect_topic_anomalies(user_id, session)
                anomalies.extend(topic_anomalies)
                
                # Detect relationship anomalies
                relationship_anomalies = self._detect_relationship_anomalies(user_id, session)
                anomalies.extend(relationship_anomalies)
                
                logger.info(f"Detected {len(anomalies)} anomalies for user {user_id}")
                
        except Exception as e:
            logger.error(f"Failed to detect anomalies: {str(e)}")
        
        return anomalies
    
    def calculate_strategic_importance_scores(self, user_id: int) -> Dict:
        """Calculate and update strategic importance scores for entities"""
        try:
            with self.db_manager.get_session() as session:
                # Update topic strategic importance
                topics = session.query(Topic).filter(Topic.user_id == user_id).all()
                for topic in topics:
                    importance_score = self._calculate_topic_importance(topic, user_id, session)
                    topic.strategic_importance = importance_score
                
                # Update person importance levels
                people = session.query(Person).filter(Person.user_id == user_id).all()
                for person in people:
                    importance_score = self._calculate_person_importance(person, user_id, session)
                    person.importance_level = importance_score
                
                session.commit()
                
                logger.info(f"Updated strategic importance scores for user {user_id}")
                
                return {
                    'topics_updated': len(topics),
                    'people_updated': len(people),
                    'success': True
                }
                
        except Exception as e:
            logger.error(f"Failed to calculate strategic importance scores: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _analyze_email_frequency(self, emails: List[Email]) -> Dict:
        """Analyze email frequency patterns"""
        if not emails:
            return {}
        
        # Group emails by day of week and hour
        day_counts = defaultdict(int)
        hour_counts = defaultdict(int)
        
        for email in emails:
            if email.email_date:
                day_counts[email.email_date.weekday()] += 1
                hour_counts[email.email_date.hour] += 1
        
        return {
            'emails_per_day': dict(day_counts),
            'emails_per_hour': dict(hour_counts),
            'total_emails': len(emails),
            'average_per_day': len(emails) / 90  # Over 90 days
        }
    
    def _analyze_topic_trends(self, user_id: int, session) -> Dict:
        """Analyze trending topics and their momentum"""
        topics = session.query(Topic).filter(Topic.user_id == user_id).all()
        
        trending_topics = []
        declining_topics = []
        
        for topic in topics:
            if topic.last_mentioned:
                days_since_mention = (datetime.utcnow() - topic.last_mentioned).days
                
                # Calculate momentum based on mentions and recency
                momentum = topic.total_mentions / max(1, days_since_mention + 1)
                
                if momentum > 0.5 and days_since_mention < 7:
                    trending_topics.append({
                        'name': topic.name,
                        'momentum': momentum,
                        'mentions': topic.total_mentions
                    })
                elif days_since_mention > 30:
                    declining_topics.append({
                        'name': topic.name,
                        'days_inactive': days_since_mention
                    })
        
        return {
            'trending': sorted(trending_topics, key=lambda x: x['momentum'], reverse=True)[:5],
            'declining': sorted(declining_topics, key=lambda x: x['days_inactive'], reverse=True)[:5]
        }
    
    def _analyze_relationship_patterns(self, user_id: int, session) -> Dict:
        """Analyze relationship interaction patterns"""
        people = session.query(Person).filter(Person.user_id == user_id).all()
        
        relationship_health = {
            'strong_relationships': 0,
            'declining_relationships': 0,
            'new_relationships': 0
        }
        
        for person in people:
            if person.last_contact:
                days_since_contact = (datetime.utcnow() - person.last_contact).days
                
                if person.total_interactions > 10 and days_since_contact < 14:
                    relationship_health['strong_relationships'] += 1
                elif person.total_interactions > 5 and days_since_contact > 30:
                    relationship_health['declining_relationships'] += 1
                elif person.total_interactions < 3:
                    relationship_health['new_relationships'] += 1
        
        return relationship_health
    
    def _analyze_meeting_patterns(self, user_id: int, session) -> Dict:
        """Analyze calendar meeting patterns"""
        recent_meetings = session.query(CalendarEvent).filter(
            CalendarEvent.user_id == user_id,
            CalendarEvent.start_time > datetime.utcnow() - timedelta(days=30)
        ).all()
        
        patterns = {
            'meetings_per_week': len(recent_meetings) / 4,
            'avg_meeting_duration': 0,
            'meeting_types': defaultdict(int)
        }
        
        total_duration = 0
        for meeting in recent_meetings:
            if meeting.start_time and meeting.end_time:
                duration = (meeting.end_time - meeting.start_time).total_seconds() / 3600
                total_duration += duration
                
                # Categorize meeting types
                if 'standup' in meeting.title.lower() or 'daily' in meeting.title.lower():
                    patterns['meeting_types']['standup'] += 1
                elif 'review' in meeting.title.lower() or 'retrospective' in meeting.title.lower():
                    patterns['meeting_types']['review'] += 1
                elif 'planning' in meeting.title.lower():
                    patterns['meeting_types']['planning'] += 1
                else:
                    patterns['meeting_types']['general'] += 1
        
        if recent_meetings:
            patterns['avg_meeting_duration'] = total_duration / len(recent_meetings)
        
        return patterns
    
    def _predict_meeting_prep_needs(self, user_id: int, session) -> List[Dict]:
        """Predict which upcoming meetings will need preparation"""
        predictions = []
        
        upcoming_meetings = session.query(CalendarEvent).filter(
            CalendarEvent.user_id == user_id,
            CalendarEvent.start_time.between(
                datetime.utcnow(),
                datetime.utcnow() + timedelta(days=7)
            )
        ).all()
        
        for meeting in upcoming_meetings:
            prep_score = self._calculate_meeting_prep_score(meeting, session)
            
            if prep_score > 0.7:
                predictions.append({
                    'type': 'meeting_preparation',
                    'title': f"Prepare for '{meeting.title}'",
                    'description': f"High-priority meeting preparation needed",
                    'confidence': prep_score,
                    'deadline': meeting.start_time - timedelta(hours=2),
                    'related_entity_type': 'event',
                    'related_entity_id': meeting.id
                })
        
        return predictions
    
    def _predict_followup_needs(self, user_id: int, session) -> List[Dict]:
        """Predict when follow-ups will be needed"""
        predictions = []
        
        # Look for recent meetings that typically require follow-up
        recent_meetings = session.query(CalendarEvent).filter(
            CalendarEvent.user_id == user_id,
            CalendarEvent.start_time.between(
                datetime.utcnow() - timedelta(days=7),
                datetime.utcnow()
            )
        ).all()
        
        for meeting in recent_meetings:
            # Predict follow-up based on meeting type and importance
            if self._meeting_likely_needs_followup(meeting):
                followup_date = meeting.end_time + timedelta(days=2)
                
                predictions.append({
                    'type': 'followup_needed',
                    'title': f"Follow up on '{meeting.title}'",
                    'description': f"This meeting typically requires follow-up actions",
                    'confidence': 0.75,
                    'suggested_date': followup_date,
                    'related_entity_type': 'event',
                    'related_entity_id': meeting.id
                })
        
        return predictions
    
    def _predict_project_attention(self, user_id: int, session) -> List[Dict]:
        """Predict which projects will need attention"""
        predictions = []
        
        # This would analyze project activity patterns
        # For now, return basic predictions based on last update time
        
        return predictions
    
    def _predict_relationship_maintenance(self, user_id: int, session) -> List[Dict]:
        """Predict relationship maintenance needs"""
        predictions = []
        
        people = session.query(Person).filter(
            Person.user_id == user_id,
            Person.importance_level > 0.6
        ).all()
        
        for person in people:
            if person.last_contact:
                days_since_contact = (datetime.utcnow() - person.last_contact).days
                
                # Predict when to reach out based on communication frequency
                if days_since_contact > 14 and person.total_interactions > 5:
                    predictions.append({
                        'type': 'relationship_maintenance',
                        'title': f"Check in with {person.name}",
                        'description': f"Haven't connected in {days_since_contact} days",
                        'confidence': 0.8,
                        'suggested_date': datetime.utcnow() + timedelta(days=1),
                        'related_entity_type': 'person',
                        'related_entity_id': person.id
                    })
        
        return predictions
    
    def _calculate_topic_importance(self, topic: Topic, user_id: int, session) -> float:
        """Calculate strategic importance score for a topic"""
        score = 0.0
        
        # Base score from mentions
        score += min(0.4, topic.total_mentions / 20)
        
        # Recency boost
        if topic.last_mentioned:
            days_since = (datetime.utcnow() - topic.last_mentioned).days
            recency_score = max(0, 0.3 - (days_since / 100))
            score += recency_score
        
        # Connection boost (how many entities are connected)
        connection_count = len(topic.people) + len(topic.tasks) + len(topic.events)
        connection_score = min(0.3, connection_count / 10)
        score += connection_score
        
        return min(1.0, score)
    
    def _calculate_person_importance(self, person: Person, user_id: int, session) -> float:
        """Calculate importance level for a person"""
        score = 0.0
        
        # Interaction frequency
        score += min(0.4, person.total_interactions / 20)
        
        # Recency of contact
        if person.last_contact:
            days_since = (datetime.utcnow() - person.last_contact).days
            recency_score = max(0, 0.3 - (days_since / 60))
            score += recency_score
        
        # Professional context
        if person.title and any(keyword in person.title.lower() for keyword in ['ceo', 'cto', 'president', 'director']):
            score += 0.2
        
        # Topic connections
        topic_connections = len(person.topics)
        score += min(0.1, topic_connections / 10)
        
        return min(1.0, score)
    
    def _calculate_meeting_prep_score(self, meeting: CalendarEvent, session) -> float:
        """Calculate how much preparation a meeting needs"""
        score = 0.0
        
        # Duration factor
        if meeting.start_time and meeting.end_time:
            duration_hours = (meeting.end_time - meeting.start_time).total_seconds() / 3600
            score += min(0.3, duration_hours / 4)  # Longer meetings need more prep
        
        # External attendees factor (would need attendee parsing)
        # For now, assume based on title keywords
        external_keywords = ['client', 'partner', 'vendor', 'external', 'board']
        if any(keyword in meeting.title.lower() for keyword in external_keywords):
            score += 0.4
        
        # Importance keywords
        important_keywords = ['review', 'presentation', 'demo', 'quarterly', 'annual']
        if any(keyword in meeting.title.lower() for keyword in important_keywords):
            score += 0.3
        
        return min(1.0, score)
    
    def _meeting_likely_needs_followup(self, meeting: CalendarEvent) -> bool:
        """Determine if a meeting type typically needs follow-up"""
        followup_keywords = ['planning', 'review', 'decision', 'discussion', 'brainstorm']
        return any(keyword in meeting.title.lower() for keyword in followup_keywords)
    
    def _detect_email_anomalies(self, user_id: int, session) -> List[Dict]:
        """Detect unusual email patterns"""
        anomalies = []
        
        # Get recent email data
        recent_emails = session.query(Email).filter(
            Email.user_id == user_id,
            Email.email_date > datetime.utcnow() - timedelta(days=30)
        ).all()
        
        # Calculate normal email volume
        daily_emails = len(recent_emails) / 30
        
        # Check last 3 days for volume anomalies
        for i in range(3):
            check_date = datetime.utcnow() - timedelta(days=i)
            day_start = check_date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            day_emails = [e for e in recent_emails if day_start <= e.email_date < day_end]
            
            if len(day_emails) > daily_emails * 2:  # More than double normal
                anomalies.append({
                    'type': 'high_email_volume',
                    'date': check_date.strftime('%Y-%m-%d'),
                    'count': len(day_emails),
                    'normal_count': int(daily_emails),
                    'severity': 'medium'
                })
            elif len(day_emails) < daily_emails * 0.3:  # Less than 30% of normal
                anomalies.append({
                    'type': 'low_email_volume',
                    'date': check_date.strftime('%Y-%m-%d'),
                    'count': len(day_emails),
                    'normal_count': int(daily_emails),
                    'severity': 'low'
                })
        
        return anomalies
    
    def _detect_topic_anomalies(self, user_id: int, session) -> List[Dict]:
        """Detect unusual topic activity patterns"""
        anomalies = []
        
        topics = session.query(Topic).filter(Topic.user_id == user_id).all()
        
        for topic in topics:
            if topic.last_mentioned:
                days_inactive = (datetime.utcnow() - topic.last_mentioned).days
                
                # High-importance topic that's been inactive
                if topic.strategic_importance > 0.8 and days_inactive > 14:
                    anomalies.append({
                        'type': 'important_topic_inactive',
                        'topic_name': topic.name,
                        'days_inactive': days_inactive,
                        'importance': topic.strategic_importance,
                        'severity': 'medium'
                    })
        
        return anomalies
    
    def _detect_relationship_anomalies(self, user_id: int, session) -> List[Dict]:
        """Detect unusual relationship patterns"""
        anomalies = []
        
        people = session.query(Person).filter(Person.user_id == user_id).all()
        
        for person in people:
            if person.last_contact and person.importance_level > 0.7:
                days_since_contact = (datetime.utcnow() - person.last_contact).days
                
                # Important person with no recent contact
                if days_since_contact > 21:
                    anomalies.append({
                        'type': 'important_contact_inactive',
                        'person_name': person.name,
                        'days_since_contact': days_since_contact,
                        'importance': person.importance_level,
                        'severity': 'high' if days_since_contact > 45 else 'medium'
                    })
        
        return anomalies

# Global instance
predictive_analytics = PredictiveAnalytics() 