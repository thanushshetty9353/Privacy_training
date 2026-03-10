"""
Organization management routes.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models import Organization, AuditLog, User, UserRole
from backend.schemas import OrgCreate, OrgResponse
from backend.auth import get_current_user

router = APIRouter(prefix="/api/organizations", tags=["Organizations"])


@router.post("/register", response_model=OrgResponse, status_code=201)
async def register_org(
    data: OrgCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = await db.execute(select(Organization).where(Organization.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Organization name already exists")

    org = Organization(
        name=data.name,
        description=data.description,
        public_key=data.public_key,
        certificate=data.certificate,
    )
    db.add(org)

    db.add(AuditLog(
        actor=user.username,
        actor_role=user.role.value,
        action="organization_registered",
        resource_type="organization",
        details={"name": data.name},
    ))

    await db.commit()
    await db.refresh(org)
    return OrgResponse.model_validate(org)


@router.get("/", response_model=List[OrgResponse])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Organization).where(Organization.is_active == True).order_by(Organization.registered_at.desc())
    )
    return [OrgResponse.model_validate(o) for o in result.scalars().all()]


@router.get("/{org_id}", response_model=OrgResponse)
async def get_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrgResponse.model_validate(org)
