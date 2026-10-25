import express from 'express'
import fs from 'node:fs/promises'
import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { spawn, execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { randomUUID } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { createStore, STATUSES } from './store.js'
import { createDemo } from './demo.js'
import { createConfigFiles, ValidationError } from './config-files.js'
import {
  tailorCvHtml,
  answerQuestion,
  extractProfileFromCv,
  checkAgentStatus,
  readAiSettings,
  writeAiSettings,
  checkBaseCv,
} from './agent-adapter.js'
import createDOMPurify from 'dompurify'
import { JSDOM } from 'jsdom'

const execFileAsync = promisify(execFile)

const domWindow = new JSDOM('').window
const DOMPurify = createDOMPurify(domWindow)

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..', '..')
const DIST = path.resolve(__dirname, '..', 'dist')
const PORT = Number(process.env.PORT) || 3100
const HOST = '127.0.0.1'
function detectPythonBin(root) {
  if (process.env.PYTHON_BIN) return process.env.PYTHON_BIN
  const candidates = [
    path.join(root, 'venv', 'Scripts', 'python.exe'),
    path.join(root, 'venv', 'bin', 'python3'),
    path.join(root, 'venv', 'bin', 'python'),
    path.join(root, '.venv', 'Scripts', 'python.exe'),
    path.join(root, '.venv', 'bin', 'python3'),
    path.join(root, '.venv', 'bin', 'python'),
  ]
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate
  }
  return process.platform === 'win32' ? 'python' : 'python3'
}

const PYTHON_BIN = detectPythonBin(ROOT)

