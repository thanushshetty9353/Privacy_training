"""
Dashboard stats route.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import (
    User, Organization, Dataset, TrainingJob, JobStatus
)
from backend.schemas import DashboardStats
from backend.auth import get_current_user

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    orgs = (await db.execute(select(func.count(Organization.id)))).scalar() or 0
    datasets = (await db.execute(select(func.count(Dataset.id)))).scalar() or 0
    total_jobs = (await db.execute(select(func.count(TrainingJob.id)))).scalar() or 0
    active_jobs = (await db.execute(
        select(func.count(TrainingJob.id)).where(TrainingJob.status == JobStatus.RUNNING)
    )).scalar() or 0
    completed_jobs = (await db.execute(
        select(func.count(TrainingJob.id)).where(TrainingJob.status == JobStatus.COMPLETED)
    )).scalar() or 0
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0

    return DashboardStats(
        total_organizations=orgs,
        total_datasets=datasets,
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        completed_jobs=completed_jobs,
        total_models=completed_jobs,
        total_users=total_users,
    )
