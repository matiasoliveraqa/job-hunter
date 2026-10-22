import express from 'express'
import fs from 'node:fs/promises'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { spawn } from 'node:child_process'
import { randomUUID } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { createStore, STATUSES } from './store.js'
import { runChat } from './chat.js'
import { createDemo } from './demo.js'
import { createConfigFiles, ValidationError } from './config-files.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..', '..')
const DIST = path.resolve(__dirname, '..', 'dist')
const PORT = Number(process.env.PORT) || 3100
const HOST = '127.0.0.1'
const PYTHON_BIN = process.env.PYTHON_BIN || 'python'

const FILE_DIRS = {
  cvs: path.join(ROOT, 'output', 'cvs'),
  output: path.join(ROOT, 'output'),
  my_cv: path.join(ROOT, 'my_cv'),
}

const demo = createDemo({ root: ROOT, host: HOST, port: PORT })
const configFiles = createConfigFiles({ root: ROOT })
const store = createStore(path.join(ROOT, 'output', 'applications.json'))
const app = express()

// Express 4 does not forward rejected promises from async handlers to the error
// middleware (and Node would crash on them), so route registration is wrapped.
for (const method of ['get', 'post', 'put', 'patch', 'delete']) {
  const register = app[method].bind(app)
  app[method] = (route, ...handlers) =>
    register(
      route,
      ...handlers.map((h) => (typeof h === 'function' ? (req, res, next) => Promise.resolve(h(req, res, next)).catch(next) : h)),
    )
}

// This app drives a local agent with file access, so it must only answer to
// pages served by itself: reject foreign Host (DNS rebinding) and foreign Origin (CSRF).
const allowedHosts = new Set(
  [PORT, 5173].flatMap((p) => [`127.0.0.1:${p}`, `localhost:${p}`]),
)
app.use((req, res, next) => {
  if (!allowedHosts.has(req.headers.host)) return res.status(403).json({ error: 'Host no permitido' })
  if (!['GET', 'HEAD'].includes(req.method)) {
    const origin = req.headers.origin
    if (origin && !allowedHosts.has(new URL(origin).host)) {
      return res.status(403).json({ error: 'Origen no permitido' })
    }
    // Requests that carry a body must be JSON (blocks "simple" cross-site form posts).
    // Body-less ones (DELETE) have no content type to check; the Origin check above still applies.
    const hasBody = Number(req.headers['content-length']) > 0 || Boolean(req.headers['transfer-encoding'])
    if (hasBody && !req.is('application/json')) return res.status(415).json({ error: 'Se requiere application/json' })
  }
  next()
})
app.use(express.json({ limit: '100kb' }))

// ---- Applications ----
app.get('/api/applications', async (_req, res) => res.json(await store.list()))

app.post('/api/applications', async (req, res) => {
  const { company, role, url, status, demo: wantsDemo } = req.body ?? {}
  if (!company?.trim() || !role?.trim()) return res.status(400).json({ error: 'company y role son obligatorios' })
  if (url && !isHttpUrl(url)) return res.status(400).json({ error: 'url inválida' })
  if (status !== undefined && !['pending', 'applied'].includes(status)) return res.status(400).json({ error: 'status inválido' })
  // Demo entries may only point at this app's own mock postings, and are flagged so they stay apart.
  const isDemoUrl = Boolean(url) && demo.isMockUrl(url)
  if (wantsDemo === true && !isDemoUrl) return res.status(400).json({ error: 'La demo solo admite publicaciones de prueba' })
  const { item, created } = await store.create({
    ...req.body,
    company: company.trim(),
    role: role.trim(),
    demo: isDemoUrl,
  })
  res.status(created ? 201 : 200).json(item)
})

app.post('/api/applications/clear-demos', async (_req, res) => res.json({ removed: await store.removeDemos() }))

app.patch('/api/applications/:id', async (req, res) => {
  const { status, reason } = req.body ?? {}
  if (status !== undefined && !STATUSES.includes(status)) return res.status(400).json({ error: 'status inválido' })
  if (status === 'rejected' && !(reason ?? '').trim()) {
    return res.status(400).json({ error: 'Indica el motivo del rechazo' })
  }
  const item = await store.update(req.params.id, req.body ?? {})
  item ? res.json(item) : res.status(404).json({ error: 'No encontrada' })
})

app.delete('/api/applications/:id', async (req, res) => {
  ;(await store.remove(req.params.id)) ? res.status(204).end() : res.status(404).json({ error: 'No encontrada' })
})

// ---- Profile (config/profile.json) ----
app.get('/api/profile', async (_req, res) => res.json(await configFiles.readProfile()))
app.put('/api/profile', async (req, res) => res.json(await configFiles.writeProfile(req.body)))

// ---- Exclusions (config/exclusions.py) ----
app.get('/api/exclusions', async (_req, res) => res.json(await configFiles.readExclusions()))
app.post('/api/exclusions', async (req, res) => res.status(201).json(await configFiles.addExclusion(req.body ?? {})))
app.put('/api/exclusions/:company', async (req, res) => {
  const entry = await configFiles.updateExclusion(req.params.company, req.body ?? {})
  entry ? res.json(entry) : res.status(404).json({ error: 'No encontrada' })
})
app.delete('/api/exclusions/:company', async (req, res) => {
  ;(await configFiles.removeExclusion(req.params.company)) ? res.status(204).end() : res.status(404).json({ error: 'No encontrada' })
})

