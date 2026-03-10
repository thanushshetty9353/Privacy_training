"""
SQLAlchemy ORM models matching the SRS database design.
Tables: User, Organization, Dataset, TrainingJob, NodeParticipation, AuditLog, TrainingMetrics
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime,
    ForeignKey, Enum, Boolean, JSON
)
from sqlalchemy.orm import relationship

from backend.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _uuid():
    return str(uuid.uuid4())


# ── Enums ────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    RESEARCHER = "researcher"
    ORG_NODE = "org_node"
    AUDITOR = "auditor"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SensitivityLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NodeStatus(str, enum.Enum):
    ACTIVE = "active"
    TRAINING = "training"
    COMPLETED = "completed"
    DISCONNECTED = "disconnected"
    FAILED = "failed"


# ── Models ───────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.RESEARCHER, nullable=False)
    is_active = Column(Boolean, default=True)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    organization = relationship("Organization", back_populates="users")
    training_jobs = relationship("TrainingJob", back_populates="created_by_user")


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    public_key = Column(Text, nullable=True)
    certificate = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    registered_at = Column(DateTime, default=_utcnow)

    users = relationship("User", back_populates="organization")
    datasets = relationship("Dataset", back_populates="organization")
    node_participations = relationship("NodeParticipation", back_populates="organization")


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    schema_metadata = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    num_samples = Column(Integer, nullable=True)
    sensitivity_level = Column(
        Enum(SensitivityLevel), default=SensitivityLevel.HIGH, nullable=False
    )
    created_at = Column(DateTime, default=_utcnow)

    organization = relationship("Organization", back_populates="datasets")


class TrainingJob(Base):
    __tablename__ = "training_jobs"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    model_type = Column(String(100), nullable=False, default="cnn_cifar10")
    privacy_budget = Column(Float, nullable=False, default=10.0)
    noise_multiplier = Column(Float, nullable=False, default=1.1)
    max_grad_norm = Column(Float, nullable=False, default=1.0)
    training_rounds = Column(Integer, nullable=False, default=5)
    min_clients = Column(Integer, nullable=False, default=2)
    fraction_fit = Column(Float, nullable=False, default=1.0)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    current_round = Column(Integer, default=0)
    final_accuracy = Column(Float, nullable=True)
    final_loss = Column(Float, nullable=True)
    epsilon_spent = Column(Float, nullable=True)
    model_path = Column(String(500), nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    created_by_user = relationship("User", back_populates="training_jobs")
    node_participations = relationship("NodeParticipation", back_populates="training_job")
    metrics = relationship("TrainingMetrics", back_populates="training_job", order_by="TrainingMetrics.round_number")


class NodeParticipation(Base):
    __tablename__ = "node_participations"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("training_jobs.id"), nullable=False)
    org_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    node_name = Column(String(255), nullable=True)
    status = Column(Enum(NodeStatus), default=NodeStatus.ACTIVE, nullable=False)
    last_round_completed = Column(Integer, default=0)
    local_samples = Column(Integer, nullable=True)
    joined_at = Column(DateTime, default=_utcnow)

    training_job = relationship("TrainingJob", back_populates="node_participations")
    organization = relationship("Organization", back_populates="node_participations")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=_uuid)
    actor = Column(String(255), nullable=False)
    actor_role = Column(String(50), nullable=True)
    action = Column(String(255), nullable=False)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    timestamp = Column(DateTime, default=_utcnow, index=True)


class TrainingMetrics(Base):
    __tablename__ = "training_metrics"

    id = Column(String, primary_key=True, default=_uuid)
    job_id = Column(String, ForeignKey("training_jobs.id"), nullable=False)
    round_number = Column(Integer, nullable=False)
    train_loss = Column(Float, nullable=True)
    eval_loss = Column(Float, nullable=True)
    eval_accuracy = Column(Float, nullable=True)
    epsilon = Column(Float, nullable=True)
    num_clients = Column(Integer, nullable=True)
    round_duration_sec = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=_utcnow)

    training_job = relationship("TrainingJob", back_populates="metrics")
