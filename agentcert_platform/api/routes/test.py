"""
Testing API routes
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..models.schemas import TestRequest, TestResponse
from ...stress_test.stress_test_nest import StressTestService

router = APIRouter()
stress_test_service = StressTestService()


@router.post("/test/{agent_id}", response_model=TestResponse)
async def run_stress_test(agent_id: str, background_tasks: BackgroundTasks):
    """
    Run stress test on a deployed agent.
    
    This endpoint:
    1. Sends malicious prompts to the agent
    2. Collects responses
    3. Retrieves A2A logs from agent
    4. Triggers LLM grader analysis (in background)
    """
    try:
        # Start stress test
        test_result = await stress_test_service.run_stress_test(agent_id)
        
        # Trigger LLM grading in background
        background_tasks.add_task(
            stress_test_service.analyze_with_grader,
            agent_id,
            test_result["test_id"]
        )
        
        return TestResponse(
            agent_id=agent_id,
            status="running",
            test_id=test_result["test_id"],
            message="Stress test started. Results will be available shortly."
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stress test failed: {str(e)}")


@router.get("/test/{agent_id}/status")
async def get_test_status(agent_id: str):
    """Get status of running stress test"""
    try:
        status = await stress_test_service.get_test_status(agent_id)
        return status
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Test not found: {str(e)}")

