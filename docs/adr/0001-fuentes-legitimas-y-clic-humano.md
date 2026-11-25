# ADR 0001 — Solo fuentes legítimas y el clic de postular es humano

- **Estado:** aceptada
- **Fecha:** 2026-11-25

## Contexto

Automatizar una búsqueda de trabajo tienta a ir al extremo: bots que postulan en masa a todo lo que
calce. Hay tres problemas con eso:

1. **Términos de uso.** LinkedIn prohíbe los bots y el scraping, y puede restringir la cuenta. Indeed
   no tiene API pública de búsqueda y su ToS también prohíbe el scraping.
2. **Rendimiento.** Las postulaciones genéricas en volumen convierten mucho peor que 5–10 dirigidas a
   la semana, con CV y carta adaptados.
3. **Defensa en entrevista.** «Construí un sistema que prioriza y prepara, y yo decido» se explica
   mejor que «construí un bot de spam».

## Decisión

- ApplyOps **solo lee ofertas de fuentes con API o feed público** (Get on Board, Remotive, RemoteOK,
  Himalayas, We Work Remotely, Torre.ai y las APIs públicas de ATS: Greenhouse, Lever y Ashby).
- Las ofertas de portales sin API (LinkedIn, Indeed, Laborum…) **se cargan a mano** (URL + texto) y se
  puntúan igual que las demás.
- **Ninguna parte del sistema postula, inicia sesión en portales ni envía formularios.** El estado
  «postulada» lo marca la persona después de hacer el clic.

## Consecuencias

- Menos ofertas que un scraper, pero todas obtenidas sin riesgo para la cuenta y con un contrato
  estable que se puede testear (contract tests con fixtures reales).
- Cada fuente nueva debe justificar en su PR que su acceso automatizado está permitido (checklist
  de la plantilla de PR e issue).
