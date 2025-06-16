"""
Error Handlers Middleware
========================

Global error handlers for the Flask application.
Extracted from main.py for better organization.
"""

import logging
from flask import render_template, jsonify, request

logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """
    Register error handlers with the Flask application.
    
    Args:
        app: Flask application instance
    """
    
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors"""
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Endpoint not found'}), 404
        return render_template('error.html', 
                             error_code=404, 
                             error_message="Page not found"), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors"""
        logger.error(f"Internal server error: {error}")
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('error.html', 
                             error_code=500, 
                             error_message="Internal server error"), 500
    
    @app.errorhandler(401)
    def unauthorized_error(error):
        """Handle 401 Unauthorized errors"""
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Authentication required'}), 401
        return jsonify({'error': 'Authentication required'}), 401
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors"""
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Access forbidden'}), 403
        return jsonify({'error': 'Access forbidden'}), 403
    
    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle 400 Bad Request errors"""
        if request.path.startswith('/api/'):
            return jsonify({'error': 'Bad request'}), 400
        return jsonify({'error': 'Bad request'}), 400 