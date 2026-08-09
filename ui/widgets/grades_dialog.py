"""
Ventana "Cargar notas".

Permite recorrer las materias una por una (con botones Anterior / Siguiente)
para cargar el estado (Pendiente / Regularizada / Aprobada) y la nota final.
Al guardar cada materia, se persiste inmediatamente en la base de datos y
se notifica a la ventana principal para refrescar la tabla y las estadísticas.
"""

from __future__ import annotations

from typing import Callable, List, Optional

import customtkinter as ctk
from tkinter import messagebox

from core.models import EstadoMateria, Materia
from ui import theme


class CargarNotasDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        materias: List[Materia],
        on_guardar: Callable[[int, EstadoMateria, Optional[float]], None],
        materia_inicial_id: Optional[int] = None,
        nombres_por_id: Optional[dict] = None,
    ):
        super().__init__(master)
        self.title("Cargar nota")
        self.geometry("520x420")
        self.minsize(480, 400)
        self.configure(fg_color=theme.COLOR_FONDO)
        self.transient(master)
        self.grab_set()

        self._materias = sorted(materias, key=lambda m: (m.nivel, m.id))
        self._on_guardar = on_guardar
        self._indice = 0
        # Mapa id -> nombre para mostrar las correlativas faltantes por su
        # nombre. Se recibe explícito porque una electiva puede requerir
        # correlativas de materias OBLIGATORIAS que no están en `materias`
        # (la lista de este diálogo puede ser solo electivas, por ejemplo).
        self._nombres_por_id = nombres_por_id or {m.id: m.nombre for m in self._materias}

        if materia_inicial_id is not None:
            for i, m in enumerate(self._materias):
                if m.id == materia_inicial_id:
                    self._indice = i
                    break

        self._construir_ui()
        self._cargar_materia_actual()

    # ------------------------------------------------------------------ #
    def _construir_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=theme.PADDING_GRANDE, pady=(theme.PADDING_GRANDE, 4))
        header.grid_columnconfigure(0, weight=1)

        self._lbl_nivel = ctk.CTkLabel(
            header, text="", font=theme.FUENTE_TEXTO_PEQUENA, text_color=theme.COLOR_TEXTO_SECUNDARIO
        )
        self._lbl_nivel.grid(row=0, column=0, sticky="w")

        self._lbl_nombre = ctk.CTkLabel(header, text="", font=theme.FUENTE_TITULO, wraplength=460, justify="left")
        self._lbl_nombre.grid(row=1, column=0, sticky="w", pady=(2, 0))

        cuerpo = ctk.CTkFrame(self, fg_color=theme.COLOR_PANEL, corner_radius=12)
        cuerpo.grid(row=1, column=0, sticky="nsew", padx=theme.PADDING_GRANDE, pady=theme.PADDING_MEDIO)
        cuerpo.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(cuerpo, text="Estado", font=theme.FUENTE_SUBTITULO).grid(
            row=0, column=0, sticky="w", padx=theme.PADDING_MEDIO, pady=(theme.PADDING_MEDIO, 4)
        )
        self._estado_var = ctk.StringVar(value=EstadoMateria.PENDIENTE.etiqueta)
        self._segmented = ctk.CTkSegmentedButton(
            cuerpo,
            values=[e.etiqueta for e in EstadoMateria],
            variable=self._estado_var,
            command=self._on_estado_cambiado,
        )
        self._segmented.grid(row=1, column=0, sticky="ew", padx=theme.PADDING_MEDIO, pady=(0, theme.PADDING_MEDIO))

        ctk.CTkLabel(cuerpo, text="Nota final (0 a 10)", font=theme.FUENTE_SUBTITULO).grid(
            row=2, column=0, sticky="w", padx=theme.PADDING_MEDIO, pady=(theme.PADDING_MEDIO, 4)
        )
        self._entry_nota = ctk.CTkEntry(cuerpo, placeholder_text="Ej: 8")
        self._entry_nota.grid(row=3, column=0, sticky="ew", padx=theme.PADDING_MEDIO, pady=(0, theme.PADDING_MEDIO))

        self._lbl_correlativas = ctk.CTkLabel(
            cuerpo,
            text="",
            font=theme.FUENTE_TEXTO_PEQUENA,
            text_color=theme.COLOR_TEXTO_SECUNDARIO,
            wraplength=440,
            justify="left",
        )
        self._lbl_correlativas.grid(row=4, column=0, sticky="w", padx=theme.PADDING_MEDIO, pady=(0, theme.PADDING_MEDIO))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=theme.PADDING_GRANDE, pady=(0, theme.PADDING_GRANDE))
        footer.grid_columnconfigure(1, weight=1)

        self._btn_anterior = ctk.CTkButton(footer, text="◀ Anterior", width=110, command=self._ir_anterior)
        self._btn_anterior.grid(row=0, column=0, sticky="w")

        self._btn_guardar = ctk.CTkButton(
            footer,
            text="Guardar",
            width=140,
            fg_color=theme.COLOR_ACENTO,
            hover_color=theme.COLOR_ACENTO_HOVER,
            command=self._guardar_actual,
        )
        self._btn_guardar.grid(row=0, column=1)

        self._btn_siguiente = ctk.CTkButton(footer, text="Siguiente ▶", width=110, command=self._ir_siguiente)
        self._btn_siguiente.grid(row=0, column=2, sticky="e")

        self._btn_cerrar = ctk.CTkButton(
            self, text="Cerrar", width=100, fg_color="transparent", border_width=1,
            command=self.destroy,
        )
        self._btn_cerrar.grid(row=3, column=0, pady=(0, theme.PADDING_MEDIO))

    # ------------------------------------------------------------------ #
    def materia_actual(self) -> Materia:
        return self._materias[self._indice]

    def _materia_actual(self) -> Materia:
        return self.materia_actual()

    def _cargar_materia_actual(self) -> None:
        m = self._materia_actual()
        self._lbl_nivel.configure(text=f"Nivel {m.nivel}  ·  ID {m.id}  ·  {m.modalidad}")
        self._lbl_nombre.configure(text=m.nombre)
        self._estado_var.set(m.estado.etiqueta)
        self._entry_nota.delete(0, "end")
        if m.nota_final is not None:
            self._entry_nota.insert(0, f"{m.nota_final:g}")

        if m.correlativas_faltantes:
            nombres = self._nombres_por_ids(m.correlativas_faltantes)
            self._lbl_correlativas.configure(
                text=f"⚠ Correlativas pendientes: {nombres}"
            )
        else:
            self._lbl_correlativas.configure(text="")

        self._on_estado_cambiado(self._estado_var.get())

        self._btn_anterior.configure(state="normal" if self._indice > 0 else "disabled")
        self._btn_siguiente.configure(state="normal" if self._indice < len(self._materias) - 1 else "disabled")
        self.title(f"Cargar nota — {self._indice + 1} / {len(self._materias)}")

    def _nombres_por_ids(self, ids: List[int]) -> str:
        return ", ".join(f"[{i}] {self._nombres_por_id.get(i, '???')}" for i in ids)

    def _on_estado_cambiado(self, valor: str) -> None:
        # La nota final solo tiene sentido si la materia está aprobada.
        if valor == EstadoMateria.APROBADA.etiqueta:
            self._entry_nota.configure(state="normal")
        else:
            self._entry_nota.configure(state="normal")

    # ------------------------------------------------------------------ #
    def _leer_nota(self) -> Optional[float]:
        texto = self._entry_nota.get().strip().replace(",", ".")
        if not texto:
            return None
        try:
            nota = float(texto)
        except ValueError as exc:
            raise ValueError("La nota debe ser un número.") from exc
        if not (0 <= nota <= 10):
            raise ValueError("La nota debe estar entre 0 y 10.")
        return nota

    def _guardar_actual(self) -> None:
        m = self._materia_actual()
        estado_txt = self._estado_var.get()
        estado = next(e for e in EstadoMateria if e.etiqueta == estado_txt)

        try:
            nota = self._leer_nota()
        except ValueError as exc:
            messagebox.showerror("Nota inválida", str(exc), parent=self)
            return

        if estado == EstadoMateria.APROBADA and nota is None:
            respuesta = messagebox.askyesno(
                "Falta la nota",
                "Marcaste la materia como Aprobada pero no ingresaste una nota final. "
                "¿Querés guardar de todas formas sin nota?",
                parent=self,
            )
            if not respuesta:
                return

        self._on_guardar(m.id, estado, nota)

    # ------------------------------------------------------------------ #
    def _ir_anterior(self) -> None:
        if self._indice > 0:
            self._indice -= 1
            self._refrescar_desde_materias_actualizadas()

    def _ir_siguiente(self) -> None:
        if self._indice < len(self._materias) - 1:
            self._indice += 1
            self._refrescar_desde_materias_actualizadas()

    def actualizar_materias(self, materias: List[Materia]) -> None:
        """Permite refrescar la info mostrada (por ej. correlativas) tras guardar."""
        id_actual = self._materia_actual().id
        self._materias = sorted(materias, key=lambda m: (m.nivel, m.id))
        for i, m in enumerate(self._materias):
            if m.id == id_actual:
                self._indice = i
                break
        self._cargar_materia_actual()

    def _refrescar_desde_materias_actualizadas(self) -> None:
        self._cargar_materia_actual()
