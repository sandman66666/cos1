"""
API Routes Package
==================

This package contains all the route blueprints for the AI Chief of Staff API.
Each blueprint handles a specific domain of functionality.
"""

from .auth_routes import auth_bp
from .email_routes import email_bp
from .intelligence_routes import intelligence_bp
from .task_routes import task_bp
from .people_routes import people_bp
from .calendar_routes import calendar_bp
from .topic_routes import topic_bp
from .settings_routes import settings_bp
from .knowledge_routes import knowledge_bp

# List of all blueprints to register
BLUEPRINTS = [
    auth_bp,
    email_bp, 
    intelligence_bp,
    task_bp,
    people_bp,
    calendar_bp,
    topic_bp,
    settings_bp,
    knowledge_bp
] 