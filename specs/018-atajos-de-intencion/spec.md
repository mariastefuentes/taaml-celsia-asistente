# Spec 018 — Atajos de intención para mensajes triviales

- **Estado:** aprobada para la sustentación del 28 de noviembre de 2026.
- **Módulo:** 3 y sustentación final.
- **Rúbrica que atiende:** 1.2 (router y planificación: no gastar el modelo en saludos ni consultas triviales) y la experiencia de la demo.

## Problema

Un “hola” o un “gracias” en el chat web pasa hoy por el agente: tarda 4–8 s y gasta cuota para responder algo que no necesita datos ni herramientas. En el puente de OpenClaw pasa lo mismo con el agente de Celsia. El webhook de Meta ya tenía un menú con botones (D19), pero no cubre el chat web ni el puente.

Jev (D9) resolvería esto con un clasificador, pero es una API en acceso anticipado y no se adoptó para la demo (D76): el riesgo de depender de un servicio nuevo el día de la sustentación no compensa.

## Objetivo

1. Reconocer **saludos, agradecimientos, despedidas y ayuda** con reglas cerradas, sin llamar al modelo.
2. Responder con un texto compartido entre el chat web y OpenClaw.
3. No secuestrar mensajes con contenido: «hola, ¿dónde queda la sede?» sigue al agente.
4. No saltarse una aprobación pendiente ni una decisión sin entregar.
5. No guardar el atajo en el historial del agente.

## Fuera de alcance

- Jev o cualquier modelo de decisión (D9 queda abierto).
- Parafraseos libres, multilingüe o análisis semántico.
- Cambiar el menú con botones de Meta: se conserva.

## Criterios de aceptación

- [ ] `respuesta_rapida` reconoce las variantes con tildes, mayúsculas, signos, emojis y letras repetidas.
- [ ] Devuelve None cuando el mensaje trae contenido, aunque empiece con un saludo.
- [ ] `/api/chat` responde un saludo con eventos `hilo`, `texto` y `fin`, costo 0, sin llamar al modelo; el chat web muestra `atajo: saludo` y el panel registra la fila con costo 0.
- [ ] `/chat` (OpenClaw) responde un saludo sin llamar al agente.
- [ ] Con un reclamo pendiente o una decisión sin entregar, el atajo no se usa.
- [ ] El webhook de Meta conserva su menú y `/nuevo`.
- [ ] `make check` y `make qa` pasan.
