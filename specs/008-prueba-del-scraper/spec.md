---
estado: cumplida
escrita: 2026-10-29
---
# Spec 008: prueba automática del scraper

Nace de la lista de cosas deseables de la sustentación («prueba automática del scraper o del contrato»). Las pruebas del contrato de datos y del pipeline ya existían; el scraper (`scripts/01_scrape_celsia.py`) no tenía ninguna. Se escribe **antes** de programar.

## Qué se necesita
`tests/test_scraper.py`, sin red y sin escribir en `data/`: una sesión falsa reemplaza a `requests` y las carpetas apuntan a un directorio temporal. Debe comprobar que el scraper:
1. envía su `User-Agent` propio y usa `timeout` en cada petición;
2. no descarga las URLs que `robots.txt` bloquea y las deja registradas con su motivo;
3. descarga el resto, guarda el HTML y registra el código HTTP y el hash SHA-1 del archivo;
4. espera `--delay` segundos entre peticiones (rate limit);
5. es reanudable: una segunda corrida no vuelve a descargar lo ya guardado;
6. registra el error de una página que falla y sigue con la siguiente;
7. lee los sitemaps y descarta las URLs en `/en/`.

## Criterios de aceptación
- `make test` pasa sin red ni claves.
- Ninguna prueba toca el sitio de Celsia.
