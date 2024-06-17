"""conversation add provider/preset

Revision ID: 28ec77033b2e
Revises: 9a533073a041
Create Date: 2023-05-13 13:57:20.591544

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "28ec77033b2e"
down_revision = "9a533073a041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversation", sa.Column("provider", sa.String(), nullable=False, server_default="")
    )
    op.add_column(
        "conversation", sa.Column("preset", sa.String(), nullable=False, server_default="")
    )
    # Attempt to back-propogate provider data based on model names.
    op.execute(
        "UPDATE conversation SET provider = 'ai21' WHERE model IN ('j2-large', 'j2-grande', 'j2-jumbo', 'j2-large-instruct', 'j2-grande-instruct', 'j2-jumbo-instruct');"
    )
    op.execute(
        "UPDATE conversation SET provider = 'chat_openai' WHERE model IN ('gpt-3.5-turbo', 'gpt-3.5-turbo-0301', 'gpt-4', 'gpt-4-0314', 'gpt-4-32k', 'gpt-4-32k-0314');"
    )
    op.execute(
        "UPDATE conversation SET provider = 'cohere' WHERE model IN ('base', 'base-light', 'command', 'command-light', 'summarize-medium', 'summarize-xlarge');"
    )
    op.execute(
        "UPDATE conversation SET provider = 'huggingface_hub' WHERE model IN ('bert-base-uncased', 'gpt2', 'xlm-roberta-base', 'roberta-base', 'microsoft/layoutlmv3-base', 'distilbert-base-uncased', 't5-base', 'xlm-roberta-large', 'bert-base-cased', 'google/flan-t5-xl');"
    )
    op.execute(
        "UPDATE conversation SET provider = 'openai' WHERE model IN ('text-ada-001', 'text-babbage-001', 'text-curie-001', 'text-davinci-001', 'text-davinci-002', 'text-davinci-003');"
    )
