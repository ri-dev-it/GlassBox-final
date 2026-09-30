"""Atomic ownership of file/identity hashes, including existing audit history."""
from alembic import op
import sqlalchemy as sa

revision = "p1220260930"
down_revision = "o1120260930"
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table("document_fingerprints",
        sa.Column("fingerprint", sa.String(72), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False))
    connection = op.get_bind()
    seen = set()
    for row in connection.execute(sa.text("SELECT file_hash, aadhaar_hash, user_id FROM document_audits ORDER BY id")):
        for prefix, digest in (("file:", row.file_hash), ("aadhaar:", row.aadhaar_hash)):
            if digest and prefix + digest not in seen:
                connection.execute(table.insert().values(fingerprint=prefix + digest, user_id=row.user_id))
                seen.add(prefix + digest)


def downgrade():
    op.drop_table("document_fingerprints")
