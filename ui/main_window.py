"""
Ventana principal de la aplicación.

Una sola ventana (como pide el requerimiento) con:
  - Un panel superior de estadísticas generales (incluye créditos de electivas).
  - Dos tablas estilo Excel organizadas en pestañas: Obligatorias y Electivas.
  - Cada fila tiene su propio botón "Cargar nota" para editar esa materia
    puntual (no hay un botón general único).

Esta clase actúa como "controlador" de la pantalla: coordina la base de
datos, el motor de correlativas y los widgets, pero no contiene lógica de
negocio propia (esa vive en core/).
"""

from __future__ import annotations

from tkinter import messagebox

import customtkinter as ctk

from core.config import CREDITOS_ELECTIVAS_REQUERIDOS
from core.correlativas import calcular_creditos, calcular_estadisticas, construir_materias
from core.models import EstadoMateria
from core.plan_loader import PlanEstudiosError, cargar_plan, nombre_carrera
from database.db_manager import DatabaseManager
from ui import theme
from ui.widgets.grades_dialog import CargarNotasDialog
from ui.widgets.materias_table import MateriasTable, columnas_electivas, columnas_obligatorias
from ui.widgets.stats_panel import StatsPanel

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()

        self._db = DatabaseManager()
        self._dialogo_notas: CargarNotasDialog | None = None

        try:
            self._definiciones = cargar_plan()
        except PlanEstudiosError as exc:
            messagebox.showerror("Error al cargar el plan de estudios", str(exc))
            self.destroy()
            return

        self._db.sincronizar_plan(self._definiciones)

        # Mapa id -> nombre de TODAS las materias (obligatorias + electivas),
        # usado para mostrar nombres de correlativas en vez de IDs sueltos.
        self._nombres_por_id = {d.id: d.nombre for d in self._definiciones}

        # Nombres solo de obligatorias: la tabla de electivas los necesita
        # para traducir sus columnas "Regulares/Aprobadas necesarias".
        self._nombres_obligatorias_por_id = {
            d.id: d.nombre for d in self._definiciones if d.categoria == "Obligatoria"
        }

        self.title(nombre_carrera())
        self.geometry("1360x820")
        self.minsize(1080, 660)
        self.configure(fg_color=theme.COLOR_FONDO)
        self.protocol("WM_DELETE_WINDOW", self._on_cerrar)

        self._construir_ui()
        self._refrescar_todo()

    # ------------------------------------------------------------------ #
    def _construir_ui(self) -> None:
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # --- Encabezado (solo título; ya no hay botón general de notas) ---
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=theme.PADDING_GRANDE, pady=(theme.PADDING_GRANDE, theme.PADDING_MEDIO))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text=nombre_carrera(),
            font=theme.FUENTE_TITULO,
        ).grid(row=0, column=0, sticky="w")

        # --- Panel de estadísticas ---
        self._stats_panel = StatsPanel(self)
        self._stats_panel.grid(row=1, column=0, sticky="ew", padx=theme.PADDING_GRANDE, pady=(0, theme.PADDING_MEDIO))

        # --- Pestañas: Obligatorias / Electivas ---
        self._tabview = ctk.CTkTabview(
            self,
            fg_color="transparent",
            segmented_button_selected_color=theme.COLOR_ACENTO,
            segmented_button_selected_hover_color=theme.COLOR_ACENTO_HOVER,
        )
        self._tabview.grid(
            row=2, column=0, sticky="nsew", padx=theme.PADDING_GRANDE, pady=(0, theme.PADDING_GRANDE)
        )
        tab_obligatorias = self._tabview.add("Materias Obligatorias")
        tab_electivas = self._tabview.add("Materias Electivas")
        tab_obligatorias.grid_rowconfigure(0, weight=1)
        tab_obligatorias.grid_columnconfigure(0, weight=1)
        tab_electivas.grid_rowconfigure(0, weight=1)
        tab_electivas.grid_columnconfigure(0, weight=1)

        self._tabla_obligatorias = MateriasTable(
            tab_obligatorias,
            columnas=columnas_obligatorias(),
            on_cargar_nota=self._abrir_dialogo_notas_para,
        )
        self._tabla_obligatorias.grid(row=0, column=0, sticky="nsew")

        self._tabla_electivas = MateriasTable(
            tab_electivas,
            columnas=columnas_electivas(self._nombres_obligatorias_por_id),
            on_cargar_nota=self._abrir_dialogo_notas_para,
        )
        self._tabla_electivas.grid(row=0, column=0, sticky="nsew")

    # ------------------------------------------------------------------ #
    # Orquestación de datos
    # ------------------------------------------------------------------ #
    def _refrescar_todo(self) -> None:
        estados = self._db.obtener_estados()
        materias = construir_materias(self._definiciones, estados)
        self._materias_actuales = materias

        obligatorias = [m for m in materias if m.categoria == "Obligatoria"]
        electivas = [m for m in materias if m.categoria == "Electiva"]

        self._tabla_obligatorias.set_materias(obligatorias)
        self._tabla_electivas.set_materias(electivas)

        # Las estadísticas superiores (aprobadas/regularizadas/pendientes/
        # promedio/progreso) reflejan solo el plan de obligatorias, que es
        # la carrera en sí; las electivas tienen su propio indicador de
        # créditos, ya que se completan de forma independiente (no hace
        # falta aprobarlas todas, solo acumular créditos).
        stats = calcular_estadisticas(obligatorias)
        creditos = calcular_creditos(electivas, CREDITOS_ELECTIVAS_REQUERIDOS)
        self._stats_panel.actualizar(stats, creditos)

    # ------------------------------------------------------------------ #
    # Diálogo de carga de notas
    # ------------------------------------------------------------------ #
    def _abrir_dialogo_notas_para(self, materia) -> None:
        if self._dialogo_notas is not None and self._dialogo_notas.winfo_exists():
            self._dialogo_notas.destroy()

        # Navega solo dentro de la misma categoría que la materia clickeada
        # (obligatorias con obligatorias, electivas con electivas).
        materias_seccion = [m for m in self._materias_actuales if m.categoria == materia.categoria]

        self._dialogo_notas = CargarNotasDialog(
            self,
            materias=materias_seccion,
            on_guardar=self._guardar_nota,
            materia_inicial_id=materia.id,
            nombres_por_id=self._nombres_por_id,
        )

    def _guardar_nota(self, materia_id: int, estado: EstadoMateria, nota: float | None) -> None:
        self._db.guardar_estado_materia(materia_id, estado, nota)
        self._refrescar_todo()

        if self._dialogo_notas is not None and self._dialogo_notas.winfo_exists():
            materias_seccion = [
                m for m in self._materias_actuales
                if m.categoria == self._dialogo_notas.materia_actual().categoria
            ]
            self._dialogo_notas.actualizar_materias(materias_seccion)

    # ------------------------------------------------------------------ #
    def _on_cerrar(self) -> None:
        self._db.close()
        self.destroy()


def main() -> None:
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
