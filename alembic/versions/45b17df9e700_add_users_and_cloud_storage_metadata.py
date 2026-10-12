"""add_users_and_cloud_storage_metadata

Revision ID: 45b17df9e700
Revises: dfb1ace84fda
Create Date: 2026-10-13 01:22:32.182933

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "45b17df9e700"
down_revision: Union[str, Sequence[str], None] = "dfb1ace84fda"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create users table if not exists
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("google_id", sa.String(length=100), nullable=True),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("full_name", sa.String(length=255), nullable=False),
            sa.Column("avatar_url", sa.String(length=1024), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_users_google_id"), "users", ["google_id"], unique=True)
        op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # 2. Add user_id column to generation_jobs if not exists
    jobs_cols = [c["name"] for c in inspector.get_columns("generation_jobs")]
    with op.batch_alter_table("generation_jobs") as batch_op:
        if "user_id" not in jobs_cols:
            batch_op.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
            batch_op.create_index(op.f("ix_generation_jobs_user_id"), ["user_id"], unique=False)
            batch_op.create_foreign_key("fk_generation_jobs_user_id", "users", ["user_id"], ["id"], ondelete="SET NULL")

    # 3. Add cloud_key column to certificate_records if not exists
    certs_cols = [c["name"] for c in inspector.get_columns("certificate_records")]
    with op.batch_alter_table("certificate_records") as batch_op:
        if "cloud_key" not in certs_cols:
            batch_op.add_column(sa.Column("cloud_key", sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("certificate_records") as batch_op:
        batch_op.drop_column("cloud_key")

    with op.batch_alter_table("generation_jobs") as batch_op:
        batch_op.drop_constraint("fk_generation_jobs_user_id", type_="foreignkey")
        batch_op.drop_index(op.f("ix_generation_jobs_user_id"))
        batch_op.drop_column("user_id")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_google_id"), table_name="users")
    op.drop_table("users")
