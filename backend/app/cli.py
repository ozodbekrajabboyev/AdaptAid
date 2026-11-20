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
    from pydantic import EmailStr, TypeAdapter, ValidationError

    from app.core.db import SessionLocal
    from app.core.security import hash_password
    from app.models import User
    from app.models.base import Role

    try:  # same rule as the sign-in form, so the account can actually log in
        email = TypeAdapter(EmailStr).validate_python(email)
    except ValidationError as e:
        raise typer.BadParameter(f"{email!r} is not a usable email address.") from e
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email.lower())):
            raise typer.BadParameter("A user with that email already exists.")
        db.add(User(email=email.lower(), full_name=full_name, password_hash=hash_password(password), role=Role.admin))
        db.commit()
    typer.echo(f"Created admin {email.lower()}.")


@cli.command()
def seed(
    pack: Path = typer.Option(None, help="Content folder (default: content/dsa)"),
    force: bool = typer.Option(False, help="Seed even if validation reports errors"),
) -> None:
    """Load (or update) a content pack into the database."""
    from app.content_pack import DEFAULT_PACK, load_pack, validate
    from app.core.db import SessionLocal
    from app.services.seed import seed_pack

    p = load_pack(pack or DEFAULT_PACK)
    errors, _ = validate(p)
    if errors and not force:
        for e in errors:
            typer.echo(f"ERROR: {e}")
        typer.echo("Fix the content (see `adaptaid validate-content`) or pass --force.")
        raise typer.Exit(1)
    with SessionLocal() as db:
        r = seed_pack(db, p)
        db.commit()
    typer.echo(
        f"Seeded course {p.code}: {r.concepts} concepts, {r.aids} aids, {r.questions} questions "
        f"({r.deactivated_aids} aids and {r.deactivated_questions} questions archived)."
    )


@cli.command("validate-content")
def validate_content(
    pack: Path = typer.Option(None, help="Content folder (default: content/dsa)"),
    concept: list[str] = typer.Option(None, "--concept", help="Only check these concept slugs"),
) -> None:
    """Check a content pack: schema, coverage rules, question pools, study-item leaks."""
    from app.content_pack import DEFAULT_PACK, load_pack, validate

    p = load_pack(pack or DEFAULT_PACK)
    errors, warnings = validate(p, set(concept) if concept else None)
    for w in warnings:
        typer.echo(f"warning: {w}")
    for e in errors:
        typer.echo(f"ERROR: {e}")
    counts = {pool: sum(1 for q in p.questions if q.pool == pool) for pool in ("diagnostic", "check", "drill", "study")}
    typer.echo(f"{len(p.concepts)} concepts, {len(p.aids)} aids, {len(p.questions)} questions {counts}")
    if errors:
        raise typer.Exit(1)
    typer.echo("Content is valid.")


@cli.command("check-links")
def check_links(
    pack: Path = typer.Option(None, help="Content folder (default: content/dsa)"),
    concept: list[str] = typer.Option(None, "--concept", help="Only check these concept slugs"),
) -> None:
    """Open every external aid URL (YouTube through oEmbed) and report broken ones."""
    from app.content_pack import DEFAULT_PACK, check_url, load_pack

    p = load_pack(pack or DEFAULT_PACK)
    bad = 0
    for a in p.aids:
        if a.delivery != "external_url" or (concept and a.concept not in concept):
            continue
        ok, info = check_url(a.url or "")
        bad += 0 if ok else 1
        typer.echo(f"{'ok  ' if ok else 'FAIL'} {a.slug:32} {a.url}  {info}")
    if bad:
        typer.echo(f"{bad} broken link(s)")
        raise typer.Exit(1)
    typer.echo("All links work.")


@cli.command("run-job")
def run_job_cmd(
    kind: str = typer.Argument("all", help="personas | risk | aid_stats | cf | bkt | all"),
    force: bool = typer.Option(True, help="Run even if a scheduled run already succeeded today"),
) -> None:
    """Run background jobs now and print their results."""
    from app.core.db import SessionLocal
    from app.jobs.runner import run_all, run_job
    from app.models import ModelRun

    ids = run_all("cli", force) if kind == "all" else {kind: run_job(kind, "cli", force)}
    with SessionLocal() as db:
        for k, run_id in ids.items():
            run = db.get(ModelRun, run_id) if run_id else None
            if run is None:
                typer.echo(f"{k:10} skipped")
                continue
            summary = {key: v for key, v in (run.metrics or {}).items() if key not in ("centroids", "concepts", "names")}
            typer.echo(f"{k:10} {run.status.value:8} {summary}")
            if run.notes:
                typer.echo(run.notes[:400])


@cli.command("seed-demo")
def seed_demo_cmd(
    students: int = typer.Option(60, help="Number of synthetic students"),
    days: int = typer.Option(28, help="Days of simulated activity"),
    seed: int = typer.Option(2026),
    password: str = typer.Option("demo-pass-2026", help="Password for the demo accounts"),
) -> None:
    """Create a demo class and simulate weeks of activity through the real services."""
    from app.demo import DemoExists, seed_demo

    typer.echo(f"Simulating {days} days for {students} students (this takes a few minutes)...")
    try:
        r = seed_demo(students, days, seed, password, progress=typer.echo)
    except DemoExists as e:
        raise typer.BadParameter(str(e)) from e
    typer.echo(f"Done: {r['students']} synthetic students, {r['sessions']} study sessions.")
    typer.echo(f"Demo accounts (password {r['password']!r}): {', '.join(r['accounts'])}")
    typer.echo(f"Class join code: {r['class_code']}")


@cli.command("reset-demo")
def reset_demo_cmd(force: bool = typer.Option(False, "--force", help="Required: deletes demo data")) -> None:
    """Remove demo accounts, synthetic students, model runs and aid statistics (content is kept)."""
    if not force:
        raise typer.BadParameter("Pass --force to confirm.")
    if get_settings().app_env == "prod":
        raise typer.BadParameter("reset-demo is disabled when APP_ENV=prod.")
    from app.core.db import SessionLocal
    from app.demo import reset_demo

    with SessionLocal() as db:
        n = reset_demo(db)
    typer.echo(f"Removed {n} demo users and all model runs.")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