const FILE_DIRS = {
  applications: path.join(ROOT, 'output', 'applications'),
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
export function addAllowedPort(p) {
  const portNum = Number(p)
  if (portNum > 0) {
    allowedHosts.add(`127.0.0.1:${portNum}`)
    allowedHosts.add(`localhost:${portNum}`)
  }
}
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
app.use(express.json({ limit: '15mb' }))

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
  if (url && !isDemoUrl && !isAllowedAtsHost(url)) {
    return res.status(400).json({
      error: 'Dominio no permitido. Por seguridad de tus datos, solo se permite registrar postulaciones en dominios oficiales de Greenhouse, Ashby o Lever.',
    })
  }
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

app.get('/api/profile/cv', async (_req, res) => {
  try {
    const myCvDir = path.join(ROOT, 'my_cv')
    if (!existsSync(myCvDir)) return res.json({ exists: false })
    const files = await fs.readdir(myCvDir)
    const cvFiles = files.filter((f) => /\.(pdf|html|md|txt)$/i.test(f) && !f.startsWith('skills_inventory'))
    if (!cvFiles.length) return res.json({ exists: false })

    const stats = await Promise.all(cvFiles.map(async (name) => {
      const st = await fs.stat(path.join(myCvDir, name))
      return { name, mtime: st.mtime, size: st.size }
    }))
    stats.sort((a, b) => b.mtime - a.mtime)
    const top = stats[0]
    res.json({
      exists: true,
      filename: top.name,
      sizeBytes: top.size,
      updatedAt: top.mtime.toISOString(),
      url: `/files/my_cv/${top.name}`,
    })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

app.post('/api/profile/upload-cv', async (req, res) => {
  const { filename, base64 } = req.body ?? {}
  if (!filename || !base64) {
    return res.status(400).json({ error: 'filename y base64 son requeridos' })
  }

  const cleanName = path.basename(filename).replace(/[^a-zA-Z0-9._-]+/g, '_')
  const ext = path.extname(cleanName).toLowerCase()
  if (!['.pdf', '.html', '.md', '.txt'].includes(ext)) {
    return res.status(400).json({ error: 'Solo se permiten archivos .pdf, .html, .md o .txt' })
  }

  const myCvDir = path.join(ROOT, 'my_cv')
  await fs.mkdir(myCvDir, { recursive: true })

  const MAX_CV_UPLOAD_BYTES = 10 * 1024 * 1024 // 10 MB
  const fileBuffer = Buffer.from(base64, 'base64')
  if (fileBuffer.length > MAX_CV_UPLOAD_BYTES) {
    return res.status(400).json({ error: 'El archivo excede el tamaño máximo permitido (10 MB)' })
  }
  const targetPath = path.join(myCvDir, cleanName)
  await fs.writeFile(targetPath, fileBuffer)

  // Extract text
  let extractedText = ''
  if (ext === '.pdf') {
    try {
      const { stdout } = await execFileAsync('pdftotext', [targetPath, '-'])
      extractedText = stdout.trim()
    } catch {
      // fallback
    }
  } else {
    extractedText = fileBuffer.toString('utf-8')
  }

  // Backup and update base cv markdown if text was extracted
  if (extractedText) {
    const cvMdPath = path.join(myCvDir, 'cv.md')
    if (existsSync(cvMdPath)) {
      const backupDir = path.join(ROOT, 'output', 'backups')
      await fs.mkdir(backupDir, { recursive: true })
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
      await fs.copyFile(cvMdPath, path.join(backupDir, `cv_${timestamp}.md.bak`))
    }
    await fs.writeFile(cvMdPath, extractedText, 'utf-8')
  }

  // Parse structured profile data using local agent
  let extracted = null
  if (extractedText) {
    try {
      extracted = await extractProfileFromCv(extractedText)
    } catch (e) {
      console.warn('[CV Upload] Error extracting profile via agent:', e.message)
    }
  }

  res.json({
    ok: true,
    filename: cleanName,
    sizeBytes: fileBuffer.length,
    url: `/files/my_cv/${cleanName}`,
    extracted,
  })
})

// ---- Exclusions (config/exclusions.py) ----
app.get('/api/exclusions', async (_req, res) => res.json(await configFiles.readExclusions()))
app.post('/api/exclusions', async (req, res) => res.status(201).json(await configFiles.addExclusion(req.body ?? {})))
app.post('/api/exclusions/import', async (req, res) => {
  const items = Array.isArray(req.body) ? req.body : req.body?.items ?? []
  res.json(await configFiles.importExclusions(items))
})
app.post('/api/exclusions/clear', async (_req, res) => {
  res.json(await configFiles.clearExclusions())
})
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
      if (entry.isFile() && entry.name.toLowerCase().endsWith('.pdf')) {
        const stat = await fs.stat(path.join(abs, entry.name))
        files.push({ dir, name: entry.name, size: stat.size, modifiedAt: stat.mtime.toISOString() })
      } else if (dir === 'applications' && entry.isDirectory()) {
        const subAbs = path.join(abs, entry.name)
        for (const sub of await fs.readdir(subAbs, { withFileTypes: true })) {
          if (!sub.isFile() || !sub.name.toLowerCase().endsWith('.pdf')) continue
          const stat = await fs.stat(path.join(subAbs, sub.name))
          files.push({
            dir,
            name: `${entry.name}/${sub.name}`,
            size: stat.size,
            modifiedAt: stat.mtime.toISOString(),
          })
        }
      }
    }
  }
  res.json(files.sort((a, b) => b.modifiedAt.localeCompare(a.modifiedAt)))
})

function sendPdfFile(req, res, dir, relName) {
  const base = FILE_DIRS[dir]
  if (!base || !isSafePdfRelPath(relName)) return res.status(400).end()
  res.sendFile(path.join(base, ...relName.split('/')), { headers: { 'Content-Type': 'application/pdf' } }, (err) => {
    if (err && !res.headersSent) res.status(404).end()
  })
}

app.get('/files/:dir/:name', (req, res) => sendPdfFile(req, res, req.params.dir, req.params.name))
app.get('/files/:dir/:sub/:name', (req, res) => sendPdfFile(req, res, req.params.dir, `${req.params.sub}/${req.params.name}`))

