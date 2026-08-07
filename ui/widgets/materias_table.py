"""
Tabla principal de materias (reutilizable para obligatorias y electivas).

Implementada sobre `tksheet`, que provee una experiencia similar a una
hoja de cálculo (encabezados fijos, redimensionado de columnas, scroll,
selección de filas) sin tener que reconstruir todo eso a mano sobre el
Treeview clásico de Tkinter.

El mismo componente `MateriasTable` se usa tanto para la tabla de materias
obligatorias como para la de electivas: cada una define su propia lista de
columnas (`ColumnaConfig`) y se la pasa al widget, evitando así duplicar
la lógica de orden, filtrado, coloreado y scroll entre ambas tablas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import customtkinter as ctk
from tksheet import Sheet

from core.models import Disponibilidad, EstadoMateria, Materia
from ui import theme


@dataclass(frozen=True)
class ColumnaConfig:
    """Define una columna de la tabla: su encabezado, ancho y cómo extraer
    y formatear el valor a partir de un objeto Materia."""

    clave: str
    encabezado: str
    ancho: int
    accesor: Callable[[Materia], object]
    formateador: Callable[[object], str]


def _fmt_texto(valor: object) -> str:
    return "" if valor is None else str(valor)


def _fmt_nota(valor: object) -> str:
    if valor is None:
        return "—"
    return f"{float(valor):.2f}".rstrip("0").rstrip(".") if "." in f"{float(valor):.2f}" else f"{float(valor):.2f}"


def _fmt_creditos(valor: object) -> str:
    if valor is None:
        return "—"
    numero = float(valor)
    return str(int(numero)) if numero.is_integer() else f"{numero:g}"


def _fmt_accion(_valor: object) -> str:
    return "📝  Cargar nota"


def _etiqueta_estado(materia: Materia) -> str:
    if materia.estado == EstadoMateria.APROBADA:
        return "Aprobada"
    if materia.estado == EstadoMateria.REGULARIZADA:
        return "Regularizada"
    if materia.disponibilidad == Disponibilidad.PUEDE_CURSAR:
        return "Puede cursar"
    return "No puede cursar"


def _hacer_formateador_ids_a_nombres(nombres_por_id: Dict[int, str]) -> Callable[[object], str]:
    """Crea un formateador que traduce una lista de IDs de correlativas a
    los nombres de esas materias (usado por la columna de electivas)."""

    def formatear(valor: object) -> str:
        if not valor:
            return "—"
        return ", ".join(nombres_por_id.get(i, f"[{i}]") for i in valor)

    return formatear


# --------------------------------------------------------------------- #
# Columnas de la tabla de materias OBLIGATORIAS
# --------------------------------------------------------------------- #
def columnas_obligatorias() -> List[ColumnaConfig]:
    return [
        ColumnaConfig("nivel", "Nivel", 70, lambda m: m.nivel, _fmt_texto),
        ColumnaConfig("id", "ID", 55, lambda m: m.id, _fmt_texto),
        ColumnaConfig("nombre", "Materia", 340, lambda m: m.nombre, _fmt_texto),
        ColumnaConfig("modalidad", "Tipo de cursado", 140, lambda m: m.modalidad, _fmt_texto),
        ColumnaConfig("estado", "Estado", 130, _etiqueta_estado, _fmt_texto),
        ColumnaConfig("nota_final", "Nota final", 90, lambda m: m.nota_final, _fmt_nota),
        ColumnaConfig("accion", "Cargar nota", 140, lambda m: m.id, _fmt_accion),
    ]


# --------------------------------------------------------------------- #
# Columnas de la tabla de materias ELECTIVAS
# --------------------------------------------------------------------- #
def columnas_electivas(nombres_obligatorias_por_id: Dict[int, str]) -> List[ColumnaConfig]:
    fmt_ids = _hacer_formateador_ids_a_nombres(nombres_obligatorias_por_id)
    return [
        ColumnaConfig("nivel", "Nivel", 70, lambda m: m.nivel, _fmt_texto),
        ColumnaConfig("nombre", "Materia", 300, lambda m: m.nombre, _fmt_texto),
        ColumnaConfig("modalidad", "Modalidad", 130, lambda m: m.modalidad, _fmt_texto),
        ColumnaConfig("regulares", "Regulares necesarias", 230, lambda m: m.definicion.regulares, fmt_ids),
        ColumnaConfig("aprobadas", "Aprobadas necesarias", 230, lambda m: m.definicion.aprobadas, fmt_ids),
        ColumnaConfig("creditos", "Créditos", 85, lambda m: m.creditos, _fmt_creditos),
        ColumnaConfig("nota_final", "Nota final", 90, lambda m: m.nota_final, _fmt_nota),
        ColumnaConfig("accion", "Cargar nota", 140, lambda m: m.id, _fmt_accion),
    ]


def _color_de_fila(materia: Materia) -> tuple[str, str]:
    """Devuelve (color_fondo, color_texto) según el estado/disponibilidad.

    Se usa tal cual tanto para materias obligatorias como electivas: el
    sistema de colores es exactamente el mismo para ambas.
    """
    if materia.estado == EstadoMateria.APROBADA:
        return theme.COLOR_APROBADA, theme.COLOR_APROBADA_TXT
    if materia.estado == EstadoMateria.REGULARIZADA:
        return theme.COLOR_REGULARIZADA, theme.COLOR_REGULARIZADA_TXT
    if materia.disponibilidad == Disponibilidad.PUEDE_CURSAR:
        return theme.COLOR_PUEDE_CURSAR, theme.COLOR_PUEDE_CURSAR_TXT
    return theme.COLOR_NO_PUEDE_CURSAR, theme.COLOR_NO_PUEDE_CURSAR_TXT


class MateriasTable(ctk.CTkFrame):
    """
    Tabla estilo Excel, genérica y reutilizable.

    Recibe su propia lista de columnas (`columnas`), por lo que el mismo
    componente sirve tanto para la tabla de obligatorias como la de
    electivas sin duplicar nada de la lógica de orden, filtrado, scroll
    o coloreado de filas.

    Mantiene internamente la lista completa de materias (`_materias_todas`)
    y una lista filtrada/ordenada (`_materias_visibles`) que es la que
    efectivamente se muestra. Los filtros y el orden se resuelven siempre
    en Python sobre estas listas, y luego se vuelca el resultado al Sheet,
    lo que evita inconsistencias entre los datos y los colores mostrados.
    """

    def __init__(
        self,
        master,
        columnas: List[ColumnaConfig],
        on_seleccionar_materia: Optional[Callable[[Materia], None]] = None,
        on_cargar_nota: Optional[Callable[[Materia], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._columnas = columnas
        self._indice_por_clave = {c.clave: i for i, c in enumerate(columnas)}
        self._indice_col_accion = self._indice_por_clave.get("accion")

        self._on_seleccionar_materia = on_seleccionar_materia
        self._on_cargar_nota = on_cargar_nota

        self._materias_todas: List[Materia] = []
        self._materias_visibles: List[Materia] = []

        self._filtro_nivel = "Todos"
        self._filtro_estado = "Todos"
        self._texto_busqueda = ""

        self._orden_columna: Optional[str] = None
        self._orden_ascendente = True

        self._construir_filtros()
        self._construir_sheet()

    # ------------------------------------------------------------------ #
    # Construcción de la UI
    # ------------------------------------------------------------------ #
    def _construir_filtros(self) -> None:
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", pady=(0, theme.PADDING_CHICO))

        ctk.CTkLabel(barra, text="Buscar:", font=theme.FUENTE_TEXTO).pack(side="left", padx=(0, 6))
        self._entry_busqueda = ctk.CTkEntry(barra, width=200, placeholder_text="Nombre de la materia...")
        self._entry_busqueda.pack(side="left", padx=(0, theme.PADDING_MEDIO))
        self._entry_busqueda.bind("<KeyRelease>", self._on_busqueda_cambiada)

        ctk.CTkLabel(barra, text="Nivel:", font=theme.FUENTE_TEXTO).pack(side="left", padx=(0, 6))
        self._combo_nivel = ctk.CTkOptionMenu(
            barra,
            values=["Todos", "1", "2", "3", "4", "5"],
            width=90,
            command=self._on_filtro_nivel,
        )
        self._combo_nivel.pack(side="left", padx=(0, theme.PADDING_MEDIO))

        ctk.CTkLabel(barra, text="Estado:", font=theme.FUENTE_TEXTO).pack(side="left", padx=(0, 6))
        self._combo_estado = ctk.CTkOptionMenu(
            barra,
            values=["Todos", "Aprobada", "Regularizada", "Puede cursar", "No puede cursar"],
            width=150,
            command=self._on_filtro_estado,
        )
        self._combo_estado.pack(side="left", padx=(0, theme.PADDING_MEDIO))

        self._lbl_conteo = ctk.CTkLabel(barra, text="", font=theme.FUENTE_TEXTO_PEQUENA, text_color=theme.COLOR_TEXTO_SECUNDARIO)
        self._lbl_conteo.pack(side="right")

    def _construir_sheet(self) -> None:
        contenedor = ctk.CTkFrame(self, fg_color=theme.COLOR_PANEL, corner_radius=10)
        contenedor.pack(fill="both", expand=True)
        contenedor.grid_rowconfigure(0, weight=1)
        contenedor.grid_columnconfigure(0, weight=1)

        encabezados = [c.encabezado for c in self._columnas]
        anchos = [c.ancho for c in self._columnas]

        self._sheet = Sheet(
            contenedor,
            headers=encabezados,
            data=[],
            show_x_scrollbar=True,
            show_y_scrollbar=True,
            show_row_index=False,
            header_height=34,
            theme="dark blue",
        )
        self._sheet.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        self._sheet.enable_bindings(
            "single_select",
            "column_width_resize",
            "double_click_column_resize",
            "arrowkeys",
            "column_select",
            "copy",
        )
        self._sheet.set_all_column_widths_manual = False
        for i, ancho in enumerate(anchos):
            self._sheet.column_width(column=i, width=ancho)

        # Ordenar al hacer clic en el encabezado de una columna.
        self._sheet.extra_bindings("column_select", self._on_header_click)
        # Clic sobre cualquier celda: selecciona la materia y, si es la
        # columna "Cargar nota", abre directamente el diálogo de esa materia.
        # (Se usa "cell_select" -no "row_select"- porque la tabla no
        # muestra la columna de índice de fila y "row_select" solo se
        # dispara al hacer clic justo ahí).
        self._sheet.extra_bindings("cell_select", self._on_cell_click)

        self._sheet.readonly(True)

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def set_materias(self, materias: List[Materia]) -> None:
        self._materias_todas = materias
        self._refrescar()

    def obtener_seleccionada(self) -> Optional[Materia]:
        seleccion = self._sheet.get_currently_selected()
        if not seleccion:
            return None
        fila_idx = seleccion.row
        if fila_idx is not None and 0 <= fila_idx < len(self._materias_visibles):
            return self._materias_visibles[fila_idx]
        return None

    # ------------------------------------------------------------------ #
    # Filtros
    # ------------------------------------------------------------------ #
    def _on_busqueda_cambiada(self, _event=None) -> None:
        self._texto_busqueda = self._entry_busqueda.get().strip().lower()
        self._refrescar()

    def _on_filtro_nivel(self, valor: str) -> None:
        self._filtro_nivel = valor
        self._refrescar()

    def _on_filtro_estado(self, valor: str) -> None:
        self._filtro_estado = valor
        self._refrescar()

    def _materia_coincide_filtros(self, materia: Materia) -> bool:
        if self._filtro_nivel != "Todos" and str(materia.nivel) != self._filtro_nivel:
            return False

        if self._filtro_estado != "Todos" and _etiqueta_estado(materia) != self._filtro_estado:
            return False

        if self._texto_busqueda and self._texto_busqueda not in materia.nombre.lower():
            return False

        return True

    # ------------------------------------------------------------------ #
    # Orden
    # ------------------------------------------------------------------ #
    def _on_header_click(self, event) -> None:
        try:
            columna_idx = event[0] if isinstance(event, (list, tuple)) else event.column
        except Exception:
            return
        if columna_idx is None or not (0 <= columna_idx < len(self._columnas)):
            return

        clave = self._columnas[columna_idx].clave
        if clave == "accion":
            return  # No tiene sentido ordenar por la columna de botones.

        if self._orden_columna == clave:
            self._orden_ascendente = not self._orden_ascendente
        else:
            self._orden_columna = clave
            self._orden_ascendente = True
        self._refrescar()

    def _aplicar_orden(self, materias: List[Materia]) -> List[Materia]:
        if not self._orden_columna:
            return materias

        columna = self._columnas[self._indice_por_clave[self._orden_columna]]

        def clave_orden(m: Materia):
            valor = columna.accesor(m)
            if isinstance(valor, list):
                valor = len(valor)
            return (valor is None, valor if valor is not None else "")

        return sorted(materias, key=clave_orden, reverse=not self._orden_ascendente)

    # ------------------------------------------------------------------ #
    # Refresco de datos + colores
    # ------------------------------------------------------------------ #
    def _refrescar(self) -> None:
        filtradas = [m for m in self._materias_todas if self._materia_coincide_filtros(m)]
        self._materias_visibles = self._aplicar_orden(filtradas)

        filas = [
            [columna.formateador(columna.accesor(m)) for columna in self._columnas]
            for m in self._materias_visibles
        ]
        # IMPORTANTE: reset_row_positions debe ir en True. Si se deja en False
        # cuando la cantidad de filas cambia (por ej. al aplicar un filtro o al
        # cargar los datos por primera vez), tksheet no recalcula la altura de
        # las filas nuevas y la tabla queda "vacía" visualmente aunque los
        # datos sí están cargados.
        self._sheet.set_sheet_data(filas, reset_col_positions=False, reset_row_positions=True)

        self._sheet.dehighlight_all()
        for fila_idx, materia in enumerate(self._materias_visibles):
            fondo, texto = _color_de_fila(materia)
            self._sheet.highlight_rows(rows=[fila_idx], bg=fondo, fg=texto, redraw=False)
            if self._indice_col_accion is not None:
                # La columna "Cargar nota" siempre se resalta igual, como si
                # fuera un botón, sin importar el color de estado de la fila.
                self._sheet.highlight_cells(
                    row=fila_idx,
                    column=self._indice_col_accion,
                    bg=theme.COLOR_ACENTO,
                    fg="#ffffff",
                    redraw=False,
                )

        self._sheet.redraw()

        total = len(self._materias_todas)
        visibles = len(self._materias_visibles)
        if visibles == total:
            self._lbl_conteo.configure(text=f"{total} materias")
        else:
            self._lbl_conteo.configure(text=f"{visibles} de {total} materias")

    def _on_cell_click(self, event) -> None:
        seleccion = self._sheet.get_currently_selected()
        if not seleccion:
            return
        fila_idx, col_idx = seleccion.row, seleccion.column
        if fila_idx is None or not (0 <= fila_idx < len(self._materias_visibles)):
            return

        materia = self._materias_visibles[fila_idx]

        if self._on_seleccionar_materia:
            self._on_seleccionar_materia(materia)

        if col_idx == self._indice_col_accion and self._on_cargar_nota:
            self._on_cargar_nota(materia)
