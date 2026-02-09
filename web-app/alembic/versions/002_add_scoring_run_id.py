"""Add scoring_run_id to scoring tables

Revision ID: 002_add_scoring_run_id
Revises: 001_add_scoring_permissions
Create Date: 2026-01-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_scoring_run_id'
down_revision: Union[str, None] = '001_add_scoring_permissions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add scoring_run_id column to all scoring tables."""

    # Add scoring_run_id to company_metrics
    op.add_column('company_metrics', sa.Column('scoring_run_id', sa.String(), nullable=True))
    op.create_index('ix_company_metrics_scoring_run_id', 'company_metrics', ['scoring_run_id'])

    # Add scoring_run_id to pillar_evaluation_criteria
    op.add_column('pillar_evaluation_criteria', sa.Column('scoring_run_id', sa.String(), nullable=True))
    op.create_index('ix_pillar_evaluation_criteria_scoring_run_id', 'pillar_evaluation_criteria', ['scoring_run_id'])

    # Add scoring_run_id to company_pillar_scores
    op.add_column('company_pillar_scores', sa.Column('scoring_run_id', sa.String(), nullable=True))
    op.create_index('ix_company_pillar_scores_scoring_run_id', 'company_pillar_scores', ['scoring_run_id'])

    # Add scoring_run_id to company_bde_scores (this is the primary record for a scoring run)
    op.add_column('company_bde_scores', sa.Column('scoring_run_id', sa.String(), nullable=True))
    op.create_index('ix_company_bde_scores_scoring_run_id', 'company_bde_scores', ['scoring_run_id'])

    # Add scoring_run_id to acquisition_recommendations
    op.add_column('acquisition_recommendations', sa.Column('scoring_run_id', sa.String(), nullable=True))
    op.create_index('ix_acquisition_recommendations_scoring_run_id', 'acquisition_recommendations', ['scoring_run_id'])

    # Add scoring_run_id to company_flags
    op.add_column('company_flags', sa.Column('scoring_run_id', sa.String(), nullable=True))
    op.create_index('ix_company_flags_scoring_run_id', 'company_flags', ['scoring_run_id'])

    # Update existing records: generate a scoring_run_id for existing data
    # This groups all existing records by company_id and assigns them the same run_id
    conn = op.get_bind()

    # Get unique company_ids from company_bde_scores
    result = conn.execute(sa.text("SELECT DISTINCT company_id FROM company_bde_scores"))
    company_ids = [row[0] for row in result.fetchall()]

    for company_id in company_ids:
        # Generate a unique run_id for this company's existing data
        import uuid
        run_id = str(uuid.uuid4())

        # Update all related tables
        conn.execute(
            sa.text("UPDATE company_metrics SET scoring_run_id = :run_id WHERE company_id = :company_id AND scoring_run_id IS NULL"),
            {"run_id": run_id, "company_id": company_id}
        )
        conn.execute(
            sa.text("UPDATE pillar_evaluation_criteria SET scoring_run_id = :run_id WHERE company_id = :company_id AND scoring_run_id IS NULL"),
            {"run_id": run_id, "company_id": company_id}
        )
        conn.execute(
            sa.text("UPDATE company_pillar_scores SET scoring_run_id = :run_id WHERE company_id = :company_id AND scoring_run_id IS NULL"),
            {"run_id": run_id, "company_id": company_id}
        )
        conn.execute(
            sa.text("UPDATE company_bde_scores SET scoring_run_id = :run_id WHERE company_id = :company_id AND scoring_run_id IS NULL"),
            {"run_id": run_id, "company_id": company_id}
        )
        conn.execute(
            sa.text("UPDATE acquisition_recommendations SET scoring_run_id = :run_id WHERE company_id = :company_id AND scoring_run_id IS NULL"),
            {"run_id": run_id, "company_id": company_id}
        )
        conn.execute(
            sa.text("UPDATE company_flags SET scoring_run_id = :run_id WHERE company_id = :company_id AND scoring_run_id IS NULL"),
            {"run_id": run_id, "company_id": company_id}
        )
        print(f"Assigned scoring_run_id {run_id} to existing data for company {company_id}")


def downgrade() -> None:
    """Remove scoring_run_id column from all scoring tables."""

    # Drop indexes first
    op.drop_index('ix_company_metrics_scoring_run_id', 'company_metrics')
    op.drop_index('ix_pillar_evaluation_criteria_scoring_run_id', 'pillar_evaluation_criteria')
    op.drop_index('ix_company_pillar_scores_scoring_run_id', 'company_pillar_scores')
    op.drop_index('ix_company_bde_scores_scoring_run_id', 'company_bde_scores')
    op.drop_index('ix_acquisition_recommendations_scoring_run_id', 'acquisition_recommendations')
    op.drop_index('ix_company_flags_scoring_run_id', 'company_flags')

    # Drop columns
    op.drop_column('company_metrics', 'scoring_run_id')
    op.drop_column('pillar_evaluation_criteria', 'scoring_run_id')
    op.drop_column('company_pillar_scores', 'scoring_run_id')
    op.drop_column('company_bde_scores', 'scoring_run_id')
    op.drop_column('acquisition_recommendations', 'scoring_run_id')
    op.drop_column('company_flags', 'scoring_run_id')
