from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import logging
from api.common.deps import get_job_runner_dep
from api.common.job_runner import JobRunner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

@router.get('/jobs/{run_id}/status')
async def get_job_status(
    run_id: int,
    job_runner: JobRunner = Depends(get_job_runner_dep)
) -> Dict[str, Any]:
    """Get status of a job run."""
    try:
        return job_runner.get_run_status(run_id=run_id)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Job run {run_id} not found"
        )

@router.post('/jobs/{run_id}/cancel')
async def cancel_job(
    run_id: int,
    job_runner: JobRunner = Depends(get_job_runner_dep)
) -> Dict[str, bool]:
    """Cancel a running job."""
    try:
        job_runner.cancel_run(run_id=run_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Job run {run_id} not found"
        )

def register_routes(app):
    """Register job routes with the FastAPI app."""
    app.include_router(router)
    logger.info("Job routes registered") 