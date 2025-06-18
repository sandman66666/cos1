"""
API Routes Package
==================

This package contains all the Flask blueprint route definitions for the AI Chief of Staff API.

Blueprints included:
- auth_routes: Authentication and session management
- email_routes: Email processing and analysis
- task_routes: Task management and creation
- people_routes: Contact and relationship management
- intelligence_routes: Business intelligence and insights
- calendar_routes: Calendar integration and event processing
- enhanced_agent_routes: Claude 4 Opus agent capabilities
- breakthrough_routes: Advanced analytics and breakthrough insights
- settings_routes: User settings and system configuration
"""

# This file makes the api/routes directory a proper Python package
# so that Flask can import the blueprint modules correctly.

# We don't import the blueprints here to avoid circular import issues
# The blueprints are imported directly in main.py 