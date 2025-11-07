#!/usr/bin/env python3
"""
Test the AgentCert Platform API

This script demonstrates how to use the backend API to:
1. Deploy an agent
2. Run stress tests
3. Get results
"""

import httpx
import json
import time
from typing import Dict, Any

API_BASE_URL = "http://localhost:8000"


def deploy_agent(github_repo: str, api_keys: Dict[str, str] = None) -> Dict[str, Any]:
    """Deploy an agent via the API"""
    print(f"🚀 Deploying agent from {github_repo}...")
    
    payload = {
        "github_repo": github_repo,
        "entry_point": "agent.py"
    }
    
    if api_keys:
        payload["api_keys"] = api_keys
    
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{API_BASE_URL}/api/deploy",
            json=payload
        )
        response.raise_for_status()
        result = response.json()
        print(f"✅ Agent deployed: {result['agent_id']}")
        return result


def run_stress_test(agent_id: str) -> Dict[str, Any]:
    """Run stress test via the API"""
    print(f"🧪 Running stress test for agent {agent_id}...")
    
    with httpx.Client(timeout=300.0) as client:
        response = client.post(
            f"{API_BASE_URL}/api/test/{agent_id}"
        )
        response.raise_for_status()
        result = response.json()
        print(f"✅ Stress test started: {result['test_id']}")
        print(f"   Status: {result['status']}")
        return result


def get_test_status(agent_id: str) -> Dict[str, Any]:
    """Check stress test status"""
    with httpx.Client(timeout=10.0) as client:
        response = client.get(
            f"{API_BASE_URL}/api/test/{agent_id}/status"
        )
        response.raise_for_status()
        return response.json()


def get_results(agent_id: str) -> Dict[str, Any]:
    """Get test results via the API"""
    print(f"📊 Getting results for agent {agent_id}...")
    
    with httpx.Client(timeout=10.0) as client:
        response = client.get(
            f"{API_BASE_URL}/api/results/{agent_id}"
        )
        response.raise_for_status()
        result = response.json()
        print(f"✅ Security Score: {result['security_score']}/100")
        print(f"   Passed: {result['passed_tests']}/{result['total_tests']}")
        return result


def wait_for_test_completion(agent_id: str, max_wait: int = 300) -> Dict[str, Any]:
    """Wait for stress test to complete"""
    print("⏳ Waiting for test to complete...")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        status = get_test_status(agent_id)
        
        if status.get("status") == "completed":
            print("✅ Test completed!")
            return status
        
        print(f"   Status: {status.get('status', 'unknown')}...")
        time.sleep(5)
    
    raise TimeoutError("Test did not complete in time")


def main():
    """Main demo flow"""
    print("=" * 70)
    print("AgentCert Platform API Demo")
    print("=" * 70)
    print()
    
    # Check if API is running
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{API_BASE_URL}/health")
            if response.status_code != 200:
                print(f"❌ API health check failed")
                return
    except Exception as e:
        print(f"❌ Cannot connect to API at {API_BASE_URL}")
        print(f"   Make sure the API server is running:")
        print(f"   cd agentcert-platform")
        print(f"   uvicorn platform.api.main:app --reload --port 8000")
        return
    
    print("✅ API server is running")
    print()
    
    # Example: Deploy agent
    # For local testing, you might use a local path or already running agent
    github_repo = input("Enter GitHub repo URL (or press Enter to skip deployment): ").strip()
    
    if github_repo:
        # Deploy agent
        deploy_result = deploy_agent(
            github_repo=github_repo,
            api_keys={"OPENAI_API_KEY": "your-key-here"} if input("Add API keys? (y/N): ").lower() == 'y' else None
        )
        agent_id = deploy_result["agent_id"]
    else:
        # Use existing agent
        agent_id = input("Enter existing agent_id: ").strip()
        if not agent_id:
            print("❌ Need either GitHub repo or agent_id")
            return
    
    print()
    
    # Run stress test
    test_result = run_stress_test(agent_id)
    print()
    
    # Wait for completion
    try:
        wait_for_test_completion(agent_id)
    except TimeoutError:
        print("⚠️  Test is taking longer than expected, checking results anyway...")
    
    print()
    
    # Get results
    results = get_results(agent_id)
    
    print()
    print("=" * 70)
    print("📋 Full Results:")
    print("=" * 70)
    print(json.dumps(results, indent=2))
    
    # Show violations
    if results.get("violations"):
        print()
        print("⚠️  Violations Found:")
        for violation in results["violations"]:
            print(f"  - {violation}")


if __name__ == "__main__":
    main()

