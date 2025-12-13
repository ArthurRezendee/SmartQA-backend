from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.shared.responses import success, error
from typing import Type
from sqlalchemy.orm import DeclarativeBase


class BaseController:
    """
    Controller base do SmartQA
    """

    async def get_all(self, db: AsyncSession, model: Type[DeclarativeBase]):
        try:
            result = await db.execute(select(model))
            records = result.scalars().all()

            data = [
                record.__dict__ | {} for record in records
            ]

            # remove _sa_instance_state
            for item in data:
                item.pop("_sa_instance_state", None)

            return success("Dados recuperados", data)

        except Exception as e:
            return error(f"Erro ao buscar registros: {str(e)}")

    async def insert(self, db: AsyncSession, model: Type[DeclarativeBase], payload):
        try:
            if isinstance(payload, dict):
                record = model(**payload)
                db.add(record)
                await db.commit()
                await db.refresh(record)

                data = record.__dict__
                data.pop("_sa_instance_state", None)

                return success("Registro criado com sucesso", data)

            elif isinstance(payload, list):
                records = []
                for item in payload:
                    record = model(**item)
                    db.add(record)
                    records.append(record)

                await db.commit()

                data = []
                for record in records:
                    await db.refresh(record)
                    d = record.__dict__
                    d.pop("_sa_instance_state", None)
                    data.append(d)

                return success("Registros criados com sucesso", data)

            return error("Tipo de dado inválido")

        except Exception as e:
            await db.rollback()
            return error(f"Erro ao inserir registro(s): {str(e)}")
