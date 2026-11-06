---
estado: cumplida
escrita: 2026-11-05
---
# Spec 010: ordenar la raíz y cerrar las ramas de la entrega

Nace de las observaciones de la sustentación del Módulo 1: la raíz del repositorio
no debería tener las aplicaciones sueltas y en GitHub quedaron muchas ramas de
trabajo abiertas. El objetivo es dejar una entrega ordenada y reutilizable para el
Taller 2, sin cambiar el comportamiento del asistente.

## Qué se necesita

1. `app.py` y `app_modulo1.py` salen de la raíz. Las aplicaciones pasan a una
   carpeta `app/` (`app/asistente.py` y `app/modulo1.py`), porque `src/taaml/` es
   la librería instalable y las apps son puntos de entrada.
2. `Makefile`, `README.md`, `AGENTS.md`, la constitución y la plantilla de PR
   apuntan a las rutas nuevas. `make lint` revisa la carpeta `app/`.
3. Las ramas de trabajo del remoto se cierran después de integrar la única que
   tenía un commit sin fusionar (`chore/scraping-demo-limpio`).

## Criterios de aceptación

- `make modulo1` y `make app` abren la misma interfaz que antes.
- `make test` y `make lint` pasan.
- En GitHub solo queda la rama `main`.
- No se reescribe la historia: los créditos de coautoría de Claude se conservan
  porque es una herramienta declarada en el informe, y reescribir cambiaría todos
  los hashes y desalinearía las PR.
