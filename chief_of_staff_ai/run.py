#!/usr/bin/env python3
"""
AI Chief of Staff - Gmail E2E Flow Entry Point

This script demonstrates the complete Gmail processing pipeline:
1. Gmail authentication
2. Message fetching
3. Email normalization  
4. Task extraction
5. Basic reporting

Usage:
    python run.py --email user@example.com
    python run.py --email user@example.com --max-emails 10
    python run.py --test-auth user@example.com
"""

import sys
import argparse
import logging
from datetime import datetime
from typing import Dict, List

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from config.settings import settings
    from auth.gmail_auth import gmail_auth
    from ingest.gmail_fetcher import gmail_fetcher
    from processors.email_normalizer import email_normalizer
    from processors.task_extractor import task_extractor
except ImportError as e:
    logger.error(f"Failed to import modules: {e}")
    logger.error("Make sure you're running from the chief_of_staff_ai directory")
    sys.exit(1)

def test_authentication(user_email: str) -> bool:
    """Test Gmail authentication for a user"""
    print(f"\n=== Testing Gmail Authentication for {user_email} ===")
    
    try:
        # Check if user is authenticated
        is_authenticated = gmail_auth.is_authenticated(user_email)
        print(f"Authentication status: {'✓ Authenticated' if is_authenticated else '✗ Not authenticated'}")
        
        if is_authenticated:
            # Test Gmail access
            gmail_access = gmail_auth.test_gmail_access(user_email)
            print(f"Gmail access: {'✓ Working' if gmail_access else '✗ Failed'}")
            
            # Get detailed status
            status = gmail_auth.get_authentication_status(user_email)
            print(f"Detailed status: {status}")
            
            return gmail_access
        else:
            print("\nTo authenticate:")
            print("1. Start the Flask app: python main.py")
            print("2. Go to http://localhost:5000")
            print("3. Complete the OAuth flow")
            print("4. Run this script again")
            
        return False
        
    except Exception as e:
        logger.error(f"Authentication test failed: {str(e)}")
        return False

def run_gmail_e2e_flow(user_email: str, max_emails: int = 10, days_back: int = 7) -> Dict:
    """Run the complete Gmail E2E flow"""
    print(f"\n=== Gmail E2E Flow for {user_email} ===")
    print(f"Fetching up to {max_emails} emails from the last {days_back} days")
    
    results = {
        'user_email': user_email,
        'started_at': datetime.now().isoformat(),
        'steps_completed': [],
        'errors': [],
        'summary': {}
    }
    
    try:
        # Step 1: Test authentication
        print("\n1. Testing authentication...")
        if not test_authentication(user_email):
            results['errors'].append('Authentication failed')
            return results
        results['steps_completed'].append('authentication')
        
        # Step 2: Fetch emails
        print("\n2. Fetching Gmail messages...")
        fetch_result = gmail_fetcher.fetch_recent_messages(
            user_email=user_email,
            max_results=max_emails,
            days_back=days_back
        )
        
        if not fetch_result.get('success'):
            error_msg = f"Failed to fetch emails: {fetch_result.get('error')}"
            print(f"✗ {error_msg}")
            results['errors'].append(error_msg)
            return results
            
        raw_messages = fetch_result.get('messages', [])
        print(f"✓ Fetched {len(raw_messages)} messages")
        results['steps_completed'].append('fetch')
        results['summary']['raw_messages_count'] = len(raw_messages)
        
        if not raw_messages:
            print("No messages to process")
            return results
        
        # Step 3: Normalize emails
        print("\n3. Normalizing email messages...")
        normalized_messages = email_normalizer.normalize_batch(raw_messages)
        
        successful_normalizations = [msg for msg in normalized_messages if not msg.get('error')]
        failed_normalizations = [msg for msg in normalized_messages if msg.get('error')]
        
        print(f"✓ Normalized {len(successful_normalizations)} messages")
        if failed_normalizations:
            print(f"✗ Failed to normalize {len(failed_normalizations)} messages")
            
        results['steps_completed'].append('normalization')
        results['summary']['normalized_messages_count'] = len(successful_normalizations)
        results['summary']['normalization_errors'] = len(failed_normalizations)
        
        # Step 4: Extract tasks
        print("\n4. Extracting tasks and action items...")
        task_results = task_extractor.extract_tasks_from_batch(successful_normalizations)
        
        # Analyze task extraction results
        total_tasks = 0
        emails_with_tasks = 0
        skipped_emails = 0
        extraction_errors = 0
        
        for result in task_results:
            if result.get('error'):
                extraction_errors += 1
            elif result.get('skipped'):
                skipped_emails += 1
            else:
                tasks = result.get('tasks', [])
                total_tasks += len(tasks)
                if tasks:
                    emails_with_tasks += 1
        
        print(f"✓ Extracted {total_tasks} tasks from {emails_with_tasks} emails")
        print(f"  - Skipped {skipped_emails} emails (auto-replies, newsletters)")
        if extraction_errors:
            print(f"  - {extraction_errors} extraction errors")
            
        results['steps_completed'].append('task_extraction')
        results['summary']['total_tasks'] = total_tasks
        results['summary']['emails_with_tasks'] = emails_with_tasks
        results['summary']['skipped_emails'] = skipped_emails
        results['summary']['extraction_errors'] = extraction_errors
        
        # Step 5: Generate report
        print("\n5. Generating summary report...")
        generate_summary_report(results, normalized_messages, task_results)
        results['steps_completed'].append('reporting')
        
        results['completed_at'] = datetime.now().isoformat()
        print("\n✓ Gmail E2E flow completed successfully!")
        
        return results
        
    except Exception as e:
        error_msg = f"Unexpected error in E2E flow: {str(e)}"
        logger.error(error_msg)
        results['errors'].append(error_msg)
        return results

