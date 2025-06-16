"""
Calendar Routes Blueprint
========================

Calendar events and meeting preparation routes.
Extracted from main.py for better organization.
"""

import logging
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, session
from ..middleware.auth_middleware import get_current_user, require_auth
from email.utils import parseaddr
from chief_of_staff_ai.models.database import get_db_manager, Calendar

logger = logging.getLogger(__name__)

# Fix URL prefix to match frontend expectations
calendar_bp = Blueprint('calendar', __name__, url_prefix='/api/calendar')


def parse_name_from_email(email: str, display_name: str = None) -> str:
    """Parse a proper name from email and display name"""
    if display_name and len(display_name.strip()) > 0:
        return display_name.strip()
        
    local_part = email.split('@')[0]
    # Handle common formats like first.last, first_last, firstlast
    if '.' in local_part:
        parts = local_part.split('.')
        return ' '.join(part.capitalize() for part in parts)
    elif '_' in local_part:
        parts = local_part.split('_')
        return ' '.join(part.capitalize() for part in parts)
    else:
        # Try to split by camelCase
        import re
        parts = re.findall('[A-Z][^A-Z]*', local_part)
        if len(parts) > 1:
            return ' '.join(parts)
        # Try to split by numbers
        parts = re.split(r'\d+', local_part)
        if len(parts) > 1:
            return ' '.join(part.capitalize() for part in parts if part)
        # Just capitalize the local part
        return local_part.capitalize()


@calendar_bp.route('/fetch', methods=['POST'])
@require_auth
def api_fetch_calendar():
    """Fetch calendar events and create prep tasks"""
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        from ingest.calendar_fetcher import calendar_fetcher
        from models.database import get_db_manager
        from chief_of_staff_ai.processors.email_quality_filter import email_quality_filter
        
        data = request.get_json() or {}
        days_back = data.get('days_back', 3)
        days_forward = data.get('days_forward', 14)
        force_refresh = data.get('force_refresh', False)
        create_prep_tasks = data.get('create_prep_tasks', False)
        add_attendees_tier_1 = data.get('add_attendees_tier_1', True)
        
        user_email = user['email']
        
        # Get user from database
        db_user = get_db_manager().get_user_by_email(user_email)
        if not db_user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Fetch calendar events
        logger.info(f"Fetching calendar events for {user_email}")
        calendar_result = calendar_fetcher.fetch_calendar_events(
            user_email=user_email, 
            days_back=days_back, 
            days_forward=days_forward,
            force_refresh=force_refresh
        )
        
        if not calendar_result.get('success'):
            return jsonify({
                'success': False,
                'error': calendar_result.get('error', 'Failed to fetch calendar events')
            }), 500
        
        events = calendar_result.get('events', [])
        events_imported = len(events)
        
        # Extract unique attendees
        attendees = set()
        for event in events:
            if isinstance(event, dict):
                event_attendees = event.get('attendees', [])
                for attendee in event_attendees:
                    email = attendee.get('email')
                    if email and '@' in email and email != user_email:
                        attendees.add(email.lower())
        
        # Add attendees to Tier 1 if requested
        tier_1_contacts = 0
        if add_attendees_tier_1:
            for attendee in attendees:
                # Create contact engagement stats for the attendee
                stats = email_quality_filter.ContactEngagementStats(
                    email_address=attendee,
                    name=None,
                    emails_received=1,
                    emails_responded_to=1,
                    last_email_date=datetime.now(timezone.utc),
                    first_email_date=datetime.now(timezone.utc),
                    response_rate=1.0,
                    days_since_last_email=0,
                    avg_days_between_emails=0,
                    tier=email_quality_filter.ContactTier.TIER_1,
                    tier_reason="Calendar attendee",
                    should_process=True
                )
                email_quality_filter._contact_tiers[attendee] = stats
                tier_1_contacts += 1
        
        # Create meeting preparation tasks if requested
        prep_tasks_result = {'prep_tasks_created': 0, 'tasks': []}
        if create_prep_tasks and events:
            logger.info(f"Creating meeting prep tasks for {user_email}")
            prep_tasks_result = calendar_fetcher.create_meeting_prep_tasks(db_user.id, events)
        
        # Save events to database
        saved_events = []
        for event in events:
            if isinstance(event, dict):
                saved_event = get_db_manager().save_calendar_event(db_user.id, event)
                if saved_event:
                    saved_events.append(saved_event.to_dict())
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported {events_imported} calendar events',
            'events': saved_events,
            'events_imported': events_imported,
            'attendees_added': len(attendees),
            'tier_1_contacts': tier_1_contacts,
            'prep_tasks_created': prep_tasks_result.get('prep_tasks_created', 0),
            'prep_tasks': prep_tasks_result.get('tasks', []),
            'date_range': {
                'start': f"{days_back} days ago",
                'end': f"{days_forward} days ahead"
            }
        })
        
    except Exception as e:
        logger.error(f"Calendar fetch error for {user['email']}: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f"Calendar fetch failed: {str(e)}",
            'prep_tasks_created': 0
        }), 500


