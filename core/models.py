"""
Modelos de datos del dominio.

Estos objetos representan la información de una materia combinando:
  - Los datos estáticos del plan de estudios (nombre, nivel, correlativas...).
  - El estado dinámico del alumno para esa materia (nota, estado, fecha).

Se mantienen como dataclasses simples para que el resto de la aplicación
(UI, lógica de correlativas, persistencia) trabaje siempre con el mismo
contrato de datos, sin importar de dónde provenga la información.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class EstadoMateria(str, Enum):
    """Estado académico real de una materia para el alumno."""

    PENDIENTE = "pendiente"
    REGULARIZADA = "regularizada"
    APROBADA = "aprobada"

    @classmethod
    def desde_texto(cls, valor: str) -> "EstadoMateria":
        valor_normalizado = (valor or "").strip().lower()
        for estado in cls:
            if estado.value == valor_normalizado:
                return estado
        return cls.PENDIENTE

    @property
    def etiqueta(self) -> str:
        return {
            EstadoMateria.PENDIENTE: "Pendiente",
            EstadoMateria.REGULARIZADA: "Regularizada",
            EstadoMateria.APROBADA: "Aprobada",
        }[self]


class Disponibilidad(str, Enum):
    """Resultado del cálculo de correlativas para una materia pendiente."""

    PUEDE_CURSAR = "puede_cursar"
    NO_PUEDE_CURSAR = "no_puede_cursar"
    NO_APLICA = "no_aplica"  # Ya está regularizada o aprobada.


@dataclass
class DefinicionMateria:
    """Datos estáticos que provienen del plan de estudios (no cambian)."""

    id: int
    nivel: int
    nombre: str
    modalidad: str
    regulares: List[int] = field(default_factory=list)
    aprobadas: List[int] = field(default_factory=list)
    categoria: str = "Obligatoria"  # "Obligatoria" u "Electiva"
    creditos: Optional[float] = None  # Solo aplica a materias electivas


@dataclass
class EstadoAlumnoMateria:
    """Datos dinámicos que dependen del avance del alumno."""

    materia_id: int
    estado: EstadoMateria = EstadoMateria.PENDIENTE
    nota_final: Optional[float] = None
    fecha_modificacion: Optional[str] = None


@dataclass
class Materia:
    """Vista combinada: lo que consume la interfaz gráfica."""

    definicion: DefinicionMateria
    estado_alumno: EstadoAlumnoMateria
    disponibilidad: Disponibilidad = Disponibilidad.NO_APLICA
    correlativas_faltantes: List[int] = field(default_factory=list)

    @property
    def id(self) -> int:
        return self.definicion.id

    @property
    def nivel(self) -> int:
        return self.definicion.nivel

    @property
    def nombre(self) -> str:
        return self.definicion.nombre

    @property
    def modalidad(self) -> str:
        return self.definicion.modalidad

    @property
    def categoria(self) -> str:
        return self.definicion.categoria

    @property
    def creditos(self) -> Optional[float]:
        return self.definicion.creditos

    @property
    def estado(self) -> EstadoMateria:
        return self.estado_alumno.estado

    @property
    def nota_final(self) -> Optional[float]:
        return self.estado_alumno.nota_final
