import typer
import subprocess
from pathlib import Path

app = typer.Typer(help="SmartQA CLI")

BASE_MODULES = Path("app/modules")

# Helpers
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

# Comandos API
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


@app.command("make:controller")
def make_controller(module: str):
    base = ensure_module(module)
    path = base / "controller" / f"{to_snake(module)}_controller.py"

    path.write_text(f"""
class {module}Controller:
    pass
""")

    typer.echo(f"✅ Controller criado em {path}")


@app.command("make:service")
def make_service(module: str):
    base = ensure_module(module)
    path = base / "service" / f"{to_snake(module)}_service.py"

    path.write_text(f"""
class {module}Service:
    pass
""")

    typer.echo(f"✅ Service criado em {path}")


@app.command("make:model")
def make_model(module: str):
    base = ensure_module(module)
    path = base / "model" / f"{to_snake(module)}_model.py"

    path.write_text(f"""
from sqlalchemy import Column, Integer
from app.core.base import Base

class {module}(Base):
    __tablename__ = "{to_snake(module)}s"

    id = Column(Integer, primary_key=True)
""")

    typer.echo(f"✅ Model criado em {path}")


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



# Database
@app.command("make:migration")
def make_migration(message: str):
    subprocess.run(["alembic", "revision", "--autogenerate", "-m", message])

@app.command("db:migrate")
def db_migrate():
    subprocess.run(["alembic", "upgrade", "head"])

@app.command("db:rollback")
def db_rollback():
    subprocess.run(["alembic", "downgrade", "-1"])


@app.command("app:run")
def app_run():
    subprocess.run([
        "uvicorn",
        "app.main:app",
        "--reload"
    ])

