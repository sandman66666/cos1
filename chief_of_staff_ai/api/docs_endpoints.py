# API Documentation and Testing Endpoints
# These endpoints provide comprehensive documentation, testing tools, and API exploration

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, render_template, send_from_directory
from functools import wraps
import json
import inspect
import os
from pathlib import Path

# Import the integration manager and other API modules
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'chief_of_staff_ai'))

from api.versioning import API_VERSIONS, CURRENT_VERSION

logger = logging.getLogger(__name__)

# Create Blueprint
docs_api_bp = Blueprint('docs_api', __name__, url_prefix='/api/docs')

# =====================================================================
# API DOCUMENTATION CONFIGURATION
# =====================================================================

API_DOCUMENTATION = {
    'info': {
        'title': 'AI Chief of Staff API',
        'description': 'Comprehensive entity-centric AI Chief of Staff API with real-time processing, analytics, and intelligent automation',
        'version': '2.0.0',
        'contact': {
            'name': 'AI Chief of Staff Team',
            'email': 'support@chief-of-staff.ai'
        },
        'license': {
            'name': 'MIT',
            'url': 'https://opensource.org/licenses/MIT'
        }
    },
    'servers': [
        {
            'url': '/api/v2',
            'description': 'Production API (Current)'
        },
        {
            'url': '/api/v1',
            'description': 'Legacy API (Deprecated)'
        }
    ],
    'tags': [
        {
            'name': 'Authentication',
            'description': 'User authentication and session management'
        },
        {
            'name': 'Email Processing',
            'description': 'Email analysis and entity extraction'
        },
        {
            'name': 'Task Management',
            'description': 'Task creation, management, and tracking'
        },
        {
            'name': 'Entity Management',
            'description': 'People, topics, and relationship management'
        },
        {
            'name': 'Analytics',
            'description': 'Business intelligence and insights'
        },
        {
            'name': 'Real-time',
            'description': 'WebSocket-based real-time processing'
        },
        {
            'name': 'Batch Processing',
            'description': 'High-volume batch operations'
        }
    ]
}

ENDPOINT_EXAMPLES = {
    '/api/auth/login': {
        'method': 'POST',
        'description': 'Authenticate user and receive JWT tokens',
        'request_example': {
            'email': 'user@example.com',
            'password': 'SecurePassword123!',
            'remember_me': False
        },
        'response_example': {
            'success': True,
            'data': {
                'user': {
                    'id': 1,
                    'email': 'user@example.com',
                    'full_name': 'John Doe',
                    'role': 'user'
                },
                'tokens': {
                    'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                    'token_type': 'Bearer',
                    'expires_in': 86400
                }
            }
        }
    },
    '/api/v2/emails/process': {
        'method': 'POST',
        'description': 'Process emails with comprehensive entity creation',
        'request_example': {
            'email_data': [
                {
                    'subject': 'Meeting with Client',
                    'body': 'Hi, let\'s schedule a meeting to discuss the project.',
                    'sender': 'client@company.com',
                    'date': '2024-01-15T10:00:00Z'
                }
            ],
            'real_time': True,
            'batch_size': 10
        },
        'response_example': {
            'success': True,
            'data': {
                'total_processed': 1,
                'entities_created': {
                    'people': 1,
                    'topics': 2,
                    'tasks': 1
                },
                'processing_time': 2.5
            }
        }
    },
    '/api/entities/people': {
        'method': 'GET',
        'description': 'Get all people entities with optional filtering',
        'parameters': {
            'limit': 100,
            'search': 'john',
            'company': 'TechCorp',
            'include_relationships': True
        },
        'response_example': {
            'success': True,
            'data': {
                'people': [
                    {
                        'id': 1,
                        'name': 'John Doe',
                        'email_address': 'john@techcorp.com',
                        'company': 'TechCorp',
                        'importance_level': 0.8,
                        'relationships': []
                    }
                ],
                'pagination': {
                    'total_count': 1,
                    'has_more': False
                }
            }
        }
    }
}

