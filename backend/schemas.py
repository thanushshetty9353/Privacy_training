"""
Pydantic schemas for request / response validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None
    role: str = "researcher"
    org_id: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    org_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ── Organization ──────────────────────────────────────────────────────

class OrgCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    public_key: Optional[str] = None
    certificate: Optional[str] = None


class OrgResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    public_key: Optional[str]
    is_active: bool
    registered_at: datetime

    class Config:
        from_attributes = True


# ── Dataset ───────────────────────────────────────────────────────────

class DatasetCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    org_id: str
    description: Optional[str] = None
    num_samples: Optional[int] = None
    schema_metadata: Optional[dict] = None
    sensitivity_level: str = "high"


class DatasetResponse(BaseModel):
    id: str
    name: str
    org_id: str
    description: Optional[str]
    num_samples: Optional[int]
    schema_metadata: Optional[dict]
    sensitivity_level: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Training Job ──────────────────────────────────────────────────────

class TrainingJobCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    model_type: str = "cnn_cifar10"
    privacy_budget: float = Field(10.0, gt=0)
    noise_multiplier: float = Field(1.1, gt=0)
    max_grad_norm: float = Field(1.0, gt=0)
    training_rounds: int = Field(5, ge=1, le=100)
    min_clients: int = Field(2, ge=1)
    fraction_fit: float = Field(1.0, gt=0, le=1.0)


class TrainingJobResponse(BaseModel):
    id: str
    name: str
    model_type: str
    privacy_budget: float
    noise_multiplier: float
    max_grad_norm: float
    training_rounds: int
    min_clients: int
    fraction_fit: float
    status: str
    current_round: int
    final_accuracy: Optional[float]
    final_loss: Optional[float]
    epsilon_spent: Optional[float]
    model_path: Optional[str]
    created_by: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class TrainingJobUpdate(BaseModel):
    status: Optional[str] = None
    current_round: Optional[int] = None
    final_accuracy: Optional[float] = None
    final_loss: Optional[float] = None
    epsilon_spent: Optional[float] = None


# ── Node Participation ────────────────────────────────────────────────

class NodeParticipationCreate(BaseModel):
    job_id: str
    org_id: str
    node_name: Optional[str] = None


class NodeParticipationResponse(BaseModel):
    id: str
    job_id: str
    org_id: str
    node_name: Optional[str]
    status: str
    last_round_completed: int
    local_samples: Optional[int]
    joined_at: datetime

    class Config:
        from_attributes = True


# ── Training Metrics ──────────────────────────────────────────────────

class TrainingMetricsResponse(BaseModel):
    id: str
    job_id: str
    round_number: int
    train_loss: Optional[float]
    eval_loss: Optional[float]
    eval_accuracy: Optional[float]
    epsilon: Optional[float]
    num_clients: Optional[int]
    round_duration_sec: Optional[float]
    timestamp: datetime

    class Config:
        from_attributes = True


# ── Audit Log ─────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: str
    actor: str
    actor_role: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[dict]
    ip_address: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


# ── Dashboard Stats ───────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_organizations: int
    total_datasets: int
    total_jobs: int
    active_jobs: int
    completed_jobs: int
    total_models: int
    total_users: int
