"""store neutral admin feedback and notification decision type"""

from alembic import op
import sqlalchemy as sa

revision = "l820260927"
down_revision = "k720260927"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "applications",
        sa.Column("admin_feedback", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "notifications",
        sa.Column("decision_type", sa.String(length=20), nullable=True),
    )


def downgrade():
    op.drop_column("notifications", "decision_type")
    op.drop_column("applications", "admin_feedback")
