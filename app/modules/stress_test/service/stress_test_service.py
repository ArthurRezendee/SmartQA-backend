import json
from collections import defaultdict
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.modules.stress_test.model.stress_test_model import StressTest
from app.modules.stress_test.model.stress_test_finding_model import StressTestFinding
from app.modules.stress_test.model.stress_test_step_model import StressTestStep
from app.modules.target.model.target_model import Target
from app.modules.billing.model.billing_account_model import BillingAccount


class StressTestService:

    async def _validate_and_consume_quota(
        self,
        db: AsyncSession,
        user_id: int,
        owner_type: str,
        owner_id: int,
    ):
        if owner_type == "organization" and owner_id:
            billing_filter = (
                BillingAccount.organization_id == owner_id,
                BillingAccount.is_active == True,
            )
        else:
            billing_filter = (
                BillingAccount.owner_user_id == user_id,
                BillingAccount.is_active == True,
            )

        result = await db.execute(
            select(BillingAccount)
            .options(selectinload(BillingAccount.plan))
            .where(*billing_filter)
        )
        billing = result.scalar_one_or_none()

        if not billing:
            owner_label = "Organização" if owner_type == "organization" else "Usuário"
            raise ValueError(f"{owner_label} sem billing account ativa")

        if billing.subscription_status != "active":
            raise ValueError("Assinatura inativa")

        plan = billing.plan
        allowed = plan.stress_tests_per_month - billing.stress_tests_used_current_cycle

        if allowed <= 0:
            raise ValueError("Limite mensal de stress tests atingido")

        billing.stress_tests_used_current_cycle += 1
        await db.flush()

    async def create(self, db: AsyncSession, target_id: int, user_id: int) -> dict:
        result = await db.execute(
            select(Target).where(
                Target.id == target_id,
                Target.user_id == user_id,
                Target.deleted_at.is_(None),
            )
        )
        target = result.scalar_one_or_none()
        if not target:
            raise ValueError("Alvo não encontrado")

        await self._validate_and_consume_quota(
            db,
            user_id=user_id,
            owner_type=target.owner_type,
            owner_id=target.owner_id,
        )

        stress_test = StressTest(
            target_id=target_id,
            user_id=user_id,
            owner_type=target.owner_type,
            owner_id=target.owner_id,
            status="pending",
        )
        db.add(stress_test)
        await db.commit()
        await db.refresh(stress_test)
        return stress_test.to_dict()

    async def get_or_fail(self, db: AsyncSession, stress_test_id: int, user_id: int) -> dict:
        result = await db.execute(
            select(StressTest)
            .options(selectinload(StressTest.findings))
            .where(
                StressTest.id == stress_test_id,
                StressTest.user_id == user_id,
                StressTest.deleted_at.is_(None),
            )
        )
        st = result.scalar_one_or_none()
        if not st:
            raise ValueError("Stress test não encontrado")
        return self._serialize(st)

    async def list_by_target(self, db: AsyncSession, target_id: int, user_id: int) -> list:
        result = await db.execute(
            select(StressTest)
            .options(selectinload(StressTest.findings))
            .where(
                StressTest.target_id == target_id,
                StressTest.user_id == user_id,
                StressTest.deleted_at.is_(None),
            )
            .order_by(StressTest.created_at.desc())
        )
        tests = result.scalars().unique().all()
        return [self._serialize(t) for t in tests]

    async def get_steps(self, db: AsyncSession, stress_test_id: int, user_id: int) -> dict:
        # Confirma acesso ao stress test
        result = await db.execute(
            select(StressTest).where(
                StressTest.id == stress_test_id,
                StressTest.user_id == user_id,
                StressTest.deleted_at.is_(None),
            )
        )
        st = result.scalar_one_or_none()
        if not st:
            raise ValueError("Stress test não encontrado")

        steps_result = await db.execute(
            select(StressTestStep)
            .where(StressTestStep.stress_test_id == stress_test_id)
            .order_by(StressTestStep.worker_id, StressTestStep.id)
        )
        steps = steps_result.scalars().all()

        # Agrupa por elemento para facilitar a visualização de cobertura
        groups: dict[str, dict] = {}
        for s in steps:
            key = f"{s.worker_id}::{s.element_label}"
            if key not in groups:
                groups[key] = {
                    "element_label": s.element_label,
                    "element_kind":  s.element_kind,
                    "field_type":    s.field_type,
                    "worker_id":     s.worker_id,
                    "attacks": [],
                    "total": 0,
                    "bugs": 0,
                    "skipped": 0,
                }
            groups[key]["attacks"].append({
                "id":                s.id,
                "attack_key":        s.attack_key,
                "attack_description": s.attack_description,
                "result":            s.result,
                "finding_id":        s.finding_id,
            })
            groups[key]["total"] += 1
            if s.result == "bug":
                groups[key]["bugs"] += 1
            elif s.result == "skipped":
                groups[key]["skipped"] += 1

        elements = list(groups.values())
        total_steps = len(steps)
        total_bugs  = sum(1 for s in steps if s.result == "bug")

        return {
            "stress_test_id": stress_test_id,
            "total_steps":    total_steps,
            "total_bugs":     total_bugs,
            "elements":       elements,
        }

    async def delete(self, db: AsyncSession, stress_test_id: int, user_id: int):
        result = await db.execute(
            select(StressTest).where(
                StressTest.id == stress_test_id,
                StressTest.user_id == user_id,
                StressTest.deleted_at.is_(None),
            )
        )
        st = result.scalar_one_or_none()
        if not st:
            raise ValueError("Stress test não encontrado")
        st.deleted_at = datetime.utcnow()
        await db.commit()

    def generate_report_markdown(self, stress_test: dict) -> str:
        findings = stress_test.get("findings") or []
        summary = stress_test.get("summary") or "Sem resumo disponível."
        total = stress_test.get("total_findings") or 0
        created_at = stress_test.get("created_at") or ""
        completed_at = stress_test.get("completed_at") or ""

        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        severity_labels = {"critical": "CRÍTICO", "high": "ALTO", "medium": "MÉDIO", "low": "BAIXO"}
        category_labels = {
            "crash": "Crash do Sistema",
            "security": "Segurança",
            "validation": "Validação",
            "ui_error": "Erro de Interface",
            "http_error": "Erro HTTP",
            "functional": "Funcional",
            "ux": "Experiência do Usuário",
        }

        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in findings:
            sev = f.get("severity", "medium")
            counts[sev] = counts.get(sev, 0) + 1

        sorted_findings = sorted(findings, key=lambda x: severity_order.get(x.get("severity", "low"), 3))

        lines = [
            f"# Stress Test Report",
            f"",
            f"**Data de início:** {created_at}",
            f"**Data de conclusão:** {completed_at}",
            f"**Total de bugs encontrados:** {total}",
            f"",
            f"---",
            f"",
            f"## Resumo Executivo",
            f"",
            summary,
            f"",
            f"---",
            f"",
            f"## Distribuição por Severidade",
            f"",
            f"| Severidade | Quantidade |",
            f"|-----------|-----------|",
            f"| Crítico   | {counts['critical']} |",
            f"| Alto      | {counts['high']} |",
            f"| Médio     | {counts['medium']} |",
            f"| Baixo     | {counts['low']} |",
            f"",
            f"---",
            f"",
            f"## Findings",
            f"",
        ]

        if not sorted_findings:
            lines.append("Nenhum bug encontrado durante o stress test.")
        else:
            for i, f in enumerate(sorted_findings, 1):
                sev = f.get("severity", "medium")
                cat = f.get("category", "functional")
                sev_label = severity_labels.get(sev, sev.upper())
                cat_label = category_labels.get(cat, cat)

                steps = f.get("steps_to_reproduce") or []
                if isinstance(steps, str):
                    try:
                        steps = json.loads(steps)
                    except Exception:
                        steps = [steps]

                lines += [
                    f"### #{i} — {f.get('title', 'Bug sem título')} [{sev_label}]",
                    f"",
                    f"**Severidade:** {sev_label}  ",
                    f"**Categoria:** {cat_label}  ",
                    f"**Elemento:** {f.get('element') or 'Não especificado'}  ",
                    f"**Input utilizado:** `{f.get('input_used') or 'N/A'}`  ",
                    f"",
                    f"**Descrição:**",
                    f"{f.get('description') or 'Sem descrição.'}",
                    f"",
                    f"**Passos para reproduzir:**",
                ]
                for j, step in enumerate(steps, 1):
                    lines.append(f"{j}. {step}")

                lines += [
                    f"",
                    f"**Detalhes do erro:** {f.get('error_details') or 'Nenhuma mensagem de erro exibida.'}",
                    f"",
                    f"---",
                    f"",
                ]

        return "\n".join(lines)

    def _serialize(self, st: StressTest) -> dict:
        data = st.to_dict()
        findings = []
        for f in (st.findings or []):
            fd = f.to_dict()
            steps_raw = fd.get("steps_to_reproduce")
            if steps_raw:
                try:
                    fd["steps_to_reproduce"] = json.loads(steps_raw)
                except Exception:
                    fd["steps_to_reproduce"] = [steps_raw]
            else:
                fd["steps_to_reproduce"] = []
            findings.append(fd)
        data["findings"] = findings
        return data
