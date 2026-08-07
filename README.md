<<<<<<< HEAD
# Gestor de Materias — Ingeniería en Sistemas (UTN)

Aplicación de escritorio (Windows) para gestionar el avance de la carrera:
correlativas automáticas, notas, estados y progreso general. Hecha en
Python + CustomTkinter, con persistencia local en SQLite.

## Instalación

Requiere Python 3.10 o superior.

```bash
pip install -r requirements.txt
```

## Ejecutar la aplicación

```bash
python main.py
```

Al ejecutarla por primera vez se crea automáticamente el archivo
`data/gestor_materias.db` con todas las materias del plan cargadas en
estado "Pendiente". A partir de ahí, todo lo que cargues (notas, estados)
queda guardado entre sesiones.

## Estructura del proyecto

```
gestor_materias/
├── main.py                     # Punto de entrada
├── requirements.txt
├── data/
│   ├── plan_estudios.json      # Plan de estudios y correlativas (editable)
│   └── gestor_materias.db      # Base de datos SQLite (se genera sola)
├── core/                       # Lógica de negocio, sin dependencias de UI
│   ├── models.py                 # Entidades: Materia, Estado, Disponibilidad
│   ├── correlativas.py           # Motor genérico de correlativas
│   └── plan_loader.py            # Lectura del plan desde JSON
├── database/
│   └── db_manager.py           # Toda la capa de acceso a SQLite
└── ui/
    ├── theme.py                 # Colores, fuentes y espaciados centralizados
    ├── main_window.py           # Ventana principal (única ventana)
    └── widgets/
        ├── stats_panel.py        # Panel superior de estadísticas
        ├── materias_table.py     # Tabla estilo Excel (tksheet)
        └── grades_dialog.py      # Ventana modal "Cargar notas"
```

## Cómo funciona el motor de correlativas

`core/correlativas.py` es completamente genérico: no tiene ninguna regla
escrita a mano para ninguna materia puntual. Para cada materia pendiente,
recorre sus listas de IDs `regulares` y `aprobadas` (definidas en
`data/plan_estudios.json`, tal como estaban en las columnas del Excel) y
verifica el estado real de esas materias correlativas. Si el plan de
estudios cambia, el motor se adapta solo — no hace falta tocar código.

## Modificar el plan de estudios

Todo el plan vive en `data/plan_estudios.json`. Cada materia tiene:

```json
{
  "nivel": 2,
  "id": 19,
  "nombre": "Base de Datos",
  "modalidad": "1C-2C",
  "regulares": [13, 16],
  "aprobadas": [5, 6],
  "categoria": "Obligatoria"
}
```

Para agregar, quitar o corregir una materia, alcanza con editar este
archivo; al reiniciar la aplicación se sincroniza automáticamente con la
base de datos (sin perder las notas ya cargadas de las demás materias).

> **Nota sobre "categoría" (obligatoria/electiva):** la planilla que
> compartiste no incluía una columna que distinguiera materias
> obligatorias de electivas, así que agregué el campo `categoria` con
> valor por defecto `"Obligatoria"` para todas. El filtro por categoría
> ya está funcionando en la tabla; si en tu plan real hay electivas,
> simplemente marcá `"categoria": "Electiva"` en las que correspondan.

## Colores de la tabla

| Color | Significado |
|---|---|
| 🟢 Verde oscuro | Materia aprobada |
| 🟢 Verde claro | Puede cursarse ahora (correlativas cumplidas) |
| 🟡 Amarillo | Materia regularizada |
| 🔴 Rojo | No puede cursarse (faltan correlativas) |

Los colores se recalculan automáticamente cada vez que cambiás el estado
de una materia, tanto para obligatorias como para electivas.

## Materias electivas y créditos

La aplicación tiene dos pestañas dentro de la misma ventana:

- **Materias Obligatorias**: el plan de estudios principal (igual que antes).
- **Materias Electivas**: se rige por un sistema de créditos en vez de
  "tenés que aprobarlas todas". Cada electiva otorga una cantidad de
  créditos al aprobarse; la carrera requiere acumular
  `CREDITOS_ELECTIVAS_REQUERIDOS` (por defecto 20, configurable en
  `core/config.py`). Solo las electivas **aprobadas** suman créditos;
  regularizadas o pendientes no suman.

El panel superior muestra un indicador **"Créditos electivas: X / 20"**
que se actualiza solo. Las estadísticas de aprobadas/regularizadas/
pendientes/promedio/progreso de arriba reflejan únicamente el plan de
obligatorias (las electivas se miden por créditos, no por cantidad).

Las correlativas de las electivas funcionan igual que las de obligatorias
(mismo motor genérico), solo que sus IDs de "regulares"/"aprobadas"
apuntan a materias obligatorias. En la tabla de electivas esos IDs se
muestran traducidos a nombres, nunca como números sueltos.

## Cargar / editar una nota

Ya no hay un botón general de "Cargar notas". Cada fila de ambas tablas
tiene su propia columna **"Cargar nota"** (resaltada en azul, funciona
como botón). Al hacer clic ahí se abre el diálogo directamente sobre esa
materia puntual, con botones Anterior/Siguiente para seguir cargando las
demás materias de la misma sección sin cerrar la ventana.

## Funcionalidades de la tabla

- Clic en el encabezado de una columna: ordena (ascendente/descendente).
- Arrastrar el borde de una columna: la redimensiona.
- Filtros por nivel y estado, más un buscador por nombre.
- Scroll vertical y horizontal con encabezados siempre visibles.
- Columna "Cargar nota" por fila para editar esa materia directamente.

## Extender la aplicación a futuro

- **Nuevas columnas en la tabla:** agregar una entrada a `columnas_obligatorias()`
  o `columnas_electivas()` en `ui/widgets/materias_table.py` (encabezado,
  ancho, cómo obtener y formatear el valor). El resto (orden, render) es
  automático — ambas tablas comparten el mismo componente `MateriasTable`.
- **Nuevos campos por materia:** agregarlos a `DefinicionMateria`
  (`core/models.py`), al esquema de `materias` en `database/db_manager.py`
  y al JSON del plan.
- **Cambiar los créditos requeridos:** editar `CREDITOS_ELECTIVAS_REQUERIDOS`
  en `core/config.py`.
- **Nuevas pantallas:** actualmente la UI está en `ui/widgets/`; cada
  pantalla nueva puede vivir en su propio archivo dentro de esa carpeta,
  siguiendo el mismo patrón que `grades_dialog.py`.
=======
# organizador-correlativas
Gestor de materias para Ingeniería en Sistemas (UTN) con cálculo automático de correlativas, notas y créditos de electivas. Python + CustomTkinter + SQLite.
>>>>>>> c982c24ca02f99c304ff179c172bce549be16ef6
