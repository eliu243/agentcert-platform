"""
Results API routes
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..models.schemas import ResultsResponse
from ...grader.scorer import ResultsService

router = APIRouter()
results_service = ResultsService()


@router.get("/results/{agent_id}", response_model=ResultsResponse)
async def get_results(agent_id: str):
    """
    Get security test results for an agent.
    
    Returns:
    - Security score (0-100)
    - Test results
    - Violations found
    - A2A logs
    - Performance metrics
    """
    try:
        results = await results_service.get_results(agent_id)
        
        if not results:
            raise HTTPException(status_code=404, detail="No results found for this agent")
        
        return ResultsResponse(**results)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve results: {str(e)}")


@router.get("/results/{agent_id}/summary")
async def get_results_summary(agent_id: str):
    """Get summary of test results (lightweight)"""
    try:
        summary = await results_service.get_summary(agent_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Results not found: {str(e)}")

