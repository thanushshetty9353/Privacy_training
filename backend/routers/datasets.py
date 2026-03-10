"""
Dataset registration routes.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Dataset, Organization, AuditLog, User, SensitivityLevel
from backend.schemas import DatasetCreate, DatasetResponse
from backend.auth import get_current_user

router = APIRouter(prefix="/api/datasets", tags=["Datasets"])


@router.post("/register", response_model=DatasetResponse, status_code=201)
async def register_dataset(
    data: DatasetCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify org exists
    result = await db.execute(select(Organization).where(Organization.id == data.org_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Organization not found")

    ds = Dataset(
        name=data.name,
        org_id=data.org_id,
        description=data.description,
        num_samples=data.num_samples,
        schema_metadata=data.schema_metadata,
        sensitivity_level=SensitivityLevel(data.sensitivity_level)
        if data.sensitivity_level in [e.value for e in SensitivityLevel]
        else SensitivityLevel.HIGH,
    )
    db.add(ds)

    db.add(AuditLog(
        actor=user.username,
        actor_role=user.role.value,
        action="dataset_registered",
        resource_type="dataset",
        details={"name": data.name, "org_id": data.org_id, "sensitivity": ds.sensitivity_level.value},
    ))

    await db.commit()
    await db.refresh(ds)
    return DatasetResponse.model_validate(ds)


@router.get("/", response_model=List[DatasetResponse])
async def list_datasets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Dataset).order_by(Dataset.created_at.desc()))
    return [DatasetResponse.model_validate(d) for d in result.scalars().all()]
