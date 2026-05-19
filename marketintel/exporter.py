import json
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def guardar_json(datos: list[dict], nombre_archivo: str) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    ruta = DATA_DIR / f"{nombre_archivo}.json"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    return ruta


def guardar_csv(datos: list[dict], nombre_archivo: str) -> Path:
    DATA_DIR.mkdir(exist_ok=True)
    ruta = DATA_DIR / f"{nombre_archivo}.csv"
    df = pd.DataFrame(datos)
    df["tipos"] = df["tipos"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)
    df["horario"] = df["horario"].apply(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, dict) else x)
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
    return ruta


def exportar(datos: list[dict], nombre_archivo: str, formato: str = "json") -> Path:
    if formato == "json":
        return guardar_json(datos, nombre_archivo)
    elif formato == "csv":
        return guardar_csv(datos, nombre_archivo)
    else:
        raise ValueError(f"Formato no soportado: {formato}. Usa 'json' o 'csv'.")