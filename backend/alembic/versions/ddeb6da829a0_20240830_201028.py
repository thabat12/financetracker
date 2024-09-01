"""20240830_201028

Revision ID: ddeb6da829a0
Revises: 59363ce7ec02
Create Date: 2024-08-30 20:10:30.044843

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ddeb6da829a0'
down_revision: Union[str, None] = '59363ce7ec02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('access_key_institution_id_fkey', 'access_key', type_='foreignkey')
    op.drop_column('access_key', 'institution_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('access_key', sa.Column('institution_id', sa.VARCHAR(length=80), autoincrement=False, nullable=True))
    op.create_foreign_key('access_key_institution_id_fkey', 'access_key', 'institution', ['institution_id'], ['institution_id'])
    # ### end Alembic commands ###