def generate_summary_report(results: Dict, normalized_messages: List[Dict], task_results: List[Dict]):
    """Generate a summary report of the processing results"""
    print("\n" + "="*60)
    print("PROCESSING SUMMARY REPORT")
    print("="*60)
    
    # Basic stats
    print(f"User: {results['user_email']}")
    print(f"Processed: {results['summary'].get('normalized_messages_count', 0)} emails")
    print(f"Extracted: {results['summary'].get('total_tasks', 0)} tasks")
    
    # Message type breakdown
    print("\nMessage Type Breakdown:")
    type_counts = {}
    for msg in normalized_messages:
        msg_type = msg.get('message_type', 'unknown')
        type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
    
    for msg_type, count in sorted(type_counts.items()):
        print(f"  {msg_type}: {count}")
    
    # Task breakdown
    print("\nTask Breakdown:")
    priority_counts = {'high': 0, 'medium': 0, 'low': 0}
    category_counts = {}
    
    for task_result in task_results:
        for task in task_result.get('tasks', []):
            priority = task.get('priority', 'medium')
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            category = task.get('category', 'other')
            category_counts[category] = category_counts.get(category, 0) + 1
    
    print("By Priority:")
    for priority, count in priority_counts.items():
        print(f"  {priority}: {count}")
    
    print("By Category:")
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count}")
    
    # High priority tasks
    high_priority_tasks = []
    urgent_tasks = []
    
    for task_result in task_results:
        for task in task_result.get('tasks', []):
            if task.get('priority') == 'high':
                high_priority_tasks.append(task)
            if task.get('due_date'):
                urgent_tasks.append(task)
    
    if high_priority_tasks:
        print(f"\nHigh Priority Tasks ({len(high_priority_tasks)}):")
        for task in high_priority_tasks[:5]:  # Show first 5
            print(f"  • {task.get('description', 'No description')}")
            if task.get('due_date'):
                print(f"    Due: {task['due_date']}")
    
    if urgent_tasks:
        print(f"\nTasks with Deadlines ({len(urgent_tasks)}):")
        for task in sorted(urgent_tasks, key=lambda x: x.get('due_date', ''))[:5]:
            print(f"  • {task.get('description', 'No description')}")
            print(f"    Due: {task.get('due_date')}")
    
    print("\n" + "="*60)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='AI Chief of Staff - Gmail E2E Flow')
    parser.add_argument('--email', '-e', required=True, help='User email address')
    parser.add_argument('--max-emails', '-m', type=int, default=10, help='Maximum emails to process (default: 10)')
    parser.add_argument('--days-back', '-d', type=int, default=7, help='Days back to fetch emails (default: 7)')
    parser.add_argument('--test-auth', action='store_true', help='Only test authentication')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate configuration
    try:
        settings.validate_required_settings()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)
    
    # Create necessary directories
    settings.create_directories()
    
    print("AI Chief of Staff - Gmail E2E Flow")
    print("=" * 40)
    
    if args.test_auth:
        # Only test authentication
        success = test_authentication(args.email)
        sys.exit(0 if success else 1)
    else:
        # Run full E2E flow
        results = run_gmail_e2e_flow(
            user_email=args.email,
            max_emails=args.max_emails,
            days_back=args.days_back
        )
        
        if results.get('errors'):
            print(f"\nCompleted with {len(results['errors'])} errors:")
            for error in results['errors']:
                print(f"  - {error}")
            sys.exit(1)
        else:
            print(f"\nCompleted successfully! Processed {results['summary'].get('normalized_messages_count', 0)} emails and extracted {results['summary'].get('total_tasks', 0)} tasks.")
            sys.exit(0)

if __name__ == '__main__':
    main()