// ---- CV files ----
app.get('/api/files', async (_req, res) => {
  const files = []
  for (const [dir, abs] of Object.entries(FILE_DIRS)) {
    if (!existsSync(abs)) continue
    for (const entry of await fs.readdir(abs, { withFileTypes: true })) {
      if (!entry.isFile() || !entry.name.toLowerCase().endsWith('.pdf')) continue
      const stat = await fs.stat(path.join(abs, entry.name))
      files.push({ dir, name: entry.name, size: stat.size, modifiedAt: stat.mtime.toISOString() })
    }
  }
  res.json(files.sort((a, b) => b.modifiedAt.localeCompare(a.modifiedAt)))
})

app.get('/files/:dir/:name', (req, res) => {
  const base = FILE_DIRS[req.params.dir]
  const { name } = req.params
  if (!base || !/^[\w.\- ]+\.pdf$/i.test(name)) return res.status(400).end()
  res.sendFile(path.join(base, name), { headers: { 'Content-Type': 'application/pdf' } }, (err) => {
    if (err && !res.headersSent) res.status(404).end()
  })
})

// ---- Application form launcher (headed browser, user submits manually) ----
const launches = new Map()

app.post('/api/apply', async (req, res) => {
  const { url, cv, applicationId, demo: wantsDemo } = req.body ?? {}
  if (!isHttpUrl(url)) return res.status(400).json({ error: 'url inválida' })
  // Mock postings are demos: always fictional profile and CV, whatever the UI sent.
  const isDemoUrl = demo.isMockUrl(url)
  if (wantsDemo === true && !isDemoUrl) return res.status(400).json({ error: 'La demo solo admite publicaciones de prueba' })
  const cvPath = isDemoUrl ? demo.cvPath : resolveCv(cv)
  if (cv && !cvPath) return res.status(400).json({ error: 'CV inválido' })

  const args = ['-m', 'src.cli', 'apply', '--url', url]
  if (cvPath) args.push('--cv', cvPath)
  const id = randomUUID()
  const launch = { id, url, status: 'running', startedAt: new Date().toISOString() }
  launches.set(id, launch)

  const env = isDemoUrl ? { ...process.env, JOBHUNTER_PROFILE: demo.profilePath } : process.env
  const child = spawn(PYTHON_BIN, args, { cwd: ROOT, env, stdio: 'ignore', windowsHide: false })
  child.on('error', () => (launch.status = 'error'))
  child.on('close', (code) => {
    if (launch.status === 'running') launch.status = code === 0 ? 'closed' : 'error'
  })
  if (applicationId) await store.update(applicationId, { event: 'Formulario abierto en el navegador' })
  res.status(202).json(launch)
})

app.get('/api/apply', (_req, res) => res.json([...launches.values()]))

// ---- Chat (SSE) ----
// Session ids issued to demo runs: only these may be resumed in demo mode.
const demoSessions = new Set()

app.post('/api/chat', async (req, res) => {
  const { sessionId, demo: isDemo } = req.body ?? {}
  let { message } = req.body ?? {}
  if (typeof message !== 'string' || !message.trim()) return res.status(400).json({ error: 'message requerido' })

  let cwd = ROOT
  let resume = sessionId
  if (isDemo === true) {
    // Demo never uses the real session, folder, profile, CV or history.
    cwd = await demo.prepareSandbox()
    resume = demoSessions.has(sessionId) ? sessionId : undefined
    if (!resume) message = `${message}

URL de la publicación de demostración: ${demo.postingUrl}`
  } else if (demoSessions.has(sessionId)) {
    resume = undefined
  }

  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
  })
  const send = (evt) => {
    if (isDemo === true && evt.type === 'session') demoSessions.add(evt.id)
    res.write(`data: ${JSON.stringify(evt)}

`)
  }
  const stop = runChat({ message, sessionId: resume, cwd, send, onClose: () => res.end(), demo: isDemo === true })
  res.on('close', stop)
})

// ---- Static client (production) ----
if (existsSync(DIST)) {
  app.use(express.static(DIST))
  app.get('*', (_req, res) => res.sendFile(path.join(DIST, 'index.html')))
}

// JSON errors only: never leak stack traces or local paths.
app.use((err, _req, res, _next) => {
  if (err instanceof ValidationError) return res.status(400).json({ error: err.message })
  res.status(err.status || 500).json({ error: err.status === 400 ? 'Solicitud inválida' : 'Error interno' })
})

app.listen(PORT, HOST, () => console.log(`Job Hunter web: http://${HOST}:${PORT}`))

function isHttpUrl(value) {
  try {
    return ['http:', 'https:'].includes(new URL(value).protocol)
  } catch {
    return false
  }
}

// Accepts "dir/name.pdf" and only resolves inside the known CV folders.
function resolveCv(ref) {
  if (!ref) return null
  const [dir, name] = String(ref).split('/')
  const base = FILE_DIRS[dir]
  if (!base || !name || !/^[\w.\- ]+\.pdf$/i.test(name)) return null
  const full = path.join(base, name)
  return existsSync(full) ? full : null
}
