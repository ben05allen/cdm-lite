import typer
from rich.console import Console
from rich.table import Table

from cdm_lite.cleaner import clean_schemas
from cdm_lite.downloader import DownloadError, download_schemas
from cdm_lite.generator import GenerationError, generate_models, generate_package_metadata
from cdm_lite.registry import CdmRegistry
from cdm_lite.store import CdmStore

app = typer.Typer(
    name="cdm-lite",
    help="Manage CDM Pydantic model versions generated from the FINOS CDM JSON Schema.",
    no_args_is_help=True,
)

console = Console()
store = CdmStore()
registry = CdmRegistry()


def _show_current_path(store: CdmStore) -> None:
    """Print the current models path prominently."""
    current = store.current_models_dir()
    console.print("\n[bold]Models available at:[/bold]")
    console.print(f"  [cyan]{current}[/cyan]")
    console.print("\n[dim]Add to your project:[/dim]")
    console.print(f'  [green]export PYTHONPATH="{current}:$PYTHONPATH"[/green]')
    console.print("\n[dim]Or in pyproject.toml (uv):[/dim]")
    console.print("  [green][tool.uv.sources][/green]")
    console.print(f'  [green]cdm-models = {{ path = "{current}" }}[/green]\n')


def _abort(message: str) -> None:
    """Print an error and exit with a non-zero code."""
    console.print(f"[bold red]Error:[/bold red] {message}")
    raise typer.Exit(code=1)


# ── versions ──────────────────────────────────────────────────────────────────


@app.command()
def versions(
    include_dev: bool = typer.Option(
        False, "--dev", help="Include development/pre-release versions."
    ),
):
    """List CDM versions available on Maven Central."""
    console.print("\n[bold]Fetching available CDM versions...[/bold]\n")

    try:
        all_versions = registry.all_versions(include_dev=include_dev)
        latest = registry.latest_stable()
        cached = {v.version for v in store.cached_versions()}
        current = store.current_version()
    except Exception as e:
        _abort(str(e))

    table = Table(show_header=True, header_style="bold")
    table.add_column("Version")
    table.add_column("Status")
    table.add_column("")

    for v in reversed(all_versions):
        tags = []
        if v.version in cached:
            tags.append("[green]✔ installed[/green]")
        if v == latest:
            tags.append("[dim]latest stable[/dim]")
        if not v.is_stable:
            tags.append("[yellow]dev[/yellow]")

        current_marker = "[bold cyan]← current[/bold cyan]" if v == current else ""
        table.add_row(v.version, " ".join(tags), current_marker)

    console.print(table)
    console.print(
        f"\n[dim]{len(all_versions)} versions shown. "
        f"Use --dev to include development releases.[/dim]\n"
    )


# ── list ──────────────────────────────────────────────────────────────────────


@app.command(name="list")
def list_installed():
    """List locally installed CDM versions."""
    cached = store.cached_versions()
    current = store.current_version()

    if not cached:
        console.print(
            "\n[yellow]No versions installed yet.[/yellow] "
            "Run [bold]cdm-lite install  <version>[/bold] to get started.\n"
        )
        raise typer.Exit()

    console.print("\n[bold]Installed CDM versions:[/bold]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Version")
    table.add_column("Downloaded")
    table.add_column("Cleaned")
    table.add_column("Generated")
    table.add_column("")

    for v in sorted(cached):
        try:
            s = store.status(v)
        except FileNotFoundError:
            continue

        def tick(val: bool) -> str:
            return "[green]✔[/green]" if val else "[dim]–[/dim]"

        current_marker = "[bold cyan]← current[/bold cyan]" if v == current else ""
        table.add_row(
            v.version,
            tick(s.downloaded),
            tick(s.cleaned),
            tick(s.generated),
            current_marker,
        )

    console.print(table)

    if current:
        _show_current_path(store)


# ── install ───────────────────────────────────────────────────────────────────


