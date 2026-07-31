# pyright: strict, reportUntypedFunctionDecorator=false
import os

from invoke.context import Context
from invoke.tasks import task  # pyright: ignore [reportUnknownVariableType]

use_pty = not os.getenv("CI", "")


@task(optional=["args"], help={"args": "pytest additional arguments"})
def test(ctx: Context, args: str = ""):
    """run tests (without coverage)"""
    ctx.run(f"pytest {args}", pty=use_pty)


@task(optional=["args"], help={"args": "pytest additional arguments"})
def test_cov(ctx: Context, args: str = ""):
    """run test vith coverage"""
    ctx.run(f"coverage run -m pytest {args}", pty=use_pty)


@task(optional=["html"], help={"html": "flag to export html report"})
def report_cov(ctx: Context, *, html: bool = False):
    """report coverage"""
    ctx.run("coverage combine", warn=True, pty=use_pty)
    ctx.run("coverage report --show-missing", pty=use_pty)
    ctx.run("coverage xml", pty=use_pty)
    if html:
        ctx.run("coverage html", pty=use_pty)


@task(
    optional=["args", "html"],
    help={
        "args": "pytest additional arguments",
        "html": "flag to export html report",
    },
)
def coverage(ctx: Context, args: str = "", *, html: bool = False):
    """run tests and report coverage"""
    test_cov(ctx, args=args)
    report_cov(ctx, html=html)


def _lint(ctx: Context, args: str = "."):
    args = args or "."  # needed for hatch script
    ctx.run("ruff --version", pty=use_pty)
    ctx.run(f"ruff check {args}", pty=use_pty)


@task(optional=["args"], help={"args": "ruff additional arguments"})
def check_lint(ctx: Context, args: str = "."):
    """check linting with ruff"""
    args = args or "."  # needed for hatch script
    _lint(ctx, args)


@task(optional=["args"], help={"args": "ruff additional arguments"})
def fix_lint(ctx: Context, args: str = "."):
    """fix linting issues with ruff"""
    args = args or "."  # needed for hatch script
    _lint(ctx, f"--fix {args}")


@task(optional=["args"], help={"args": "check tools (pyright) additional arguments"})
def check_type(ctx: Context, args: str = ""):
    """check static types with pyright"""
    ctx.run("pyright --version")
    ctx.run(f"pyright {args}", pty=use_pty)


def _format(ctx: Context, args: str = "."):
    args = args or "."  # needed for hatch script
    ctx.run("ruff --version", pty=use_pty)
    ctx.run(f"ruff format {args}", pty=use_pty)


@task(optional=["args"], help={"args": "ruff additional arguments"})
def check_format(ctx: Context, args: str = "."):
    """check formatting with ruff"""
    args = args or "."  # needed for hatch script
    _format(ctx, f"--check {args}")


@task(optional=["args"], help={"args": "ruff additional arguments"})
def fix_format(ctx: Context, args: str = "."):
    """fix formatting with ruff"""
    args = args or "."  # needed for hatch script
    _format(ctx, args)


@task(optional=["args"], help={"args": "additional arguments"})
def check_all(ctx: Context, args: str = ""):
    """check linting, formatting and static types"""
    args = args or "."  # needed for hatch script
    check_lint(ctx, args)
    check_format(ctx, args)
    check_type(ctx, args)


@task(optional=["args"], help={"args": "additional arguments"})
def fix_all(ctx: Context, args: str = ""):
    """Fix everything automatically"""
    args = args or "."  # needed for hatch script
    fix_lint(ctx, args)
    fix_format(ctx, args)
