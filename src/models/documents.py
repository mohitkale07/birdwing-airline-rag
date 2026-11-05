import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.db.database import Base


class Document(Base):
    __tablename__ = "documents"

    __table_args__ = (
        CheckConstraint(
            "source IN ('hr', 'customer_service', 'public')",
            name="ck_documents_source",
        ),
        CheckConstraint(
            "status IN ('uploaded', 'processing', 'indexed', 'failed')",
            name="ck_documents_status",
        ),
        CheckConstraint(
            "version >= 1",
            name="ck_documents_version",
        ),
        Index(
            "ix_documents_source_status",
            "source",
            "status",
        ),
        Index(
            "ix_documents_checksum",
            "checksum",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Private file/object storage location.
    storage_key: Mapped[str] = mapped_column(
        String(1024),
        unique=True,
        nullable=False,
    )

    # Document category used for retrieval filtering.
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # SHA-256 checksum of the original file.
    checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default=text("1"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="uploaded",
        server_default=text("'uploaded'"),
        nullable=False,
    )

    # Authoritative document access configuration.
    # Copy the relevant metadata into Qdrant payload during indexing.
    allowed_roles: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
