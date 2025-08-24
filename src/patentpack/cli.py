from __future__ import annotations

from typing import Optional

import typer

from .client import PatentPack
from .core.contracts import Provider

app = typer.Typer(help="patentpack: unified CLI for USPTO/EPO providers")


@app.command("count-cpc-year")
def count_cpc_year(
    year: int = typer.Argument(..., help="Calendar year (e.g., 2021)"),
    cpc: str = typer.Option("Y02", help="CPC prefix (e.g., Y02)"),
    provider: Provider = typer.Option(
        Provider.USPTO, "--provider", case_sensitive=False, help="Data source"
    ),
    utility_only: bool = typer.Option(
        False, help="Restrict to utility patents, if supported by provider"
    ),
    rpm: int = typer.Option(30, help="Requests per minute pacing"),
    debug: bool = typer.Option(False, help="Verbose provider diagnostics"),
):
    """Return total count for CPC prefix in a given year."""
    kwargs = {"rpm": rpm}
    if debug:
        kwargs["debug"] = True
    pp = PatentPack(provider, **kwargs)
    res = pp.count_cpc_year(year=year, cpc=cpc, utility_only=utility_only)
    typer.echo(res.total)
    return None


@app.command("count-cpc-company-year")
def count_cpc_company_year(
    company: str = typer.Argument(
        ..., help="Assignee/Applicant name (exact string)"
    ),
    year: int = typer.Option(..., help="Calendar year (e.g., 2021)"),
    cpc: str = typer.Option("Y02", help="CPC prefix (e.g., Y02)"),
    which: str = typer.Option(
        "cpc_current", help="Provider-specific CPC scope (e.g., cpc_current)"
    ),
    provider: Provider = typer.Option(
        Provider.USPTO, "--provider", case_sensitive=False, help="Data source"
    ),
    utility_only: bool = typer.Option(
        False, help="Restrict to utility patents, if supported"
    ),
    rpm: int = typer.Option(30, help="Requests per minute pacing"),
    debug: bool = typer.Option(False, help="Verbose provider diagnostics"),
    epo_key: Optional[str] = typer.Option(None, help="EPO OPS key"),
    epo_secret: Optional[str] = typer.Option(None, help="EPO OPS secret"),
):
    kwargs = {"rpm": rpm}
    if provider == Provider.EPO:
        if epo_key is not None:
            kwargs["key"] = epo_key
        if epo_secret is not None:
            kwargs["secret"] = epo_secret
    if debug:
        kwargs["debug"] = True
    pp = PatentPack(provider, **kwargs)
    res = pp.count_cpc_company_year(
        year=year,
        cpc=cpc,
        company=company,
        which=which,
        utility_only=utility_only,
    )
    typer.echo(res.total)
    return None


@app.command("assignee-discover")
def assignee_discover(
    prefix: str = typer.Argument(
        ..., help="Organization prefix (e.g., 'BASF')"
    ),
    provider: Provider = typer.Option(
        Provider.USPTO, "--provider", case_sensitive=False, help="Data source"
    ),
    limit: int = typer.Option(400, help="Max candidates to return"),
    rpm: int = typer.Option(30, help="Requests per minute pacing"),
):
    """List assignees whose organization begins with the given prefix."""
    pp = PatentPack(provider, rpm=rpm)
    res = pp.assignee_discover(prefix=prefix, limit=limit)
    for a in res.items:
        loc = " / ".join(x for x in [a.country, a.state, a.city] if x)
        typer.echo(f"{a.organization}\t{loc}")


def main() -> None:
    app()


if __name__ == "__main__":
    app()
