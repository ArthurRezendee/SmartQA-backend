"""refactor_screen_target_separation

Separação de responsabilidades:
- Screen (tela): conhecimento/documentação
- Target (alvo): execução de análise (casos de teste, scripts playwright)

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-04-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ============================================================
    # 1. Cria tabela screens
    # ============================================================
    op.create_table(
        'screens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('owner_type', sa.String(length=20), nullable=False, server_default='user'),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('screen_context', sa.Text(), nullable=True),
        sa.Column('documentation_description', sa.Text(), nullable=True),
        sa.Column('uiux_description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    # ============================================================
    # 2. Renomeia qa_analyses → targets e ajusta colunas
    # ============================================================
    op.rename_table('qa_analyses', 'targets')

    # Remove colunas que vão para Screen
    op.drop_column('targets', 'target_url')
    op.drop_column('targets', 'screen_context')
    op.drop_column('targets', 'documentation_description')
    op.drop_column('targets', 'uiux_description')

    # ============================================================
    # 3. Cria tabela target_screens (many-to-many)
    # ============================================================
    op.create_table(
        'target_screens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('screen_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['target_id'], ['targets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['screen_id'], ['screens.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('target_id', 'screen_id', name='uq_target_screens'),
    )
    op.create_index('ix_target_screens_target_id', 'target_screens', ['target_id'])
    op.create_index('ix_target_screens_screen_id', 'target_screens', ['screen_id'])

    # ============================================================
    # 4. Migração de dados: cria uma Screen por Target existente
    # ============================================================
    op.execute("""
        INSERT INTO screens (user_id, owner_type, owner_id, name, url, description,
                             screen_context, documentation_description, uiux_description,
                             status, created_at, updated_at)
        SELECT user_id, owner_type, owner_id, name,
               '' AS url,
               description, NULL AS screen_context,
               NULL AS documentation_description,
               NULL AS uiux_description,
               'active' AS status,
               created_at, updated_at
        FROM targets
    """)

    # Vincula cada target à screen correspondente via target_screens
    op.execute("""
        INSERT INTO target_screens (target_id, screen_id)
        SELECT t.id, s.id
        FROM targets t
        JOIN screens s ON s.user_id = t.user_id
            AND s.owner_type = t.owner_type
            AND s.owner_id = t.owner_id
            AND s.created_at = t.created_at
    """)

    # ============================================================
    # 5. Renomeia qa_documents → screen_documents
    #    e muda FK de qa_analysis_id → screen_id
    # ============================================================
    op.rename_table('qa_documents', 'screen_documents')

    # Adiciona nova coluna screen_id
    op.add_column('screen_documents', sa.Column('screen_id', sa.Integer(), nullable=True))

    # Popula screen_id usando o mapeamento target → screen
    op.execute("""
        UPDATE screen_documents sd
        SET screen_id = ts.screen_id
        FROM target_screens ts
        WHERE ts.target_id = sd.qa_analysis_id
    """)

    # Torna screen_id NOT NULL e adiciona FK
    op.alter_column('screen_documents', 'screen_id', nullable=False)
    op.create_foreign_key(
        'fk_screen_documents_screen_id',
        'screen_documents', 'screens',
        ['screen_id'], ['id'],
    )

    # Remove coluna antiga
    op.drop_constraint('qa_documents_qa_analysis_id_fkey', 'screen_documents', type_='foreignkey')
    op.drop_column('screen_documents', 'qa_analysis_id')

    # ============================================================
    # 6. Atualiza access_credentials: qa_analysis_id → screen_id
    # ============================================================
    op.add_column('access_credentials', sa.Column('screen_id', sa.Integer(), nullable=True))
    # Mapeia qa_analysis_id → screen via target_screens (cada target virou uma screen)
    op.execute("""
        UPDATE access_credentials ac
        SET screen_id = ts.screen_id
        FROM target_screens ts
        WHERE ts.target_id = ac.qa_analysis_id
    """)
    op.alter_column('access_credentials', 'screen_id', nullable=False)
    op.create_foreign_key(
        'fk_access_credentials_screen_id',
        'access_credentials', 'screens',
        ['screen_id'], ['id'], ondelete='CASCADE',
    )
    op.drop_constraint('access_credentials_qa_analysis_id_fkey', 'access_credentials', type_='foreignkey')
    op.drop_column('access_credentials', 'qa_analysis_id')

    # ============================================================
    # 7. Atualiza test_cases: qa_analysis_id → target_id
    # ============================================================
    op.add_column('test_cases', sa.Column('target_id', sa.Integer(), nullable=True))
    op.execute("UPDATE test_cases SET target_id = qa_analysis_id")
    op.alter_column('test_cases', 'target_id', nullable=False)
    op.create_foreign_key(
        'fk_test_cases_target_id',
        'test_cases', 'targets',
        ['target_id'], ['id'], ondelete='CASCADE',
    )
    op.drop_constraint('test_cases_qa_analysis_id_fkey', 'test_cases', type_='foreignkey')
    op.drop_index('ix_test_cases_qa_analysis_id', table_name='test_cases', if_exists=True)
    op.drop_column('test_cases', 'qa_analysis_id')
    op.create_index('ix_test_cases_target_id', 'test_cases', ['target_id'])

    # ============================================================
    # 8. Atualiza playwright_scripts: analysis_id → target_id
    # ============================================================
    op.add_column('playwright_scripts', sa.Column('target_id', sa.Integer(), nullable=True))
    op.execute("UPDATE playwright_scripts SET target_id = analysis_id")
    op.alter_column('playwright_scripts', 'target_id', nullable=False)
    op.create_foreign_key(
        'fk_playwright_scripts_target_id',
        'playwright_scripts', 'targets',
        ['target_id'], ['id'], ondelete='CASCADE',
    )
    op.drop_constraint('uq_playwright_scripts_analysis_version', 'playwright_scripts', type_='unique')
    op.drop_constraint('playwright_scripts_analysis_id_fkey', 'playwright_scripts', type_='foreignkey')
    op.drop_index('ix_playwright_scripts_analysis_status', table_name='playwright_scripts', if_exists=True)
    op.drop_column('playwright_scripts', 'analysis_id')
    op.create_unique_constraint(
        'uq_playwright_scripts_target_version',
        'playwright_scripts', ['target_id', 'version'],
    )
    op.create_index('ix_playwright_scripts_target_status', 'playwright_scripts', ['target_id', 'status'])

    # ============================================================
    # 9. Migra documentations: qa_analysis_id → screen_id
    #    (documentação é da tela, não do alvo)
    # ============================================================
    op.add_column('documentations', sa.Column('screen_id', sa.Integer(), nullable=True))

    # Popula screen_id: mapeia qa_analysis_id → screen via target_screens
    op.execute("""
        UPDATE documentations d
        SET screen_id = ts.screen_id
        FROM target_screens ts
        WHERE ts.target_id = d.qa_analysis_id
    """)

    op.alter_column('documentations', 'screen_id', nullable=False)
    op.create_foreign_key(
        'fk_documentations_screen_id',
        'documentations', 'screens',
        ['screen_id'], ['id'], ondelete='CASCADE',
    )
    op.drop_constraint('uq_documentations_analysis_version', 'documentations', type_='unique')
    op.drop_constraint('documentations_qa_analysis_id_fkey', 'documentations', type_='foreignkey')
    op.drop_index('ix_documentations_analysis_status', table_name='documentations', if_exists=True)
    op.drop_column('documentations', 'qa_analysis_id')
    op.create_unique_constraint(
        'uq_documentations_screen_version',
        'documentations', ['screen_id', 'version'],
    )
    op.create_index('ix_documentations_screen_status', 'documentations', ['screen_id', 'status'])

    # ============================================================
    # 10. Renomeia analysis_jobs → target_jobs
    #     e muda FK de qa_analysis_id → target_id
    # ============================================================
    op.rename_table('analysis_jobs', 'target_jobs')
    op.add_column('target_jobs', sa.Column('target_id', sa.Integer(), nullable=True))
    op.execute("UPDATE target_jobs SET target_id = qa_analysis_id")
    op.alter_column('target_jobs', 'target_id', nullable=False)
    op.create_foreign_key(
        'fk_target_jobs_target_id',
        'target_jobs', 'targets',
        ['target_id'], ['id'], ondelete='CASCADE',
    )
    op.drop_constraint('analysis_jobs_qa_analysis_id_fkey', 'target_jobs', type_='foreignkey')
    op.drop_column('target_jobs', 'qa_analysis_id')


def downgrade() -> None:
    # ============================================================
    # Reverter: target_jobs → analysis_jobs
    # ============================================================
    op.add_column('target_jobs', sa.Column('qa_analysis_id', sa.Integer(), nullable=True))
    op.execute("UPDATE target_jobs SET qa_analysis_id = target_id")
    op.drop_constraint('fk_target_jobs_target_id', 'target_jobs', type_='foreignkey')
    op.drop_column('target_jobs', 'target_id')
    op.rename_table('target_jobs', 'analysis_jobs')

    # ============================================================
    # Reverter: documentations screen_id → qa_analysis_id
    # ============================================================
    op.add_column('documentations', sa.Column('qa_analysis_id', sa.Integer(), nullable=True))
    op.execute("""
        UPDATE documentations d
        SET qa_analysis_id = ts.target_id
        FROM target_screens ts
        WHERE ts.screen_id = d.screen_id
    """)
    op.drop_constraint('fk_documentations_screen_id', 'documentations', type_='foreignkey')
    op.drop_constraint('uq_documentations_screen_version', 'documentations', type_='unique')
    op.drop_index('ix_documentations_screen_status', table_name='documentations')
    op.drop_column('documentations', 'screen_id')
    op.create_unique_constraint('uq_documentations_analysis_version', 'documentations', ['qa_analysis_id', 'version'])
    op.create_index('ix_documentations_analysis_status', 'documentations', ['qa_analysis_id', 'status'])

    # ============================================================
    # Reverter: playwright_scripts target_id → analysis_id
    # ============================================================
    op.add_column('playwright_scripts', sa.Column('analysis_id', sa.Integer(), nullable=True))
    op.execute("UPDATE playwright_scripts SET analysis_id = target_id")
    op.drop_constraint('fk_playwright_scripts_target_id', 'playwright_scripts', type_='foreignkey')
    op.drop_constraint('uq_playwright_scripts_target_version', 'playwright_scripts', type_='unique')
    op.drop_index('ix_playwright_scripts_target_status', table_name='playwright_scripts')
    op.drop_column('playwright_scripts', 'target_id')

    # ============================================================
    # Reverter: test_cases target_id → qa_analysis_id
    # ============================================================
    op.add_column('test_cases', sa.Column('qa_analysis_id', sa.Integer(), nullable=True))
    op.execute("UPDATE test_cases SET qa_analysis_id = target_id")
    op.drop_constraint('fk_test_cases_target_id', 'test_cases', type_='foreignkey')
    op.drop_index('ix_test_cases_target_id', table_name='test_cases')
    op.drop_column('test_cases', 'target_id')
    op.create_index('ix_test_cases_qa_analysis_id', 'test_cases', ['qa_analysis_id'])

    # ============================================================
    # Reverter: access_credentials screen_id → qa_analysis_id
    # ============================================================
    op.add_column('access_credentials', sa.Column('qa_analysis_id', sa.Integer(), nullable=True))
    op.execute("""
        UPDATE access_credentials ac
        SET qa_analysis_id = ts.target_id
        FROM target_screens ts
        WHERE ts.screen_id = ac.screen_id
    """)
    op.drop_constraint('fk_access_credentials_screen_id', 'access_credentials', type_='foreignkey')
    op.drop_column('access_credentials', 'screen_id')

    # ============================================================
    # Reverter: screen_documents → qa_documents
    # ============================================================
    op.add_column('screen_documents', sa.Column('qa_analysis_id', sa.Integer(), nullable=True))
    op.execute("""
        UPDATE screen_documents sd
        SET qa_analysis_id = ts.target_id
        FROM target_screens ts
        WHERE ts.screen_id = sd.screen_id
    """)
    op.drop_constraint('fk_screen_documents_screen_id', 'screen_documents', type_='foreignkey')
    op.drop_column('screen_documents', 'screen_id')
    op.rename_table('screen_documents', 'qa_documents')

    # ============================================================
    # Reverter: remove target_screens e screens
    # ============================================================
    op.drop_table('target_screens')
    op.drop_table('screens')

    # ============================================================
    # Reverter: targets → qa_analyses e restaura colunas
    # ============================================================
    op.add_column('targets', sa.Column('target_url', sa.Text(), nullable=True))
    op.add_column('targets', sa.Column('screen_context', sa.Text(), nullable=True))
    op.add_column('targets', sa.Column('documentation_description', sa.Text(), nullable=True))
    op.add_column('targets', sa.Column('uiux_description', sa.Text(), nullable=True))
    op.rename_table('targets', 'qa_analyses')