# =====================================================================
# API DOCUMENTATION ENDPOINTS
# =====================================================================

@docs_api_bp.route('/', methods=['GET'])
def api_documentation_home():
    """
    Serve the main API documentation page.
    """
    try:
        return render_template('api_docs.html', 
                             api_info=API_DOCUMENTATION['info'],
                             api_versions=API_VERSIONS,
                             current_version=CURRENT_VERSION)
    except Exception as e:
        # Fallback to JSON if template not available
        return jsonify({
            'success': True,
            'data': {
                'message': 'AI Chief of Staff API Documentation',
                'api_info': API_DOCUMENTATION['info'],
                'available_endpoints': [
                    '/api/docs/openapi.json - OpenAPI specification',
                    '/api/docs/endpoints - List all endpoints',
                    '/api/docs/examples - API usage examples',
                    '/api/docs/testing - Interactive API testing',
                    '/api/versions - API version information'
                ]
            }
        })

@docs_api_bp.route('/openapi.json', methods=['GET'])
def get_openapi_spec():
    """
    Generate OpenAPI 3.0 specification for the API.
    """
    try:
        openapi_spec = {
            'openapi': '3.0.0',
            'info': API_DOCUMENTATION['info'],
            'servers': API_DOCUMENTATION['servers'],
            'tags': API_DOCUMENTATION['tags'],
            'paths': _generate_openapi_paths(),
            'components': _generate_openapi_components(),
            'security': [
                {'BearerAuth': []}
            ]
        }
        
        return jsonify(openapi_spec)
        
    except Exception as e:
        logger.error(f"Error generating OpenAPI spec: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@docs_api_bp.route('/endpoints', methods=['GET'])
def list_api_endpoints():
    """
    List all available API endpoints with descriptions.
    """
    try:
        version = request.args.get('version', CURRENT_VERSION)
        include_deprecated = request.args.get('include_deprecated', 'false').lower() == 'true'
        
        endpoints = _get_api_endpoints(version, include_deprecated)
        
        return jsonify({
            'success': True,
            'data': {
                'version': version,
                'endpoints': endpoints,
                'total_count': len(endpoints),
                'include_deprecated': include_deprecated
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing endpoints: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@docs_api_bp.route('/examples', methods=['GET'])
def get_api_examples():
    """
    Get API usage examples for different endpoints.
    """
    try:
        endpoint = request.args.get('endpoint')
        
        if endpoint:
            # Get specific endpoint example
            if endpoint in ENDPOINT_EXAMPLES:
                return jsonify({
                    'success': True,
                    'data': {
                        'endpoint': endpoint,
                        'example': ENDPOINT_EXAMPLES[endpoint]
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'No example available for endpoint: {endpoint}'
                }), 404
        else:
            # Get all examples
            return jsonify({
                'success': True,
                'data': {
                    'examples': ENDPOINT_EXAMPLES,
                    'available_endpoints': list(ENDPOINT_EXAMPLES.keys())
                }
            })
            
    except Exception as e:
        logger.error(f"Error getting examples: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@docs_api_bp.route('/testing', methods=['GET'])
def api_testing_interface():
    """
    Serve interactive API testing interface.
    """
    try:
        return render_template('api_testing.html',
                             api_info=API_DOCUMENTATION['info'],
                             endpoints=ENDPOINT_EXAMPLES,
                             api_versions=API_VERSIONS,
                             current_version=CURRENT_VERSION)
    except Exception:
        # Fallback to JSON interface description
        return jsonify({
            'success': True,
            'data': {
                'message': 'Interactive API Testing Interface',
                'usage': 'This endpoint provides an interactive interface to test API endpoints',
                'features': [
                    'Live API testing',
                    'Request/response examples',
                    'Authentication testing',
                    'Error handling demonstration',
                    'Response validation'
                ],
                'available_tests': list(ENDPOINT_EXAMPLES.keys())
            }
        })

@docs_api_bp.route('/test/<path:endpoint>', methods=['POST'])
def test_api_endpoint(endpoint: str):
    """
    Test a specific API endpoint with provided data.
    """
    try:
        test_data = request.get_json() or {}
        
        # This would make actual API calls to test endpoints
        # For now, return a mock testing response
        
        test_result = {
            'endpoint': f'/{endpoint}',
            'method': test_data.get('method', 'GET'),
            'test_data': test_data,
            'simulated_response': {
                'success': True,
                'message': 'This is a simulated test response',
                'actual_testing': 'Would require implementing actual API calls'
            },
            'validation': {
                'request_valid': True,
                'response_valid': True,
                'authentication_required': endpoint not in ['health', 'versions'],
                'estimated_response_time': '< 1s'
            }
        }
        
        return jsonify({
            'success': True,
            'data': test_result
        })
        
    except Exception as e:
        logger.error(f"Error testing endpoint {endpoint}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =====================================================================
# API SCHEMA AND VALIDATION ENDPOINTS
# =====================================================================

@docs_api_bp.route('/schema/<model_name>', methods=['GET'])
def get_data_schema(model_name: str):
    """
    Get JSON schema for data models.
    """
    try:
        schemas = _get_data_schemas()
        
        if model_name in schemas:
            return jsonify({
                'success': True,
                'data': {
                    'model': model_name,
                    'schema': schemas[model_name]
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Schema not found for model: {model_name}',
                'available_schemas': list(schemas.keys())
            }), 404
            
    except Exception as e:
        logger.error(f"Error getting schema for {model_name}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@docs_api_bp.route('/validate', methods=['POST'])
def validate_api_request():
    """
    Validate API request data against schemas.
    """
    try:
        validation_data = request.get_json() or {}
        endpoint = validation_data.get('endpoint')
        data = validation_data.get('data', {})
        
        if not endpoint:
            return jsonify({
                'success': False,
                'error': 'Endpoint is required for validation'
            }), 400
        
        # Perform validation (simplified implementation)
        validation_result = _validate_request_data(endpoint, data)
        
        return jsonify({
            'success': True,
            'data': validation_result
        })
        
    except Exception as e:
        logger.error(f"Error validating request: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =====================================================================
# API STATISTICS AND MONITORING
# =====================================================================

@docs_api_bp.route('/stats', methods=['GET'])
def get_api_statistics():
    """
    Get API usage statistics and performance metrics.
    """
    try:
        # This would integrate with actual monitoring system
        # For now, return mock statistics
        
        stats = {
            'api_version': CURRENT_VERSION,
            'total_endpoints': len(_get_all_endpoints()),
            'endpoints_by_category': {
                'authentication': 8,
                'email_processing': 3,
                'task_management': 6,
                'entity_management': 12,
                'analytics': 15,
                'real_time': 8,
                'batch_processing': 7
            },
            'deprecation_status': {
                'deprecated_endpoints': 5,
                'current_endpoints': 54,
                'beta_endpoints': 0
            },
            'usage_statistics': {
                'daily_requests': 12847,
                'avg_response_time': '145ms',
                'success_rate': '99.2%',
                'most_used_endpoints': [
                    '/api/v2/emails/process',
                    '/api/v2/tasks',
                    '/api/auth/login'
                ]
            }
        }
        
        return jsonify({
            'success': True,
            'data': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting API statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@docs_api_bp.route('/health-check', methods=['GET'])
def docs_health_check():
    """
    Health check for documentation endpoints.
    """
    try:
        health_status = {
            'status': 'healthy',
            'documentation': 'available',
            'openapi_spec': 'generated',
            'testing_interface': 'available',
            'examples': len(ENDPOINT_EXAMPLES),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(health_status)
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def _generate_openapi_paths() -> Dict:
    """Generate OpenAPI paths specification"""
    paths = {}
    
    # Add key endpoints with basic documentation
    endpoints = [
        {
            'path': '/api/auth/login',
            'method': 'post',
            'summary': 'User Login',
            'description': 'Authenticate user and receive JWT tokens',
            'tags': ['Authentication']
        },
        {
            'path': '/api/v2/emails/process',
            'method': 'post',
            'summary': 'Process Emails',
            'description': 'Process emails with entity extraction',
            'tags': ['Email Processing']
        },
        {
            'path': '/api/entities/people',
            'method': 'get',
            'summary': 'List People',
            'description': 'Get all people entities',
            'tags': ['Entity Management']
        }
    ]
    
    for endpoint in endpoints:
        if endpoint['path'] not in paths:
            paths[endpoint['path']] = {}
        
        paths[endpoint['path']][endpoint['method']] = {
            'summary': endpoint['summary'],
            'description': endpoint['description'],
            'tags': endpoint['tags'],
            'responses': {
                '200': {
                    'description': 'Successful response',
                    'content': {
                        'application/json': {
                            'schema': {'type': 'object'}
                        }
                    }
                }
            }
        }
    
    return paths

def _generate_openapi_components() -> Dict:
    """Generate OpenAPI components specification"""
    return {
        'securitySchemes': {
            'BearerAuth': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT'
            }
        },
        'schemas': _get_data_schemas()
    }

def _get_data_schemas() -> Dict:
    """Get JSON schemas for data models"""
    return {
        'User': {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'email': {'type': 'string', 'format': 'email'},
                'full_name': {'type': 'string'},
                'role': {'type': 'string', 'enum': ['user', 'admin']}
            }
        },
        'Person': {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'name': {'type': 'string'},
                'email_address': {'type': 'string'},
                'company': {'type': 'string'},
                'importance_level': {'type': 'number'}
            }
        },
        'Task': {
            'type': 'object',
            'properties': {
                'id': {'type': 'integer'},
                'description': {'type': 'string'},
                'status': {'type': 'string'},
                'priority': {'type': 'string'},
                'due_date': {'type': 'string', 'format': 'date-time'}
            }
        }
    }

def _get_api_endpoints(version: str, include_deprecated: bool) -> List[Dict]:
    """Get list of API endpoints for specified version"""
    endpoints = [
        {
            'path': '/api/auth/login',
            'method': 'POST',
            'description': 'User authentication',
            'category': 'Authentication',
            'deprecated': False
        },
        {
            'path': '/api/v2/emails/process',
            'method': 'POST',
            'description': 'Process emails with entity extraction',
            'category': 'Email Processing',
            'deprecated': False
        },
        {
            'path': '/api/entities/people',
            'method': 'GET',
            'description': 'List people entities',
            'category': 'Entity Management',
            'deprecated': False
        },
        {
            'path': '/api/v1/process-email',
            'method': 'POST',
            'description': 'Legacy email processing',
            'category': 'Email Processing',
            'deprecated': True
        }
    ]
    
    if not include_deprecated:
        endpoints = [ep for ep in endpoints if not ep['deprecated']]
    
    return endpoints

def _get_all_endpoints() -> List[str]:
    """Get list of all available endpoints"""
    return [
        '/api/auth/login', '/api/auth/register', '/api/auth/refresh',
        '/api/v2/emails/process', '/api/v2/emails/normalize',
        '/api/v2/tasks', '/api/v2/tasks/from-email',
        '/api/entities/people', '/api/entities/topics',
        '/api/analytics/insights', '/api/analytics/email/patterns',
        '/api/realtime/start', '/api/realtime/stream/emails',
        '/api/batch/emails/process', '/api/batch/tasks/create'
    ]

def _validate_request_data(endpoint: str, data: Dict) -> Dict:
    """Validate request data for endpoint"""
    validation_result = {
        'endpoint': endpoint,
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    # Add validation logic based on endpoint
    if 'auth/login' in endpoint:
        if not data.get('email'):
            validation_result['errors'].append('Email is required')
            validation_result['valid'] = False
        if not data.get('password'):
            validation_result['errors'].append('Password is required')
            validation_result['valid'] = False
    
    return validation_result

# Export the blueprint
__all__ = ['docs_api_bp'] 