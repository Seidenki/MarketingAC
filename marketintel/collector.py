import os
import requests
from dotenv import load_dotenv

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SERPAPI_URL = "https://serpapi.com/search.json"


def buscar_agencias(query: str, ciudad: str, latitud: float, longitud: float, zoom: int = 14) -> list[dict]:
    """
    Busca negocios en Google Maps via SerpAPI.
    Retorna lista de resultados crudos.
    """
    params = {
        "engine": "google_maps",
        "q": query,
        "ll": f"@{latitud},{longitud},{zoom}z",
        "hl": "es",
        "api_key": SERPAPI_KEY,
    }

    response = requests.get(SERPAPI_URL, params=params)
    response.raise_for_status()

    data = response.json()
    resultados = data.get("local_results", [])

    print(f"✓ {len(resultados)} resultados encontrados para '{query}' en {ciudad}")
    return resultados


def extraer_campos(resultado: dict) -> dict:
    """
    Extrae solo los campos relevantes de un resultado crudo de SerpAPI.
    """
    return {
        "nombre": resultado.get("title"),
        "rating": resultado.get("rating"),
        "reseñas": resultado.get("reviews"),
        "tipos": resultado.get("types", []),
        "direccion": resultado.get("address"),
        "telefono": resultado.get("phone"),
        "sitio_web": resultado.get("website"),
        "horario": resultado.get("operating_hours", {}),
        "place_id": resultado.get("place_id"),
        "data_id": resultado.get("data_id"),
        "reviews_link": resultado.get("reviews_link"),
        "latitud": resultado.get("gps_coordinates", {}).get("latitude"),
        "longitud": resultado.get("gps_coordinates", {}).get("longitude"),
    }


def recolectar(query: str, ciudad: str, latitud: float, longitud: float) -> list[dict]:
    """
    Función principal — busca y limpia los resultados.
    """
    crudos = buscar_agencias(query, ciudad, latitud, longitud)
    return [extraer_campos(r) for r in crudos]