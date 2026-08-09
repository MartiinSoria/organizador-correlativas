"""
Motor de correlativas.

Este módulo NO conoce reglas particulares de ninguna materia puntual.
Toma, de forma completamente genérica, las listas de IDs "regulares" y
"aprobadas" definidas para cada materia en el plan de estudios, y las
contrasta contra el estado real del alumno para decidir si la materia
puede cursarse o no.

De esta forma, el plan de estudios (data/plan_estudios.json) es la única
fuente de verdad de las correlativas: si el plan cambia, el motor se
adapta automáticamente sin necesidad de tocar código.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

from core.models import (
    DefinicionMateria,
    Disponibilidad,
    EstadoAlumnoMateria,
    EstadoMateria,
    Materia,
)


def _cumple_regular(estado: EstadoMateria) -> bool:
    """Una materia satisface el requisito de 'regularizada' si está
    regularizada o si ya fue directamente aprobada (una materia aprobada
    siempre implica que en algún momento fue regularizada)."""
    return estado in (EstadoMateria.REGULARIZADA, EstadoMateria.APROBADA)


def _cumple_aprobada(estado: EstadoMateria) -> bool:
    return estado == EstadoMateria.APROBADA


def calcular_disponibilidad(
    definicion: DefinicionMateria,
    estados_por_id: Dict[int, EstadoMateria],
) -> tuple[Disponibilidad, List[int]]:
    """
    Calcula si una materia puede cursarse actualmente.

    Devuelve una tupla (disponibilidad, ids_faltantes) donde ids_faltantes
    contiene los IDs de las correlativas que todavía no se cumplen (útil
    para mostrar tooltips o mensajes explicativos en la UI).
    """
    estado_propio = estados_por_id.get(definicion.id, EstadoMateria.PENDIENTE)

    # Si la materia ya está regularizada o aprobada, el concepto de
    # "puede cursar" no aplica: ya fue cursada.
    if estado_propio != EstadoMateria.PENDIENTE:
        return Disponibilidad.NO_APLICA, []

    faltantes: List[int] = []

    for req_id in definicion.regulares:
        estado_req = estados_por_id.get(req_id, EstadoMateria.PENDIENTE)
        if not _cumple_regular(estado_req):
            faltantes.append(req_id)

    for req_id in definicion.aprobadas:
        estado_req = estados_por_id.get(req_id, EstadoMateria.PENDIENTE)
        if not _cumple_aprobada(estado_req):
            if req_id not in faltantes:
                faltantes.append(req_id)

    if faltantes:
        return Disponibilidad.NO_PUEDE_CURSAR, faltantes

    return Disponibilidad.PUEDE_CURSAR, []


def construir_materias(
    definiciones: Iterable[DefinicionMateria],
    estados: Dict[int, EstadoAlumnoMateria],
) -> List[Materia]:
    """
    Combina las definiciones estáticas del plan con el estado dinámico
    del alumno y calcula la disponibilidad de cada materia.
    """
    estados_por_id = {
        materia_id: estado_alumno.estado for materia_id, estado_alumno in estados.items()
    }

    materias: List[Materia] = []
    for definicion in definiciones:
        estado_alumno = estados.get(
            definicion.id, EstadoAlumnoMateria(materia_id=definicion.id)
        )
        disponibilidad, faltantes = calcular_disponibilidad(definicion, estados_por_id)
        materias.append(
            Materia(
                definicion=definicion,
                estado_alumno=estado_alumno,
                disponibilidad=disponibilidad,
                correlativas_faltantes=faltantes,
            )
        )
    return materias


def calcular_estadisticas(materias: Iterable[Materia]) -> dict:
    """Calcula los contadores y el promedio general mostrados en el panel superior."""
    materias = list(materias)
    total = len(materias)

    aprobadas = [m for m in materias if m.estado == EstadoMateria.APROBADA]
    regularizadas = [m for m in materias if m.estado == EstadoMateria.REGULARIZADA]
    pendientes = [m for m in materias if m.estado == EstadoMateria.PENDIENTE]

    notas = [m.nota_final for m in aprobadas if m.nota_final is not None]
    promedio = round(sum(notas) / len(notas), 2) if notas else 0.0

    progreso = round((len(aprobadas) / total) * 100, 1) if total else 0.0

    return {
        "total": total,
        "aprobadas": len(aprobadas),
        "regularizadas": len(regularizadas),
        "pendientes": len(pendientes),
        "promedio": promedio,
        "progreso_pct": progreso,
    }


def calcular_creditos(materias: Iterable[Materia], requeridos: int) -> dict:
    """
    Suma los créditos de las materias electivas aprobadas.

    Solo las materias aprobadas otorgan créditos; pendientes o regularizadas
    no suman. Es completamente genérica: no le importa si le pasan solo
    electivas o una mezcla, simplemente ignora las que no tengan `creditos`.
    """
    acumulados = sum(
        m.creditos for m in materias if m.estado == EstadoMateria.APROBADA and m.creditos
    )
    return {
        "acumulados": acumulados,
        "requeridos": requeridos,
        "completo": acumulados >= requeridos,
    }
