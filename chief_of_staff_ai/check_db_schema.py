#!/usr/bin/env python3
"""
Check current database schema to diagnose the missing columns issue
"""

import sqlite3
import os
import sys

def check_database_schema():
    """Check the current database schema"""
    
    # Find database files
    db_files = [f for f in os.listdir('.') if f.endswith('.db')]
    print(f"Database files found: {db_files}")
    
    if not db_files:
        print("No database files found!")
        return False
    
    db_path = db_files[0]
    print(f"Checking database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Expected enhanced columns
    expected_people_columns = [
        'phone', 'relationship_type', 'importance_level', 'communication_frequency',
        'last_contact', 'total_interactions', 'linkedin_url', 'bio', 
        'professional_story', 'updated_at'
    ]
    
    expected_topics_columns = [
        'keywords', 'is_official', 'confidence_score', 'total_mentions',
        'last_mentioned', 'intelligence_summary', 'strategic_importance',
        'updated_at', 'version'
    ]
    
    expected_emails_columns = [
        'recipient_emails', 'business_category', 'sentiment', 'urgency_score',
        'strategic_importance', 'content_hash', 'blob_storage_key', 
        'primary_topic_id', 'processed_at', 'processing_version'
    ]
    
    print("\n" + "="*60)
    print("DATABASE SCHEMA ANALYSIS")
    print("="*60)
    
    # Check people table
    print("\n🔍 PEOPLE TABLE:")
    cursor.execute('PRAGMA table_info(people)')
    people_columns = [row[1] for row in cursor.fetchall()]
    print(f"Current columns: {people_columns}")
    
    missing_people = [col for col in expected_people_columns if col not in people_columns]
    if missing_people:
        print(f"❌ Missing columns: {missing_people}")
    else:
        print("✅ All expected columns present")
    
    # Check topics table
    print("\n🔍 TOPICS TABLE:")
    cursor.execute('PRAGMA table_info(topics)')
    topics_columns = [row[1] for row in cursor.fetchall()]
    print(f"Current columns: {topics_columns}")
    
    missing_topics = [col for col in expected_topics_columns if col not in topics_columns]
    if missing_topics:
        print(f"❌ Missing columns: {missing_topics}")
    else:
        print("✅ All expected columns present")
    
    # Check emails table
    print("\n🔍 EMAILS TABLE:")
    cursor.execute('PRAGMA table_info(emails)')
    emails_columns = [row[1] for row in cursor.fetchall()]
    print(f"Current columns: {emails_columns}")
    
    missing_emails = [col for col in expected_emails_columns if col not in emails_columns]
    if missing_emails:
        print(f"❌ Missing columns: {missing_emails}")
    else:
        print("✅ All expected columns present")
    
    # Summary
    total_missing = len(missing_people) + len(missing_topics) + len(missing_emails)
    print(f"\n📊 SUMMARY:")
    print(f"Total missing columns: {total_missing}")
    
    if total_missing > 0:
        print("\n🚨 DATABASE MIGRATION REQUIRED!")
        print("The enhanced columns were not successfully added to the database.")
        print("Need to run the migration script to fix schema mismatch.")
    else:
        print("\n✅ DATABASE SCHEMA IS COMPLETE!")
        print("All enhanced columns are present.")
    
    conn.close()
    return total_missing == 0

if __name__ == "__main__":
    success = check_database_schema()
    if not success:
        sys.exit(1) 