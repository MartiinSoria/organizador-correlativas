"""Panel superior: contadores de estado, promedio y barra de progreso."""

from __future__ import annotations

import customtkinter as ctk

from ui import theme


class _StatCard(ctk.CTkFrame):
    """Una tarjeta individual con un número grande y una etiqueta debajo."""

    def __init__(self, master, titulo: str, color_valor: str, **kwargs):
        super().__init__(
            master,
            fg_color=theme.COLOR_PANEL_CLARO,
            corner_radius=10,
            **kwargs,
        )
        self.grid_columnconfigure(0, weight=1)

        self._valor_lbl = ctk.CTkLabel(
            self,
            text="0",
            font=theme.FUENTE_NUMERO_STAT,
            text_color=color_valor,
        )
        self._valor_lbl.grid(row=0, column=0, padx=theme.PADDING_MEDIO, pady=(theme.PADDING_MEDIO, 0))

        self._titulo_lbl = ctk.CTkLabel(
            self,
            text=titulo,
            font=theme.FUENTE_TEXTO_PEQUENA,
            text_color=theme.COLOR_TEXTO_SECUNDARIO,
        )
        self._titulo_lbl.grid(row=1, column=0, padx=theme.PADDING_MEDIO, pady=(0, theme.PADDING_MEDIO))

    def set_valor(self, valor: str) -> None:
        self._valor_lbl.configure(text=valor)


class StatsPanel(ctk.CTkFrame):
    """Fila superior de la ventana principal con el resumen general de avance."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        for col in range(6):
            self.grid_columnconfigure(col, weight=1)

        self._card_aprobadas = _StatCard(self, "Aprobadas", theme.COLOR_PUEDE_CURSAR_TXT)
        self._card_aprobadas.grid(row=0, column=0, sticky="nsew", padx=(0, theme.PADDING_CHICO))

        self._card_regularizadas = _StatCard(self, "Regularizadas", theme.COLOR_REGULARIZADA_TXT)
        self._card_regularizadas.grid(row=0, column=1, sticky="nsew", padx=theme.PADDING_CHICO)

        self._card_pendientes = _StatCard(self, "Pendientes", theme.COLOR_TEXTO)
        self._card_pendientes.grid(row=0, column=2, sticky="nsew", padx=theme.PADDING_CHICO)

        self._card_promedio = _StatCard(self, "Promedio general", theme.COLOR_ACENTO)
        self._card_promedio.grid(row=0, column=3, sticky="nsew", padx=theme.PADDING_CHICO)

        self._card_creditos = _StatCard(self, "Créditos electivas", theme.COLOR_REGULARIZADA_TXT)
        self._card_creditos.grid(row=0, column=4, sticky="nsew", padx=theme.PADDING_CHICO)

        # Tarjeta de progreso, con la barra incluida.
        self._card_progreso = ctk.CTkFrame(
            self, fg_color=theme.COLOR_PANEL_CLARO, corner_radius=10
        )
        self._card_progreso.grid(row=0, column=5, sticky="nsew", padx=(theme.PADDING_CHICO, 0))
        self._card_progreso.grid_columnconfigure(0, weight=1)

        self._progreso_pct_lbl = ctk.CTkLabel(
            self._card_progreso,
            text="0%",
            font=theme.FUENTE_NUMERO_STAT,
            text_color=theme.COLOR_ACENTO,
        )
        self._progreso_pct_lbl.grid(row=0, column=0, padx=theme.PADDING_MEDIO, pady=(theme.PADDING_MEDIO, 2))

        self._progreso_bar = ctk.CTkProgressBar(
            self._card_progreso,
            progress_color=theme.COLOR_ACENTO,
        )
        self._progreso_bar.grid(row=1, column=0, sticky="ew", padx=theme.PADDING_MEDIO, pady=(0, 4))
        self._progreso_bar.set(0)

        self._progreso_titulo_lbl = ctk.CTkLabel(
            self._card_progreso,
            text="Avance de la carrera",
            font=theme.FUENTE_TEXTO_PEQUENA,
            text_color=theme.COLOR_TEXTO_SECUNDARIO,
        )
        self._progreso_titulo_lbl.grid(row=2, column=0, padx=theme.PADDING_MEDIO, pady=(0, theme.PADDING_MEDIO))

    def actualizar(self, stats: dict, creditos: dict) -> None:
        self._card_aprobadas.set_valor(str(stats["aprobadas"]))
        self._card_regularizadas.set_valor(str(stats["regularizadas"]))
        self._card_pendientes.set_valor(str(stats["pendientes"]))
        self._card_promedio.set_valor(f"{stats['promedio']:.2f}" if stats["promedio"] else "—")

        acumulados = creditos["acumulados"]
        requeridos = creditos["requeridos"]
        acumulados_txt = str(int(acumulados)) if float(acumulados).is_integer() else f"{acumulados:g}"
        self._card_creditos.set_valor(f"{acumulados_txt} / {requeridos}")

        pct = stats["progreso_pct"]
        self._progreso_pct_lbl.configure(text=f"{pct:.1f}%")
        self._progreso_bar.set(pct / 100.0)
