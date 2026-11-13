# Auditoría de dependencias (2026-11-09)

Comando: `uv export --frozen --no-hashes --no-emit-project` seguido de `uvx pip-audit -r <archivo> --no-deps --disable-pip`.
Alcance: las versiones fijadas en `uv.lock`. Es solo lectura: no se cambió ninguna dependencia.

Actualización (2026-11-13): se reemplazó `chromadb` por `qdrant-client`; la misma auditoría da **44 vulnerabilidades en 3 paquetes** (pillow, opentelemetry-api y soupsieve), ninguna de Qdrant. La tabla de abajo es la medición original.

Resultado: **62 vulnerabilidades conocidas en 5 paquetes**, cuatro indirectos y chromadb, que es dependencia directa.

| Paquete | Versión fijada | Avisos | Corregido en | Entra por |
|---|---|---|---|---|
| pillow | 12.3.0 | 39 | 13.0.0 | streamlit |
| filelock | 3.32.7 | 13 | 4.0.9 / 4.2.1 | por revisar |
| chromadb | 1.5.9 | 5 | sin versión corregida | dependencia directa |
| pyasn1 | 0.6.4 | 4 | 0.6.5 | por revisar |
| oauthlib | 4.0.0 | 1 | 4.0.1 | por revisar |

## Detalle completo

```
Name     Version ID                  Fix Versions
-------- ------- ------------------- ------------
chromadb 1.5.9   PYSEC-2026-311
chromadb 1.5.9   PYSEC-2026-311
chromadb 1.5.9   PYSEC-2026-3814
chromadb 1.5.9   PYSEC-2026-3815
chromadb 1.5.9   PYSEC-2026-3813
filelock 3.32.7  CVE-2026-112940     4.2.1
filelock 3.32.7  CVE-2026-112913     4.2.1
filelock 3.32.7  CVE-2026-112907     4.2.1
filelock 3.32.7  CVE-2026-112938     4.2.1
filelock 3.32.7  CVE-2026-112936     4.0.9
filelock 3.32.7  CVE-2026-112910     4.2.1
filelock 3.32.7  CVE-2026-112909     4.2.1
filelock 3.32.7  CVE-2026-112911     4.2.1
filelock 3.32.7  CVE-2026-112939     4.2.1
filelock 3.32.7  CVE-2026-112915     4.2.1
filelock 3.32.7  CVE-2026-112935     4.2.1
filelock 3.32.7  CVE-2026-112912     4.2.1
filelock 3.32.7  CVE-2026-112908     4.2.1
oauthlib 4.0.0   CVE-2026-49272      4.0.1
pillow   12.3.0  PYSEC-2026-4327     13.0.0
pillow   12.3.0  PYSEC-2026-4328     13.0.0
pillow   12.3.0  PYSEC-2026-4326     13.0.0
pillow   12.3.0  PYSEC-2026-4339     13.0.0
pillow   12.3.0  PYSEC-2026-4340     13.0.0
pillow   12.3.0  PYSEC-2026-4343     13.0.0
pillow   12.3.0  PYSEC-2026-4334     13.0.0
pillow   12.3.0  PYSEC-2026-4337     13.0.0
pillow   12.3.0  PYSEC-2026-4341     13.0.0
pillow   12.3.0  PYSEC-2026-4330     13.0.0
pillow   12.3.0  PYSEC-2026-4338     13.0.0
pillow   12.3.0  PYSEC-2026-4335     13.0.0
pillow   12.3.0  PYSEC-2026-4336     13.0.0
pillow   12.3.0  PYSEC-2026-4331     13.0.0
pillow   12.3.0  PYSEC-2026-4332     13.0.0
pillow   12.3.0  PYSEC-2026-4329     13.0.0
pillow   12.3.0  PYSEC-2026-4333     13.0.0
pillow   12.3.0  PYSEC-2026-4342     13.0.0
pillow   12.3.0  CVE-2026-112895     13.0.0
pillow   12.3.0  CVE-2026-112400     13.0.0
pillow   12.3.0  CVE-2026-112897     13.0.0
pillow   12.3.0  CVE-2026-112395     13.0.0
pillow   12.3.0  CVE-2026-112404     13.0.0
pillow   12.3.0  CVE-2026-112899     13.0.0
pillow   12.3.0  CVE-2026-112900     13.0.0
pillow   12.3.0  CVE-2026-112893     13.0.0
pillow   12.3.0  CVE-2026-112891     13.0.0
pillow   12.3.0  CVE-2026-112390     13.0.0
pillow   12.3.0  CVE-2026-112401     13.0.0
pillow   12.3.0  CVE-2026-112391     13.0.0
pillow   12.3.0  CVE-2026-112894     13.0.0
pillow   12.3.0  CVE-2026-112406     13.0.0
pillow   12.3.0  CVE-2026-112399     13.0.0
pillow   12.3.0  CVE-2026-112892     13.0.0
pillow   12.3.0  CVE-2026-112393     13.0.0
pillow   12.3.0  CVE-2026-96638      13.0.0
pillow   12.3.0  CVE-2026-96640      13.0.0
pillow   12.3.0  CVE-2026-96778      13.0.0
pillow   12.3.0  GHSA-78g4-xqwv-q3g8 13.0.0
pyasn1   0.6.4   CVE-2026-119196     0.6.5
pyasn1   0.6.4   CVE-2026-119194     0.6.5
pyasn1   0.6.4   CVE-2026-119197     0.6.5
pyasn1   0.6.4   CVE-2026-119195     0.6.5
```
