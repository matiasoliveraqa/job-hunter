import path from 'node:path'
import os from 'node:os'
import fs from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { createSafeRouter } from '../router-utils.js'
import { store, STATUSES, demo, isHttpUrl, isAllowedAtsHost, FILE_DIRS } from '../context.js'
import { checkAgentStatus } from '../agent-adapter.js'

export const applicationsRouter = createSafeRouter()

applicationsRouter.get('/api/applications', async (_req, res) => {
  res.json(await store.list())
})

applicationsRouter.post('/api/applications', async (req, res) => {
  const { company, role, url, status, demo: wantsDemo } = req.body ?? {}
  if (!company?.trim() || !role?.trim()) return res.status(400).json({ error: 'company y role son obligatorios' })
  if (url && !isHttpUrl(url)) return res.status(400).json({ error: 'url inválida' })
  if (status !== undefined && !['pending', 'applied'].includes(status)) return res.status(400).json({ error: 'status inválido' })

  const isDemoUrl = Boolean(url) && demo.isMockUrl(url)
  if (wantsDemo === true && !isDemoUrl) return res.status(400).json({ error: 'La demo solo admite publicaciones de prueba' })
  if (url && !isDemoUrl && !isAllowedAtsHost(url)) {
    return res.status(400).json({
      error: 'Dominio no permitido. Por seguridad de tus datos, solo se permite registrar postulaciones en dominios oficiales de plataformas ATS soportadas (Greenhouse, Ashby, Lever, Workable, Breezy, Recruitee, BambooHR).',
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

applicationsRouter.post('/api/applications/clear-demos', async (_req, res) => {
  res.json({ removed: await store.removeDemos() })
})

applicationsRouter.patch('/api/applications/:id', async (req, res) => {
  const { status, reason } = req.body ?? {}
  if (status !== undefined && !STATUSES.includes(status)) return res.status(400).json({ error: 'status inválido' })
  if (status === 'rejected' && !(reason ?? '').trim()) {
    return res.status(400).json({ error: 'Indica el motivo del rechazo' })
  }
  const item = await store.update(req.params.id, req.body ?? {})
  item ? res.json(item) : res.status(404).json({ error: 'No encontrada' })
})

applicationsRouter.delete('/api/applications/:id', async (req, res) => {
  ;(await store.remove(req.params.id)) ? res.status(204).end() : res.status(404).json({ error: 'No encontrada' })
})

applicationsRouter.post('/api/applications/:id/open-folder', async (req, res) => {
  const appItem = await store.get(req.params.id)
  if (!appItem) return res.status(404).json({ error: 'Postulación no encontrada' })

  let folderName = ''
  if (appItem.cv && typeof appItem.cv === 'string' && appItem.cv.startsWith('applications/')) {
    const parts = appItem.cv.split('/')
    if (parts.length > 2) folderName = parts[1]
  }
  if (!folderName && appItem.notes) {
    const match = appItem.notes.match(/Carpeta:\s*([^\s\r\n]+)/)
    if (match) folderName = match[1]
  }

  const applicationsRoot = FILE_DIRS.applications
  let folderPath = null

  if (folderName) {
    const cand = path.join(applicationsRoot, folderName)
    if (existsSync(cand)) folderPath = cand
  }

  if (!folderPath) {
    const compSlug = (appItem.company || '').toLowerCase().replace(/[^a-z0-9]+/g, '')
    if (compSlug && existsSync(applicationsRoot)) {
      const entries = await fs.readdir(applicationsRoot, { withFileTypes: true }).catch(() => [])
      const found = entries.find((e) => e.isDirectory() && e.name.toLowerCase().replace(/[^a-z0-9]+/g, '').includes(compSlug))
      if (found) {
        folderPath = path.join(applicationsRoot, found.name)
        folderName = found.name
      }
    }
  }

  if (!folderPath && folderName) {
    const docCvPath = path.join(os.homedir(), 'Documents', 'CV', folderName)
    if (existsSync(docCvPath)) folderPath = docCvPath
  }

  if (!folderPath) {
    const ym = new Date().toISOString().slice(0, 7)
    const sanitize = (s) => (s || '').replace(/[^a-zA-Z0-9_-]+/g, '_').replace(/^_+|_+$/g, '')
    const cSlug = sanitize(appItem.company) || 'Company'
    const rSlug = sanitize(appItem.role) || 'Role'
    folderName = `${ym}_${cSlug}_${rSlug}`
    folderPath = path.join(applicationsRoot, folderName)
    await fs.mkdir(folderPath, { recursive: true })
  }

  const resolved = path.resolve(folderPath)
  const allowedRoots = [path.resolve(applicationsRoot), path.resolve(os.homedir(), 'Documents', 'CV')]
  const isAllowed = allowedRoots.some((r) => resolved === r || resolved.startsWith(r + path.sep))
  if (!isAllowed) {
    return res.status(403).json({ error: 'Ruta no permitida' })
  }

  const platform = process.platform
  let cmd = 'xdg-open'
  let args = [resolved]
  if (platform === 'win32') {
    cmd = 'explorer'
    args = [resolved]
  } else if (platform === 'darwin') {
    cmd = 'open'
    args = [resolved]
  }

  try {
    const child = spawn(cmd, args, { detached: true, stdio: 'ignore' })
    child.unref()
    child.on('error', (err) => {
      console.warn('[open-app-folder] Error invoking command:', cmd, err.message)
    })
    res.json({ ok: true, path: resolved, folderName, platform })
  } catch (err) {
    res.status(500).json({ error: 'No se pudo abrir la carpeta en el sistema', path: resolved })
  }
})

applicationsRouter.post('/api/applications/:id/use-base-cv', async (req, res) => {
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