// ---- Cross-platform folder opener (Linux, macOS, Windows) ----
app.post('/api/open-folder', async (req, res) => {
  const target = req.body?.folder || 'applications'
  const allowed = {
    applications: FILE_DIRS.applications,
    cvs: FILE_DIRS.cvs,
    output: FILE_DIRS.output,
  }
  const folderPath = allowed[target] || allowed.applications
  if (!existsSync(folderPath)) {
    await fs.mkdir(folderPath, { recursive: true })
  }

  const platform = process.platform
  let cmd = ''
  let args = []
  if (platform === 'win32') {
    cmd = 'explorer'
    args = [folderPath]
  } else if (platform === 'darwin') {
    cmd = 'open'
    args = [folderPath]
  } else {
    cmd = 'xdg-open'
    args = [folderPath]
  }

  try {
    const child = spawn(cmd, args, { detached: true, stdio: 'ignore' })
    child.unref()
    child.on('error', (err) => {
      console.warn(`[open-folder] Error invoking ${cmd}:`, err.message)
    })
    res.json({ ok: true, path: folderPath, platform })
  } catch (err) {
    res.status(500).json({ error: 'No se pudo abrir la carpeta en el sistema', path: folderPath })
  }
})

// ---- Application form launcher (headed browser, user submits manually) ----
const launches = new Map()
const ALLOWED_ATS_DOMAINS = [
  'greenhouse.io',
  'boards.greenhouse.io',
  'job-boards.greenhouse.io',
  'ashbyhq.com',
  'jobs.ashbyhq.com',
  'lever.co',
  'jobs.lever.co',
]

export function isAllowedAtsHost(urlString) {
  try {
    const parsed = new URL(urlString)
    const hostname = parsed.hostname.toLowerCase()
    return ALLOWED_ATS_DOMAINS.some((allowed) => hostname === allowed || hostname.endsWith(`.${allowed}`))
  } catch {
    return false
  }
}

app.post('/api/apply', async (req, res) => {
  const { url, cv, company: bodyCompany, role: bodyRole, applicationId, demo: wantsDemo } = req.body ?? {}
  if (!isHttpUrl(url)) return res.status(400).json({ error: 'url inválida' })

  // Mock postings are demos: always fictional profile and CV, whatever the UI sent.
  const isDemoUrl = demo.isMockUrl(url)
  if (wantsDemo === true && !isDemoUrl) return res.status(400).json({ error: 'La demo solo admite publicaciones de prueba' })

  if (!isDemoUrl && !isAllowedAtsHost(url)) {
    return res.status(400).json({
      error: 'Dominio no permitido. Por seguridad de tus datos, solo se permite autocompletar en dominios oficiales de Greenhouse, Ashby o Lever.',
    })
  }

  // Prevent runaway concurrent browser processes
  const runningCount = [...launches.values()].filter((l) => l.status === 'running').length
  if (runningCount >= 2) {
    return res.status(429).json({ error: 'Ya hay un navegador de postulación activo. Ciérralo antes de abrir uno nuevo.' })
  }

  let cvPath = isDemoUrl ? demo.cvPath : resolveCv(cv)
  if (cv && !cvPath) return res.status(400).json({ error: 'CV inválido' })

  let company = typeof bodyCompany === 'string' ? bodyCompany.trim() : ''
  let role = typeof bodyRole === 'string' ? bodyRole.trim() : ''
  if (applicationId && (!company || !role)) {
    const allApps = await store.list()
    const match = allApps.find((a) => a.id === applicationId)
    if (match) {
      company = company || match.company || ''
      role = role || match.role || ''
    }
  }

  // Fallback to base CV in my_cv/ if no specific CV was provided or associated
  if (!cvPath) {
    const baseCv = await checkBaseCv()
    if (baseCv.exists) {
      cvPath = baseCv.relPath
    }
  }

  const args = ['-m', 'src.cli', 'apply', '--url', url]
  if (cvPath) args.push('--cv', cvPath)
  if (company && !isDemoUrl) args.push('--company', company)
  if (role && !isDemoUrl) args.push('--role', role)

  const id = randomUUID()
  const launch = { id, url, status: 'running', startedAt: new Date().toISOString() }
  launches.set(id, launch)

  if (req.body?.dryRun === true) {
    launch.status = 'dry_run'
    launch.company = company
    launch.role = role
    return res.status(202).json(launch)
  }

  const env = isDemoUrl ? { ...process.env, JOBHUNTER_PROFILE: demo.profilePath } : process.env
  const child = spawn(PYTHON_BIN, args, { cwd: ROOT, env, stdio: ['ignore', 'pipe', 'pipe'], windowsHide: false })
  child.stdout.on('data', (d) => console.log('[Apply stdout]', d.toString()))
  child.stderr.on('data', (d) => console.error('[Apply stderr]', d.toString()))
  child.on('error', (err) => {
    console.error('[Apply error]', err)
    launch.status = 'error'
  })
  child.on('close', (code) => {
    console.log('[Apply close] Exited with code:', code)
    if (launch.status === 'running') launch.status = code === 0 ? 'closed' : 'error'
    // Purge oldest records to prevent memory leaks
    if (launches.size > 20) {
      const oldestKeys = [...launches.keys()].slice(0, launches.size - 20)
      for (const k of oldestKeys) launches.delete(k)
    }
  })

  if (applicationId) {
    // Record event but keep status as pending until user confirms manual submission
    await store.update(applicationId, {
      event: 'Formulario abierto en el navegador Playwright para revisión y envío',
    })
  }

  res.status(202).json(launch)
})

