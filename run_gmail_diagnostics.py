#!/usr/bin/env python3
"""
Gmail Diagnostics Runner
========================

This script runs the Gmail diagnostic endpoints to troubleshoot sent emails issues.
Make sure the Flask app is running before executing this script.
"""

import requests
import json
import sys
import os
from datetime import datetime

def run_diagnostics(base_url="http://localhost:8080"):
    """Run Gmail diagnostics via HTTP endpoints"""
    
    print("🧠 Gmail Diagnostics Runner")
    print("=" * 50)
    print(f"Testing endpoints at: {base_url}")
    print()
    
    # Test 1: Gmail connection test
    print("1. Testing Gmail connection...")
    try:
        response = requests.get(f"{base_url}/api/gmail/test-connection")
        if response.status_code == 200:
            data = response.json()
            print("✅ Connection test successful")
            print(f"   User: {data.get('user_email')}")
            print(f"   Messages accessible: {data.get('total_messages_accessible')}")
            print(f"   Authentication: {data.get('authentication_status')}")
        else:
            print(f"❌ Connection test failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Connection test error: {str(e)}")
    
    print()
    
    # Test 2: Gmail diagnostics
    print("2. Running Gmail diagnostics...")
    try:
        response = requests.get(f"{base_url}/api/gmail/diagnostics")
        if response.status_code == 200:
            data = response.json()
            diagnostics = data.get('diagnostics', {})
            print("✅ Diagnostics completed")
            print(f"   User: {data.get('user_email')}")
            
            # Show test results
            tests = diagnostics.get('tests_performed', [])
            for test in tests:
                status = "✅" if test.get('status') == 'pass' else "❌" if test.get('status') == 'fail' else "ℹ️"
                print(f"   {status} {test.get('test')}: {test.get('result')}")
            
            # Show recommendations
            recommendations = diagnostics.get('recommendations', [])
            if recommendations:
                print("\n   💡 Recommendations:")
                for rec in recommendations:
                    print(f"      - {rec}")
        else:
            print(f"❌ Diagnostics failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Diagnostics error: {str(e)}")
    
    print()
    
    # Test 3: Gmail query test
    print("3. Testing Gmail queries...")
    try:
        response = requests.post(f"{base_url}/api/gmail/test-sent-query", 
                               json={'days_back': 90})
        if response.status_code == 200:
            data = response.json()
            print("✅ Query test completed")
            print(f"   User: {data.get('user_email')}")
            
            # Show query results
            results = data.get('query_results', [])
            for result in results:
                status = "✅" if result.get('success') and result.get('count', 0) > 0 else "❌"
                print(f"   {status} {result.get('description')}: {result.get('count')} emails")
                if not result.get('success'):
                    print(f"      Error: {result.get('error')}")
        else:
            print(f"❌ Query test failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Query test error: {str(e)}")
    
    print()
    print("=" * 50)
    print("Diagnostics completed!")

def main():
    """Main function"""
    base_url = os.getenv('API_BASE_URL', 'http://localhost:8080')
    
    print("Make sure the Flask app is running before executing this script.")
    print("You can start it with: python main.py")
    print()
    
    try:
        run_diagnostics(base_url)
    except KeyboardInterrupt:
        print("\n\nScript interrupted by user")
    except Exception as e:
        print(f"\n❌ Script failed: {str(e)}")
        print("Make sure the Flask app is running and accessible")

if __name__ == "__main__":
    main() 