@app.command()
def install(
    version: str | None = typer.Argument(None, help="CDM version to install (e.g. 6.19.0)."),
    python_version: str = typer.Option(
        "3.11", "--python", help="Target Python version for generated models."
    ),
):
    """Download, clean and generate Pydantic models for a CDM version."""
    store.init()

    # Resolve version
    try:
        if version is None:
            cdm_version = registry.latest_stable()
            console.print(
                f"\n[dim]No version specified, using latest stable: "
                f"[bold]{cdm_version}[/bold][/dim]"
            )
        else:
            cdm_version = registry.get(version)
    except Exception as e:
        _abort(str(e))

    store.init_version(cdm_version)
    status = store.status(cdm_version)

    console.print(f"\n[bold]Installing CDM {cdm_version}[/bold]\n")

    # ── Step 1: Download ──────────────────────────────────────────────────────

    if status.downloaded:
        console.print("[dim]  Step 1/3: Schemas already downloaded, skipping.[/dim]")
    else:
        console.print("[bold]  Step 1/3: Downloading schemas...[/bold]")
        try:
            download_schemas(cdm_version, store.schema_raw_dir(cdm_version))
            store.mark_downloaded(cdm_version)
        except DownloadError as e:
            _abort(f"Download failed: {e}")

    # ── Step 2: Clean ─────────────────────────────────────────────────────────

    if status.cleaned:
        console.print("[dim]  Step 2/3: Schemas already cleaned, skipping.[/dim]")
    else:
        console.print("[bold]  Step 2/3: Cleaning schemas...[/bold]")
        result = clean_schemas(
            store.schema_raw_dir(cdm_version),
            store.schema_clean_dir(cdm_version),
        )
        store.mark_cleaned(cdm_version)
        console.print(f"  [dim]{result}[/dim]")

    # ── Step 3: Generate ──────────────────────────────────────────────────────

    if status.generated:
        console.print("[dim]  Step 3/3: Models already generated, skipping.[/dim]")
    else:
        console.print("[bold]  Step 3/3: Generating Pydantic models...[/bold]")
        try:
            result = generate_models(
                store.schema_clean_dir(cdm_version),
                store.models_dir(cdm_version),
                python_version=python_version,
            )
        except GenerationError as e:
            _abort(str(e))

        if not result.success:
            _abort(f"Model generation failed:\n{result.stderr}")

        store.mark_generated(cdm_version, cdm_lite_version=_get_version())

        generate_package_metadata(
            store.models_dir(cdm_version),
            cdm_version=cdm_version.version,
            python_version=python_version,
        )

        console.print(f"  [dim]{result}[/dim]")

    console.print(f"\n[bold green]✔ CDM {cdm_version} installed successfully.[/bold green]")
    console.print(
        f"\n[dim]Run [bold]cdm-lite use  {cdm_version}[/bold] "
        f"to make this the active version.[/dim]\n"
    )


# ── use ───────────────────────────────────────────────────────────────────────


@app.command()
def use(
    version: str = typer.Argument(..., help="CDM version to activate."),
):
    """Set the active CDM version and update the current/ symlink."""
    try:
        cdm_version = registry.get(version)
    except Exception as e:
        _abort(str(e))

    if not store.is_generated(cdm_version):
        _abort(
            f"CDM {version} is not fully installed. "
            f"Run [bold]cdm-lite install {version}[/bold] first."
        )

    store.set_current_version(cdm_version)
    store.update_current_symlink(cdm_version)

    console.print(f"\n[bold green]✔ Now using CDM {version}[/bold green]")
    _show_current_path(store)


# ── status ────────────────────────────────────────────────────────────────────


@app.command()
def status():
    """Show the currently active CDM version and cache location."""
    current = store.current_version()

    if current is None:
        console.print(
            "\n[yellow]No active CDM version.[/yellow] "
            "Run [bold]cdm-lite install[/bold] to get started.\n"
        )
        raise typer.Exit()

    try:
        s = store.status(current)
    except FileNotFoundError:
        _abort(f"Version {current} is set as current but not found in cache.")

    console.print("\n[bold]CDM Lite Status[/bold]\n")
    console.print(f"  Current version : [bold cyan]{current}[/bold cyan]")
    console.print(f"  Downloaded      : {'[green]✔[/green]' if s.downloaded else '[red]✘[/red]'}")
    console.print(f"  Cleaned         : {'[green]✔[/green]' if s.cleaned else '[red]✘[/red]'}")
    console.print(f"  Generated       : {'[green]✔[/green]' if s.generated else '[red]✘[/red]'}")

    if s.generated_at:
        console.print(f"  Generated at    : [dim]{s.generated_at}[/dim]")
    if s.cdm_lite_version:
        console.print(f"  Generated by    : [dim]cdm-lite {s.cdm_lite_version}[/dim]")

    _show_current_path(store)


# ── clear ─────────────────────────────────────────────────────────────────────


@app.command()
def clear(
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt."),
):
    """Clear the entire CDM cache (all versions and generated models)."""
    cache_dir = store.cache_dir

    if not cache_dir.exists():
        console.print("\n[dim]Cache is already empty.[/dim]\n")
        raise typer.Exit()

    cached = store.cached_versions()

    console.print("\n[bold yellow]⚠ Warning[/bold yellow]")
    console.print("  This will delete the entire CDM cache at:")
    console.print(f"  [cyan]{cache_dir}[/cyan]")
    console.print(f"  {len(cached)} version(s) will be removed.\n")

    if not force:
        confirmed = typer.confirm("Are you sure you want to continue?", default=False)
        if not confirmed:
            console.print("\n[dim]Aborted.[/dim]\n")
            raise typer.Exit()

    import shutil

    shutil.rmtree(cache_dir)
    console.print("\n[bold green]✔ Cache cleared.[/bold green]\n")


# ── helpers ───────────────────────────────────────────────────────────────────


def _get_version() -> str:
    """Return the installed cdm-lite version."""
    try:
        from importlib.metadata import version

        return version("cdm-lite")
    except Exception:
        return "unknown"


# ── entry point ───────────────────────────────────────────────────────────────


def main():
    app()


if __name__ == "__main__":
    main()
