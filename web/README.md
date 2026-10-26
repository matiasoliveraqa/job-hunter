# Job Hunter Web

Panel local (Vue 3 + Vuetify + Node/Express) para operar Job Hunter sin la consola.

- **Postulaciones**: historial con estado (enviada, entrevista, oferta, rechazada con motivo, retirada). Datos en `output/applications.json`.
- **CVs**: visor de los PDFs de `output/cvs/`, `output/` y `my_cv/`.
- **Chat con el agente**: ejecuta tu `claude` local (Claude Code) en modo headless con tu propia sesión; no usa API key.
- **Nueva postulación**: el botón "Abrir formulario" lanza `python -m src.cli apply` (navegador con el formulario pre-rellenado). El envío siempre lo haces tú.

## Uso

```bash
cd web
npm install
npm run build
npm start          # http://127.0.0.1:3100
```

Desarrollo con recarga: `npm run dev:server` y `npm run dev:client` (http://127.0.0.1:5173).

Requisitos: Node 20+, Claude Code instalado y con sesión iniciada (`claude`), y Python con las dependencias del proyecto.

## Variables de entorno

| Variable | Por defecto | Uso |
|---|---|---|
| `PORT` | `3100` | Puerto del servidor (siempre en 127.0.0.1) |
| `JOBHUNTER_NO_OPEN` | sin definir | Si está definida, no abre el navegador al arrancar |
| `CLAUDE_BIN` | `claude` | Ruta del ejecutable de Claude Code |
| `PYTHON_BIN` | `python` | Intérprete usado para `apply` |
| `JOBHUNTER_ALLOWED_TOOLS` | ver `server/chat.js` | Herramientas que el agente puede usar sin pedir permiso (separadas por coma) |

## Seguridad

- Solo escucha en `127.0.0.1` y rechaza Host u Origin ajenos, para que ninguna web externa pueda hablar con el agente.
- El agente puede leer y escribir archivos del proyecto y ejecutar solo `scan`, `build-cv` y `curl`. Amplía la lista con cuidado.
- `output/` y la configuración personal están fuera de git.
