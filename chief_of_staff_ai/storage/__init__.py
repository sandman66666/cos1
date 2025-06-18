"""
Strategic Intelligence Platform - Storage Layer
=============================================
Multi-database architecture with PostgreSQL, ChromaDB, Neo4j, Redis, and MinIO
"""

from .storage_manager import storage_manager

__all__ = ['storage_manager'] 