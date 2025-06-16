"""
AI Chief of Staff - Flask App Factory
=====================================

This module creates and configures the Flask application using the factory pattern.
Refactored from monolithic main.py for better maintainability and testing.
"""

import os
import sys
import logging
import tempfile
from datetime import timedelta
from flask import Flask
from flask_session import Session

# Add the chief_of_staff_ai directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'chief_of_staff_ai'))

from .routes import BLUEPRINTS
from .middleware.error_handlers import register_error_handlers
from .middleware.request_logging import setup_request_logging

def register_blueprints(app):
    """
    Register all API blueprints with the Flask application.
    
    Args:
        app: Flask application instance
    """
    # Register blueprints
    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)
        
    print(f"✓ Registered {len(BLUEPRINTS)} API blueprints")

def create_app(config_name='default'):
    """
    Flask application factory.
    
    Args:
        config_name: Configuration to use ('default', 'development', 'production', 'testing')
        
    Returns:
        Flask application instance
    """
    
    # Import configuration here to avoid circular imports
    try:
        from config.settings import settings
    except ImportError as e:
        print(f"Failed to import settings: {e}")
        sys.exit(1)
    
    # Create Flask application
    app = Flask(__name__)
    
    # Configure application
    app.secret_key = settings.SECRET_KEY
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.path.join(tempfile.gettempdir(), 'cos_flask_session')
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=settings.SESSION_TIMEOUT_HOURS)
    
    # Initialize extensions
    Session(app)
    
    # Create necessary directories
    settings.create_directories()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Register middleware
    register_error_handlers(app)
    setup_request_logging(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Health check route
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'AI Chief of Staff API'}
    
    return app


def run_app(app=None, host='localhost', port=5000, debug=False):
    """
    Run the Flask application.
    
    Args:
        app: Flask app instance (creates new one if None)
        host: Host to run on
        port: Port to run on
        debug: Enable debug mode
    """
    if app is None:
        app = create_app()
    
    try:
        # Validate settings
        from config.settings import settings
        config_errors = settings.validate_config()
        if config_errors:
            raise ValueError(f"Configuration errors: {', '.join(config_errors)}")
        
        print("🚀 Starting AI Chief of Staff Web Application")
        print(f"📧 Gmail integration: {'✓ Configured' if settings.GOOGLE_CLIENT_ID else '✗ Missing'}")
        print(f"📅 Calendar integration: {'✓ Enabled' if 'https://www.googleapis.com/auth/calendar.readonly' in settings.GMAIL_SCOPES else '✗ Missing'}")
        print(f"🤖 Claude integration: {'✓ Configured' if settings.ANTHROPIC_API_KEY else '✗ Missing'}")
        print(f"🧠 Enhanced Intelligence: ✓ Active")
        print(f"🌐 Server: http://{host}:{port}")
        
        app.run(host=host, port=port, debug=debug)
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        sys.exit(1) 