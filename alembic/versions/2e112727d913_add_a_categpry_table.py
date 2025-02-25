"""add a categpry table 

Revision ID: 2e112727d913
Revises: 96a9300bec11
Create Date: 2024-11-02 22:17:58.082940

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2e112727d913'
down_revision: Union[str, None] = '96a9300bec11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('categories', sa.Column('icon', sa.String(length=255), nullable=True))
    op.alter_column('categories', 'name',
               existing_type=sa.VARCHAR(),
               nullable=True)
    op.alter_column('categories', 'description',
               existing_type=sa.VARCHAR(),
               type_=sa.Text(),
               existing_nullable=True)
    op.drop_column('categories', 'created_at')
    op.drop_column('categories', 'updated_at')
    op.add_column('products', sa.Column('category_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'products', 'categories', ['category_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'products', type_='foreignkey')
    op.drop_column('products', 'category_id')
    op.add_column('categories', sa.Column('updated_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.add_column('categories', sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True))
    op.alter_column('categories', 'description',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(),
               existing_nullable=True)
    op.alter_column('categories', 'name',
               existing_type=sa.VARCHAR(),
               nullable=False)
    op.drop_column('categories', 'icon')
    # ### end Alembic commands ###
