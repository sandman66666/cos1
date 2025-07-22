"""
Settings Routes Blueprint
========================

User settings, sync configuration, and system management routes.
Extracted from main.py for better organization.
"""

import logging
from flask import Blueprint, request, jsonify
from ..middleware.auth_middleware import get_current_user, require_auth

logger = logging.getLogger(__name__)

# Create blueprint
settings_bp = Blueprint('settings', __name__, url_prefix='/api')


@settings_bp.route('/settings', methods=['GET'])
def api_get_settings():
    """API endpoint to get user settings"""
    from ..middleware.auth_middleware import get_current_user
    from chief_of_staff_ai.models.database import get_db_manager
    
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        db_user = get_db_manager().get_user_by_email(user['email'])
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        settings_data = {
            'email_fetch_limit': db_user.email_fetch_limit,
            'email_days_back': db_user.email_days_back,
            'auto_process_emails': db_user.auto_process_emails,
            'last_login': db_user.last_login.isoformat() if db_user.last_login else None,
            'created_at': db_user.created_at.isoformat() if db_user.created_at else None,
            'name': db_user.name,
            'email': db_user.email
        }
        
        return jsonify({
            'success': True,
            'settings': settings_data
        })
        
    except Exception as e:
        logger.error(f"Get settings API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/settings', methods=['PUT'])
def api_update_settings():
    """API endpoint to update user settings"""
    from ..middleware.auth_middleware import get_current_user
    from chief_of_staff_ai.models.database import get_db_manager
    
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        db_user = get_db_manager().get_user_by_email(user['email'])
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update user settings directly on the object
        if 'email_fetch_limit' in data:
            db_user.email_fetch_limit = int(data['email_fetch_limit'])
        if 'email_days_back' in data:
            db_user.email_days_back = int(data['email_days_back'])
        if 'auto_process_emails' in data:
            db_user.auto_process_emails = bool(data['auto_process_emails'])
        
        # Save changes using the database manager's session
        with get_db_manager().get_session() as db_session:
            db_session.merge(db_user)
            db_session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Settings updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Update settings API error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/sync-settings', methods=['GET'])
@require_auth
def get_sync_settings():
    """Get current sync settings"""
    try:
        # Return default settings for now - could be stored in database later
        settings = {
            'email': {
                'maxEmails': 25,
                'daysBack': 7
            },
            'calendar': {
                'daysBack': 3,
                'daysForward': 14
            }
        }
        
        return jsonify({
            'success': True,
            'settings': settings,
            **settings  # Flatten for backward compatibility
        })
        
    except Exception as e:
        logger.error(f"Get sync settings error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/sync-settings', methods=['POST'])
@require_auth
def save_sync_settings():
    """Save sync settings"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No settings provided'}), 400
        
        # For now, just return success - could save to database later
        logger.info(f"Sync settings saved: {data}")
        
        return jsonify({
            'success': True,
            'message': 'Settings saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Save sync settings error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/email-quality/refresh-tiers', methods=['POST'])
@require_auth
def refresh_contact_tiers():
    """Refresh contact tier analysis"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.processors.email_quality_filter import email_quality_filter
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        logger.info(f"🔄 Refreshing contact tiers for user {user_email}")
        
        # Force refresh of contact tiers
        email_quality_filter.force_tier_refresh(db_user.id)
        
        # Get the updated tier summary
        tier_summary = email_quality_filter.get_contact_tier_summary(db_user.id)
        
        return jsonify({
            'success': True,
            'message': 'Contact tiers refreshed successfully',
            'contacts_analyzed': tier_summary.get('total_contacts', 0),
            'tier_summary': tier_summary
        })
        
    except Exception as e:
        logger.error(f"Refresh contact tiers error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/email-quality/build-tier-rules', methods=['POST'])
@require_auth
def build_tier_rules():
    """Build contact tier rules from contact patterns - all sent contacts are Tier 1"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.processors.email_quality_filter import email_quality_filter
        from chief_of_staff_ai.engagement_analysis.smart_contact_strategy import smart_contact_strategy
        
        # Get request data, but don't require it
        data = request.get_json(silent=True) or {}
        contact_patterns = data.get('contact_patterns', {})
        build_rules_only = data.get('build_rules_only', True)
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        logger.info(f"🧠 Building contact tier rules for user {user_email}")
        
        # Get total contacts from contact patterns or default to 0
        total_contacts = contact_patterns.get('total_contacts', 0)
        
        # All contacts from sent emails are Tier 1
        tier_1_count = total_contacts if total_contacts > 0 else 1  # At least 1 Tier 1
        tier_2_count = 0  # No Tier 2 anymore
        tier_last_count = 0  # Start with no LAST tier
        
        logger.info(f"📊 Tier distribution - all sent contacts are Tier 1:")
        logger.info(f"   Tier 1: {tier_1_count}")
        logger.info(f"   Tier LAST: {tier_last_count}")
        
        # Force a tier refresh to apply the new rules
        if not build_rules_only:
            email_quality_filter.force_tier_refresh(db_user.id)
        
        # Set all contacts to Tier 1
        email_quality_filter.set_all_contacts_tier_1(user_email)
        
        # Get tier summary after building rules
        tier_summary = email_quality_filter.get_contact_tier_summary(db_user.id)
        
        logger.info(f"✅ Built tier rules: {tier_1_count} Tier 1, {tier_last_count} Tier LAST")
        
        return jsonify({
            'success': True,
            'message': 'Contact tier rules built successfully - all sent contacts are Tier 1',
            'rules': {
                'tier_1_count': tier_1_count,
                'tier_2_count': 0,  # No Tier 2
                'tier_last_count': tier_last_count,
                'total_contacts': tier_1_count + tier_last_count,
                'rules_created': True,
                'engagement_based_classification': False,  # Not using engagement scores
                'initial_setup': total_contacts == 0,  # Flag if this is initial setup
                'all_sent_tier_1': True  # Flag indicating our new approach
            },
            'tier_summary': tier_summary,
            'contact_patterns': contact_patterns
        })
        
    except Exception as e:
        logger.error(f"Build tier rules error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/email-quality/contact-tiers', methods=['GET'])
@require_auth
def get_contact_tiers():
    """Get contact tier summary"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.processors.email_quality_filter import email_quality_filter
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get tier summary
        tier_summary = email_quality_filter.get_contact_tier_summary(db_user.id)
        
        return jsonify({
            'success': True,
            'tier_summary': tier_summary
        })
        
    except Exception as e:
        logger.error(f"Get contact tiers error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/email-quality/cleanup-existing', methods=['POST'])
@require_auth
def cleanup_low_quality_data():
    """Clean up existing low-quality data from Tier LAST contacts"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        from chief_of_staff_ai.processors.email_quality_filter import email_quality_filter, ContactTier
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        logger.info(f"🧹 Starting cleanup of low-quality data for user {user_email}")
        
        # Get tier summary first
        tier_summary = email_quality_filter.get_contact_tier_summary(db_user.id)
        tier_last_contacts = []
        
        # Get Tier LAST contact emails
        for email, stats in email_quality_filter._contact_tiers.items():
            if stats.tier == ContactTier.TIER_LAST:
                tier_last_contacts.append(email)
        
        if not tier_last_contacts:
            return jsonify({
                'success': True,
                'message': 'No Tier LAST contacts found to clean up',
                'stats': {
                    'emails_removed': 0,
                    'tasks_removed': 0,
                    'tier_last_contacts': 0
                }
            })
        
        # Clean up emails and tasks from Tier LAST contacts
        with get_db_manager().get_session() as session:
            from models.enhanced_models import Email, Task
            
            emails_removed = 0
            tasks_removed = 0
            
            # Remove emails from Tier LAST contacts
            for contact_email in tier_last_contacts:
                emails_to_remove = session.query(Email).filter(
                    Email.user_id == db_user.id,
                    Email.sender.ilike(f'%{contact_email}%')
                ).all()
                
                for email in emails_to_remove:
                    session.delete(email)
                    emails_removed += 1
                
                # Remove tasks related to these contacts
                tasks_to_remove = session.query(Task).filter(
                    Task.user_id == db_user.id,
                    Task.source_context.ilike(f'%{contact_email}%')
                ).all()
                
                for task in tasks_to_remove:
                    session.delete(task)
                    tasks_removed += 1
            
            session.commit()
        
        logger.info(f"✅ Cleanup complete: removed {emails_removed} emails and {tasks_removed} tasks from {len(tier_last_contacts)} Tier LAST contacts")
        
        return jsonify({
            'success': True,
            'message': f'Cleanup complete: removed {emails_removed} emails and {tasks_removed} tasks',
            'stats': {
                'emails_removed': emails_removed,
                'tasks_removed': tasks_removed,
                'tier_last_contacts': len(tier_last_contacts)
            }
        })
        
    except Exception as e:
        logger.error(f"Cleanup low-quality data error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@settings_bp.route('/flush-database', methods=['POST'])
@require_auth
def flush_database():
    """Flush all user data from the database"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        from chief_of_staff_ai.models.database import get_db_manager
        
        user_email = user['email']
        db_user = get_db_manager().get_user_by_email(user_email)
        
        if not db_user:
            return jsonify({'error': 'User not found'}), 404
        
        logger.warning(f"🗑️ FLUSHING ALL DATA for user {user_email}")
        
        # Flush all user data
        result = get_db_manager().flush_user_data(db_user.id)
        
        if result:
            logger.info(f"✅ Database flush complete for user {user_email}")
            return jsonify({
                'success': True,
                'message': 'All user data has been permanently deleted',
                'flushed_data': {
                    'emails': 'All emails and AI analysis deleted',
                    'people': 'All contacts and relationships deleted', 
                    'tasks': 'All tasks and projects deleted',
                    'topics': 'All topics and insights deleted',
                    'calendar': 'All calendar events deleted'
                }
            })
        else:
            return jsonify({'error': 'Database flush failed'}), 500
        
    except Exception as e:
        logger.error(f"Database flush error: {str(e)}")
        return jsonify({'error': str(e)}), 500 