# perfil/

Datos del candidato que alimentan el scoring y, más adelante, la generación de CV y carta.

| Archivo | Versionado | Para qué |
|---|---|---|
| `busqueda.example.yaml` | Sí | Plantilla de criterios de búsqueda: skills, sueldo, modalidad, seniority, idiomas. |
| `busqueda.yaml` | **No** (`.gitignore`) | Tus criterios reales. Si no existe, la app usa el ejemplo y lo avisa en el log. |
| `perfil.yaml` | **No** | Hechos del CV (hito 3). Lleva datos de contacto: nunca se versiona. |

En Docker Compose esta carpeta se monta de solo lectura en `/app/perfil`.
