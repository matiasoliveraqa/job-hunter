import path from 'node:path'
import fs from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { spawn } from 'node:child_process'
import createDOMPurify from 'dompurify'
import { JSDOM } from 'jsdom'
import { createSafeRouter } from '../router-utils.js'
import { configFiles, ROOT, PYTHON_BIN, store } from '../context.js'
import {
  tailorCvHtml,
  checkAgentStatus,
  readAiSettings,
  writeAiSettings,
} from '../agent-adapter.js'

const domWindow = new JSDOM('').window
const DOMPurify = createDOMPurify(domWindow)

export const agentRouter = createSafeRouter()

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

agentRouter.post('/api/tailor-cv', async (req, res) => {
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

agentRouter.get('/api/agent/status', async (_req, res) => {
  try {
    const status = await checkAgentStatus()
    res.json(status)
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

agentRouter.get('/api/agent/config', async (_req, res) => {
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

agentRouter.post('/api/agent/config', async (req, res) => {
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
