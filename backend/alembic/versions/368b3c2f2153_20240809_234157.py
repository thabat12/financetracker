"""20240809_234157

Revision ID: 368b3c2f2153
Revises: 611767e03d39
Create Date: 2024-08-09 23:41:59.079088

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '368b3c2f2153'
down_revision: Union[str, None] = '611767e03d39'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('google_user',
    sa.Column('google_user_id', sa.String(length=255), nullable=False),
    sa.Column('user_id', sa.String(length=20), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['financetracker_user.user_id'], ),
    sa.PrimaryKeyConstraint('google_user_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('google_user')
    # ### end Alembic commands ###