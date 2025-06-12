#!/usr/bin/env python3
"""
Create missing entity_relationships table
"""

import sqlite3
import logging

logger = logging.getLogger(__name__)

def create_entity_relationships_table():
    """Create the missing entity_relationships table"""
    
    try:
        # Connect to database
        conn = sqlite3.connect('chief_of_staff.db')
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entity_relationships'")
        if cursor.fetchone():
            print("✅ entity_relationships table already exists")
            return True
        
        # Create the table
        create_table_sql = """
        CREATE TABLE entity_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            entity_type_a VARCHAR(50) NOT NULL,
            entity_id_a INTEGER NOT NULL,
            entity_type_b VARCHAR(50) NOT NULL,
            entity_id_b INTEGER NOT NULL,
            relationship_type VARCHAR(100),
            strength FLOAT DEFAULT 0.5,
            frequency INTEGER DEFAULT 1,
            context_summary TEXT,
            last_interaction DATETIME,
            total_interactions INTEGER DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        """
        
        cursor.execute(create_table_sql)
        
        # Create indexes
        indexes = [
            "CREATE INDEX idx_entity_rel_user ON entity_relationships(user_id);",
            "CREATE INDEX idx_entity_rel_a ON entity_relationships(entity_type_a, entity_id_a);",
            "CREATE INDEX idx_entity_rel_b ON entity_relationships(entity_type_b, entity_id_b);",
            "CREATE INDEX idx_entity_rel_strength ON entity_relationships(user_id, strength);"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        conn.commit()
        print("✅ Created entity_relationships table with indexes")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create entity_relationships table: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_entity_relationships_table() 