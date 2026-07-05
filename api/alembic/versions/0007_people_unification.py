"""people unification — canonical Person table, migrate FKs

Revision ID: 0007_people_unification
Revises: 0006_relationship_graph_core
Create Date: 2026-07-05 03:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_people_unification"
down_revision = "0006_relationship_graph_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "people",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("workspace_id", sa.String(length=36), sa.ForeignKey("founder_workspaces.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=255), nullable=True),
        sa.Column("relationship_status", sa.String(length=80), nullable=False, server_default="new"),
        sa.Column("last_contact_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_follow_up_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_kind", sa.String(length=40), nullable=False, server_default="contact"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.add_column("contacts", sa.Column("person_id", sa.String(length=36), sa.ForeignKey("people.id"), nullable=True))
    op.add_column("investors", sa.Column("person_id", sa.String(length=36), sa.ForeignKey("people.id"), nullable=True))

    conn = op.get_bind()
    for table, kind in [("contacts", "contact"), ("investors", "investor")]:
        rows = conn.execute(sa.text(f"SELECT id, workspace_id, name, email, company, role, "
                                   f"relationship_status, last_contact_at, next_follow_up_at, "
                                   f"notes, created_at FROM {table}")).fetchall()
        for row in rows:
            conn.execute(
                sa.text(
                    f"INSERT INTO people (id, workspace_id, name, email, company, role, "
                    f"relationship_status, last_contact_at, next_follow_up_at, notes, "
                    f"source_kind, created_at) "
                    f"VALUES (:id, :ws, :name, :email, :company, :role, "
                    f":rs, :lca, :nfa, :notes, :sk, :ca)"
                ),
                {
                    "id": row[0], "ws": row[1], "name": row[2],
                    "email": row[3] if kind == "contact" else None,
                    "company": row[4] if kind == "contact" else None,
                    "role": row[5] if kind == "contact" else None,
                    "rs": row[6], "lca": row[7], "nfa": row[8],
                    "notes": row[9] if kind == "contact" else None,
                    "sk": kind, "ca": row[10],
                },
            )
            conn.execute(
                sa.text(f"UPDATE {table} SET person_id = :pid WHERE id = :id"),
                {"pid": row[0], "id": row[0]},
            )

    op.add_column("relationship_edges", sa.Column("source_person_id", sa.String(length=36), sa.ForeignKey("people.id"), nullable=True))
    op.add_column("relationship_edges", sa.Column("target_person_id", sa.String(length=36), sa.ForeignKey("people.id"), nullable=True))
    conn.execute(sa.text(
        "UPDATE relationship_edges SET source_person_id = source_contact_id, target_person_id = target_contact_id"
    ))
    op.alter_column("relationship_edges", "source_person_id", nullable=False)
    op.drop_constraint("relationship_edges_ibfk_2", "relationship_edges", type_="foreignkey")
    op.drop_constraint("relationship_edges_ibfk_3", "relationship_edges", type_="foreignkey")
    op.drop_column("relationship_edges", "source_contact_id")
    op.drop_column("relationship_edges", "target_contact_id")

    op.add_column("intro_paths", sa.Column("from_person_id", sa.String(length=36), sa.ForeignKey("people.id"), nullable=True))
    op.add_column("intro_paths", sa.Column("to_person_id", sa.String(length=36), sa.ForeignKey("people.id"), nullable=True))
    conn.execute(sa.text(
        "UPDATE intro_paths SET from_person_id = from_contact_id, "
        "to_person_id = COALESCE(to_investor_id, to_contact_id)"
    ))
    op.alter_column("intro_paths", "from_person_id", nullable=False)
    op.drop_constraint("intro_paths_ibfk_2", "intro_paths", type_="foreignkey")
    op.drop_constraint("intro_paths_ibfk_3", "intro_paths", type_="foreignkey")
    op.drop_constraint("intro_paths_ibfk_4", "intro_paths", type_="foreignkey")
    op.drop_column("intro_paths", "from_contact_id")
    op.drop_column("intro_paths", "to_investor_id")
    op.drop_column("intro_paths", "to_contact_id")

    op.drop_constraint("dispatches_ibfk_2", "dispatches", type_="foreignkey")
    op.create_foreign_key("dispatches_ibfk_2", "dispatches", "people", ["person_id"], ["id"])

    op.add_column("opportunities", sa.Column("person_id", sa.String(length=36), sa.ForeignKey("people.id"), nullable=True))
    conn.execute(sa.text(
        "UPDATE opportunities SET person_id = COALESCE(contact_id, investor_id)"
    ))
    op.drop_constraint("opportunities_ibfk_2", "opportunities", type_="foreignkey")
    op.drop_constraint("opportunities_ibfk_3", "opportunities", type_="foreignkey")
    op.drop_column("opportunities", "contact_id")
    op.drop_column("opportunities", "investor_id")

    op.add_column("interaction_notes", sa.Column("person_id", sa.String(length=36), sa.ForeignKey("people.id"), nullable=True))
    conn.execute(sa.text(
        "UPDATE interaction_notes SET person_id = COALESCE(contact_id, investor_id)"
    ))
    op.drop_constraint("interaction_notes_ibfk_2", "interaction_notes", type_="foreignkey")
    op.drop_constraint("interaction_notes_ibfk_3", "interaction_notes", type_="foreignkey")
    op.drop_column("interaction_notes", "contact_id")
    op.drop_column("interaction_notes", "investor_id")

    op.add_column("follow_up_tasks", sa.Column("person_id", sa.String(length=36), sa.ForeignKey("people.id"), nullable=True))
    conn.execute(sa.text(
        "UPDATE follow_up_tasks SET person_id = COALESCE(contact_id, investor_id)"
    ))
    op.drop_constraint("follow_up_tasks_ibfk_2", "follow_up_tasks", type_="foreignkey")
    op.drop_constraint("follow_up_tasks_ibfk_3", "follow_up_tasks", type_="foreignkey")
    op.drop_column("follow_up_tasks", "contact_id")
    op.drop_column("follow_up_tasks", "investor_id")

    op.drop_constraint("pipeline_deals_ibfk_2", "pipeline_deals", type_="foreignkey")
    op.alter_column("pipeline_deals", "investor_id", new_column_name="person_id")
    op.create_foreign_key("pipeline_deals_ibfk_2", "pipeline_deals", "people", ["person_id"], ["id"])


def downgrade() -> None:
    pass
