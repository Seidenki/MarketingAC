import typer
from rich.console import Console
from rich.table import Table
from marketintel.collector import recolectar
from marketintel.exporter import exportar

app = typer.Typer(
    name="marketintel",
    help="CLI de inteligencia de mercado local — powered by SerpAPI",
    no_args_is_help=True,
)

console = Console()


@app.callback()
def callback():
    """marketintel — inteligencia de mercado local."""


@app.command()
def search(
    query: str = typer.Option("agencia de marketing", "--query", "-q", help="Qué buscar"),
    ciudad: str = typer.Option("Bucaramanga", "--ciudad", "-c", help="Ciudad de búsqueda"),
    latitud: float = typer.Option(7.11967, "--lat", help="Latitud del centro de búsqueda"),
    longitud: float = typer.Option(-73.11254, "--lng", help="Longitud del centro de búsqueda"),
    formato: str = typer.Option("json", "--formato", "-f", help="Formato de salida: json o csv"),
    nombre: str = typer.Option("resultados", "--nombre", "-n", help="Nombre del archivo de salida"),
):
    """Busca agencias o negocios en Google Maps y guarda los resultados."""

    console.print(f"\n[bold blue]🔍 Buscando:[/bold blue] {query} en {ciudad}")

    with console.status("[bold green]Consultando SerpAPI..."):
        resultados = recolectar(query, ciudad, latitud, longitud)

    if not resultados:
        console.print("[bold red]No se encontraron resultados.[/bold red]")
        raise typer.Exit(1)

    tabla = Table(title=f"Resultados — {ciudad}", show_lines=True)
    tabla.add_column("#", style="dim", width=3)
    tabla.add_column("Nombre", style="bold")
    tabla.add_column("Rating", justify="center")
    tabla.add_column("Reseñas", justify="center")
    tabla.add_column("Tipos")

    for i, r in enumerate(resultados, 1):
        tabla.add_row(
            str(i),
            r.get("nombre") or "—",
            str(r.get("rating") or "—"),
            str(r.get("reseñas") or "—"),
            ", ".join(r.get("tipos", [])[:2]),
        )

    console.print(tabla)

    ruta = exportar(resultados, nombre, formato)
    console.print(f"\n[bold green]✓ Guardado en:[/bold green] {ruta}\n")


if __name__ == "__main__":
    app()