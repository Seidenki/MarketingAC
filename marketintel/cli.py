import json
import unicodedata
import typer
from pathlib import Path
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


def cargar_config() -> dict:
    ruta = Path(__file__).parent / "config.json"
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)

def bayesian_score(rating: float, reviews: int, mean_rating: float, C: int = 13) -> float:
    if not rating or not reviews:
        return 0.0
    return (C * mean_rating + reviews * rating) / (C + reviews)

def normalizar_ciudad(ciudad: str, ciudades: dict) -> dict | None:
    ciudad_norm = unicodedata.normalize("NFD", ciudad)
    ciudad_norm = "".join(c for c in ciudad_norm if unicodedata.category(c) != "Mn")
    ciudad_norm = ciudad_norm.lower().strip()
    return ciudades.get(ciudad_norm)


@app.callback()
def callback():
    """marketintel — inteligencia de mercado local."""


@app.command()
def search(
    query: str = typer.Option(None, "--query", "-q", help="Qué buscar"),
    ciudad: str = typer.Option(None, "--ciudad", "-c", help="Ciudad de búsqueda"),
    formato: str = typer.Option(None, "--formato", "-f", help="Formato de salida: json o csv"),
    nombre: str = typer.Option(None, "--nombre", "-n", help="Nombre del archivo de salida"),
):
    """Busca agencias o negocios en Google Maps y guarda los resultados."""

    config = cargar_config()
    defaults = config["defaults"]
    ciudades = config["ciudades"]

    query = query or defaults["query"]
    ciudad_input = ciudad or defaults["ciudad"]
    formato = formato or defaults["formato"]
    nombre = nombre or defaults["nombre_archivo"]

    datos_ciudad = normalizar_ciudad(ciudad_input, ciudades)

    if not datos_ciudad:
        console.print(f"[bold red]Ciudad '{ciudad_input}' no encontrada.[/bold red]")
        console.print(f"Ciudades disponibles: {', '.join(ciudades.keys())}")
        raise typer.Exit(1)

    lat = datos_ciudad["lat"]
    lng = datos_ciudad["lng"]

    console.print(f"\n[bold blue]🔍 Buscando:[/bold blue] {query} en {ciudad_input}")

    with console.status("[bold green]Consultando SerpAPI..."):
        resultados = recolectar(query, ciudad_input, lat, lng)

    if not resultados:
        console.print("[bold red]No se encontraron resultados.[/bold red]")
        raise typer.Exit(1)
    
    # calcular media global
    ratings_validos = [r for r in resultados if r.get("rating") and r.get("reseñas")]
    mean_rating = sum(r["rating"] for r in ratings_validos) / len(ratings_validos) if ratings_validos else 4.0

    # ordenar por bayesian score
    resultados = sorted(
        resultados,
        key=lambda r: bayesian_score(r.get("rating", 0), r.get("reseñas", 0), mean_rating),
        reverse=True
    )

    tabla = Table(title=f"Resultados — {ciudad_input}", show_lines=True)
    tabla.add_column("#", style="dim", width=3)
    tabla.add_column("Nombre", style="bold")
    tabla.add_column("Rating", justify="center")
    tabla.add_column("Reseñas", justify="center")
    tabla.add_column("Tipos")
    tabla.add_column("Score", justify="center", style="cyan")

    for i, r in enumerate(resultados, 1):
        score = bayesian_score(r.get("rating", 0), r.get("reseñas", 0), mean_rating)
        tabla.add_row(
        str(i),
        r.get("nombre") or "—",
        str(r.get("rating") or "—"),
        str(r.get("reseñas") or "—"),
        ", ".join(r.get("tipos", [])[:2]),
        f"{score:.2f}",
        )
        

    console.print(tabla)

    ruta = exportar(resultados, nombre, formato)
    console.print(f"\n[bold green]✓ Guardado en:[/bold green] {ruta}\n")


if __name__ == "__main__":
    app()