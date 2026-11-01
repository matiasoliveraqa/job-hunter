import { randomUUID } from 'node:crypto'
import { spawn } from 'node:child_process'
import { createSafeRouter } from '../router-utils.js'
import {
  isHttpUrl,
  demo,
  isAllowedAtsHost,
  resolveCv,
  store,
  PYTHON_BIN,
  ROOT,
} from '../context.js'
import { checkBaseCv } from '../agent-adapter.js'

export const applyRouter = createSafeRouter()

export const launches = new Map()

applyRouter.post('/api/apply', async (req, res) => {
  const { url, cv, company: bodyCompany, role: bodyRole, applicationId, demo: wantsDemo } = req.body ?? {}
  if (!isHttpUrl(url)) return res.status(400).json({ error: 'url inválida' })

  // Mock postings are demos: always fictional profile and CV, whatever the UI sent.
  const isDemoUrl = demo.isMockUrl(url)
  if (wantsDemo === true && !isDemoUrl) return res.status(400).json({ error: 'La demo solo admite publicaciones de prueba' })

  if (!isDemoUrl && !isAllowedAtsHost(url)) {
    return res.status(400).json({
      error: 'Dominio no permitido. Por seguridad de tus datos, solo se permite autocompletar en dominios oficiales de plataformas ATS soportadas (Greenhouse, Ashby, Lever, Workable, Breezy, Recruitee, BambooHR).',
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

applyRouter.get('/api/apply', (_req, res) => {
  res.json([...launches.values()])
})
