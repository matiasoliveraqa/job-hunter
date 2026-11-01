import path from 'node:path'
import fs from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { createSafeRouter } from '../router-utils.js'
import { FILE_DIRS, isSafePdfRelPath } from '../context.js'

export const filesRouter = createSafeRouter()

export function sendPdfFile(req, res, dir, relName) {
  const base = FILE_DIRS[dir]
  if (!base || !isSafePdfRelPath(relName)) return res.status(400).end()
  res.sendFile(path.join(base, ...relName.split('/')), { headers: { 'Content-Type': 'application/pdf' } }, (err) => {
    if (err && !res.headersSent) res.status(404).end()
  })
}

filesRouter.get('/api/files', async (_req, res) => {
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

filesRouter.get('/files/:dir/:name', (req, res) => {
  sendPdfFile(req, res, req.params.dir, req.params.name)
})

filesRouter.get('/files/:dir/:sub/:name', (req, res) => {
  sendPdfFile(req, res, req.params.dir, `${req.params.sub}/${req.params.name}`)
})

filesRouter.post('/api/open-folder', async (req, res) => {
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
      console.warn('[open-folder] Error invoking command:', cmd, err.message)
    })
    res.json({ ok: true, path: folderPath, platform })
  } catch {
    res.status(500).json({ error: 'No se pudo abrir la carpeta en el sistema', path: folderPath })
  }
})
