"""
Carga el plan de estudios (materias + correlativas) desde un archivo JSON.

El JSON reproduce exactamente la estructura de columnas del Excel original
(nivel, id, nombre, modalidad, regulares, aprobadas), por lo que agregar,
quitar o modificar materias del plan NO requiere tocar código: solo el
archivo data/plan_estudios.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from core.models import DefinicionMateria

PLAN_PATH = Path(__file__).resolve().parent.parent / "data" / "plan_estudios.json"


class PlanEstudiosError(Exception):
    """Error al leer o interpretar el plan de estudios."""


def cargar_plan(ruta: Path = PLAN_PATH) -> List[DefinicionMateria]:
    if not ruta.exists():
        raise PlanEstudiosError(f"No se encontró el archivo del plan de estudios: {ruta}")

    try:
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PlanEstudiosError(f"El plan de estudios tiene un formato inválido: {exc}") from exc

    materias_raw = contenido.get("materias", [])
    if not materias_raw:
        raise PlanEstudiosError("El plan de estudios no contiene materias.")

    definiciones: List[DefinicionMateria] = []
    ids_vistos = set()

    for fila in materias_raw:
        try:
            materia_id = int(fila["id"])
            nivel = int(fila["nivel"])
            nombre = str(fila["nombre"]).strip()
            modalidad = str(fila.get("modalidad", "")).strip()
            regulares = [int(x) for x in fila.get("regulares", [])]
            aprobadas = [int(x) for x in fila.get("aprobadas", [])]
            categoria = str(fila.get("categoria", "Obligatoria")).strip() or "Obligatoria"
            creditos_raw = fila.get("creditos")
            creditos = float(creditos_raw) if creditos_raw is not None else None
        except (KeyError, ValueError, TypeError) as exc:
            raise PlanEstudiosError(f"Fila inválida en el plan de estudios: {fila}") from exc

        if materia_id in ids_vistos:
            raise PlanEstudiosError(f"ID de materia duplicado en el plan: {materia_id}")
        ids_vistos.add(materia_id)

        definiciones.append(
            DefinicionMateria(
                id=materia_id,
                nivel=nivel,
                nombre=nombre,
                modalidad=modalidad,
                regulares=regulares,
                aprobadas=aprobadas,
                categoria=categoria,
                creditos=creditos,
            )
        )

    definiciones.sort(key=lambda d: (d.nivel, d.id))
    return definiciones


def nombre_carrera(ruta: Path = PLAN_PATH) -> str:
    if not ruta.exists():
        return "Gestor de Materias"
    contenido = json.loads(ruta.read_text(encoding="utf-8"))
    return contenido.get("carrera", "Gestor de Materias")