app.get('/api/apply', (_req, res) => res.json([...launches.values()]))

// ---- Structured Scanner (Background Service with SSE Broadcast) ----
let activeScanChild = null
let latestScanMatches = []
const initialScanResultsPath = path.join(ROOT, 'output', 'scan_results.json')
try {
  if (existsSync(initialScanResultsPath)) {
    const rawData = JSON.parse(readFileSync(initialScanResultsPath, 'utf-8'))
    if (Array.isArray(rawData)) latestScanMatches = rawData
  }
} catch {}
const scanState = {
  isScanning: false,
  checked: 0,
  total: 0,
  platform: '',
  company: '',
  errorCount: 0,
  startedAt: null,
}
const scanSubscribers = new Set()

function broadcastScanEvent(evt) {
  const line = `data: ${JSON.stringify(evt)}\n\n`
  for (const res of scanSubscribers) {
    try {
      if (res.writable && !res.writableEnded) {
        res.write(line)
      } else {
        scanSubscribers.delete(res)
      }
    } catch {
      scanSubscribers.delete(res)
    }
  }
}

app.get('/api/scan/status', (_req, res) => {
  res.json({
    ...scanState,
    matches: latestScanMatches,
  })
})

app.get('/api/scan/results', async (_req, res) => {
  const scanResultsPath = path.join(ROOT, 'output', 'scan_results.json')
  if (latestScanMatches.length > 0) {
    return res.json({ matches: latestScanMatches })
  }
  if (existsSync(scanResultsPath)) {
    try {
      const data = JSON.parse(await fs.readFile(scanResultsPath, 'utf-8'))
      return res.json({ matches: Array.isArray(data) ? data : [] })
    } catch {}
  }
  res.json({ matches: [] })
})

app.get('/api/scan/events', (req, res) => {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
  })

  scanSubscribers.add(res)
  res.write(`data: ${JSON.stringify({ type: 'sync', scanState, matches: latestScanMatches })}\n\n`)

  req.on('close', () => {
    scanSubscribers.delete(res)
  })
})

