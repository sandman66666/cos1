# Handles fetching calendar events from Google Calendar API

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from dateutil import parser as date_parser

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth.gmail_auth import gmail_auth
from chief_of_staff_ai.models.database import get_db_manager, Calendar
from config.settings import settings
from processors.realtime_processing import realtime_processor, EventType
from processors.enhanced_ai_pipeline import enhanced_ai_processor
from processors.unified_entity_engine import entity_engine, EntityContext
from processors.intelligence_engine import intelligence_engine

logger = logging.getLogger(__name__)

class CalendarFetcher:
    """Fetches calendar events from Google Calendar API with attendee intelligence"""
    
    def __init__(self):
        self.batch_size = 50
        self.max_results = 500
        self.default_days_forward = 30
        self.default_days_back = 7
        
    def fetch_calendar_events(
        self, 
        user_email: str, 
        days_back: int = 7, 
        days_forward: int = 30,
        limit: int = None,
        force_refresh: bool = False
    ) -> Dict:
        """
        Fetch calendar events for a user from their Google Calendar
        
        Args:
            user_email: Gmail address of the user
            days_back: Number of days back to fetch events
            days_forward: Number of days forward to fetch events
            limit: Maximum number of events to fetch
            force_refresh: Whether to bypass database cache and fetch fresh data
            
        Returns:
            Dictionary containing fetched events and metadata
        """
        try:
            # Get user from database
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return self._error_response(f"User {user_email} not found in database")
            
            # Calculate date range - ensure timezone-aware
            now_utc = datetime.now(timezone.utc)
            start_date = now_utc - timedelta(days=days_back)
            end_date = now_utc + timedelta(days=days_forward)
            
            # Check if we should use cached data (unless force refresh)
            if not force_refresh:
                cached_events = get_db_manager().get_user_calendar_events(
                    user.id, start_date, end_date, limit or 100
                )
                if cached_events:
                    logger.info(f"Using cached calendar events for {user_email}: {len(cached_events)} events")
                    return {
                        'success': True,
                        'user_email': user_email,
                        'events': [event.to_dict() for event in cached_events],
                        'count': len(cached_events),
                        'source': 'database_cache',
                        'fetched_at': datetime.now(timezone.utc).isoformat(),
                        'date_range': {
                            'start': start_date.isoformat(),
                            'end': end_date.isoformat()
                        }
                    }
            
            # Get valid credentials (same OAuth as Gmail)
            credentials = gmail_auth.get_valid_credentials(user_email)
            if not credentials:
                return self._error_response(f"No valid credentials for {user_email}")
            
            # Build Calendar service
            service = build('calendar', 'v3', credentials=credentials)
            
            # Fetch calendar list first to get all calendars
            calendar_list = self._fetch_calendar_list(service)
            
            # Fetch events from all calendars
            all_events = []
            for calendar_info in calendar_list:
                calendar_events = self._fetch_events_from_calendar(
                    service, calendar_info['id'], start_date, end_date, limit, user.id
                )
                all_events.extend(calendar_events)
            
            # Sort events by start time
            all_events.sort(key=lambda x: x.get('start_time', datetime.min))
            
            # Apply limit if specified
            if limit:
                all_events = all_events[:limit]
            
            # Save events to database and get attendee intelligence
            processed_events = []
            for event_data in all_events:
                # Save/update event in database
                event_record = get_db_manager().save_calendar_event(user.id, event_data)
                
                if event_record:
                    # Convert to dict for response (and add attendee intelligence)
                    event_dict = event_record.to_dict()
                    
                    # Get attendee intelligence for this event  
                    attendee_intel = get_db_manager().get_calendar_attendee_intelligence(
                        user.id, 
                        event_record.event_id
                    )
                    
                    if attendee_intel:
                        event_dict['attendee_intelligence'] = attendee_intel
                    
                    processed_events.append(event_dict)
            
            # Process attendee contacts - create People records for meeting attendees
            logger.info(f"Processing attendee contacts for {len(all_events)} events...")
            self._process_calendar_attendees(user.id, all_events)
            
            logger.info(f"Successfully fetched {len(processed_events)} calendar events for {user_email}")
            
            return {
                'success': True,
                'user_email': user_email,
                'events': processed_events,
                'count': len(processed_events),
                'source': 'google_calendar_api',
                'fetched_at': datetime.now(timezone.utc).isoformat(),
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'calendars_processed': len(calendar_list)
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch calendar events for {user_email}: {str(e)}")
            return self._error_response(str(e))
    
    def fetch_free_time_analysis(
        self, 
        user_email: str, 
        days_forward: int = 7
    ) -> Dict:
        """
        Analyze calendar to identify free time slots for recommendations
        
        Args:
            user_email: Gmail address of the user
            days_forward: Number of days forward to analyze
            
        Returns:
            Dictionary containing free time slots and recommendations
        """
        try:
            # Get user from database
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return self._error_response(f"User {user_email} not found in database")
            
            # Calculate date range (focus on upcoming time) - ensure timezone-aware
            now_utc = datetime.now(timezone.utc)
            start_date = now_utc
            end_date = now_utc + timedelta(days=days_forward)
            
            # Get free time slots from database analysis
            free_slots = get_db_manager().get_free_time_slots(user.id, start_date, end_date)
            
            # Categorize free time slots by duration and time of day
            categorized_slots = self._categorize_free_time(free_slots)
            
            # Generate recommendations for each free slot
            recommendations = self._generate_time_recommendations(categorized_slots)
            
            logger.info(f"Found {len(free_slots)} free time slots for {user_email}")
            
            return {
                'success': True,
                'user_email': user_email,
                'analysis_period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days_analyzed': days_forward
                },
                'free_slots': free_slots,
                'categorized_slots': categorized_slots,
                'recommendations': recommendations,
                'total_free_time_minutes': sum(slot['duration_minutes'] for slot in free_slots),
                'analyzed_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze free time for {user_email}: {str(e)}")
            return self._error_response(str(e))
    
    def _fetch_calendar_list(self, service) -> List[Dict]:
        """Fetch list of user's calendars - ONLY PRIMARY CALENDAR"""
        try:
            calendar_list_result = service.calendarList().list().execute()
            calendars = calendar_list_result.get('items', [])
            
            # ONLY include the primary calendar for each user
            relevant_calendars = []
            for calendar in calendars:
                if calendar.get('primary', False):
                    relevant_calendars.append({
                        'id': 'primary',  # Always use 'primary' for API calls
                        'summary': calendar.get('summary', 'Primary Calendar'),
                        'primary': True,
                        'access_role': calendar.get('accessRole')
                    })
                    break  # Only need one primary calendar
            
            # Fallback if no primary calendar found
            if not relevant_calendars:
                relevant_calendars = [{'id': 'primary', 'summary': 'Primary Calendar', 'primary': True}]
            
            logger.info(f"Found {len(relevant_calendars)} relevant calendars (primary only)")
            return relevant_calendars
            
        except Exception as e:
            logger.error(f"Failed to fetch calendar list: {str(e)}")
            return [{'id': 'primary', 'summary': 'Primary Calendar', 'primary': True}]
    
    def _fetch_events_from_calendar(
        self, 
        service, 
        calendar_id: str, 
        start_date: datetime, 
        end_date: datetime, 
        limit: int = None,
        user_id: int = None
    ) -> List[Dict]:
        """Fetch events from a specific calendar"""
        try:
            api_calendar_id = calendar_id if calendar_id != 'primary' else 'primary'
            
            events_result = service.events().list(
                calendarId=api_calendar_id,
                timeMin=start_date.isoformat(),
                timeMax=end_date.isoformat(),
                maxResults=limit or self.max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            processed_events = []
            
            for event in events:
                processed_event = self._process_calendar_event(event, calendar_id, user_id)
                if processed_event:
                    processed_events.append(processed_event)
            
            logger.info(f"Fetched {len(processed_events)} events from calendar {api_calendar_id}")
            return processed_events
            
        except Exception as e:
            logger.error(f"Failed to fetch events from calendar {calendar_id}: {str(e)}")
            return []
    
    def _process_calendar_event(self, event: Dict, calendar_id: str, user_id: int = None) -> Optional[Dict]:
        """Process a Google Calendar event into our standard format"""
        try:
            # Extract event ID
            event_id = event.get('id')
            if not event_id:
                return None
            
            # Parse start and end times
            start = event.get('start', {})
            end = event.get('end', {})
            
            # Handle all-day events
            if 'date' in start:
                is_all_day = True
                # For all-day events, parse date and set to midnight
                start_date = datetime.strptime(start['date'], '%Y-%m-%d')
                end_date = datetime.strptime(end['date'], '%Y-%m-%d')
                
                # Convert to UTC
                start_time = start_date.replace(tzinfo=timezone.utc)
                end_time = end_date.replace(tzinfo=timezone.utc)
                timezone_str = 'UTC'
            else:
                is_all_day = False
                # For timed events, parse datetime
                start_datetime_str = start.get('dateTime')
                end_datetime_str = end.get('dateTime')
                
                if start_datetime_str and end_datetime_str:
                    # Parse timezone-aware datetime
                    start_time = datetime.fromisoformat(start_datetime_str.replace('Z', '+00:00'))
                    end_time = datetime.fromisoformat(end_datetime_str.replace('Z', '+00:00'))
                    timezone_str = start.get('timeZone', 'UTC')
                else:
                    # Fallback for events without proper time data
                    return None
            
            # Process attendees
            attendees = []
            attendee_emails = []
            for attendee in event.get('attendees', []):
                attendee_info = {
                    'email': attendee.get('email'),
                    'name': attendee.get('displayName', attendee.get('email', '').split('@')[0]),
                    'response_status': attendee.get('responseStatus', 'needsAction'),
                    'optional': attendee.get('optional', False),
                    'organizer': attendee.get('organizer', False)
                }
                attendees.append(attendee_info)
                
                if attendee.get('email'):
                    attendee_emails.append(attendee['email'])
            
            # Build event data structure
            event_data = {
                'event_id': event_id,
                'calendar_id': calendar_id,
                'recurring_event_id': event.get('recurringEventId'),
                'title': event.get('summary', 'Untitled Event'),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'status': event.get('status', 'confirmed'),
                'start_time': start_time,
                'end_time': end_time,
                'timezone': timezone_str,
                'is_all_day': is_all_day,
                'attendees': attendees,
                'attendee_emails': attendee_emails,
                'organizer_email': event.get('organizer', {}).get('email'),
                'organizer_name': event.get('organizer', {}).get('displayName'),
                'html_link': event.get('htmlLink'),
                'hangout_link': event.get('hangoutLink'),
                'ical_uid': event.get('iCalUID'),
                'sequence': event.get('sequence', 0),
                'visibility': event.get('visibility', 'default'),
                'is_recurring': 'recurrence' in event,
                'recurrence_rules': event.get('recurrence', [])
            }
            
            # Extract conference/meeting details
            conference_data = event.get('conferenceData', {})
            if conference_data:
                event_data['conference_data'] = conference_data
                
                # Extract common meeting links
                entry_points = conference_data.get('entryPoints', [])
                for entry_point in entry_points:
                    if entry_point.get('entryPointType') == 'video':
                        event_data['hangout_link'] = entry_point.get('uri')
                        event_data['meeting_type'] = 'video_call'
                        break
                else:
                    event_data['meeting_type'] = 'in_person' if event_data['location'] else 'unknown'
            else:
                event_data['meeting_type'] = 'in_person' if event_data['location'] else 'unknown'
            
            # Determine if this blocks time (for free time analysis)
            # Default to busy unless explicitly marked as transparent/free
            transparency = event.get('transparency', 'opaque')  # Default to opaque (busy)
            event_data['transparency'] = transparency
            event_data['is_busy'] = transparency != 'transparent'
            
            # Force all non-declined events to be busy for better free time detection
            if event_data['status'] in ['confirmed', 'tentative']:
                event_data['is_busy'] = True
            
            # Add processing metadata
            event_data['fetched_at'] = datetime.now(timezone.utc)
            
            return event_data
            
        except Exception as e:
            logger.error(f"Failed to process calendar event {event.get('id', 'unknown')}: {str(e)}")
            return None
    
    def _enhance_event_with_business_context(self, user_id: int, event_data: Dict) -> Dict:
        """
        Enhance calendar event with business context from emails and topics
        
        This connects your email insights (like about "random forest" VC) to calendar events
        """
        try:
            if not event_data.get('attendee_emails'):
                return event_data
            
            db_manager = get_db_manager()
            
            # Find people in database who are attendees
            known_attendees = []
            business_insights = []
            topic_connections = []
            
            for attendee_email in event_data['attendee_emails']:
                # Find person in database
                person = db_manager.find_person_by_email(user_id, attendee_email)
                if person:
                    known_attendees.append({
                        'name': person.name,
                        'email': person.email_address,
                        'company': person.company,
                        'title': person.title,
                        'relationship_type': person.relationship_type,
                        'total_emails': person.total_emails
                    })
                    
                    # Find emails with this person
                    emails = db_manager.get_user_emails(user_id, limit=100)
                    person_emails = [e for e in emails if e.sender and 
                                   e.sender.lower() == attendee_email.lower()]
                    
                    # Extract insights from recent emails with this person
                    for email in person_emails[:5]:  # Recent 5 emails
                        if email.ai_summary:
                            business_insights.append({
                                'source': f'email with {person.name}',
                                'insight': email.ai_summary[:200],
                                'date': email.email_date.isoformat() if email.email_date else None
                            })
                        
                        # Extract key insights
                        if email.key_insights and isinstance(email.key_insights, dict):
                            if email.key_insights.get('key_decisions'):
                                for decision in email.key_insights['key_decisions'][:2]:
                                    business_insights.append({
                                        'source': f'decision with {person.name}',
                                        'insight': decision,
                                        'type': 'decision',
                                        'date': email.email_date.isoformat() if email.email_date else None
                                    })
                            
                            if email.key_insights.get('strategic_opportunities'):
                                for opp in email.key_insights['strategic_opportunities'][:2]:
                                    business_insights.append({
                                        'source': f'opportunity with {person.name}',
                                        'insight': opp,
                                        'type': 'opportunity',
                                        'date': email.email_date.isoformat() if email.email_date else None
                                    })
                        
                        # Find topic connections
                        if email.topics:
                            for topic in email.topics:
                                if topic and len(topic) > 2:
                                    topic_connections.append({
                                        'topic': topic,
                                        'person': person.name,
                                        'company': person.company or 'Unknown'
                                    })
            
            # Look for meeting-related topics in the title and description
            meeting_text = f"{event_data.get('title', '')} {event_data.get('description', '')}".lower()
            
            # Get all user topics to see if any match this meeting
            topics = db_manager.get_user_topics(user_id)
            relevant_topics = []
            
            for topic in topics:
                if (topic.name.lower() in meeting_text or 
                    any(keyword.lower() in meeting_text for keyword in (topic.keywords or []))):
                    relevant_topics.append({
                        'name': topic.name,
                        'description': topic.description,
                        'is_official': topic.is_official,
                        'email_count': topic.email_count,
                        'confidence': topic.confidence_score
                    })
            
            # Generate business context summary
            context_parts = []
            
            if known_attendees:
                context_parts.append(f"Meeting with {len(known_attendees)} known contacts")
                
                # Highlight key people
                key_people = [p for p in known_attendees if p.get('total_emails', 0) > 5]
                if key_people:
                    context_parts.append(f"Key relationships: {', '.join([p['name'] for p in key_people[:3]])}")
            
            if business_insights:
                recent_insights = [i for i in business_insights if i.get('type') in ['decision', 'opportunity']]
                if recent_insights:
                    context_parts.append(f"Recent business activity: {len(recent_insights)} decisions/opportunities")
            
            if relevant_topics:
                context_parts.append(f"Related topics: {', '.join([t['name'] for t in relevant_topics[:3]])}")
            
            if topic_connections:
                unique_topics = list(set([tc['topic'] for tc in topic_connections]))
                if unique_topics:
                    context_parts.append(f"Discussion topics: {', '.join(unique_topics[:3])}")
            
            # Add enhanced context to event
            if context_parts or business_insights or relevant_topics:
                # Combine context parts into a single business_context string
                all_context_parts = context_parts.copy()
                
                if business_insights:
                    insights_summary = f"Recent insights: {len(business_insights)} business activities"
                    all_context_parts.append(insights_summary)
                
                if relevant_topics:
                    topics_summary = f"Related topics: {', '.join([t['name'] for t in relevant_topics[:3]])}"
                    all_context_parts.append(topics_summary)
                
                event_data['business_context'] = '; '.join(all_context_parts)
                
                # Set preparation flags
                event_data['preparation_needed'] = len(business_insights) > 0 or len(relevant_topics) > 0
                
                # AI summary generation
                if business_insights or relevant_topics:
                    summary_parts = []
                    if event_data.get('title'):
                        summary_parts.append(f"Meeting: {event_data['title']}")
                    
                    if business_insights:
                        summary_parts.append(f"Recent activity: {len(business_insights)} business insights")
                    
                    event_data['ai_summary'] = '\n'.join(summary_parts)
            
            return event_data
            
        except Exception as e:
            logger.error(f"Failed to enhance event with business context: {str(e)}")
            return event_data
    
    def _categorize_free_time(self, free_slots: List[Dict]) -> Dict:
        """Categorize free time slots by duration and time of day"""
        categories = {
            'quick_slots': [],      # 30-60 minutes
            'medium_slots': [],     # 1-2 hours
            'long_slots': [],       # 2+ hours
            'morning_slots': [],    # 6 AM - 12 PM
            'afternoon_slots': [],  # 12 PM - 6 PM
            'evening_slots': []     # 6 PM - 11 PM
        }
        
        for slot in free_slots:
            duration = slot['duration_minutes']
            start_time = slot['start_time']
            
            # Categorize by duration
            if 30 <= duration < 60:
                categories['quick_slots'].append(slot)
            elif 60 <= duration < 120:
                categories['medium_slots'].append(slot)
            elif duration >= 120:
                categories['long_slots'].append(slot)
            
            # Categorize by time of day
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            
            # Ensure timezone-aware datetime
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            
            # Convert to local time for hour-based categorization
            local_time = start_time.astimezone()  # Uses system timezone
            hour = local_time.hour
            
            if 6 <= hour < 12:
                categories['morning_slots'].append(slot)
            elif 12 <= hour < 18:
                categories['afternoon_slots'].append(slot)
            elif 18 <= hour < 23:
                categories['evening_slots'].append(slot)
        
        return categories
    
    def _generate_time_recommendations(self, categorized_slots: Dict) -> List[Dict]:
        """Generate activity recommendations for different free time slots"""
        recommendations = []
        
        # Quick slots (30-60 min) - Focus tasks
        for slot in categorized_slots['quick_slots'][:3]:  # Top 3
            recommendations.append({
                'slot': slot,
                'type': 'focused_work',
                'title': 'Quick Focus Session',
                'description': 'Perfect for concentrated work on a specific task or quick meetings.',
                'suggestions': [
                    'Review and respond to important emails',
                    'Make important phone calls',
                    'Complete urgent task items',
                    'Quick team check-in meeting',
                    'Review calendar and plan day'
                ],
                'priority': 'high'
            })
        
        # Medium slots (1-2 hours) - Substantial work
        for slot in categorized_slots['medium_slots'][:3]:  # Top 3
            recommendations.append({
                'slot': slot,
                'type': 'substantial_work',
                'title': 'Deep Work Session',
                'description': 'Ideal for meaningful progress on important projects.',
                'suggestions': [
                    'Work on strategic business projects',
                    'Schedule important business meetings',
                    'Strategic planning and thinking time',
                    'Client calls or investor meetings',
                    'Team collaboration sessions'
                ],
                'priority': 'high'
            })
        
        # Long slots (2+ hours) - Major initiatives
        for slot in categorized_slots['long_slots'][:2]:  # Top 2
            recommendations.append({
                'slot': slot,
                'type': 'major_initiative',
                'title': 'Major Project Block',
                'description': 'Extended time for significant business initiatives.',
                'suggestions': [
                    'Board meeting preparation',
                    'Investor presentation development',
                    'Strategic business planning',
                    'Product development sessions',
                    'Team offsites or workshops'
                ],
                'priority': 'very_high'
            })
        
        # Morning slots - High-energy work
        morning_suggestions = [
            'Schedule important meetings with key stakeholders',
            'Tackle challenging analytical work',
            'Strategic decision making',
            'Investor or client presentations'
        ]
        
        # Afternoon slots - Collaborative work
        afternoon_suggestions = [
            'Team meetings and collaboration',
            'Client calls and business development',
            'Networking events or industry meetings',
            'Project coordination sessions'
        ]
        
        # Evening slots - Planning and prep
        evening_suggestions = [
            'Plan next day and week',
            'Review business metrics and progress',
            'Prepare for upcoming meetings',
            'Personal development time'
        ]
        
        # Add time-of-day specific recommendations
        for morning_slot in categorized_slots['morning_slots'][:2]:
            recommendations.append({
                'slot': morning_slot,
                'type': 'morning_energy',
                'title': 'High-Energy Morning Work',
                'description': 'Take advantage of peak morning energy.',
                'suggestions': morning_suggestions,
                'priority': 'high'
            })
        
        return recommendations[:8]  # Return top 8 recommendations
    
    def _error_response(self, error_message: str) -> Dict:
        """Generate standardized error response"""
        return {
            'success': False,
            'error': error_message,
            'count': 0,
            'events': [],
            'fetched_at': datetime.now(timezone.utc).isoformat()
        }

    def create_meeting_prep_tasks(self, user_id: int, events: List[Dict]) -> Dict:
        """Create meeting preparation tasks using intelligence engine"""
        try:
            from processors.intelligence_engine import intelligence_engine
            from chief_of_staff_ai.models.database import get_db_manager
            
            db_manager = get_db_manager()
            prep_tasks_created = 0
            all_tasks = []
            
            for event_dict in events:
                try:
                    # Find the calendar event in database
                    with db_manager.get_session() as session:
                        from chief_of_staff_ai.models.database import Calendar
                        event = session.query(Calendar).filter(
                            Calendar.user_id == user_id,
                            Calendar.event_id == event_dict.get('event_id', event_dict.get('id'))
                        ).first()
                        
                        if event and event.attendee_emails:
                            # Skip if meeting is too far in future or too soon
                            if event.start_time:
                                from datetime import datetime, timedelta
                                hours_until = (event.start_time - datetime.utcnow()).total_seconds() / 3600
                                
                                # Only process meetings 2-72 hours away
                                if 2 <= hours_until <= 72:
                                    # Generate comprehensive meeting intelligence
                                    meeting_intel = intelligence_engine.generate_meeting_intelligence(user_id, event)
                                    
                                    if meeting_intel:
                                        # Create preparation tasks
                                        for task_info in meeting_intel.preparation_tasks:
                                            prep_tasks_created += 1
                                            all_tasks.append(task_info)
                                        
                                        # Store meeting intelligence in database
                                        intelligence_data = {
                                            'business_context': meeting_intel.business_context,
                                            'importance_score': meeting_intel.strategic_importance,
                                            'preparation_needed': True if meeting_intel.preparation_tasks else False
                                        }
                                        
                                        db_manager.enhance_calendar_event_with_intelligence(
                                            user_id, event.event_id, intelligence_data
                                        )
                                        
                                        logger.info(f"Generated {len(meeting_intel.preparation_tasks)} prep tasks for meeting: {event.title}")
                        
                        session.expunge_all()
                        
                except Exception as e:
                    logger.error(f"Failed to process event for prep tasks: {str(e)}")
                    continue
            
            logger.info(f"Created {prep_tasks_created} meeting preparation tasks for {len(events)} events")
            
            return {
                'success': True,
                'prep_tasks_created': prep_tasks_created,
                'tasks': all_tasks
            }
            
        except Exception as e:
            logger.error(f"Failed to create meeting prep tasks: {str(e)}")
            return {
                'success': False,
                'prep_tasks_created': 0,
                'tasks': [],
                'error': str(e)
            }

    def _process_calendar_attendees(self, user_id: int, events: List[Dict]):
        """Process calendar attendees and create People records for new contacts"""
        try:
            db_manager = get_db_manager()
            
            # Get user email by getting all users and finding the match
            # (Alternative to get_user_by_id which may not exist)
            user_email = None
            try:
                # We can get the user email from the first user with this ID
                with db_manager.get_session() as session:
                    from chief_of_staff_ai.models.database import User
                    user = session.query(User).filter_by(id=user_id).first()
                    user_email = user.email if user else None
            except:
                user_email = None
            
            attendee_count = 0
            new_people_created = 0
            
            for event_data in events:
                if not event_data.get('attendees'):
                    continue
                
                for attendee in event_data['attendees']:
                    attendee_email = attendee.get('email')
                    attendee_name = attendee.get('name', attendee_email.split('@')[0] if attendee_email else 'Unknown')
                    
                    if attendee_email and attendee_email != user_email:  # Don't create record for the user themselves
                        attendee_count += 1
                        
                        # Check if person already exists
                        existing_person = db_manager.find_person_by_email(user_id, attendee_email)
                        
                        if not existing_person:
                            # Create new person record from calendar attendee
                            person_data = {
                                'email_address': attendee_email,
                                'name': attendee_name,
                                'first_name': attendee_name.split()[0] if ' ' in attendee_name else attendee_name,
                                'last_name': ' '.join(attendee_name.split()[1:]) if ' ' in attendee_name else '',
                                'relationship_type': 'meeting_attendee',
                                'communication_frequency': 'unknown',
                                'importance_level': 0.5,
                                'notes': f'Added from calendar event: {event_data.get("title", "Untitled Event")}',
                                'total_emails': 0,  # No emails yet, just calendar
                                'first_mentioned': event_data.get('start_time', datetime.now(timezone.utc)),
                                'last_interaction': event_data.get('start_time', datetime.now(timezone.utc))
                            }
                            
                            try:
                                new_person = db_manager.create_or_update_person(user_id, person_data)
                                new_people_created += 1
                                logger.debug(f"Created person record for calendar attendee: {attendee_name} ({attendee_email})")
                            except Exception as e:
                                logger.warning(f"Failed to create person record for {attendee_email}: {str(e)}")
                        else:
                            # Update last interaction for existing person
                            try:
                                existing_person.last_interaction = event_data.get('start_time', datetime.now(timezone.utc))
                                logger.debug(f"Updated last interaction for existing person: {existing_person.name}")
                            except Exception as e:
                                logger.warning(f"Failed to update person {attendee_email}: {str(e)}")
            
            logger.info(f"Processed {attendee_count} calendar attendees, created {new_people_created} new people records")
            
        except Exception as e:
            logger.error(f"Failed to process calendar attendees: {str(e)}")

    def fetch_recent_events(self, user_email: str, days_ahead: int = 7, days_back: int = 1) -> Dict:
        """
        Fetch recent calendar events and process them through enhanced entity-centric pipeline
        """
        try:
            # Get Calendar credentials
            credentials = self.gmail_auth.get_valid_credentials(user_email)
            if not credentials:
                return {'success': False, 'error': 'User not authenticated'}
            
            # Build Calendar service
            service = build('calendar', 'v3', credentials=credentials)
            
            # Calculate time range
            now = datetime.utcnow()
            time_min = (now - timedelta(days=days_back)).isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            logger.info(f"Fetching calendar events for {user_email} from {days_back} days back to {days_ahead} days ahead")
            
            # Get user database record for enhanced processing
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                logger.warning(f"User {user_email} not found in database")
                return {'success': False, 'error': 'User not found in database'}
            
            # Fetch events from primary calendar
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            events_processed = 0
            processed_events = []
            
            # Process each event
            for event in events:
                try:
                    # Extract event data
                    event_data = self._extract_event_data(event)
                    
                    if event_data:
                        # Check if we already processed this event (avoid duplicates)
                        if not self._is_event_processed(event_data['id'], user.id):
                            # Enhanced processing: Send to real-time processor
                            if realtime_processor.is_running:
                                realtime_processor.process_new_calendar_event(event_data, user.id, priority=4)
                                logger.debug(f"Sent event to real-time processor: {event_data.get('title', 'No title')}")
                            else:
                                # Fallback: Process directly through enhanced AI pipeline
                                logger.info("Real-time processor not running, processing directly")
                                result = enhanced_ai_processor.enhance_calendar_event_with_intelligence(event_data, user.id)
                                if result.success:
                                    logger.debug(f"Direct event processing success: {result.entities_created}")
                                else:
                                    logger.warning(f"Direct event processing failed: {result.error}")
                            
                            # Store basic event metadata for tracking
                            self._store_event_metadata(event_data, user.id)
                            
                            events_processed += 1
                        
                        processed_events.append(event_data)
                        
                except Exception as e:
                    logger.error(f"Error processing event {event.get('id', 'unknown')}: {str(e)}")
                    continue
            
            # Generate summary with enhanced metrics
            result = {
                'success': True,
                'events_fetched': len(events),
                'events_processed': events_processed,
                'events': processed_events,
                'user_id': user.id,
                'enhanced_processing': True,
                'real_time_processing': realtime_processor.is_running,
                'processing_stats': {
                    'total_events_found': len(events),
                    'new_events_processed': events_processed,
                    'existing_events_skipped': len(events) - events_processed,
                    'sent_to_real_time': events_processed if realtime_processor.is_running else 0
                },
                'fetch_time': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Enhanced calendar fetch complete for {user_email}: {events_processed} new events processed")
            
            # Generate proactive insights if we have significant upcoming events
            upcoming_important_events = [e for e in processed_events 
                                       if e.get('start_time') and 
                                       datetime.fromisoformat(e['start_time']) > now and
                                       datetime.fromisoformat(e['start_time']) < now + timedelta(days=2)]
            
            if len(upcoming_important_events) > 2 and realtime_processor.is_running:
                realtime_processor.trigger_proactive_insights(user.id, priority=3)
                logger.info("Triggered proactive insights for upcoming meetings")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to fetch calendar events for {user_email}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'events_fetched': 0,
                'events': []
            }

    def _is_event_processed(self, google_event_id: str, user_id: int) -> bool:
        """Check if calendar event has already been processed"""
        try:
            from models.enhanced_models import CalendarEvent
            
            with get_db_manager().get_session() as session:
                existing = session.query(CalendarEvent).filter(
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.google_event_id == google_event_id
                ).first()
                
                return existing is not None
                
        except Exception as e:
            logger.debug(f"Error checking if event processed: {str(e)}")
            return False
    
    def _store_event_metadata(self, event_data: Dict, user_id: int):
        """Store basic event metadata for tracking purposes"""
        try:
            from models.enhanced_models import CalendarEvent
            
            with get_db_manager().get_session() as session:
                # Check if already exists
                existing = session.query(CalendarEvent).filter(
                    CalendarEvent.user_id == user_id,
                    CalendarEvent.google_event_id == event_data['id']
                ).first()
                
                if not existing:
                    event = CalendarEvent(
                        user_id=user_id,
                        google_event_id=event_data['id'],
                        title=event_data.get('title', ''),
                        description=event_data.get('description', ''),
                        location=event_data.get('location', ''),
                        start_time=datetime.fromisoformat(event_data.get('start_time', datetime.utcnow().isoformat())),
                        end_time=datetime.fromisoformat(event_data.get('end_time', datetime.utcnow().isoformat())),
                        created_at=datetime.utcnow()
                    )
                    
                    session.add(event)
                    session.commit()
                    logger.debug(f"Stored event metadata: {event_data.get('title', 'No title')}")
                
        except Exception as e:
            logger.warning(f"Failed to store event metadata: {str(e)}")

    def process_events_with_enhanced_intelligence(self, user_email: str, event_batch: List[Dict], 
                                                enable_real_time: bool = True) -> Dict:
        """
        Process a batch of calendar events using enhanced entity-centric intelligence
        This demonstrates meeting preparation and attendee intelligence
        """
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            processing_results = {
                'success': True,
                'total_events': len(event_batch),
                'processed_events': 0,
                'entities_created': {'tasks': 0, 'people': 0},
                'entities_updated': {'events': 0, 'people': 0},
                'prep_tasks_generated': 0,
                'insights_generated': [],
                'processing_method': 'real_time' if enable_real_time else 'direct',
                'enhanced_features': True
            }
            
            for event_data in event_batch:
                try:
                    if enable_real_time and realtime_processor.is_running:
                        # Send to real-time processor
                        realtime_processor.process_new_calendar_event(event_data, user.id, priority=3)
                        processing_results['processed_events'] += 1
                    else:
                        # Process directly through enhanced AI pipeline
                        result = enhanced_ai_processor.enhance_calendar_event_with_intelligence(event_data, user.id)
                        
                        if result.success:
                            processing_results['processed_events'] += 1
                            
                            # Aggregate statistics
                            for entity_type in result.entities_created:
                                if entity_type in processing_results['entities_created']:
                                    processing_results['entities_created'][entity_type] += result.entities_created[entity_type]
                            
                            for entity_type in result.entities_updated:
                                if entity_type in processing_results['entities_updated']:
                                    processing_results['entities_updated'][entity_type] += result.entities_updated[entity_type]
                            
                            processing_results['insights_generated'].extend(result.insights_generated)
                        else:
                            logger.warning(f"Event processing failed: {result.error}")
                    
                except Exception as e:
                    logger.error(f"Failed to process event {event_data.get('id', 'unknown')}: {str(e)}")
                    continue
            
            # Generate proactive insights for meeting preparation
            if processing_results['processed_events'] > 0:
                if enable_real_time and realtime_processor.is_running:
                    realtime_processor.trigger_proactive_insights(user.id, priority=2)
                    processing_results['proactive_insights_triggered'] = True
                else:
                    # Generate insights directly
                    insights = entity_engine.generate_proactive_insights(user.id)
                    meeting_prep_insights = [insight for insight in insights if insight.insight_type == 'meeting_prep']
                    processing_results['meeting_prep_insights'] = [
                        {
                            'type': insight.insight_type,
                            'title': insight.title,
                            'description': insight.description,
                            'priority': insight.priority
                        }
                        for insight in meeting_prep_insights
                    ]
            
            logger.info(f"Enhanced calendar processing complete: {processing_results['processed_events']}/{processing_results['total_events']} events processed")
            
            return processing_results
            
        except Exception as e:
            logger.error(f"Enhanced calendar processing failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'total_events': len(event_batch),
                'processed_events': 0
            }

    def generate_meeting_preparation_tasks(self, user_email: str, days_ahead: int = 3) -> Dict:
        """
        Generate intelligent meeting preparation tasks for upcoming events
        This showcases the enhanced meeting intelligence capabilities
        """
        try:
            user = get_db_manager().get_user_by_email(user_email)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Get upcoming events
            events_result = self.fetch_recent_events(user_email, days_ahead=days_ahead, days_back=0)
            
            if not events_result['success']:
                return events_result
            
            upcoming_events = [e for e in events_result['events'] 
                             if e.get('start_time') and 
                             datetime.fromisoformat(e['start_time']) > datetime.utcnow()]
            
            prep_results = {
                'success': True,
                'upcoming_events': len(upcoming_events),
                'prep_tasks_generated': 0,
                'high_priority_meetings': 0,
                'attendee_intelligence': {},
                'enhanced_meeting_context': []
            }
            
            for event_data in upcoming_events:
                try:
                    # Calculate meeting priority based on attendees, title, etc.
                    attendee_count = len(event_data.get('attendees', []))
                    has_external_attendees = any('@' in attendee and 
                                                not attendee.endswith(user_email.split('@')[1])
                                                for attendee in event_data.get('attendees', []))
                    
                    is_high_priority = (attendee_count > 3 or has_external_attendees or 
                                      any(keyword in event_data.get('title', '').lower() 
                                          for keyword in ['board', 'executive', 'quarterly', 'review', 'presentation']))
                    
                    if is_high_priority:
                        prep_results['high_priority_meetings'] += 1
                        
                        # Create meeting preparation context
                        context = EntityContext(
                            source_type='calendar',
                            source_id=event_data.get('id'),
                            user_id=user.id,
                            confidence=0.9
                        )
                        
                        # Generate prep tasks using entity engine
                        meeting_title = event_data.get('title', 'Meeting')
                        prep_task_description = f"Prepare for '{meeting_title}' - review agenda, attendee backgrounds, and relevant documents"
                        
                        task = entity_engine.create_task_with_full_context(
                            description=prep_task_description,
                            assignee_email=None,  # User's own prep task
                            topic_names=[meeting_title],
                            context=context,
                            priority='high'
                        )
                        
                        if task:
                            prep_results['prep_tasks_generated'] += 1
                        
                        # Store enhanced meeting context
                        prep_results['enhanced_meeting_context'].append({
                            'event_id': event_data.get('id'),
                            'title': meeting_title,
                            'start_time': event_data.get('start_time'),
                            'attendee_count': attendee_count,
                            'has_external_attendees': has_external_attendees,
                            'prep_task_created': bool(task)
                        })
                
                except Exception as e:
                    logger.error(f"Failed to generate prep for event {event_data.get('id', 'unknown')}: {str(e)}")
                    continue
            
            logger.info(f"Meeting preparation complete: {prep_results['prep_tasks_generated']} prep tasks generated for {prep_results['high_priority_meetings']} high-priority meetings")
            
            return prep_results
            
        except Exception as e:
            logger.error(f"Meeting preparation generation failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'prep_tasks_generated': 0
            }

# Create global instance
calendar_fetcher = CalendarFetcher() 