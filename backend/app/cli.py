"""AdaptAid command line: `python -m app.cli --help` (or the `adaptaid` script)."""

from pathlib import Path

import typer
from sqlalchemy import select, text
from sqlalchemy.engine import make_url

from app.core.config import get_settings

cli = typer.Typer(help="AdaptAid administration commands.", no_args_is_help=True, add_completion=False)
BACKEND_DIR = Path(__file__).resolve().parents[1]


def _migrate(url: str) -> None:
    from alembic.config import Config

    from alembic import command

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["database_url"] = url
    command.upgrade(cfg, "head")


@cli.command()
def migrate() -> None:
    """Apply all database migrations."""
    _migrate(get_settings().database_url)
    typer.echo("Database is up to date.")


@cli.command("reset-db")
def reset_db(
    force: bool = typer.Option(False, "--force", help="Required. Deletes every row in the database."),
) -> None:
    """Drop and recreate the schema. Refuses to run in production."""
    settings = get_settings()
    if not force:
        raise typer.BadParameter("Pass --force to confirm. This deletes all data.")
    if settings.app_env == "prod":
        raise typer.BadParameter("reset-db is disabled when APP_ENV=prod.")
    from app.core.db import engine

    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    _migrate(settings.database_url)
    typer.echo(f"Reset database {make_url(settings.database_url).database}.")


@cli.command("create-admin")
def create_admin(
    email: str = typer.Option(..., prompt=True),
    full_name: str = typer.Option("Administrator", prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
) -> None:
    """Create an administrator account (admins cannot self-register)."""
    from app.core.db import SessionLocal
    from app.core.security import hash_password
    from app.models import User
    from app.models.base import Role

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email.lower())):
            raise typer.BadParameter("A user with that email already exists.")
        db.add(User(email=email.lower(), full_name=full_name, password_hash=hash_password(password), role=Role.admin))
        db.commit()
    typer.echo(f"Created admin {email.lower()}.")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
