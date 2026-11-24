"""
SQLAlchemy ORM models for PostgreSQL.
These define the actual database tables you'll see in DBeaver.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from src.database.connection import Base


class IncidentStatus(PyEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    ROOT_CAUSE_IDENTIFIED = "root_cause_identified"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentSeverity(PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentCategory(PyEnum):
    DATABASE = "database"
    BACKEND = "backend"
    INFRASTRUCTURE = "infrastructure"
    NETWORK = "network"
    UNKNOWN = "unknown"


class ApprovalStatus(PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Incident(Base):
    """
    Main incidents table.
    You can browse this in DBeaver after running migrations.
    """

    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String(50), unique=True, nullable=False, index=True)

    # Incident details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    service = Column(String(100), nullable=False)
    reported_by = Column(String(200), nullable=False)

    # Classification (populated by triage agent)
    category = Column(Enum(IncidentCategory, name="incident_category"), nullable=True)
    severity = Column(Enum(IncidentSeverity, name="incident_severity"), nullable=True)
    status = Column(
        Enum(IncidentStatus, name="incident_status"),
        default=IncidentStatus.OPEN,
        nullable=False,
        index=True,
    )

    # Investigation results
    investigation_data = Column(JSONB, default=dict)
    root_cause = Column(Text, nullable=True)
    recommendation = Column(Text, nullable=True)
    recommended_action = Column(JSONB, default=dict)

    # Resolution
    resolution_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(200), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    workflow_runs = relationship(
        "WorkflowRun", back_populates="incident", cascade="all, delete-orphan"
    )
    approval_requests = relationship(
        "ApprovalRequest", back_populates="incident", cascade="all, delete-orphan"
    )
    events = relationship(
        "WorkflowEvent", back_populates="incident", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Incident {self.external_id}: {self.title[:50]}>"


class WorkflowRun(Base):
    """
    Tracks each workflow execution for an incident.
    Contains the durable state that survives across steps.
    """

    __tablename__ = "workflow_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_number = Column(Integer, nullable=False)

    # Durable workflow state (JSON - you can view/expand in DBeaver)
    state = Column(JSONB, default=dict)
    current_step = Column(String(100), nullable=True)

    # Execution metadata
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="running", nullable=False)
    error_message = Column(Text, nullable=True)

    # Relationships
    incident = relationship("Incident", back_populates="workflow_runs")
    events = relationship(
        "WorkflowEvent", back_populates="workflow_run", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<WorkflowRun {self.incident_id} #{self.run_number}: {self.status}>"


class WorkflowEvent(Base):
    """
    Stores workflow events for observability.
    Each step in the workflow emits events here.
    """

    __tablename__ = "workflow_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_run_id = Column(
        UUID(as_uuid=True),
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
    )

    event_type = Column(String(100), nullable=False, index=True)
    executor_name = Column(String(100), nullable=True)
    data = Column(JSONB, default=dict)

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    incident = relationship("Incident", back_populates="events")
    workflow_run = relationship("WorkflowRun", back_populates="events")

    def __repr__(self):
        return f"<WorkflowEvent {self.event_type} ({self.executor_name})>"


class ApprovalRequest(Base):
    """
    Human approval requests for recommended actions.
    Created when the AI recommends an action that needs human sign-off.
    """

    __tablename__ = "approval_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
    )

    # What needs approval
    action_type = Column(String(100), nullable=False)
    action_details = Column(JSONB, default=dict)
    reasoning = Column(Text, nullable=False)

    # Approval state
    status = Column(
        Enum(ApprovalStatus, name="approval_status"),
        default=ApprovalStatus.PENDING,
        nullable=False,
    )
    reviewed_by = Column(String(200), nullable=True)
    review_notes = Column(Text, nullable=True)

    # Timestamps
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)

    # Relationships
    incident = relationship("Incident", back_populates="approval_requests")

    def __repr__(self):
        return f"<ApprovalRequest {self.action_type}: {self.status}>"
