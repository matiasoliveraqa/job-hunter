import path from 'node:path'
import fs from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { createSafeRouter } from '../router-utils.js'
import { configFiles, ROOT } from '../context.js'
import { extractProfileFromCv } from '../agent-adapter.js'

const execFileAsync = promisify(execFile)

export const profileRouter = createSafeRouter()

profileRouter.get('/api/profile', async (_req, res) => {
  res.json(await configFiles.readProfile())
})

profileRouter.put('/api/profile', async (req, res) => {
  res.json(await configFiles.writeProfile(req.body))
})

profileRouter.get('/api/profile/cv', async (_req, res) => {
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

profileRouter.post('/api/profile/upload-cv', async (req, res) => {
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
