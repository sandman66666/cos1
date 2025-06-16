"""
Request Logging Middleware
=========================

Middleware for logging and handling requests.
"""

import logging
from flask import request

logger = logging.getLogger(__name__)


def setup_request_logging(app):
    """
    Setup request logging middleware.
    
    Args:
        app: Flask application instance
    """
    
    @app.after_request
    def after_request(response):
        """Add cache-busting headers to prevent session contamination"""
        # Prevent caching for API endpoints and sensitive pages
        if (request.endpoint and 
            (request.endpoint.startswith('api_') or 
             request.path.startswith('/api/') or
             request.path in ['/dashboard', '/debug/session'])):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    
    @app.before_request
    def log_request_info():
        """Log basic request information"""
        if request.path.startswith('/api/'):
            logger.debug(f"API Request: {request.method} {request.path}")
    
    return app 