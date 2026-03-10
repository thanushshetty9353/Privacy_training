"""
Training job routes: create, list, status, start, metrics.
"""

import os
import json
import subprocess
import sys
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import (
    TrainingJob, JobStatus, AuditLog, User, UserRole,
    TrainingMetrics, NodeParticipation
)
from backend.schemas import (
    TrainingJobCreate, TrainingJobResponse,
    TrainingMetricsResponse, NodeParticipationResponse
)
from backend.auth import get_current_user
from backend.config import settings

router = APIRouter(prefix="/api/jobs", tags=["Training Jobs"])


def _run_fl_training(job_id: str, job_config: dict):
    """Background task: launch FL simulation as a subprocess."""
    try:
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "fl_core", "run_simulation.py"
        )
        cmd = [
            sys.executable, script_path,
            "--job-id", job_id,
            "--rounds", str(job_config["training_rounds"]),
            "--clients", str(job_config["min_clients"]),
            "--noise-multiplier", str(job_config["noise_multiplier"]),
            "--max-grad-norm", str(job_config["max_grad_norm"]),
            "--db-url", settings.DATABASE_URL,
        ]
        subprocess.Popen(cmd, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except Exception as e:
        print(f"[FL Training Error] {e}")


@router.post("/create", response_model=TrainingJobResponse, status_code=201)
async def create_training_job(
    data: TrainingJobCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    job = TrainingJob(
        name=data.name,
        model_type=data.model_type,
        privacy_budget=data.privacy_budget,
        noise_multiplier=data.noise_multiplier,
        max_grad_norm=data.max_grad_norm,
        training_rounds=data.training_rounds,
        min_clients=data.min_clients,
        fraction_fit=data.fraction_fit,
        created_by=user.id,
    )
    db.add(job)

    db.add(AuditLog(
        actor=user.username,
        actor_role=user.role.value,
        action="training_job_created",
        resource_type="training_job",
        details={"name": data.name, "model_type": data.model_type, "rounds": data.training_rounds},
    ))

    await db.commit()
    await db.refresh(job)
    return TrainingJobResponse.model_validate(job)


@router.post("/{job_id}/start", response_model=TrainingJobResponse)
async def start_training_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(TrainingJob).where(TrainingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != JobStatus.PENDING:
        raise HTTPException(status_code=400, detail=f"Job is already {job.status.value}")

    job.status = JobStatus.RUNNING
    job.started_at = datetime.now(timezone.utc)

    db.add(AuditLog(
        actor=user.username,
        actor_role=user.role.value,
        action="training_job_started",
        resource_type="training_job",
        resource_id=job_id,
    ))

    await db.commit()
    await db.refresh(job)

    # Launch FL in background
    background_tasks.add_task(
        _run_fl_training, job_id,
        {
            "training_rounds": job.training_rounds,
            "min_clients": job.min_clients,
            "noise_multiplier": job.noise_multiplier,
            "max_grad_norm": job.max_grad_norm,
        }
    )

    return TrainingJobResponse.model_validate(job)


@router.get("/", response_model=List[TrainingJobResponse])
async def list_jobs(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = select(TrainingJob).order_by(TrainingJob.created_at.desc())
    if status:
        query = query.where(TrainingJob.status == JobStatus(status))
    result = await db.execute(query)
    return [TrainingJobResponse.model_validate(j) for j in result.scalars().all()]


@router.get("/{job_id}", response_model=TrainingJobResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(TrainingJob).where(TrainingJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return TrainingJobResponse.model_validate(job)


@router.get("/{job_id}/metrics", response_model=List[TrainingMetricsResponse])
async def get_job_metrics(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TrainingMetrics)
        .where(TrainingMetrics.job_id == job_id)
        .order_by(TrainingMetrics.round_number)
    )
    return [TrainingMetricsResponse.model_validate(m) for m in result.scalars().all()]


@router.get("/{job_id}/nodes", response_model=List[NodeParticipationResponse])
async def get_job_nodes(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(NodeParticipation).where(NodeParticipation.job_id == job_id)
    )
    return [NodeParticipationResponse.model_validate(n) for n in result.scalars().all()]
