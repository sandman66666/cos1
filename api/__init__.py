"""
AI Chief of Staff API Package
============================

Modular Flask API for the AI Chief of Staff application.
Refactored from monolithic main.py for better maintainability.
"""

__version__ = "2.0.0"
__author__ = "AI Chief of Staff Team"

# Export main API components (legacy)
from .enhanced_endpoints import enhanced_api_bp
from .realtime_endpoints import realtime_api_bp
from .analytics_endpoints import analytics_api_bp
from .entity_endpoints import entity_api_bp

# Export modular routes
try:
    from .routes.auth_routes import auth_bp
    from .routes.email_routes import email_bp
    from .routes.settings_routes import settings_bp
    from .routes.intelligence_routes import intelligence_bp
    from .routes.task_routes import task_bp
    from .routes.people_routes import people_bp
    from .routes.topic_routes import topic_bp
    from .routes.calendar_routes import calendar_bp
    
    modular_routes_available = True
except ImportError as e:
    print(f"Warning: Could not import modular routes: {e}")
    modular_routes_available = False

__all__ = [
    'enhanced_api_bp',
    'realtime_api_bp', 
    'analytics_api_bp',
    'entity_api_bp'
]

if modular_routes_available:
    __all__.extend([
        'auth_bp',
        'email_bp', 
        'settings_bp',
        'intelligence_bp',
        'task_bp',
        'people_bp',
        'topic_bp',
        'calendar_bp'
    ]) 