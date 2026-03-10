"""
Model access routes.
"""

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import TrainingJob, JobStatus, User
from backend.schemas import TrainingJobResponse
from backend.auth import get_current_user
from backend.config import settings

router = APIRouter(prefix="/api/models", tags=["Models"])


@router.get("/latest", response_model=Optional[TrainingJobResponse])
async def get_latest_model(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TrainingJob)
        .where(TrainingJob.status == JobStatus.COMPLETED)
        .order_by(TrainingJob.completed_at.desc())
        .limit(1)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="No completed models found")
    return TrainingJobResponse.model_validate(job)


@router.get("/{job_id}/download")
async def download_model(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(TrainingJob).where(TrainingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.model_path or not os.path.exists(job.model_path):
        raise HTTPException(status_code=404, detail="Model file not found")
    return FileResponse(
        job.model_path,
        media_type="application/octet-stream",
        filename=f"model_{job_id}.pt",
    )