function launchScanProcess({ roles, platforms, locations, maxYears, concurrency, allowCaptcha }) {
  if (activeScanChild) {
    try { activeScanChild.kill('SIGTERM') } catch {}
    activeScanChild = null
  }

  const args = ['-m', 'src.cli', 'scan', '--stream-json']
  if (Array.isArray(roles) && roles.length) {
    args.push('--roles', roles.join(','))
  }
  if (Array.isArray(platforms) && platforms.length) {
    args.push('--platforms', platforms.join(','))
  }
  if (Array.isArray(locations) && locations.length) {
    args.push('--locations', locations.join(','))
  }
  if (typeof maxYears === 'number' && maxYears >= 0) {
    args.push('--max-years', String(maxYears))
  }
  if (typeof concurrency === 'number' && concurrency > 0) {
    args.push('--concurrency', String(concurrency))
  }
  if (allowCaptcha === true) {
    args.push('--allow-captcha')
  }

  latestScanMatches = []
  Object.assign(scanState, {
    isScanning: true,
    checked: 0,
    total: 0,
    platform: '',
    company: '',
    errorCount: 0,
    startedAt: new Date().toISOString(),
  })

  broadcastScanEvent({ type: 'start' })

  const child = spawn(PYTHON_BIN, args, { cwd: ROOT, env: process.env, stdio: ['ignore', 'pipe', 'pipe'] })
  activeScanChild = child

  let stdoutBuf = ''
  child.stdout.on('data', (chunk) => {
    stdoutBuf += chunk.toString('utf-8')
    let nl
    while ((nl = stdoutBuf.indexOf('\n')) !== -1) {
      const line = stdoutBuf.slice(0, nl).trim()
      stdoutBuf = stdoutBuf.slice(nl + 1)
      if (!line) continue
      try {
        const parsed = JSON.parse(line)
        if (parsed.type === 'progress') {
          scanState.checked = parsed.checked
          scanState.total = parsed.total
          scanState.platform = parsed.platform
          scanState.company = parsed.company
        } else if (parsed.type === 'match' && parsed.posting) {
          latestScanMatches.push(parsed.posting)
        } else if (parsed.type === 'board_error') {
          scanState.errorCount++
        } else if (parsed.type === 'done') {
          scanState.isScanning = false
        }
        broadcastScanEvent(parsed)
      } catch {
        broadcastScanEvent({ type: 'raw', text: line })
      }
    }
  })

  child.stderr.on('data', (chunk) => {
    const errText = chunk.toString('utf-8').trim()
    if (errText) broadcastScanEvent({ type: 'log', message: errText })
  })

  child.on('close', (code) => {
    if (activeScanChild === child) {
      activeScanChild = null
      scanState.isScanning = false
    }
    broadcastScanEvent({ type: 'exit', code })
  })

  child.on('error', (err) => {
    if (activeScanChild === child) {
      activeScanChild = null
      scanState.isScanning = false
    }
    broadcastScanEvent({ type: 'error', error: err.message })
  })

  return child
}

app.post('/api/scan/start', (req, res) => {
  launchScanProcess(req.body ?? {})
  res.json({ started: true })
})

app.post('/api/scan/stream', (req, res) => {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
  })

  scanSubscribers.add(res)
  launchScanProcess(req.body ?? {})

  req.on('close', () => {
    scanSubscribers.delete(res)
  })
})

app.post('/api/scan/stop', (_req, res) => {
  if (activeScanChild) {
    try { activeScanChild.kill('SIGTERM') } catch {}
    activeScanChild = null
    scanState.isScanning = false
    broadcastScanEvent({ type: 'exit', code: 0 })
    return res.json({ stopped: true })
  }
  scanState.isScanning = false
  res.json({ stopped: false })
})

// ---- Tailored CV Generator (Isolated Multi-Agent) ----
let activeTailorCount = 0
const MAX_CONCURRENT_TAILORS = 1

export function sanitizeCvHtml(rawHtml) {
  if (!rawHtml || typeof rawHtml !== 'string') return ''
  const sanitized = DOMPurify.sanitize(rawHtml, {
    WHOLE_DOCUMENT: true,
    FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form', 'applet', 'base', 'meta', 'link'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur'],
  })
  return sanitized
    .replace(/@import\s+[^;]+;/gi, '')
    .replace(/<img\b([^>]*?)\bsrc=["']https?:\/\/[^"'>]+["']([^>]*?)>/gi, '<img$1src=""$2>')
}

