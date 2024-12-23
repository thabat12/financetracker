"""revision

Revision ID: b4293f4aa125
Revises: 
Create Date: 2024-12-23 00:32:27.550414

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b4293f4aa125'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('security',
    sa.Column('security_id', sa.String(length=255), nullable=False),
    sa.Column('institution_security_id', sa.LargeBinary(), nullable=True),
    sa.Column('name', sa.LargeBinary(), nullable=False),
    sa.Column('ticker_symbol', sa.LargeBinary(), nullable=True),
    sa.Column('is_cash_equivalent', sa.Boolean(), nullable=False),
    sa.Column('type', sa.LargeBinary(), nullable=True),
    sa.Column('close_price', sa.LargeBinary(), nullable=False),
    sa.Column('close_price_as_of', sa.LargeBinary(), nullable=False),
    sa.Column('update_datetime', sa.DateTime(), nullable=True),
    sa.Column('iso_currency_code', sa.String(length=10), nullable=True),
    sa.Column('unofficial_currency_code', sa.String(length=10), nullable=True),
    sa.Column('market_identifier_code', sa.String(length=10), nullable=True),
    sa.Column('sector', sa.LargeBinary(), nullable=True),
    sa.Column('industry', sa.LargeBinary(), nullable=True),
    sa.Column('option_contract_type', sa.LargeBinary(), nullable=True),
    sa.Column('option_expiration_date', sa.DateTime(), nullable=True),
    sa.Column('option_strike_price', sa.LargeBinary(), nullable=True),
    sa.Column('option_underlying_ticker', sa.LargeBinary(), nullable=True),
    sa.Column('yield_rate', sa.LargeBinary(), nullable=True),
    sa.Column('percentage', sa.LargeBinary(), nullable=True),
    sa.Column('maturity_date', sa.LargeBinary(), nullable=True),
    sa.Column('issue_date', sa.LargeBinary(), nullable=True),
    sa.Column('face_value', sa.LargeBinary(), nullable=True),
    sa.Column('user_id', sa.String(length=20), nullable=True),
    sa.Column('account_id', sa.String(length=80), nullable=True),
    sa.Column('institution_id', sa.String(length=80), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['account.account_id'], ),
    sa.ForeignKeyConstraint(['institution_id'], ['institution.institution_id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['financetracker_user.user_id'], ),
    sa.PrimaryKeyConstraint('security_id')
    )
    op.create_table('holding',
    sa.Column('holding_id', sa.String(length=255), nullable=False),
    sa.Column('institution_price', sa.LargeBinary(), nullable=False),
    sa.Column('institution_price_as_of', sa.LargeBinary(), nullable=True),
    sa.Column('institution_value', sa.LargeBinary(), nullable=False),
    sa.Column('cost_basis', sa.LargeBinary(), nullable=True),
    sa.Column('quantity', sa.LargeBinary(), nullable=False),
    sa.Column('iso_currency_code', sa.LargeBinary(), nullable=True),
    sa.Column('unofficial_currency_code', sa.LargeBinary(), nullable=True),
    sa.Column('vested_quantity', sa.LargeBinary(), nullable=True),
    sa.Column('vested_value', sa.LargeBinary(), nullable=True),
    sa.Column('account_id', sa.String(length=80), nullable=False),
    sa.Column('security_id', sa.String(length=255), nullable=False),
    sa.Column('institution_id', sa.String(length=80), nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['account.account_id'], ),
    sa.ForeignKeyConstraint(['institution_id'], ['institution.institution_id'], ),
    sa.ForeignKeyConstraint(['security_id'], ['security.security_id'], ),
    sa.PrimaryKeyConstraint('holding_id')
    )
    op.drop_table('subscription')
    op.drop_table('investment_holding')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('investment_holding',
    sa.Column('investment_holding_id', sa.VARCHAR(length=255), autoincrement=False, nullable=False),
    sa.Column('name', postgresql.BYTEA(), autoincrement=False, nullable=True),
    sa.Column('ticker', postgresql.BYTEA(), autoincrement=False, nullable=True),
    sa.Column('cost_basis', postgresql.BYTEA(), autoincrement=False, nullable=True),
    sa.Column('institution_price', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('institution_price_as_of', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('institution_value', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('iso_currency_code', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('quantity', postgresql.BYTEA(), autoincrement=False, nullable=True),
    sa.Column('unofficial_currency_code', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.Column('vested_quantity', postgresql.BYTEA(), autoincrement=False, nullable=True),
    sa.Column('vested_value', postgresql.BYTEA(), autoincrement=False, nullable=True),
    sa.Column('account_id', sa.VARCHAR(length=80), autoincrement=False, nullable=True),
    sa.Column('user_id', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['account_id'], ['account.account_id'], name='investment_holding_account_id_fkey'),
    sa.ForeignKeyConstraint(['user_id'], ['financetracker_user.user_id'], name='investment_holding_user_id_fkey'),
    sa.PrimaryKeyConstraint('investment_holding_id', name='investment_holding_pkey')
    )
    op.create_table('subscription',
    sa.Column('subscription_id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(length=80), autoincrement=False, nullable=False),
    sa.Column('price', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
    sa.Column('renewal_date', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.Column('user_id', sa.VARCHAR(length=20), autoincrement=False, nullable=False),
    sa.Column('merchant_id', sa.VARCHAR(length=20), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['merchant_id'], ['merchant.merchant_id'], name='subscription_merchant_id_fkey'),
    sa.ForeignKeyConstraint(['user_id'], ['financetracker_user.user_id'], name='subscription_user_id_fkey'),
    sa.PrimaryKeyConstraint('subscription_id', name='subscription_pkey')
    )
    op.drop_table('holding')
    op.drop_table('security')
    # ### end Alembic commands ###
