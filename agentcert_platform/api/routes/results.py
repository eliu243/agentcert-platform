"""
Results API routes
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ..models.schemas import ResultsResponse
from ...grader.scorer import ResultsService
from ..auth.dependencies import get_current_user

router = APIRouter()
results_service = ResultsService()


@router.get("/results/{agent_id}", response_model=ResultsResponse)
async def get_results(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
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
        # Verify agent belongs to user
        from ..utils import get_deployment_service
        deployment_service = get_deployment_service()
        await deployment_service.get_deployment_status(agent_id, user_id=user["user_id"])
        
        results = await results_service.get_results(agent_id)
        
        if not results:
            raise HTTPException(status_code=404, detail="No results found for this agent")
        
        return ResultsResponse(**results)
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve results: {str(e)}")


@router.get("/results/{agent_id}/summary")
async def get_results_summary(
    agent_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get summary of test results (lightweight)"""
    try:
        # Verify agent belongs to user
        from ..utils import get_deployment_service
        deployment_service = get_deployment_service()
        await deployment_service.get_deployment_status(agent_id, user_id=user["user_id"])
        
        summary = await results_service.get_summary(agent_id)
        return summary
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Results not found: {str(e)}")

