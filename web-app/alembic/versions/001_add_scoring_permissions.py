"""Add scoring permissions

Revision ID: 001_add_scoring_permissions
Revises:
Create Date: 2026-01-13

"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_add_scoring_permissions'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Scoring permissions to add
SCORING_PERMISSIONS = [
    {"name": "scoring:read", "category": "scoring", "description": "View BDE scores and analysis"},
    {"name": "scoring:write", "category": "scoring", "description": "Trigger scoring and analysis"},
    {"name": "scoring:admin", "category": "scoring", "description": "Manage scoring configuration"},
]


def upgrade() -> None:
    """Add scoring permissions to the permissions table and assign to all roles."""
    # Get connection for raw SQL execution
    conn = op.get_bind()

    # Step 1: Add scoring permissions
    permission_ids = {}
    for perm in SCORING_PERMISSIONS:
        # Check if permission already exists
        result = conn.execute(
            sa.text("SELECT id FROM permissions WHERE name = :name"),
            {"name": perm["name"]}
        ).fetchone()

        if result is None:
            # Insert new permission
            perm_id = str(uuid.uuid4())
            conn.execute(
                sa.text("""
                    INSERT INTO permissions (id, name, category, description)
                    VALUES (:id, :name, :category, :description)
                """),
                {
                    "id": perm_id,
                    "name": perm["name"],
                    "category": perm["category"],
                    "description": perm["description"],
                }
            )
            permission_ids[perm["name"]] = perm_id
            print(f"Added permission: {perm['name']}")
        else:
            permission_ids[perm["name"]] = result[0]
            print(f"Permission already exists: {perm['name']}")

    # Step 2: Get all roles
    roles = conn.execute(sa.text("SELECT id, name FROM roles")).fetchall()

    # Step 3: Assign all scoring permissions to every role
    for role_id, role_name in roles:
        for perm_name, perm_id in permission_ids.items():
            # Check if association already exists
            existing = conn.execute(
                sa.text("""
                    SELECT 1 FROM role_permissions
                    WHERE role_id = :role_id AND permission_id = :permission_id
                """),
                {"role_id": role_id, "permission_id": perm_id}
            ).fetchone()

            if existing is None:
                conn.execute(
                    sa.text("""
                        INSERT INTO role_permissions (role_id, permission_id)
                        VALUES (:role_id, :permission_id)
                    """),
                    {"role_id": role_id, "permission_id": perm_id}
                )
                print(f"Assigned {perm_name} to role {role_name}")
            else:
                print(f"Role {role_name} already has {perm_name}")


def downgrade() -> None:
    """Remove scoring permissions from the permissions table."""
    conn = op.get_bind()

    for perm in SCORING_PERMISSIONS:
        # First remove any role_permissions associations
        conn.execute(
            sa.text("""
                DELETE FROM role_permissions
                WHERE permission_id IN (SELECT id FROM permissions WHERE name = :name)
            """),
            {"name": perm["name"]}
        )

        # Then remove the permission
        conn.execute(
            sa.text("DELETE FROM permissions WHERE name = :name"),
            {"name": perm["name"]}
        )
        print(f"Removed permission: {perm['name']}")
