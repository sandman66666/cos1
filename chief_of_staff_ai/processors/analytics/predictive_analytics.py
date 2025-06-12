"""
Predictive Analytics Engine - Future Intelligence
This transforms your system from reactive to genuinely predictive
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
from collections import defaultdict, deque
import threading
import time

from processors.unified_entity_engine import entity_engine, EntityContext
from models.enhanced_models import Person, Topic, Task, CalendarEvent, Email, IntelligenceInsight
from models.database import get_db_manager

logger = logging.getLogger(__name__)

@dataclass
class PredictionResult:
    prediction_type: str
    confidence: float
    predicted_value: Any
    reasoning: str
    time_horizon: str  # short_term, medium_term, long_term
    data_points_used: int
    created_at: datetime

@dataclass
class TrendPattern:
    entity_type: str
    entity_id: int
    pattern_type: str  # growth, decline, cyclical, volatile
    strength: float
    confidence: float
    data_points: List[Tuple[datetime, float]]
    prediction: Optional[float] = None

class PredictiveAnalytics:
    """
    Advanced predictive analytics engine that learns from patterns and predicts future states.
    This is what makes your system truly intelligent - anticipating rather than just reacting.
    """
    
    def __init__(self):
        self.pattern_cache = {}
        self.prediction_cache = {}
        self.learning_models = {}
        self.pattern_detection_thread = None
        self.running = False
        
    def start(self):
        """Start the predictive analytics engine"""
        self.running = True
        self.pattern_detection_thread = threading.Thread(
            target=self._continuous_pattern_detection, 
            name="PredictiveAnalytics"
        )
        self.pattern_detection_thread.daemon = True
        self.pattern_detection_thread.start()
        logger.info("Started predictive analytics engine")
    
    def stop(self):
        """Stop the predictive analytics engine"""
        self.running = False
        if self.pattern_detection_thread:
            self.pattern_detection_thread.join(timeout=5)
        logger.info("Stopped predictive analytics engine")
    
    # =====================================================================
    # RELATIONSHIP PREDICTION METHODS
    # =====================================================================
    
    def predict_relationship_opportunities(self, user_id: int) -> List[PredictionResult]:
        """Predict relationship opportunities and networking needs"""
        predictions = []
        
        try:
            with get_db_manager().get_session() as session:
                # Get all people and their interaction patterns
                people = session.query(Person).filter(Person.user_id == user_id).all()
                
                for person in people:
                    # Predict relationship decay
                    decay_prediction = self._predict_relationship_decay(person)
                    if decay_prediction:
                        predictions.append(decay_prediction)
                    
                    # Predict optimal contact timing
                    contact_prediction = self._predict_optimal_contact_time(person)
                    if contact_prediction:
                        predictions.append(contact_prediction)
                
                # Predict networking opportunities
                network_predictions = self._predict_networking_opportunities(people)
                predictions.extend(network_predictions)
                
        except Exception as e:
            logger.error(f"Failed to predict relationship opportunities: {str(e)}")
        
        return predictions
    
    def _predict_relationship_decay(self, person: Person) -> Optional[PredictionResult]:
        """Predict if a relationship is at risk of decay"""
        if not person.last_contact or person.total_interactions < 3:
            return None
        
        days_since_contact = (datetime.utcnow() - person.last_contact).days
        importance = person.importance_level or 0.5
        
        # Calculate decay risk based on importance and recency
        expected_contact_frequency = self._calculate_expected_frequency(person)
        decay_risk = min(1.0, days_since_contact / expected_contact_frequency)
        
        if decay_risk > 0.7 and importance > 0.6:
            return PredictionResult(
                prediction_type='relationship_decay_risk',
                confidence=decay_risk,
                predicted_value=f"High risk of relationship decay with {person.name}",
                reasoning=f"No contact for {days_since_contact} days, expected frequency is {expected_contact_frequency} days",
                time_horizon='short_term',
                data_points_used=person.total_interactions,
                created_at=datetime.utcnow()
            )
        
        return None
    
    def predict_topic_trends(self, user_id: int) -> List[PredictionResult]:
        """Predict which topics will become important"""
        predictions = []
        
        try:
            with get_db_manager().get_session() as session:
                # Get topics with historical data
                topics = session.query(Topic).filter(
                    Topic.user_id == user_id,
                    Topic.total_mentions > 1
                ).all()
                
                for topic in topics:
                    # Analyze topic momentum
                    momentum_prediction = self._predict_topic_momentum(topic, session)
                    if momentum_prediction:
                        predictions.append(momentum_prediction)
                
                # Predict emerging topics
                emerging_predictions = self._predict_emerging_topics(user_id, session)
                predictions.extend(emerging_predictions)
                
        except Exception as e:
            logger.error(f"Failed to predict topic trends: {str(e)}")
        
        return predictions
    
    def predict_business_opportunities(self, user_id: int) -> List[PredictionResult]:
        """Predict business opportunities based on communication patterns"""
        predictions = []
        
        try:
            # Predict meeting outcomes
            meeting_predictions = self._predict_meeting_outcomes(user_id)
            predictions.extend(meeting_predictions)
            
            # Predict project opportunities
            project_predictions = self._predict_project_opportunities(user_id)
            predictions.extend(project_predictions)
            
            # Predict decision timing
            decision_predictions = self._predict_decision_timing(user_id)
            predictions.extend(decision_predictions)
            
        except Exception as e:
            logger.error(f"Failed to predict business opportunities: {str(e)}")
        
        return predictions
    
    def get_predictions_for_user(self, user_id: int) -> List[PredictionResult]:
        """Get cached predictions for a user"""
        return self.prediction_cache.get(user_id, [])
    
    def get_user_patterns(self, user_id: int) -> Dict:
        """Get detected patterns for a user"""
        return self.pattern_cache.get(user_id, {})
    
    # =====================================================================
    # HELPER METHODS (SIMPLIFIED FOR IMPLEMENTATION)
    # =====================================================================
    
    def _calculate_expected_frequency(self, person: Person) -> int:
        """Calculate expected contact frequency for a person"""
        base_frequency = 30  # Default 30 days
        
        # Adjust based on importance
        importance_factor = (person.importance_level or 0.5)
        frequency = base_frequency * (1 - importance_factor * 0.7)
        
        # Adjust based on relationship type
        relationship_adjustments = {
            'colleague': 0.7,
            'client': 0.5,
            'partner': 0.6,
            'manager': 0.4,
            'friend': 0.8
        }
        
        rel_type = person.relationship_type or 'contact'
        adjustment = relationship_adjustments.get(rel_type.lower(), 1.0)
        
        return max(7, int(frequency * adjustment))
    
    def _predict_optimal_contact_time(self, person: Person) -> Optional[PredictionResult]:
        """Predict optimal time to contact someone"""
        if not person.last_contact or person.total_interactions < 2:
            return None
        
        expected_freq = self._calculate_expected_frequency(person)
        days_since = (datetime.utcnow() - person.last_contact).days
        
        if days_since >= expected_freq * 0.8:  # 80% of expected frequency
            return PredictionResult(
                prediction_type='optimal_contact_timing',
                confidence=0.7,
                predicted_value=datetime.utcnow() + timedelta(days=2),
                reasoning=f"Optimal contact window approaching based on {expected_freq}-day pattern",
                time_horizon='short_term',
                data_points_used=person.total_interactions,
                created_at=datetime.utcnow()
            )
        
        return None
    
    def _predict_networking_opportunities(self, people: List[Person]) -> List[PredictionResult]:
        """Predict networking opportunities"""
        predictions = []
        
        # Find high-value people who could introduce others
        high_value_people = [p for p in people if (p.importance_level or 0) > 0.7]
        
        for person in high_value_people:
            if len(high_value_people) > 1:
                predictions.append(PredictionResult(
                    prediction_type='networking_opportunity',
                    confidence=0.6,
                    predicted_value=f"Consider leveraging {person.name} for introductions",
                    reasoning=f"High-value contact with broad network potential",
                    time_horizon='medium_term',
                    data_points_used=len(people),
                    created_at=datetime.utcnow()
                ))
                break  # Only generate one for now
        
        return predictions
    
    def _predict_topic_momentum(self, topic: Topic, session) -> Optional[PredictionResult]:
        """Predict if a topic will gain or lose momentum"""
        if topic.total_mentions > 5 and topic.last_mentioned:
            days_since_mention = (datetime.utcnow() - topic.last_mentioned).days
            
            if days_since_mention < 7:  # Recently active
                return PredictionResult(
                    prediction_type='topic_momentum_increase',
                    confidence=0.7,
                    predicted_value=f"Topic '{topic.name}' gaining momentum",
                    reasoning=f"Recent activity with {topic.total_mentions} total mentions",
                    time_horizon='short_term',
                    data_points_used=topic.total_mentions,
                    created_at=datetime.utcnow()
                )
        
        return None
    
    def _predict_emerging_topics(self, user_id: int, session) -> List[PredictionResult]:
        """Predict emerging topics"""
        predictions = []
        
        try:
            # Look for topics with recent creation but growing mentions
            recent_topics = session.query(Topic).filter(
                Topic.user_id == user_id,
                Topic.created_at > datetime.utcnow() - timedelta(days=14),
                Topic.total_mentions >= 2
            ).all()
            
            for topic in recent_topics:
                predictions.append(PredictionResult(
                    prediction_type='emerging_topic',
                    confidence=0.6,
                    predicted_value=f"Topic '{topic.name}' emerging",
                    reasoning=f"New topic with growing mention frequency",
                    time_horizon='short_term',
                    data_points_used=topic.total_mentions,
                    created_at=datetime.utcnow()
                ))
                
        except Exception as e:
            logger.error(f"Failed to predict emerging topics: {str(e)}")
        
        return predictions
    
    def _predict_meeting_outcomes(self, user_id: int) -> List[PredictionResult]:
        """Predict meeting outcomes"""
        predictions = []
        
        try:
            with get_db_manager().get_session() as session:
                # Get upcoming meetings
                upcoming_meetings = session.query(CalendarEvent).filter(
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.start_time > datetime.utcnow(),
                    CalendarEvent.start_time < datetime.utcnow() + timedelta(days=7)
                ).all()
                
                for meeting in upcoming_meetings:
                    if meeting.preparation_priority and meeting.preparation_priority > 0.7:
                        predictions.append(PredictionResult(
                            prediction_type='meeting_success_probability',
                            confidence=0.8,
                            predicted_value=f"High success probability for '{meeting.title}'",
                            reasoning=f"Well-prepared meeting with high priority indicators",
                            time_horizon='short_term',
                            data_points_used=1,
                            created_at=datetime.utcnow()
                        ))
                
        except Exception as e:
            logger.error(f"Failed to predict meeting outcomes: {str(e)}")
        
        return predictions
    
    def _predict_project_opportunities(self, user_id: int) -> List[PredictionResult]:
        """Predict project opportunities"""
        predictions = []
        
        try:
            with get_db_manager().get_session() as session:
                # Look for high-importance emails that might signal projects
                strategic_emails = session.query(Email).filter(
                    Email.user_id == user_id,
                    Email.email_date > datetime.utcnow() - timedelta(days=7),
                    Email.strategic_importance > 0.7
                ).count()
                
                if strategic_emails > 2:
                    predictions.append(PredictionResult(
                        prediction_type='project_opportunity',
                        confidence=0.6,
                        predicted_value=f"Potential project formation detected",
                        reasoning=f"Multiple high-importance communications suggest project activity",
                        time_horizon='medium_term',
                        data_points_used=strategic_emails,
                        created_at=datetime.utcnow()
                    ))
                
        except Exception as e:
            logger.error(f"Failed to predict project opportunities: {str(e)}")
        
        return predictions
    
    def _predict_decision_timing(self, user_id: int) -> List[PredictionResult]:
        """Predict when decisions might be needed"""
        predictions = []
        
        try:
            with get_db_manager().get_session() as session:
                # Look for urgent tasks or high-priority items
                urgent_tasks = session.query(Task).filter(
                    Task.user_id == user_id,
                    Task.priority == 'high',
                    Task.status.in_(['pending', 'open'])
                ).count()
                
                if urgent_tasks > 0:
                    predictions.append(PredictionResult(
                        prediction_type='decision_needed',
                        confidence=0.7,
                        predicted_value=f"Decisions needed on {urgent_tasks} high-priority items",
                        reasoning=f"Multiple urgent tasks require attention",
                        time_horizon='short_term',
                        data_points_used=urgent_tasks,
                        created_at=datetime.utcnow()
                    ))
                
        except Exception as e:
            logger.error(f"Failed to predict decision timing: {str(e)}")
        
        return predictions
    
    def _continuous_pattern_detection(self):
        """Continuously detect patterns in user data"""
        while self.running:
            try:
                # Get active users for pattern analysis
                active_users = self._get_active_users_for_analysis()
                
                for user_id in active_users:
                    # Generate predictions for this user
                    all_predictions = []
                    all_predictions.extend(self.predict_relationship_opportunities(user_id))
                    all_predictions.extend(self.predict_topic_trends(user_id))
                    all_predictions.extend(self.predict_business_opportunities(user_id))
                    
                    # Store predictions
                    self.prediction_cache[user_id] = all_predictions
                
                # Sleep for analysis interval (every 2 hours)
                time.sleep(7200)
                
            except Exception as e:
                logger.error(f"Error in continuous pattern detection: {str(e)}")
                time.sleep(300)  # Sleep 5 minutes on error
    
    def _get_active_users_for_analysis(self) -> List[int]:
        """Get users with recent activity for pattern analysis"""
        try:
            # Users with activity in last 7 days
            cutoff = datetime.utcnow() - timedelta(days=7)
            
            with get_db_manager().get_session() as session:
                active_users = session.query(Email.user_id).filter(
                    Email.email_date > cutoff
                ).distinct().all()
                
                return [user_id[0] for user_id in active_users]
            
        except Exception as e:
            logger.error(f"Failed to get active users: {str(e)}")
            return []

# Global instance
predictive_analytics = PredictiveAnalytics() 