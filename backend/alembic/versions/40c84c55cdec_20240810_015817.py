"""20240810_015817

Revision ID: 40c84c55cdec
Revises: de43f5c4b194
Create Date: 2024-08-10 01:58:18.607097

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '40c84c55cdec'
down_revision: Union[str, None] = 'de43f5c4b194'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('financetracker_user', sa.Column('is_verified', sa.Boolean(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('financetracker_user', 'is_verified')
    # ### end Alembic commands ###