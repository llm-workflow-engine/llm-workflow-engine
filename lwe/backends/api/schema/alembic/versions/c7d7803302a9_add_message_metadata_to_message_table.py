"""Add message_metadata to message table

Revision ID: c7d7803302a9
Revises: 82656e325f36
Create Date: 2023-06-17 17:57:44.292951

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c7d7803302a9"
down_revision = "82656e325f36"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("message", sa.Column("message_metadata", sa.String()))
