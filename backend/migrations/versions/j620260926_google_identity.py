"""store verified Google subject on user accounts"""

from alembic import op
import sqlalchemy as sa

revision = "j620260926"
down_revision = "i520260923"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users", sa.Column("google_sub", sa.String(length=255), nullable=True)
    )
    op.create_index(
        "ix_users_google_sub", "users", ["google_sub"], unique=True
    )


def downgrade():
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "google_sub")
