"""rename stripe_* billing columns to provider-neutral billing_*

Switched the billing provider from Stripe to Lemon Squeezy (Merchant of Record).
The columns are renamed rather than dropped so the tier-reconciliation state
survives, and the neutral names outlast any future provider change.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-02 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'stripe_customer_id', new_column_name='billing_customer_id')
    op.alter_column('users', 'stripe_subscription_id', new_column_name='billing_subscription_id')


def downgrade() -> None:
    op.alter_column('users', 'billing_customer_id', new_column_name='stripe_customer_id')
    op.alter_column('users', 'billing_subscription_id', new_column_name='stripe_subscription_id')
