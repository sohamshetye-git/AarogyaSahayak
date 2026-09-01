"""populate_government_schemes_catalog

Revision ID: 5360c828eb23
Revises: 97fadbd11b95
Create Date: 2026-09-01 22:02:10.371737

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5360c828eb23'
down_revision: Union[str, Sequence[str], None] = '97fadbd11b95'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Idempotently populate the canonical government schemes catalog and assistance capabilities."""
    bind = op.get_bind()
    from sqlalchemy.orm import Session
    from app.schemes.import_kb import import_knowledge_base
    from app.models import SchemeModel
    
    session = Session(bind=bind)
    try:
        scheme_count = session.query(SchemeModel).count()
        if scheme_count == 0:
            import_knowledge_base(db_session=session)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def downgrade() -> None:
    """Downgrade schema."""
    pass
