import json
import math
import unicodedata
import requests
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from marketintel.collector import recolectar
from marketintel.exporter import exportar
import time

app = typer.Typer(
    name="marketintel",
    help="CLI de inteligencia de mercado local — powered by SerpAPI",
    no_args_is_help=True,
)

console = Console()

KEYWORDS_SEO = ["⭐", "mejor", "número 1", "#1", "top", "bogotá", "medellín", "cali",
                "barranquilla", "cartagena", "bucaramanga", "pereira", "manizales",
                "santa marta", "cúcuta", "cucuta", "digital", "seo", "marketing"]

SIMILARWEB_URL = "https://data.similarweb.com/api/v1/data"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


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


def penalizacion_nombre(nombre: str) -> float:
    nombre_norm = unicodedata.normalize("NFD", nombre.lower())
    nombre_norm = "".join(c for c in nombre_norm if unicodedata.category(c) != "Mn")
    hits = sum(1 for k in KEYWORDS_SEO if k.lower() in nombre_norm)
    return max(0.7, 1.0 - (hits * 0.05))


def verificar_web(url: str) -> float:
    if not url:
        return 0.5
    try:
        r = requests.get(url, timeout=5, allow_redirects=True, headers=HEADERS)
        return 1.0 if r.status_code in (200, 403) else 0.7
    except Exception:
        return 0.6


def obtener_dominio(url: str) -> str | None:
    if not url:
        return None
    url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    return url.split("/")[0]



def obtener_trafico(url: str) -> int:
    dominio = obtener_dominio(url)
    if not dominio:
        return 0
    try:
        time.sleep(6)
        r = requests.get(SIMILARWEB_URL, params={"domain": dominio}, timeout=8, headers=HEADERS)
        data = r.json()
        visitas = data.get("EstimatedMonthlyVisits", {})
        return sum(visitas.values())
    except Exception:
        return 0


def normalizar_trafico(resultados: list[dict]) -> list[dict]:
    valores = [r.get("_trafico", 0) for r in resultados]
    t_min = min(valores)
    t_max = max(valores)
    for r in resultados:
        if t_max == t_min:
            r["_trafico_norm"] = 0.5
        else:
            r["_trafico_norm"] = (r.get("_trafico", 0) - t_min) / (t_max - t_min)
    return resultados


def calcular_score_final(bayesian: float, web: float, nombre_factor: float, trafico_norm: float) -> float:
    return (
        0.40 * (bayesian / 5.0) +
        0.35 * trafico_norm +
        0.15 * web +
        0.10 * nombre_factor
    )


@app.callback()
def callback():
    """marketintel — inteligencia de mercado local."""


@app.command()
def search(
    query: str = typer.Option(None, "--query", "-q", help="Qué buscar"),
    ciudad: str = typer.Option(None, "--ciudad", "-c", help="Ciudad de búsqueda"),
    formato: str = typer.Option(None, "--formato", "-f", help="Formato de salida: json, csv o excel"),
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

    # media global para bayesian
    ratings_validos = [r for r in resultados if r.get("rating") and r.get("reseñas")]
    mean_rating = sum(r["rating"] for r in ratings_validos) / len(ratings_validos) if ratings_validos else 4.0

    # verificar webs y obtener tráfico
    console.print("[bold yellow]⏳ Verificando sitios web y consultando tráfico...[/bold yellow]")
    for r in resultados:
        r["_web_score"] = verificar_web(r.get("sitio_web"))
        r["_nombre_factor"] = penalizacion_nombre(r.get("nombre", ""))
        r["_bayesian"] = bayesian_score(r.get("rating", 0), r.get("reseñas", 0), mean_rating)
        r["_trafico"] = obtener_trafico(r.get("sitio_web"))

    # normalizar tráfico relativo al grupo
    resultados = normalizar_trafico(resultados)

    # calcular score final
    for r in resultados:
        r["_score_final"] = calcular_score_final(
            r["_bayesian"],
            r["_web_score"],
            r["_nombre_factor"],
            r["_trafico_norm"],
        )

    # ordenar
    resultados = sorted(resultados, key=lambda r: r["_score_final"], reverse=True)

    tabla = Table(title=f"Resultados — {ciudad_input}", show_lines=True)
    tabla.add_column("#", style="dim", width=3)
    tabla.add_column("Nombre", style="bold")
    tabla.add_column("Rating", justify="center")
    tabla.add_column("Reseñas", justify="center")
    tabla.add_column("Web", justify="center")
    tabla.add_column("Tráfico", justify="center", style="yellow")
    tabla.add_column("Tipos")
    tabla.add_column("Score", justify="center", style="cyan")

    for i, r in enumerate(resultados, 1):
        web_status = "✓" if r["_web_score"] == 1.0 else ("~" if r["_web_score"] >= 0.6 else "✗")
        trafico = r.get("_trafico", 0)
        tabla.add_row(
            str(i),
            r.get("nombre") or "—",
            str(r.get("rating") or "—"),
            str(r.get("reseñas") or "—"),
            web_status,
            f"{trafico:,}",
            ", ".join(r.get("tipos", [])[:2]),
            f"{r['_score_final']:.2f}",
        )

    console.print(tabla)

    # limpiar campos internos antes de exportar
    for r in resultados:
        r["trafico_3m"] = r.pop("_trafico")
        r["score"] = round(r.pop("_score_final"), 3)
        for k in ["_web_score", "_nombre_factor", "_bayesian", "_trafico_norm"]:
            r.pop(k, None)

    ruta = exportar(resultados, nombre, formato)
    console.print(f"\n[bold green]✓ Guardado en:[/bold green] {ruta}\n")


if __name__ == "__main__":
    app()