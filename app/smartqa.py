import typer
import subprocess
from pathlib import Path

app = typer.Typer(help="SmartQA CLI")

BASE_MODULES = Path("app/modules")

# =====================================================
# Helpers
# =====================================================
def to_snake(name: str) -> str:
    return "".join(
        f"_{c.lower()}" if c.isupper() else c
        for c in name
    ).lstrip("_")


def ensure_module(name: str) -> Path:
    module = BASE_MODULES / to_snake(name)
    module.mkdir(parents=True, exist_ok=True)
    (module / "__init__.py").touch(exist_ok=True)
    return module


# =====================================================
# make:module
# =====================================================
@app.command("make:module")
def make_module(module: str):
    """
    Cria um módulo com:
    - pastas de camadas (vazias)
    - router.py com rota /
    - controller inicial herdando BaseController
    """
    module_snake = to_snake(module)
    module_path = BASE_MODULES / module_snake

    module_path.mkdir(parents=True, exist_ok=True)
    (module_path / "__init__.py").touch(exist_ok=True)

    for layer in ["controller", "service", "model", "schemas"]:
        layer_path = module_path / layer
        layer_path.mkdir(exist_ok=True)
        (layer_path / "__init__.py").touch(exist_ok=True)

    controller_file = module_path / "controller" / f"{module_snake}_controller.py"
    if not controller_file.exists():
        controller_file.write_text(f"""
from app.shared.controller import BaseController


class {module}Controller(BaseController):

    def __init__(self):
        pass

    async def index(self):
        return {{
            "status": True,
            "message": "{module} module ready",
            "data": None
        }}
""")

    router_file = module_path / "router.py"
    if not router_file.exists():
        router_file.write_text(f"""
from fastapi import APIRouter
from app.modules.{module_snake}.controller.{module_snake}_controller import {module}Controller

router = APIRouter(
    prefix="/{module_snake}",
    tags=["{module}"]
)

controller = {module}Controller()


@router.get("/")
async def index():
    return await controller.index()
""")

    typer.echo(f"✅ Módulo '{module}' criado com sucesso")


# =====================================================
# make:controller
# =====================================================
@app.command("make:controller")
def make_controller(module: str):
    base = ensure_module(module)
    path = base / "controller" / f"{to_snake(module)}_controller.py"

    path.write_text(f"""
class {module}Controller:

    def __init__(self):
        pass
""")

    typer.echo(f"✅ Controller criado em {path}")


# =====================================================
# make:service
# =====================================================
@app.command("make:service")
def make_service(module: str):
    base = ensure_module(module)
    path = base / "service" / f"{to_snake(module)}_service.py"

    path.write_text(f"""
class {module}Service:

    def __init__(self):
        pass
""")

    typer.echo(f"✅ Service criado em {path}")


# =====================================================
# make:model
# =====================================================
@app.command("make:model")
def make_model(module: str, model: str):
    """
    Cria um model dentro de um módulo existente
    """

    module_snake = to_snake(module)
    model_snake = to_snake(model)

    base = ensure_module(module)
    path = base / "model" / f"{model_snake}_model.py"

    if path.exists():
        typer.echo(f"❌ Model já existe: {path}")
        raise typer.Exit(1)

    path.write_text(f"""
from sqlalchemy import Column, Integer
from app.core.base import Base


class {model}(Base):
    __tablename__ = "{model_snake}s"

    id = Column(Integer, primary_key=True)
""")

    typer.echo(f"✅ Model '{model}' criado em {path}")


# =====================================================
# make:schema
# =====================================================
@app.command("make:schema")
def make_schema(module: str):
    base = ensure_module(module)
    path = base / "schemas" / f"{to_snake(module)}_schema.py"

    path.write_text(f"""
from pydantic import BaseModel


class {module}Create(BaseModel):
    pass


class {module}Response({module}Create):
    id: int

    class Config:
        from_attributes = True
""")

    typer.echo(f"✅ Schema criado em {path}")


