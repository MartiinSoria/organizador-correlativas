"""
Capa de acceso a datos (SQLite).

Responsable de:
  - Crear el esquema de la base de datos si no existe.
  - Sincronizar la tabla `materias` con el plan de estudios (data/plan_estudios.json)
    cada vez que arranca la aplicación, sin pisar el progreso ya cargado.
  - Leer y escribir el estado del alumno (nota, estado, fecha) para cada materia.

Toda la aplicación accede a SQLite exclusivamente a través de esta clase,
para mantener las consultas centralizadas y fáciles de mantener.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from core.models import DefinicionMateria, EstadoAlumnoMateria, EstadoMateria

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "gestor_materias.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS materias (
    id          INTEGER PRIMARY KEY,
    nivel       INTEGER NOT NULL,
    nombre      TEXT NOT NULL,
    modalidad   TEXT NOT NULL DEFAULT '',
    regulares   TEXT NOT NULL DEFAULT '',
    aprobadas   TEXT NOT NULL DEFAULT '',
    categoria   TEXT NOT NULL DEFAULT 'Obligatoria',
    creditos    REAL
);

CREATE TABLE IF NOT EXISTS estado_materias (
    materia_id          INTEGER PRIMARY KEY,
    estado              TEXT NOT NULL DEFAULT 'pendiente',
    nota_final          REAL,
    fecha_modificacion  TEXT,
    FOREIGN KEY (materia_id) REFERENCES materias (id) ON DELETE CASCADE
);
"""


def _ids_a_texto(ids: List[int]) -> str:
    return ",".join(str(i) for i in ids)


def _texto_a_ids(texto: str) -> List[int]:
    if not texto:
        return []
    return [int(x) for x in texto.split(",") if x.strip()]


class DatabaseManager:
    """Maneja la conexión y todas las operaciones sobre SQLite."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.row_factory = sqlite3.Row
        self._crear_esquema()

    # ------------------------------------------------------------------ #
    # Inicialización
    # ------------------------------------------------------------------ #
    def _crear_esquema(self) -> None:
        with self._conn:
            self._conn.executescript(SCHEMA)
            self._migrar_columnas_faltantes()

    def _migrar_columnas_faltantes(self) -> None:
        columnas = {fila["name"] for fila in self._conn.execute("PRAGMA table_info(materias)")}
        if "categoria" not in columnas:
            self._conn.execute(
                "ALTER TABLE materias ADD COLUMN categoria TEXT NOT NULL DEFAULT 'Obligatoria'"
            )
        if "creditos" not in columnas:
            self._conn.execute("ALTER TABLE materias ADD COLUMN creditos REAL")

    def sincronizar_plan(self, definiciones: List[DefinicionMateria]) -> None:
        """
        Inserta o actualiza las materias del plan en la base de datos, y
        crea un registro de estado 'pendiente' para las materias nuevas.
        No modifica el estado de materias ya existentes (para no perder
        el progreso cargado por el alumno).
        """
        with self._conn:
            for d in definiciones:
                self._conn.execute(
                    """
                    INSERT INTO materias (id, nivel, nombre, modalidad, regulares, aprobadas, categoria, creditos)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        nivel = excluded.nivel,
                        nombre = excluded.nombre,
                        modalidad = excluded.modalidad,
                        regulares = excluded.regulares,
                        aprobadas = excluded.aprobadas,
                        categoria = excluded.categoria,
                        creditos = excluded.creditos
                    """,
                    (
                        d.id,
                        d.nivel,
                        d.nombre,
                        d.modalidad,
                        _ids_a_texto(d.regulares),
                        _ids_a_texto(d.aprobadas),
                        d.categoria,
                        d.creditos,
                    ),
                )
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO estado_materias (materia_id, estado)
                    VALUES (?, 'pendiente')
                    """,
                    (d.id,),
                )

    # ------------------------------------------------------------------ #
    # Lecturas
    # ------------------------------------------------------------------ #
    def obtener_definiciones(self) -> List[DefinicionMateria]:
        filas = self._conn.execute(
            "SELECT id, nivel, nombre, modalidad, regulares, aprobadas, categoria, creditos FROM materias "
            "ORDER BY nivel, id"
        ).fetchall()
        return [
            DefinicionMateria(
                id=f["id"],
                nivel=f["nivel"],
                nombre=f["nombre"],
                modalidad=f["modalidad"],
                regulares=_texto_a_ids(f["regulares"]),
                aprobadas=_texto_a_ids(f["aprobadas"]),
                categoria=f["categoria"],
                creditos=f["creditos"],
            )
            for f in filas
        ]

    def obtener_estados(self) -> Dict[int, EstadoAlumnoMateria]:
        filas = self._conn.execute(
            "SELECT materia_id, estado, nota_final, fecha_modificacion FROM estado_materias"
        ).fetchall()
        resultado: Dict[int, EstadoAlumnoMateria] = {}
        for f in filas:
            resultado[f["materia_id"]] = EstadoAlumnoMateria(
                materia_id=f["materia_id"],
                estado=EstadoMateria.desde_texto(f["estado"]),
                nota_final=f["nota_final"],
                fecha_modificacion=f["fecha_modificacion"],
            )
        return resultado

    # ------------------------------------------------------------------ #
    # Escrituras
    # ------------------------------------------------------------------ #
    def guardar_estado_materia(
        self,
        materia_id: int,
        estado: EstadoMateria,
        nota_final: Optional[float],
    ) -> None:
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO estado_materias (materia_id, estado, nota_final, fecha_modificacion)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(materia_id) DO UPDATE SET
                    estado = excluded.estado,
                    nota_final = excluded.nota_final,
                    fecha_modificacion = excluded.fecha_modificacion
                """,
                (materia_id, estado.value, nota_final, ahora),
            )

    def close(self) -> None:
        self._conn.close()