app.post('/api/tailor-cv', async (req, res) => {
  const { company, role, url, description, provider } = req.body ?? {}
  if (!company || !role) {
    return res.status(400).json({ error: 'company y role son requeridos' })
  }

  if (activeTailorCount >= MAX_CONCURRENT_TAILORS) {
    return res.status(429).json({ error: 'Ya hay una generación de CV en curso. Espera a que termine.' })
  }
  activeTailorCount++

  try {
    const profile = await configFiles.readProfile()
    let skillsInventory = ''
    const inventoryPath = path.join(ROOT, 'my_cv', 'skills_inventory.md')
    const cvMdPath = path.join(ROOT, 'my_cv', 'cv.md')
    if (existsSync(inventoryPath)) {
      skillsInventory = await fs.readFile(inventoryPath, 'utf-8')
    } else if (existsSync(cvMdPath)) {
      skillsInventory = await fs.readFile(cvMdPath, 'utf-8')
    }

    const templatePath = path.join(ROOT, 'src', 'cv', 'templates', 'modern_ats.html')
    let baseTemplate = ''
    if (existsSync(templatePath)) {
      baseTemplate = await fs.readFile(templatePath, 'utf-8')
    }

    const tailoredHtml = await tailorCvHtml({
      jobTitle: role,
      company,
      jobDescription: description || '',
      profile,
      skillsInventory,
      baseTemplateHtml: baseTemplate,
      provider: provider || 'auto',
    })

    const sanitizedHtml = sanitizeCvHtml(tailoredHtml)
    if (!sanitizedHtml || sanitizedHtml.length < 100 || !sanitizedHtml.includes('<html')) {
      throw new Error('El HTML generado para el CV es inválido o está vacío')
    }

    const ym = new Date().toISOString().slice(0, 7)
    const sanitize = (s) => (s || '').replace(/[^a-zA-Z0-9_-]+/g, '_').replace(/^_+|_+$/g, '')
    const compSlug = sanitize(company) || 'Company'
    const roleSlug = sanitize(role) || 'Role'
    const folderName = `${ym}_${compSlug}_${roleSlug}`
    const appDir = path.join(ROOT, 'output', 'applications', folderName)
    await fs.mkdir(appDir, { recursive: true })

    const htmlPath = path.join(appDir, 'cv_tailored.html')
    await fs.writeFile(htmlPath, sanitizedHtml, 'utf-8')

    // Compile to PDF via python cli build-cv
    const buildArgs = ['-m', 'src.cli', 'build-cv', '--html', htmlPath, '--company', company, '--role', role]
    let compiledPdfPath = ''
    await new Promise((resolve, reject) => {
      const child = spawn(PYTHON_BIN, buildArgs, { cwd: ROOT, env: process.env, stdio: ['ignore', 'pipe', 'pipe'] })
      let outBuf = ''
      let errBuf = ''
      child.stdout.on('data', (d) => {
        outBuf += d.toString('utf-8')
      })
      child.stderr.on('data', (d) => (errBuf += d.toString('utf-8')))
      child.on('close', (code) => {
        if (code === 0) {
          const match = outBuf.match(/\[CV_PATH\]\s*(.+)/)
          if (match) compiledPdfPath = match[1].trim()
          resolve()
        } else {
          reject(new Error(errBuf || `Error al compilar PDF (código ${code})`))
        }
      })
    })

    let relCvPath = null
    if (compiledPdfPath && existsSync(compiledPdfPath)) {
      relCvPath = path.relative(path.join(ROOT, 'output'), compiledPdfPath).replace(/\\/g, '/')
    } else {
      const files = await fs.readdir(appDir).catch(() => [])
      const pdfFile = files.find((f) => f.toLowerCase().endsWith('.pdf'))
      if (pdfFile) {
        relCvPath = `applications/${folderName}/${pdfFile}`
      } else {
        const appsDir = path.join(ROOT, 'output', 'applications')
        const entries = await fs.readdir(appsDir, { withFileTypes: true }).catch(() => [])
        for (const entry of entries) {
          if (entry.isDirectory() && entry.name.toLowerCase().includes(compSlug.toLowerCase())) {
            const subFiles = await fs.readdir(path.join(appsDir, entry.name)).catch(() => [])
            const subPdf = subFiles.find((f) => f.toLowerCase().endsWith('.pdf'))
            if (subPdf) {
              relCvPath = `applications/${entry.name}/${subPdf}`
              break
            }
          }
        }
      }
    }

    let existing = (await store.list()).find(
      (a) => a.company?.toLowerCase() === company.toLowerCase() && (a.role?.toLowerCase() === role.toLowerCase() || (url && a.url === url))
    )
    let appId
    if (existing) {
      appId = existing.id
      await store.update(appId, { cv: relCvPath || existing.cv, url: url || existing.url })
    } else {
      const newApp = await store.create({
        company,
        role,
        url: url || '',
        cv: relCvPath || undefined,
        status: 'pending',
        notes: `CV adaptado con ${provider || 'agente local'}`,
      })
      appId = newApp.id
    }

    res.json({ ok: true, cv: relCvPath, folder: folderName, applicationId: appId })
  } catch (err) {
    res.status(500).json({ error: err.message })
  } finally {
    activeTailorCount--
  }
})

