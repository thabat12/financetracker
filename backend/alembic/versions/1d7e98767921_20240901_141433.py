"""20240901_141433

Revision ID: 1d7e98767921
Revises: 81fa85319003
Create Date: 2024-09-01 14:14:34.936856

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d7e98767921'
down_revision: Union[str, None] = '81fa85319003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('transaction', sa.Column('institution_id', sa.String(length=80), nullable=True))
    op.create_foreign_key(None, 'transaction', 'institution', ['institution_id'], ['institution_id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'transaction', type_='foreignkey')
    op.drop_column('transaction', 'institution_id')
    # ### end Alembic commands ###
