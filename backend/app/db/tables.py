"""SQLAlchemy Core mappings for tables already created by Supabase migrations.

These definitions are used to build queries; the API never calls create_all().
"""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB


metadata = MetaData()

incidents = Table(
    "incidents",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("title", String(200), nullable=False),
    Column("description", Text, nullable=False),
    Column("incident_type", String(80), nullable=False),
    Column("location_name", String(200), nullable=False),
    Column("latitude", Float),
    Column("longitude", Float),
    Column("severity", String(20), nullable=False),
    Column("status", String(20), nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="public",
)

evidence = Table(
    "evidence",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("incident_id", Uuid(as_uuid=True), ForeignKey("public.incidents.id"), nullable=False),
    Column("code", String(80), nullable=False),
    Column("evidence_type", String(80), nullable=False),
    Column("state", String(30), nullable=False),
    Column("value_numeric", Float),
    Column("value_text", Text),
    Column("unit", String(40)),
    Column("source", String(200), nullable=False),
    Column("observed_at", DateTime(timezone=True), nullable=False),
    Column("reliability_score", Float, nullable=False),
    Column("provenance", JSONB().with_variant(JSON(), "sqlite"), nullable=False),
    Column("is_simulated", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("id", "incident_id", name="evidence_id_incident_unique"),
    schema="public",
)

decisions = Table(
    "decisions",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("incident_id", Uuid(as_uuid=True), ForeignKey("public.incidents.id"), nullable=False),
    Column("question", Text, nullable=False),
    Column("deadline", DateTime(timezone=True), nullable=False),
    Column("status", String(30), nullable=False),
    Column("current_version", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("id", "incident_id", name="decisions_id_incident_unique"),
    schema="public",
)

decision_versions = Table(
    "decision_versions",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("decision_id", Uuid(as_uuid=True), ForeignKey("public.decisions.id"), nullable=False),
    Column("version_number", Integer, nullable=False),
    Column("summary", Text, nullable=False),
    Column("uncertainty_level", String(20), nullable=False),
    Column("evidence_snapshot", JSONB().with_variant(JSON(), "sqlite"), nullable=False),
    Column("approval_status", String(30), nullable=False),
    Column("created_by", String(120), nullable=False),
    Column("approved_by", String(120)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("decision_id", "version_number", name="decision_versions_unique_version"),
    schema="public",
)

hypotheses = Table(
    "hypotheses",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("incident_id", Uuid(as_uuid=True), ForeignKey("public.incidents.id"), nullable=False),
    Column("code", String(40), nullable=False),
    Column("title", String(200), nullable=False),
    Column("description", Text, nullable=False),
    Column("status", String(30), nullable=False, server_default="ACTIVE"),
    Column("support_score", Float, nullable=False, server_default="0"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("incident_id", "code", name="hypotheses_incident_code_unique"),
    schema="public",
)

evidence_gaps = Table(
    "evidence_gaps",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("incident_id", Uuid(as_uuid=True), ForeignKey("public.incidents.id"), nullable=False),
    Column("decision_id", Uuid(as_uuid=True), nullable=False),
    Column("code", String(80), nullable=False),
    Column("description", Text, nullable=False),
    Column("criticality", String(20), nullable=False, server_default="MEDIUM"),
    Column("status", String(30), nullable=False, server_default="OPEN"),
    Column("rationale", Text),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ForeignKeyConstraint(
        ["decision_id", "incident_id"],
        ["public.decisions.id", "public.decisions.incident_id"],
        name="evidence_gaps_decision_incident_fk",
    ),
    UniqueConstraint("id", "decision_id", "incident_id", name="evidence_gaps_id_decision_incident_unique"),
    schema="public",
)

actors = Table(
    "actors",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("code", String(80), nullable=False, unique=True),
    Column("name", String(160), nullable=False),
    Column("actor_type", String(60), nullable=False),
    Column("capabilities", JSONB().with_variant(JSON(), "sqlite"), nullable=False),
    Column("location_name", String(200)),
    Column("available", Boolean, nullable=False, server_default="true"),
    Column("capacity", Integer, nullable=False, server_default="1"),
    Column("turnaround_minutes", Integer),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="public",
)

evidence_requests = Table(
    "evidence_requests",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("incident_id", Uuid(as_uuid=True), ForeignKey("public.incidents.id"), nullable=False),
    Column("decision_id", Uuid(as_uuid=True), nullable=False),
    Column("evidence_gap_id", Uuid(as_uuid=True)),
    Column("assigned_actor_id", Uuid(as_uuid=True), ForeignKey("public.actors.id")),
    Column("result_evidence_id", Uuid(as_uuid=True)),
    Column("requested_evidence_code", String(80), nullable=False),
    Column("purpose", Text, nullable=False),
    Column("priority", String(20), nullable=False, server_default="ROUTINE"),
    Column("status", String(30), nullable=False, server_default="DRAFT"),
    Column("estimated_cost", Float),
    Column("estimated_minutes", Integer),
    Column("requested_by", String(120), nullable=False, server_default="system"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ForeignKeyConstraint(
        ["decision_id", "incident_id"],
        ["public.decisions.id", "public.decisions.incident_id"],
        name="evidence_requests_decision_incident_fk",
    ),
    ForeignKeyConstraint(
        ["evidence_gap_id", "decision_id", "incident_id"],
        ["public.evidence_gaps.id", "public.evidence_gaps.decision_id", "public.evidence_gaps.incident_id"],
        name="evidence_requests_gap_fk",
    ),
    ForeignKeyConstraint(
        ["result_evidence_id", "incident_id"],
        ["public.evidence.id", "public.evidence.incident_id"],
        name="evidence_requests_result_incident_fk",
    ),
    schema="public",
)

request_status_events = Table(
    "request_status_events",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("request_id", Uuid(as_uuid=True), ForeignKey("public.evidence_requests.id"), nullable=False),
    Column("from_status", String(30)),
    Column("to_status", String(30), nullable=False),
    Column("actor_name", String(120), nullable=False),
    Column("note", Text),
    Column("occurred_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="public",
)

audit_events = Table(
    "audit_events",
    metadata,
    Column("id", Uuid(as_uuid=True), primary_key=True),
    Column("incident_id", Uuid(as_uuid=True), ForeignKey("public.incidents.id")),
    Column("entity_type", String(60), nullable=False),
    Column("entity_id", Uuid(as_uuid=True), nullable=False),
    Column("event_type", String(80), nullable=False),
    Column("actor_name", String(120), nullable=False),
    Column("payload", JSONB().with_variant(JSON(), "sqlite"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    schema="public",
)
