import uuid
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from sqlalchemy import TIMESTAMP, UniqueConstraint

from src.common.database import Base


class EntitySemanticLinkDb(Base):
    __tablename__ = "entity_semantic_links"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)  # data_domain | data_product | data_contract
    iri = Column(Text, nullable=False)
    label = Column(Text, nullable=True)

    created_by = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("entity_id", "entity_type", "iri", name="uq_entity_semantic_link"),
    )

    def __repr__(self):
        return f"<EntitySemanticLinkDb(id={self.id}, entity_type='{self.entity_type}', entity_id='{self.entity_id}', iri='{self.iri}')>"


