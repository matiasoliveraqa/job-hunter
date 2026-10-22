import { spawn } from 'node:child_process'

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

const SYSTEM_PROMPT = `You are the Job Hunter agent, running inside the Job Hunter web app.
Read AGENT_INSTRUCTIONS.md in the working directory and follow it.

Web app context:
- The user's applications live in output/applications.json (array of {id, company, role, url, appliedAt, status, reason, notes, cv}).
  status is one of: applied, interview, offer, rejected, withdrawn. "reason" explains rejections.
  Read this file at the start of a conversation and whenever the user asks about their applications, so you see changes made in the UI.
  Never apply to a company already listed there, nor to one in config/exclusions.py. Use rejection reasons to adjust future filtering.
- When you tailor a CV, save the HTML and PDF as output/cvs/<company-slug>.html and output/cvs/<company-slug>.pdf so the web app can list them.
- You cannot run "apply" yourself (it opens a browser window and blocks). For every posting you recommend, end your message with a block like this; the web app turns it into a card that loads the posting into the Applications page and gives the user the "Open form" / "Sent" / "Not sent" buttons. Do NOT write step-by-step instructions about buttons or registering:
\`\`\`jobhunter-posting
{"company":"<company>","role":"<role>","url":"<application url>"}
\`\`\`
  Add "cv":"output/cvs/<file>.pdf" only if you generated a tailored CV for it.
- The status "pending" means the posting is loaded but not submitted yet; "not_sent" means the user decided not to submit. Never treat pending/not_sent postings as applied.
- The user will tell you when they mark a posting as sent or not sent. If sent: add one line \`"company-slug": "Ya postulado (YYYY-MM-DD)",\` to EXCLUSION_REASONS in config/exclusions.py (keep one entry per line; the user manages this list from the "Exclusiones" page) and continue with the next candidate. If not sent: do not exclude it; briefly ask why only if it helps refine the search.
- The user always submits applications manually. Be concise and answer in the user's language.`

const DEFAULT_TOOLS = [
  'Read',
  'Glob',
  'Grep',
  'Edit',
  'Write',
  'WebFetch',
  'Bash(python -m src.cli scan:*)',
  'Bash(python -m src.cli build-cv:*)',
  'Bash(curl:*)',
]

// Demo mode: the agent only sees the fictional files in its throwaway folder.
export const DEMO_SYSTEM_PROMPT = `Eres el agente de Job Hunter en MODO PRUEBA. Todo lo que hay en tu carpeta de trabajo es ficticio:
- posting.html: la única publicación disponible (una oferta de demostración, no existe).
- profile.json: perfil de un candidato ficticio (Alex Mercer).
- cv.md: CV del candidato ficticio.
- applications.json: historial ficticio de postulaciones.

Cuando el usuario pida buscar publicaciones, no busques en plataformas reales: lee posting.html, compárala con el perfil y el CV ficticios, revisa que no esté duplicada en applications.json y preséntala como una oferta encontrada (empresa, puesto, ubicación, URL, coincidencias y brechas).
Aclara brevemente que es una demostración con datos ficticios. Solo puedes leer archivos de tu carpeta; no intentes acceder a nada más.
La URL pública de la publicación te llega al final del mensaje del usuario; úsala tal cual.
Para cada publicación que recomiendes, termina tu mensaje con un bloque como este (el panel lo convierte en una tarjeta con los botones; NO expliques pasos ni botones por tu cuenta):
\`\`\`jobhunter-posting
{"company":"<empresa>","role":"<puesto>","url":"<url de la postulación>"}
\`\`\`
Incluye "cv":"output/cvs/<archivo>.pdf" solo si generaste un CV adaptado.
Cuando el usuario te avise que envió o no envió la postulación, responde en una o dos frases (en demo, sin tocar nada) y, si no la envió, pregunta brevemente el motivo. Responde en el idioma del usuario.`

export function isValidSessionId(id) {
  return typeof id === 'string' && UUID_RE.test(id)
}

/**
 * Runs the locally installed Claude Code CLI in headless mode and streams
 * simplified events to `send`. Uses the user's own Claude login: API key
 * variables are stripped so the CLI never falls back to pay-per-use billing.
 */
export function runChat({ message, sessionId, cwd, send, onClose, demo = false }) {
  const bin = process.env.CLAUDE_BIN || 'claude'
  const tools = process.env.JOBHUNTER_ALLOWED_TOOLS
    ? process.env.JOBHUNTER_ALLOWED_TOOLS.split(',').map((t) => t.trim()).filter(Boolean)
    : DEFAULT_TOOLS

  const args = ['-p', '--output-format', 'stream-json', '--verbose', '--include-partial-messages']
  if (demo) {
    // Read-only built-in tools and no extra directories:
    // file access stays inside `cwd`, which only holds fictional files.
    args.push('--append-system-prompt', DEMO_SYSTEM_PROMPT)
    if (isValidSessionId(sessionId)) args.push('--resume', sessionId)
    args.push('--tools', 'Read,Glob,Grep')
    // Ignore the user's own permission rules: nothing outside `cwd` may be allowed.
    args.push('--setting-sources', 'project')
  } else {
    args.push('--append-system-prompt', SYSTEM_PROMPT)
    if (isValidSessionId(sessionId)) args.push('--resume', sessionId)
    args.push('--allowedTools', ...tools)
  }

  const env = { ...process.env }
  delete env.ANTHROPIC_API_KEY
  delete env.ANTHROPIC_AUTH_TOKEN

  const child = spawn(bin, args, { cwd, env, stdio: ['pipe', 'pipe', 'pipe'] })
  let buffer = ''
  let stderr = ''
  let finished = false

  child.on('error', (err) => {
    send({ type: 'error', message: `No se pudo iniciar "${bin}": ${err.message}` })
    finish()
  })

  child.stdin.end(message)

  child.stdout.on('data', (chunk) => {
    buffer += chunk.toString('utf-8')
    let nl
    while ((nl = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, nl).trim()
      buffer = buffer.slice(nl + 1)
      if (line) handleLine(line)
    }
  })

  child.stderr.on('data', (chunk) => {
    stderr += chunk.toString('utf-8')
  })

  child.on('close', (code) => {
    if (buffer.trim()) handleLine(buffer.trim())
    if (code !== 0 && !finished) {
      send({ type: 'error', message: stderr.trim().slice(-500) || `claude terminó con código ${code}` })
    }
    finish()
  })

  function handleLine(line) {
    let evt
    try {
      evt = JSON.parse(line)
    } catch {
      return
    }
    if (evt.type === 'system' && evt.subtype === 'init') {
      send({ type: 'session', id: evt.session_id })
    } else if (evt.type === 'stream_event') {
      const delta = evt.event?.delta
      if (delta?.type === 'text_delta') send({ type: 'text', text: delta.text })
    } else if (evt.type === 'assistant') {
      for (const block of evt.message?.content ?? []) {
        if (block.type === 'tool_use') {
          send({ type: 'tool', name: block.name, input: summarizeInput(block.input) })
        }
      }
    } else if (evt.type === 'result') {
      send({
        type: 'done',
        sessionId: evt.session_id,
        isError: Boolean(evt.is_error),
        result: evt.is_error ? evt.result : undefined,
      })
    }
  }

  function finish() {
    if (finished) return
    finished = true
    onClose()
  }

  return () => {
    if (!finished) child.kill()
  }
}

function summarizeInput(input = {}) {
  const value = input.command ?? input.file_path ?? input.pattern ?? input.url ?? ''
  return String(value).slice(0, 120)
}
