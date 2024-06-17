"""Migrate model data to messages, remove dead message columns, add message_type

Revision ID: 82656e325f36
Revises: ea7ed165a4ef
Create Date: 2023-06-15 18:08:09.508380

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "82656e325f36"
down_revision = "ea7ed165a4ef"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("message", "prompt_tokens")
    op.drop_column("message", "completion_tokens")
    op.add_column(
        "message", sa.Column("message_type", sa.String(), nullable=False, server_default="content")
    )
    op.add_column("message", sa.Column("model", sa.String(), nullable=False, server_default=""))
    op.add_column("message", sa.Column("provider", sa.String(), nullable=False, server_default=""))
    op.add_column("message", sa.Column("preset", sa.String(), nullable=False, server_default=""))
    op.execute(
        "UPDATE message SET provider = (SELECT provider FROM conversation WHERE conversation.id = message.conversation_id), model = (SELECT model FROM conversation WHERE conversation.id = message.conversation_id), preset = (SELECT preset FROM conversation WHERE conversation.id = message.conversation_id);"
    )
    op.drop_column("conversation", "provider")
    op.drop_column("conversation", "preset")
    op.drop_column("conversation", "model")