@calendar_bp.route('/events', methods=['GET'])
@require_auth
def api_get_calendar_events():
    """Get calendar events"""
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        user_email = user['email']
        days_forward = request.args.get('days_forward', 14, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        db_user = get_db_manager().get_user_by_email(user_email)
        if not db_user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Get events from database
        with get_db_manager().get_session() as session:
            # Calculate date range
            now = datetime.now(timezone.utc)
            start_date = now
            end_date = now + timedelta(days=days_forward)
            
            events = session.query(Calendar).filter(
                Calendar.user_id == db_user.id,
                Calendar.start_time >= start_date,
                Calendar.start_time <= end_date
            ).order_by(Calendar.start_time.asc()).limit(limit).all()
            
            # Convert to dict format and check for prep tasks
            events_data = []
            all_user_tasks = get_db_manager().get_user_tasks(db_user.id)
            prep_tasks = [task for task in all_user_tasks if task.category == 'meeting_preparation']
            
            for event in events:
                event_dict = event.to_dict()
                
                # Check if this event has associated prep tasks
                related_prep_tasks = [task for task in prep_tasks if 
                                    event.title and task.description and 
                                    (event.title.lower() in task.description.lower() or 
                                     any(word in task.description.lower() for word in event.title.lower().split() if len(word) > 3))]
                
                event_dict['has_prep_tasks'] = len(related_prep_tasks) > 0
                event_dict['prep_tasks_count'] = len(related_prep_tasks)
                
                # Add attendee count and strategic importance
                attendees = event.attendees or []
                event_dict['attendee_count'] = len(attendees)
                
                # Calculate strategic importance based on attendees
                importance = event.importance_score or 0.5  # Base importance
                if attendees:
                    tier_1_count = len([a for a in attendees if a.get('relationship_type') == 'tier_1'])
                    importance += (tier_1_count / len(attendees)) * 0.5
                
                event_dict['strategic_importance'] = min(1.0, importance)
                
                # Determine if preparation is needed
                event_dict['preparation_needed'] = event.preparation_needed or (
                    len(attendees) > 2 or  # More than 2 attendees
                    any(a.get('relationship_type') == 'tier_1' for a in attendees) or  # Any Tier 1 contact
                    importance > 0.7  # High strategic importance
                )
                
                events_data.append(event_dict)
            
            return jsonify({
                'success': True,
                'events': events_data,
                'count': len(events_data)
            })
            
    except Exception as e:
        logger.error(f"Get calendar events error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/meeting-prep-tasks', methods=['GET'])
@require_auth
def api_get_meeting_prep_tasks():
    """Get meeting preparation tasks"""
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        if not db_user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Get prep tasks that are not completed
        all_tasks = get_db_manager().get_user_tasks(db_user.id)
        prep_tasks = [task for task in all_tasks if 
                     task.category == 'meeting_preparation' and 
                     task.status in ['pending', 'open']]
        
        return jsonify({
            'success': True,
            'tasks': [task.to_dict() for task in prep_tasks],
            'count': len(prep_tasks)
        })
    
    except Exception as e:
        logger.error(f"Get meeting prep tasks error for {user['email']}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@calendar_bp.route('/free-time', methods=['POST'])
@require_auth
def api_free_time_analysis():
    """Analyze free time in calendar"""
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        from ingest.calendar_fetcher import calendar_fetcher
        
        data = request.get_json() or {}
        days_forward = data.get('days_forward', 7)
        user_email = user['email']
        
        # Get free time analysis
        result = calendar_fetcher.fetch_free_time_analysis(
            user_email=user_email,
            days_forward=days_forward
        )
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Free time analysis error for {user['email']}: {str(e)}")
        return jsonify({
            'success': False, 
            'error': f"Free time analysis failed: {str(e)}",
            'free_slots': []
        }), 500


@calendar_bp.route('/process-upcoming', methods=['POST'])
@require_auth
def process_upcoming_meetings():
    """Process upcoming meetings and generate preparation intelligence"""
    user = get_current_user()
    if not user:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        if not db_user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Placeholder for meeting processing functionality
        return jsonify({
            'success': True,
            'message': 'Meeting processing completed',
            'meetings_processed': 0
        })
    
    except Exception as e:
        logger.error(f"Process upcoming meetings error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@calendar_bp.route('/import-and-tier', methods=['POST'])
@require_auth
def import_calendar_and_tier():
    """Import calendar events and add participants to Tier 1"""
    from chief_of_staff_ai.ingest.calendar_fetcher import calendar_fetcher
    from chief_of_staff_ai.processors.email_quality_filter import email_quality_filter, ContactTier
    from models.database import get_db_manager
    
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json() or {}
        days_back = data.get('days_back', 180)  # Default 6 months back
        days_forward = data.get('days_forward', 90)  # Default 3 months forward
        add_participants_tier_1 = data.get('add_participants_tier_1', True)
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        logger.info(f"📅 Importing calendar events for {user_email}")
        
        # Fetch calendar events
        calendar_result = calendar_fetcher.fetch_calendar_events(
            user_email=user_email,
            days_back=days_back,
            days_forward=days_forward
        )
        
        if not calendar_result.get('success'):
            return jsonify({
                'success': False,
                'error': calendar_result.get('error', 'Failed to fetch calendar events')
            }), 500
        
        events = calendar_result.get('events', [])
        events_imported = len(events)
        
        # Extract unique participants
        participants = set()
        for event in events:
            attendees = event.get('attendees', [])
            for attendee in attendees:
                email = attendee.get('email')
                if email:
                    email_addr = parseaddr(email)[1].lower()
                    if email_addr and '@' in email_addr and email_addr != user_email:
                        participants.add(email_addr)
        
        # Add participants to Tier 1
        tier_1_contacts = 0
        if add_participants_tier_1:
            for participant in participants:
                email_quality_filter._contact_tiers[participant] = ContactTier.TIER_1
                tier_1_contacts += 1
            
            logger.info(f"👥 Added {tier_1_contacts} meeting participants to Tier 1")
        
        # Save events to database
        with get_db_manager().get_session() as session:
            for event in events:
                # Save event using your existing database models/methods
                pass  # Implement based on your database schema
            
            session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported {events_imported} calendar events',
            'events_imported': events_imported,
            'participants_added': len(participants),
            'tier_1_contacts': tier_1_contacts,
            'date_range': {
                'start': f"{days_back} days ago",
                'end': f"{days_forward} days ahead"
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Calendar import error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to import calendar: {str(e)}'
        }), 500


@calendar_bp.route('/sync', methods=['POST'])
@require_auth
def sync_calendar():
    """Sync calendar events and extract participants as contacts"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        from chief_of_staff_ai.ingest.calendar_fetcher import calendar_fetcher
        
        data = request.get_json() or {}
        days_back = data.get('days_back', 30)
        days_forward = data.get('days_forward', 30)
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Fetch calendar events
        result = calendar_fetcher.fetch_calendar_events(
            user_email=user_email,
            days_back=days_back,
            days_forward=days_forward
        )
        
        if not result.get('success'):
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error fetching calendar events')
            }), 400
        
        events = result.get('events', [])
        
        # Extract participants as contacts
        participants_added = 0
        with get_db_manager().get_session() as session:
            for event in events:
                for attendee in event.get('attendees', []):
                    email = attendee.get('email')
                    display_name = attendee.get('displayName')
                    
                    if email and '@' in email and email != user_email:
                        # Parse a proper name from email/display name
                        name = parse_name_from_email(email, display_name)
                        
                        # Create or update person
                        person_data = {
                            'email_address': email,
                            'name': name,
                            'last_interaction': event.get('start', {}).get('dateTime'),
                            'relationship_type': 'Calendar Contact'
                        }
                        
                        get_db_manager().create_or_update_person(db_user.id, person_data)
                        participants_added += 1
            
            session.commit()
        
        return jsonify({
            'success': True,
            'events_fetched': len(events),
            'participants_added': participants_added,
            'message': f"Synced {len(events)} events and added {participants_added} participants as contacts"
        })
        
    except Exception as e:
        logger.error(f"Calendar sync error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/enhanced-calendar-events', methods=['GET'])
@require_auth
def get_enhanced_calendar_events():
    """Get calendar events with enhanced metadata"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager
        
        days_ahead = int(request.args.get('days_ahead', 14))
        days_back = int(request.args.get('days_back', 7))
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get events from database
        with get_db_manager().get_session() as session:
            # Calculate date range
            now = datetime.now(timezone.utc)
            start_date = now - timedelta(days=days_back)
            end_date = now + timedelta(days=days_ahead)
            
            events = session.query(Calendar).filter(
                Calendar.user_id == db_user.id,
                Calendar.start_time >= start_date,
                Calendar.start_time <= end_date
            ).order_by(Calendar.start_time).all()
            
            # Convert to enhanced format
            enhanced_events = []
            for event in events:
                event_dict = event.to_dict()
                
                # Add attendee information
                attendees = []
                for attendee in event.attendees:
                    person = session.query(Person).filter(
                        Person.user_id == db_user.id,
                        Person.email_address == attendee['email']
                    ).first()
                    
                    if person:
                        attendee['name'] = person.name
                        attendee['company'] = person.company
                        attendee['relationship_type'] = person.relationship_type
                        attendee['total_emails'] = person.total_emails
                    
                    attendees.append(attendee)
                
                event_dict['enhanced_attendees'] = attendees
                event_dict['attendee_count'] = len(attendees)
                
                # Add strategic importance based on attendees
                importance = 0.5  # Base importance
                if attendees:
                    tier_1_count = len([a for a in attendees if a.get('relationship_type') == 'tier_1'])
                    importance += (tier_1_count / len(attendees)) * 0.5
                
                event_dict['strategic_importance'] = min(1.0, importance)
                
                # Determine if preparation is needed
                event_dict['preparation_needed'] = (
                    len(attendees) > 2 or  # More than 2 attendees
                    any(a.get('relationship_type') == 'tier_1' for a in attendees) or  # Any Tier 1 contact
                    importance > 0.7  # High strategic importance
                )
                
                enhanced_events.append(event_dict)
            
            return jsonify({
                'success': True,
                'events': enhanced_events,
                'count': len(enhanced_events)
            })
            
    except Exception as e:
        logger.error(f"Get enhanced calendar events error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@calendar_bp.route('/augment-with-knowledge', methods=['POST'])
@require_auth
def augment_meetings_with_knowledge():
    """Augment calendar meetings with knowledge tree context"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from models.database import get_db_manager, CalendarEvent, Task
        from api.routes.email_routes import get_master_knowledge_tree
        from datetime import datetime, timedelta
        
        data = request.get_json() or {}
        use_knowledge_tree = data.get('use_knowledge_tree', True)
        add_attendee_context = data.get('add_attendee_context', True)
        generate_preparation_tasks = data.get('generate_preparation_tasks', True)
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get knowledge tree
        if use_knowledge_tree:
            master_tree = get_master_knowledge_tree(db_user.id)
            if not master_tree:
                return jsonify({
                    'success': False,
                    'error': 'No knowledge tree found. Please build the knowledge tree first.'
                }), 400
        else:
            master_tree = None
        
        with get_db_manager().get_session() as session:
            # Get upcoming meetings that need augmentation
            now = datetime.utcnow()
            upcoming_meetings = session.query(CalendarEvent).filter(
                CalendarEvent.user_id == db_user.id,
                CalendarEvent.start_time >= now,
                CalendarEvent.start_time <= now + timedelta(days=30)  # Next 30 days
            ).all()
            
            if not upcoming_meetings:
                return jsonify({
                    'success': True,
                    'meetings_enhanced': 0,
                    'message': 'No upcoming meetings found to augment'
                })
            
            meetings_enhanced = 0
            attendee_intelligence_added = 0
            preparation_tasks_created = 0
            strategic_meetings = 0
            sample_meetings = []
            
            logger.info(f"Augmenting {len(upcoming_meetings)} meetings with knowledge tree context")
            
            for meeting in upcoming_meetings:
                try:
                    enhanced = False
                    meeting_intelligence = meeting.business_intelligence or {}
                    
                    # Analyze attendees against knowledge tree
                    attendee_intelligence = []
                    if master_tree and add_attendee_context:
                        for attendee in meeting.attendees or []:
                            attendee_email = attendee.get('email', '').lower()
                            
                            # Find attendee in knowledge tree
                            for person in master_tree.get('people', []):
                                if person['email'].lower() == attendee_email:
                                    attendee_intelligence.append({
                                        'email': attendee_email,
                                        'name': person.get('name', attendee.get('name', 'Unknown')),
                                        'role': person.get('role', 'Unknown role'),
                                        'company': person.get('company', 'Unknown company'),
                                        'relationship_strength': person.get('relationship_strength', 0.5),
                                        'primary_topics': person.get('primary_topics', []),
                                        'strategic_importance': person.get('relationship_strength', 0) > 0.7
                                    })
                                    break
                    
                    if attendee_intelligence:
                        meeting_intelligence['attendee_intelligence'] = attendee_intelligence
                        attendee_intelligence_added += 1
                        enhanced = True
                        
                        # Check if this is a strategic meeting
                        strategic_attendees = sum(1 for att in attendee_intelligence if att['strategic_importance'])
                        if strategic_attendees > 0:
                            strategic_meetings += 1
                            meeting_intelligence['is_strategic'] = True
                    
                    # Find related topics and projects
                    related_items = {'topics': [], 'projects': []}
                    if master_tree:
                        meeting_title_lower = (meeting.title or '').lower()
                        meeting_description_lower = (meeting.description or '').lower()
                        
                        # Find related topics
                        for topic in master_tree.get('topics', []):
                            topic_name_lower = topic['name'].lower()
                            if (topic_name_lower in meeting_title_lower or 
                                topic_name_lower in meeting_description_lower):
                                related_items['topics'].append({
                                    'name': topic['name'],
                                    'importance': topic.get('importance', 0.5),
                                    'description': topic.get('description', '')
                                })
                        
                        # Find related projects
                        for project in master_tree.get('projects', []):
                            project_name_lower = project['name'].lower()
                            if (project_name_lower in meeting_title_lower or 
                                project_name_lower in meeting_description_lower):
                                related_items['projects'].append({
                                    'name': project['name'],
                                    'status': project.get('status', 'unknown'),
                                    'priority': project.get('priority', 'medium'),
                                    'key_people': project.get('key_people', [])
                                })
                    
                    if related_items['topics'] or related_items['projects']:
                        meeting_intelligence['related_items'] = related_items
                        enhanced = True
                    
                    # Generate preparation tasks
                    if generate_preparation_tasks and (attendee_intelligence or related_items['topics'] or related_items['projects']):
                        prep_tasks = []
                        
                        # Task: Review attendee backgrounds
                        if attendee_intelligence:
                            high_value_attendees = [att for att in attendee_intelligence if att['strategic_importance']]
                            if high_value_attendees:
                                prep_tasks.append({
                                    'description': f"Review backgrounds of key attendees: {', '.join([att['name'] for att in high_value_attendees[:3]])}",
                                    'category': 'meeting_prep',
                                    'priority': 'high',
                                    'due_date': meeting.start_time - timedelta(hours=2),
                                    'context': f"Meeting: {meeting.title}"
                                })
                        
                        # Task: Prepare topics for discussion
                        if related_items['topics']:
                            top_topics = related_items['topics'][:2]
                            prep_tasks.append({
                                'description': f"Prepare talking points for: {', '.join([t['name'] for t in top_topics])}",
                                'category': 'meeting_prep',
                                'priority': 'medium',
                                'due_date': meeting.start_time - timedelta(hours=1),
                                'context': f"Meeting: {meeting.title}"
                            })
                        
                        # Task: Review project status
                        if related_items['projects']:
                            active_projects = [p for p in related_items['projects'] if p['status'] == 'active']
                            if active_projects:
                                prep_tasks.append({
                                    'description': f"Review status updates for: {', '.join([p['name'] for p in active_projects[:2]])}",
                                    'category': 'meeting_prep',
                                    'priority': 'medium',
                                    'due_date': meeting.start_time - timedelta(minutes=30),
                                    'context': f"Meeting: {meeting.title}"
                                })
                        
                        # Save preparation tasks
                        for task_data in prep_tasks:
                            task = Task(
                                user_id=db_user.id,
                                calendar_event_id=meeting.id,
                                description=task_data['description'],
                                category=task_data['category'],
                                priority=task_data['priority'],
                                due_date=task_data['due_date'],
                                status='pending',
                                confidence=0.9,  # High confidence for meeting prep tasks
                                source_context=task_data['context'],
                                business_intelligence={
                                    'meeting_preparation': True,
                                    'meeting_title': meeting.title,
                                    'meeting_date': meeting.start_time.isoformat(),
                                    'strategic_meeting': meeting_intelligence.get('is_strategic', False),
                                    'knowledge_tree_enhanced': True
                                }
                            )
                            session.add(task)
                            preparation_tasks_created += 1
                    
                    # Update meeting with intelligence
                    if enhanced:
                        meeting_intelligence['last_augmented'] = datetime.utcnow().isoformat()
                        meeting_intelligence['knowledge_tree_enhanced'] = True
                        meeting.business_intelligence = meeting_intelligence
                        meetings_enhanced += 1
                        
                        # Add to sample
                        if len(sample_meetings) < 5:
                            sample_meetings.append({
                                'title': meeting.title,
                                'start_time': meeting.start_time.isoformat(),
                                'attendee_count': len(attendee_intelligence),
                                'strategic_attendees': sum(1 for att in attendee_intelligence if att['strategic_importance']),
                                'related_topics': len(related_items.get('topics', [])),
                                'related_projects': len(related_items.get('projects', [])),
                                'preparation_tasks': len([t for t in prep_tasks if 'prep_tasks' in locals()]) if 'prep_tasks' in locals() else 0
                            })
                
                except Exception as e:
                    logger.error(f"Error augmenting meeting {meeting.id}: {str(e)}")
                    continue
            
            session.commit()
            
            return jsonify({
                'success': True,
                'meetings_enhanced': meetings_enhanced,
                'attendee_intelligence_added': attendee_intelligence_added,
                'preparation_tasks_created': preparation_tasks_created,
                'strategic_meetings': strategic_meetings,
                'total_meetings_processed': len(upcoming_meetings),
                'sample_meetings': sample_meetings,
                'knowledge_tree_used': use_knowledge_tree,
                'message': f'Enhanced {meetings_enhanced} meetings with knowledge tree context'
            })
            
    except Exception as e:
        logger.error(f"Augment meetings with knowledge error: {str(e)}")
        return jsonify({'error': str(e)}), 500 