# =====================================================
# make:router
# =====================================================
@app.command("make:router")
def make_router(module: str):
    base = ensure_module(module)
    path = base / "router.py"

    path.write_text(f"""
from fastapi import APIRouter

router = APIRouter(
    prefix="/{to_snake(module)}",
    tags=["{module}"]
)
""")

    typer.echo(f"✅ Router criado em {path}")


# =====================================================
# make:crud
# =====================================================
@app.command("make:crud")
def make_crud(
    module: str,
    entity: str,
    from_model: bool = typer.Option(False, "--from-model"),
    controller: str = typer.Option(None, "--controller"),
    readonly: bool = typer.Option(False, "--readonly"),
    no_delete: bool = typer.Option(False, "--no-delete"),
):
    """
    Gera um CRUD completo para uma entidade dentro de um módulo
    """

    module_snake = to_snake(module)
    entity_snake = to_snake(entity)

    module_path = ensure_module(module)

    model_path = module_path / "model" / f"{entity_snake}_model.py"
    schema_path = module_path / "schemas" / f"{entity_snake}_schema.py"
    service_path = module_path / "service" / f"{entity_snake}_service.py"

    # -------------------------------------
    # CONTROLLER RESOLUTION (CORRIGIDO)
    # -------------------------------------
    controller_name = controller or entity
    controller_snake = to_snake(controller_name)
    controller_path = module_path / "controller" / f"{controller_snake}_controller.py"

    router_path = module_path / "router.py"

    # -------------------------------------
    # VALIDATIONS
    # -------------------------------------
    if not from_model and model_path.exists():
        typer.echo("❌ Model já existe. Use --from-model se quiser reutilizar.")
        raise typer.Exit(1)

    for path in [schema_path, service_path]:
        if path.exists():
            typer.echo(f"❌ Arquivo já existe: {path}")
            raise typer.Exit(1)

    # -------------------------------------
    # CREATE CONTROLLER IF NOT EXISTS ✅
    # -------------------------------------
    if not controller_path.exists():
        controller_path.write_text(f"""
from app.shared.controller import BaseController
from app.modules.{module_snake}.service.{entity_snake}_service import {entity}Service


class {controller_name}Controller(BaseController):

    def __init__(self):
        self.service = {entity}Service()
""")
        typer.echo(f"ℹ Controller '{controller_name}Controller' criado automaticamente")

    # -------------------------------------
    # MODEL
    # -------------------------------------
    if not from_model:
        model_path.write_text(f"""
from sqlalchemy import Column, Integer, String
from app.core.base import Base


class {entity}(Base):
    __tablename__ = "{entity_snake}s"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
""")

    # -------------------------------------
    # SCHEMA
    # -------------------------------------
    schema_path.write_text(f"""
from pydantic import BaseModel


class {entity}Base(BaseModel):
    name: str


class {entity}Create({entity}Base):
    pass


class {entity}Update({entity}Base):
    pass


class {entity}Response({entity}Base):
    id: int

    class Config:
        from_attributes = True
""")

    # -------------------------------------
    # SERVICE
    # -------------------------------------
    service_path.write_text(f"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.{module_snake}.model.{entity_snake}_model import {entity}


class {entity}Service:

    def __init__(self):
        pass

    async def list(self, db: AsyncSession):
        result = await db.execute(select({entity}))
        return result.scalars().all()

    async def get(self, db: AsyncSession, entity_id: int):
        result = await db.execute(
            select({entity}).where({entity}.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: dict):
        record = {entity}(**data)
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record

    async def update(self, db: AsyncSession, entity_id: int, data: dict):
        record = await self.get(db, entity_id)
        if not record:
            return None

        for key, value in data.items():
            setattr(record, key, value)

        await db.commit()
        await db.refresh(record)
        return record

    async def delete(self, db: AsyncSession, entity_id: int):
        record = await self.get(db, entity_id)
        if not record:
            return None

        await db.delete(record)
        await db.commit()
        return record
""")

    # -------------------------------------
    # CONTROLLER METHODS (APPEND)
    # -------------------------------------
    controller_code = f"""
    async def list_{entity_snake}s(self, db):
        return await self.service.list(db)

    async def get_{entity_snake}(self, db, entity_id: int):
        return await self.service.get(db, entity_id)

    async def create_{entity_snake}(self, db, data):
        return await self.service.create(db, data.dict())

    async def update_{entity_snake}(self, db, entity_id: int, data):
        return await self.service.update(db, entity_id, data.dict())
"""

    if not readonly:
        controller_code += f"""
    async def delete_{entity_snake}(self, db, entity_id: int):
        return await self.service.delete(db, entity_id)
"""

    with open(controller_path, "a", encoding="utf-8") as f:
        f.write(controller_code)

    # -------------------------------------
    # ROUTER
    # -------------------------------------
    with open(router_path, "a", encoding="utf-8") as f:
        f.write(f"""

# {entity} CRUD
@router.get("/{entity_snake}s")
async def list_{entity_snake}s(db=Depends(get_db)):
    return await controller.list_{entity_snake}s(db)

@router.get("/{entity_snake}s/{{entity_id}}")
async def get_{entity_snake}(entity_id: int, db=Depends(get_db)):
    return await controller.get_{entity_snake}(db, entity_id)

@router.post("/{entity_snake}s")
async def create_{entity_snake}(data: {entity}Create, db=Depends(get_db)):
    return await controller.create_{entity_snake}(db, data)

@router.put("/{entity_snake}s/{{entity_id}}")
async def update_{entity_snake}(entity_id: int, data: {entity}Update, db=Depends(get_db)):
    return await controller.update_{entity_snake}(db, entity_id, data)
""")

        if not readonly and not no_delete:
            f.write(f"""
@router.delete("/{entity_snake}s/{{entity_id}}")
async def delete_{entity_snake}(entity_id: int, db=Depends(get_db)):
    return await controller.delete_{entity_snake}(db, entity_id)
""")

    typer.echo(f"✅ CRUD '{entity}' criado no módulo '{module}'")


@app.command("make:job")
def make_job(group: str, name: str):
    """
    Cria um job Celery padronizado e registra no app/jobs/__init__.py
    """

    jobs_base = Path("app/jobs")
    group_snake = to_snake(group)
    job_snake = to_snake(name)

    jobs_base.mkdir(parents=True, exist_ok=True)

    # registry principal
    main_init = jobs_base / "__init__.py"
    if not main_init.exists():
        main_init.write_text("# jobs registry (auto-generated)\n")

    # pasta do grupo
    group_path = jobs_base / group_snake
    group_path.mkdir(parents=True, exist_ok=True)

    # opcional, mas ok manter
    (group_path / "__init__.py").touch(exist_ok=True)

    # arquivo do job
    job_path = group_path / f"{job_snake}.py"
    if job_path.exists():
        typer.echo(f"❌ Job já existe: {job_path}")
        raise typer.Exit(1)

    job_path.write_text(f'''
from app.core.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(
    name="jobs.{group_snake}.{job_snake}",
    autoretry_for=(Exception,),
    retry_kwargs={{"max_retries": 3, "countdown": 10}},
)
def {job_snake}(*args, **kwargs):
    logger.info("🚀 Job {name} iniciado", extra={{
        "args": args,
        "kwargs": kwargs
    }})

    # TODO: implementar lógica do job

    logger.info("✅ Job {name} finalizado")
'''.lstrip())

    # registra import no app/jobs/__init__.py
    import_line = f"\nimport app.jobs.{group_snake}.{job_snake}"
    current = main_init.read_text(encoding="utf-8")

    if import_line not in current:
        with open(main_init, "a", encoding="utf-8") as f:
            f.write(import_line)

    typer.echo(f"✅ Job '{name}' criado em {job_path} e registrado em app/jobs/__init__.py")



# =====================================================
# Database
# =====================================================
@app.command("make:migration")
def make_migration(message: str):
    subprocess.run(["alembic", "revision", "--autogenerate", "-m", message])


@app.command("db:migrate")
def db_migrate():
    subprocess.run(["alembic", "upgrade", "head"])


@app.command("db:rollback")
def db_rollback():
    subprocess.run(["alembic", "downgrade", "-1"])


# =====================================================
# App
# =====================================================
@app.command("app:run")
def app_run():
    subprocess.run([
        "uvicorn",
        "app.main:app",
        "--reload"
    ])