// ---- Agent Status, Settings & Base CV Fallback Endpoints ----
app.get('/api/agent/status', async (_req, res) => {
  try {
    const status = await checkAgentStatus()
    res.json(status)
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

app.get('/api/agent/config', async (_req, res) => {
  try {
    const settings = await readAiSettings()
    res.json({
      provider: settings.provider || 'auto',
      hasAnthropicKey: Boolean(settings.anthropicApiKey),
      hasOpenAiKey: Boolean(settings.openaiApiKey),
      hasGeminiKey: Boolean(settings.geminiApiKey),
      hasDeepSeekKey: Boolean(settings.deepseekApiKey),
      hasKimiKey: Boolean(settings.kimiApiKey),
      hasCustomKey: Boolean(settings.customOpenAiApiKey),
      anthropicApiKey: settings.anthropicApiKey ? `${settings.anthropicApiKey.slice(0, 7)}...${settings.anthropicApiKey.slice(-4)}` : '',
      openaiApiKey: settings.openaiApiKey ? `${settings.openaiApiKey.slice(0, 5)}...${settings.openaiApiKey.slice(-4)}` : '',
      geminiApiKey: settings.geminiApiKey ? `${settings.geminiApiKey.slice(0, 6)}...${settings.geminiApiKey.slice(-4)}` : '',
      deepseekApiKey: settings.deepseekApiKey ? `${settings.deepseekApiKey.slice(0, 5)}...${settings.deepseekApiKey.slice(-4)}` : '',
      kimiApiKey: settings.kimiApiKey ? `${settings.kimiApiKey.slice(0, 5)}...${settings.kimiApiKey.slice(-4)}` : '',
      customOpenAiApiKey: settings.customOpenAiApiKey ? `${settings.customOpenAiApiKey.slice(0, 5)}...${settings.customOpenAiApiKey.slice(-4)}` : '',
      customOpenAiBaseUrl: settings.customOpenAiBaseUrl || '',
      customOpenAiModel: settings.customOpenAiModel || '',
    })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

app.post('/api/agent/config', async (req, res) => {
  try {
    const body = req.body || {}
    const current = await readAiSettings()
    const payload = {
      provider: body.provider || current.provider,
      anthropicApiKey: body.anthropicApiKey && !body.anthropicApiKey.includes('...') ? body.anthropicApiKey : current.anthropicApiKey,
      openaiApiKey: body.openaiApiKey && !body.openaiApiKey.includes('...') ? body.openaiApiKey : current.openaiApiKey,
      geminiApiKey: body.geminiApiKey && !body.geminiApiKey.includes('...') ? body.geminiApiKey : current.geminiApiKey,
      deepseekApiKey: body.deepseekApiKey && !body.deepseekApiKey.includes('...') ? body.deepseekApiKey : current.deepseekApiKey,
      kimiApiKey: body.kimiApiKey && !body.kimiApiKey.includes('...') ? body.kimiApiKey : current.kimiApiKey,
      customOpenAiApiKey: body.customOpenAiApiKey && !body.customOpenAiApiKey.includes('...') ? body.customOpenAiApiKey : current.customOpenAiApiKey,
      customOpenAiBaseUrl: body.customOpenAiBaseUrl !== undefined ? body.customOpenAiBaseUrl : current.customOpenAiBaseUrl,
      customOpenAiModel: body.customOpenAiModel !== undefined ? body.customOpenAiModel : current.customOpenAiModel,
    }
    await writeAiSettings(payload)
    const status = await checkAgentStatus()
    res.json({ ok: true, status })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

app.post('/api/applications/:id/use-base-cv', async (req, res) => {
  try {
    const { id } = req.params
    const targetApp = await store.get(id)
    if (!targetApp) return res.status(404).json({ error: 'Postulación no encontrada' })

    const status = await checkAgentStatus()
    if (!status.baseCv?.exists) {
      return res.status(400).json({ error: 'No se encontró un CV base en my_cv/' })
    }

    const relCvPath = status.baseCv.relPath
    const updated = await store.update(id, {
      cv: relCvPath,
      event: `Asignado CV base estándar (${status.baseCv.filename})`,
    })
    res.json({ ok: true, cv: relCvPath, application: updated })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
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

function startServer(port = PORT, attemptsLeft = 10) {
  return new Promise((resolve, reject) => {
    function tryPort(p, attempts) {
      const server = app.listen(p, HOST)
      server.on('listening', () => {
        const activePort = server.address().port
        addAllowedPort(activePort)
        demo.setPort(activePort)
        console.log(`Job Hunter web: http://${HOST}:${activePort}`)
        resolve(server)
      })
      server.on('error', (err) => {
        if (err.code === 'EADDRINUSE' && attempts > 0) {
          console.warn(`Puerto ${p} ocupado. Probando puerto ${p + 1}...`)
          tryPort(p + 1, attempts - 1)
        } else {
          console.error(`No se pudo iniciar el servidor web: ${err.message}`)
          if (process.env.NODE_ENV === 'test') {
            reject(err)
          } else {
            process.exit(1)
          }
        }
      })
    }
    tryPort(port, attemptsLeft)
  })
}

const isDirectExecution = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
if (isDirectExecution && process.env.NODE_ENV !== 'test') {
  startServer(PORT)
}

export { app, startServer }

function isHttpUrl(value) {
  try {
    return ['http:', 'https:'].includes(new URL(value).protocol)
  } catch {
    return false
  }
}

function isSafePdfRelPath(rel) {
  if (!rel || typeof rel !== 'string') return false
  const parts = rel.split('/')
  if (parts.length < 1 || parts.length > 2) return false
  if (!parts.every((p) => /^[\w.\- ]+$/.test(p) && p !== '.' && p !== '..')) return false
  return parts[parts.length - 1].toLowerCase().endsWith('.pdf')
}

// Accepts "dir/name.pdf", "applications/folder/name.pdf", absolute paths, or "output/..." inside known CV folders.
function resolveCv(ref) {
  if (!ref) return null
  if (path.isAbsolute(ref)) {
    const norm = path.normalize(ref)
    const allowedRoots = [FILE_DIRS.applications, FILE_DIRS.cvs]
    const isUnderAllowed = allowedRoots.some((r) => norm.startsWith(r))
    if (isUnderAllowed && norm.toLowerCase().endsWith('.pdf') && existsSync(norm)) {
      return norm
    }
  }
  let parts = String(ref).replace(/\\/g, '/').split('/').filter(Boolean)
  if (parts[0] === 'output' && (parts[1] === 'applications' || parts[1] === 'cvs')) {
    parts = parts.slice(1)
  }
  const [dir, ...rest] = parts
  const rel = rest.join('/')
  const base = FILE_DIRS[dir]
  if (!base || !isSafePdfRelPath(rel)) return null
  const full = path.join(base, ...rest)
  return existsSync(full) ? full : null
}
