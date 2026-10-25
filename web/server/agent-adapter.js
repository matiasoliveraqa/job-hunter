import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { existsSync } from 'node:fs'
import fs from 'node:fs/promises'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..', '..')

const SYSTEM_RULES = `You are a professional ATS resume specialist.
CRITICAL EXECUTION RULE:
- DO NOT CALL ANY TOOLS OR RUN COMMANDS. DO NOT EXPLORE THE FILESYSTEM.
- All candidate information, inventory, and templates are provided in this prompt.
- You are operating strictly as a text generator. Output the final response directly.

CRITICAL RULES FOR CV GENERATION:
1. STRICT TRUTH & FIDELITY: Never invent companies, dates, certifications, degrees, or tools outside the candidate's actual profile and inventory.
2. HUMAN WRITING RULES (Wikipedia:Signs_of_AI_writing):
   - Never use AI vocabulary words: additionally, align with, boasts, bolstered, crucial, cutting-edge, deep dive, delve, diverse array, elevate, emphasizing, encompassing, enduring, enhance, enhancing, fostering, cultivating, garner, groundbreaking, highlight, highlighting, interplay, intricate, intricacies, landscape, leverage, leveraging, meticulous, meticulously, mission-critical, pivotal, profound, proven track record, renowned, resonate with, robust, rock-solid, seamlessly, showcase, showcasing, spearheaded, streamlined, tapestry, testament, underscore, underscoring, valuable insights, vibrant.
   - No superficial present-participle tails (-ing) at the end of sentences ("...integrated Playwright into GitHub Actions, ensuring high reliability"). End sentences with a period.
   - No puffery, legacy clichés, or significance statements ("stands as a testament", "plays a crucial role", "evolving landscape", "passion for excellence").
   - No negative parallelisms ("Not only X, but also Y", "Not X, but Y").
   - Use simple copulatives: is, are, has, uses, built, tested.
   - No em dashes ("—"). Use commas or parentheses.
   - Use straight quotes (" and '), never curly quotes.
3. ROLE TITLE RESTRICTIONS:
   - Never use "Lead", "Principal", "Manager", "Head", or "Director" in the CV title or header.
   - Use "QA Automation Engineer" or "QA Engineer" (or the specific technical title matching the role without seniority inflation).
`

function buildCleanEnv() {
  const env = { ...process.env }
  delete env.ANTHROPIC_API_KEY
  delete env.ANTHROPIC_AUTH_TOKEN

  const venvBins = [
    path.join(ROOT, 'venv', 'bin'),
    path.join(ROOT, 'venv', 'Scripts'),
    path.join(ROOT, '.venv', 'bin'),
    path.join(ROOT, '.venv', 'Scripts'),
  ].filter((p) => existsSync(p))

  if (venvBins.length && env.PATH) {
    env.PATH = [...venvBins, env.PATH].join(path.delimiter)
  }
  return env
}

async function runTextCommand(bin, args, input = '', timeoutMs = 180000) {
  return new Promise((resolve, reject) => {
    const child = spawn(bin, args, {
      cwd: ROOT,
      env: buildCleanEnv(),
      stdio: ['pipe', 'pipe', 'pipe'],
    })

    let stdout = ''
    let stderr = ''
    let timer = setTimeout(() => {
      child.kill('SIGTERM')
      reject(new Error(`Tiempo de espera agotado al ejecutar "${bin}" (${timeoutMs / 1000}s)`))
    }, timeoutMs)

    child.stdout.on('data', (d) => (stdout += d.toString('utf-8')))
    child.stderr.on('data', (d) => (stderr += d.toString('utf-8')))

    child.on('error', (err) => {
      clearTimeout(timer)
      reject(new Error(`No se pudo iniciar "${bin}": ${err.message}`))
    })

    child.on('close', (code) => {
      clearTimeout(timer)
      if (code === 0) {
        resolve(stdout.trim())
      } else {
        const msg = stderr.trim() || stdout.trim() || `Proceso terminó con código ${code}`
        reject(new Error(msg))
      }
    })

    if (input) {
      child.stdin.write(input)
    }
    child.stdin.end()
  })
}

const AI_SETTINGS_FILE = path.join(ROOT, 'config', 'ai_settings.json')

export async function readAiSettings() {
  try {
    if (existsSync(AI_SETTINGS_FILE)) {
      return JSON.parse(await fs.readFile(AI_SETTINGS_FILE, 'utf-8'))
    }
  } catch (e) {
    console.warn('[AI Settings] No se pudo leer ai_settings.json:', e.message)
  }
  return {
    provider: 'auto',
    anthropicApiKey: process.env.ANTHROPIC_API_KEY || '',
    openaiApiKey: process.env.OPENAI_API_KEY || '',
    geminiApiKey: process.env.GEMINI_API_KEY || '',
    deepseekApiKey: process.env.DEEPSEEK_API_KEY || '',
    kimiApiKey: process.env.KIMI_API_KEY || '',
    customOpenAiApiKey: process.env.CUSTOM_OPENAI_API_KEY || '',
    customOpenAiBaseUrl: process.env.CUSTOM_OPENAI_BASE_URL || '',
    customOpenAiModel: process.env.CUSTOM_OPENAI_MODEL || '',
  }
}

export async function writeAiSettings(settings) {
  const current = await readAiSettings()
  const updated = {
    ...current,
    provider: settings.provider || current.provider || 'auto',
    anthropicApiKey: settings.anthropicApiKey !== undefined ? settings.anthropicApiKey.trim() : (current.anthropicApiKey || ''),
    openaiApiKey: settings.openaiApiKey !== undefined ? settings.openaiApiKey.trim() : (current.openaiApiKey || ''),
    geminiApiKey: settings.geminiApiKey !== undefined ? settings.geminiApiKey.trim() : (current.geminiApiKey || ''),
    deepseekApiKey: settings.deepseekApiKey !== undefined ? settings.deepseekApiKey.trim() : (current.deepseekApiKey || ''),
    kimiApiKey: settings.kimiApiKey !== undefined ? settings.kimiApiKey.trim() : (current.kimiApiKey || ''),
    customOpenAiApiKey: settings.customOpenAiApiKey !== undefined ? settings.customOpenAiApiKey.trim() : (current.customOpenAiApiKey || ''),
    customOpenAiBaseUrl: settings.customOpenAiBaseUrl !== undefined ? settings.customOpenAiBaseUrl.trim() : (current.customOpenAiBaseUrl || ''),
    customOpenAiModel: settings.customOpenAiModel !== undefined ? settings.customOpenAiModel.trim() : (current.customOpenAiModel || ''),
  }
  const configDir = path.dirname(AI_SETTINGS_FILE)
  if (!existsSync(configDir)) {
    await fs.mkdir(configDir, { recursive: true })
  }
  await fs.writeFile(AI_SETTINGS_FILE, JSON.stringify(updated, null, 2) + '\n', 'utf-8')
  return updated
}

async function checkCommandAvailable(bin, args = ['--version'], timeoutMs = 2500) {
  return new Promise((resolve) => {
    try {
      const child = spawn(bin, args, {
        cwd: ROOT,
        env: buildCleanEnv(),
        stdio: ['ignore', 'pipe', 'pipe'],
      })
      let finished = false
      const timer = setTimeout(() => {
        if (!finished) {
          finished = true
          try { child.kill('SIGTERM') } catch {}
          resolve(false)
        }
      }, timeoutMs)

      child.on('error', () => {
        if (!finished) {
          finished = true
          clearTimeout(timer)
          resolve(false)
        }
      })
      child.on('close', (code) => {
        if (!finished) {
          finished = true
          clearTimeout(timer)
          resolve(code === 0)
        }
      })
    } catch {
      resolve(false)
    }
  })
}

export async function checkBaseCv() {
  const myCvDir = path.join(ROOT, 'my_cv')
  if (!existsSync(myCvDir)) {
    return { exists: false, filename: null, relPath: null }
  }
  try {
    const files = await fs.readdir(myCvDir)
    const pdfs = files.filter((f) => f.toLowerCase().endsWith('.pdf') && !f.startsWith('skills_inventory'))
    if (!pdfs.length) {
      return { exists: false, filename: null, relPath: null }
    }
    return {
      exists: true,
      filename: pdfs[0],
      relPath: `my_cv/${pdfs[0]}`,
    }
  } catch {
    return { exists: false, filename: null, relPath: null }
  }
}

async function queryAnthropicApi(prompt, apiKey) {
  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
      'content-type': 'application/json',
    },
    body: JSON.stringify({
      model: 'claude-3-5-sonnet-20241022',
      max_tokens: 4096,
      messages: [{ role: 'user', content: prompt }],
    }),
  })
  if (!res.ok) {
    const errText = await res.text()
    throw new Error(`Error Anthropic API (${res.status}): ${errText}`)
  }
  const data = await res.json()
  return data.content?.[0]?.text || ''
}

async function queryOpenAiCompatibleApi({ prompt, apiKey, baseUrl, model }) {
  const cleanBase = (baseUrl || 'https://api.openai.com/v1').replace(/\/+$/, '')
  const url = cleanBase.endsWith('/chat/completions')
    ? cleanBase
    : `${cleanBase}/chat/completions`

  const headers = {
    'Content-Type': 'application/json',
  }
  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`
  }

  const res = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      model: model || 'gpt-4o',
      messages: [{ role: 'user', content: prompt }],
    }),
  })

  if (!res.ok) {
    const errText = await res.text()
    throw new Error(`Error en API compatible (${res.status}): ${errText}`)
  }

  const data = await res.json()
  return data.choices?.[0]?.message?.content || ''
}

async function queryGeminiApi(prompt, apiKey) {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${encodeURIComponent(apiKey)}`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
    }),
  })
  if (!res.ok) {
    const errText = await res.text()
    throw new Error(`Error Google Gemini API (${res.status}): ${errText}`)
  }
  const data = await res.json()
  return data.candidates?.[0]?.content?.parts?.[0]?.text || ''
}

export async function checkAgentStatus() {
  const settings = await readAiSettings()
  const baseCv = await checkBaseCv()

  const [hasClaude, hasAgy, hasCodex] = await Promise.all([
    checkCommandAvailable(process.env.CLAUDE_BIN || 'claude', ['--version']),
    checkCommandAvailable(process.env.AGY_BIN || 'agy', ['--version']),
    checkCommandAvailable(process.env.CODEX_BIN || 'codex', ['--version']),
  ])

  const hasAnthropicApi = Boolean(settings.anthropicApiKey && settings.anthropicApiKey.startsWith('sk-ant-'))
  const hasOpenAiApi = Boolean(settings.openaiApiKey && settings.openaiApiKey.startsWith('sk-'))
  const hasGeminiApi = Boolean(settings.geminiApiKey && settings.geminiApiKey.length > 15)
  const hasDeepSeekApi = Boolean(settings.deepseekApiKey && settings.deepseekApiKey.startsWith('sk-'))
  const hasKimiApi = Boolean(settings.kimiApiKey && settings.kimiApiKey.startsWith('sk-'))
  const hasCustomOpenAi = Boolean(
    settings.customOpenAiBaseUrl &&
    (settings.customOpenAiApiKey || settings.customOpenAiBaseUrl.includes('localhost') || settings.customOpenAiBaseUrl.includes('127.0.0.1'))
  )

  const providers = [
    { id: 'claude', name: 'Claude Code CLI', available: hasClaude, type: 'cli' },
    { id: 'agy', name: 'Antigravity / Gemini CLI', available: hasAgy, type: 'cli' },
    { id: 'codex', name: 'Codex CLI', available: hasCodex, type: 'cli' },
    { id: 'deepseek_api', name: 'DeepSeek API', available: hasDeepSeekApi, type: 'api', configured: Boolean(settings.deepseekApiKey) },
    { id: 'kimi_api', name: 'Kimi (Moonshot) API', available: hasKimiApi, type: 'api', configured: Boolean(settings.kimiApiKey) },
    { id: 'anthropic_api', name: 'Anthropic Claude (API Key)', available: hasAnthropicApi, type: 'api', configured: Boolean(settings.anthropicApiKey) },
    { id: 'openai_api', name: 'OpenAI (API Key)', available: hasOpenAiApi, type: 'api', configured: Boolean(settings.openaiApiKey) },
    { id: 'gemini_api', name: 'Google Gemini (API Key)', available: hasGeminiApi, type: 'api', configured: Boolean(settings.geminiApiKey) },
    { id: 'custom_openai_api', name: 'Personalizado (OpenAI compatible / Ollama / Groq)', available: hasCustomOpenAi, type: 'api', configured: Boolean(settings.customOpenAiBaseUrl) },
  ]

  let activeId = 'none'
  let activeName = 'Sin motor de IA'
  const pref = settings.provider || 'auto'

  if (pref !== 'auto') {
    const match = providers.find((p) => p.id === pref)
    if (match && match.available) {
      activeId = match.id
      activeName = match.name
    }
  }

  const isAntigravity = Boolean(
    process.env.ANTIGRAVITY_AGENT ||
    process.env.ANTIGRAVITY_LS_VERSION ||
    process.env.ANTIGRAVITY_LS_ADDRESS
  )

  if (activeId === 'none') {
    if (isAntigravity && hasAgy) { activeId = 'agy'; activeName = 'Gemini (Antigravity)' }
    else if (hasDeepSeekApi) { activeId = 'deepseek_api'; activeName = 'DeepSeek API' }
    else if (hasKimiApi) { activeId = 'kimi_api'; activeName = 'Kimi (Moonshot) API' }
    else if (hasGeminiApi) { activeId = 'gemini_api'; activeName = 'Google Gemini API' }
    else if (hasAnthropicApi) { activeId = 'anthropic_api'; activeName = 'Anthropic Claude API' }
    else if (hasOpenAiApi) { activeId = 'openai_api'; activeName = 'OpenAI API' }
    else if (hasCustomOpenAi) { activeId = 'custom_openai_api'; activeName = 'API Compatible Personalizada' }
    else if (hasAgy) { activeId = 'agy'; activeName = 'Gemini (Agy CLI)' }
    else if (hasClaude) { activeId = 'claude'; activeName = 'Claude Code CLI' }
    else if (hasCodex) { activeId = 'codex'; activeName = 'Codex CLI' }
  }

  const connected = activeId !== 'none'

  return {
    connected,
    activeProvider: activeId,
    activeProviderName: activeName,
    preferredProvider: pref,
    providers,
    baseCv,
  }
}

async function queryClaude(prompt) {
  const bin = process.env.CLAUDE_BIN || 'claude'
  const args = [
    '-p',
    '--output-format', 'text',
    '--tools', '',
    '--no-session-persistence',
  ]
  return runTextCommand(bin, args, prompt)
}

async function queryAgy(prompt) {
  const bin = process.env.AGY_BIN || 'agy'
  const args = [
    '--output-format', 'text',
    '--disable-slash-commands',
    '--dangerously-skip-permissions',
    '-p',
    prompt,
  ]
  return runTextCommand(bin, args)
}

async function queryCodex(prompt) {
  const bin = process.env.CODEX_BIN || 'codex'
  const args = ['exec', '--no-tools', prompt]
  return runTextCommand(bin, args)
}

export async function queryIsolatedModel(prompt, preferredProvider = 'auto') {
  const settings = await readAiSettings()
  const provider = preferredProvider === 'auto'
    ? (settings.provider || process.env.AGENT_PROVIDER || 'auto')
    : preferredProvider

  if (provider === 'deepseek_api') {
    if (!settings.deepseekApiKey) throw new Error('No hay clave de DeepSeek API configurada')
    return queryOpenAiCompatibleApi({
      prompt,
      apiKey: settings.deepseekApiKey,
      baseUrl: 'https://api.deepseek.com/v1',
      model: 'deepseek-chat',
    })
  }

  if (provider === 'kimi_api') {
    if (!settings.kimiApiKey) throw new Error('No hay clave de Kimi (Moonshot) API configurada')
    return queryOpenAiCompatibleApi({
      prompt,
      apiKey: settings.kimiApiKey,
      baseUrl: 'https://api.moonshot.cn/v1',
      model: 'moonshot-v1-8k',
    })
  }

  if (provider === 'custom_openai_api') {
    if (!settings.customOpenAiBaseUrl) throw new Error('No se definió la URL base del proveedor compatible')
    return queryOpenAiCompatibleApi({
      prompt,
      apiKey: settings.customOpenAiApiKey,
      baseUrl: settings.customOpenAiBaseUrl,
      model: settings.customOpenAiModel || 'gpt-4o',
    })
  }

  if (provider === 'anthropic_api') {
    if (!settings.anthropicApiKey) throw new Error('No hay clave de Anthropic API configurada')
    return queryAnthropicApi(prompt, settings.anthropicApiKey)
  }
  if (provider === 'openai_api') {
    if (!settings.openaiApiKey) throw new Error('No hay clave de OpenAI API configurada')
    return queryOpenAiCompatibleApi({
      prompt,
      apiKey: settings.openaiApiKey,
      baseUrl: 'https://api.openai.com/v1',
      model: 'gpt-4o',
    })
  }
  if (provider === 'gemini_api') {
    if (!settings.geminiApiKey) throw new Error('No hay clave de Google Gemini API configurada')
    return queryGeminiApi(prompt, settings.geminiApiKey)
  }

  if (provider === 'agy') {
    try {
      return await queryAgy(prompt)
    } catch {
      return queryClaude(prompt)
    }
  }

  if (provider === 'codex') {
    try {
      return await queryCodex(prompt)
    } catch {
      try {
        return await queryClaude(prompt)
      } catch {
        return queryAgy(prompt)
      }
    }
  }

  if (provider === 'claude') {
    try {
      return await queryClaude(prompt)
    } catch {
      return queryAgy(prompt)
    }
  }

  // Provider is 'auto': check configured APIs first, then local CLIs
  if (settings.deepseekApiKey && settings.deepseekApiKey.startsWith('sk-')) {
    try {
      return await queryOpenAiCompatibleApi({
        prompt,
        apiKey: settings.deepseekApiKey,
        baseUrl: 'https://api.deepseek.com/v1',
        model: 'deepseek-chat',
      })
    } catch (e) { console.warn('[Auto] DeepSeek API falló:', e.message) }
  }

  if (settings.kimiApiKey && settings.kimiApiKey.startsWith('sk-')) {
    try {
      return await queryOpenAiCompatibleApi({
        prompt,
        apiKey: settings.kimiApiKey,
        baseUrl: 'https://api.moonshot.cn/v1',
        model: 'moonshot-v1-8k',
      })
    } catch (e) { console.warn('[Auto] Kimi API falló:', e.message) }
  }

  if (settings.customOpenAiBaseUrl) {
    try {
      return await queryOpenAiCompatibleApi({
        prompt,
        apiKey: settings.customOpenAiApiKey,
        baseUrl: settings.customOpenAiBaseUrl,
        model: settings.customOpenAiModel || 'gpt-4o',
      })
    } catch (e) { console.warn('[Auto] Custom OpenAI API falló:', e.message) }
  }

  if (settings.anthropicApiKey && settings.anthropicApiKey.startsWith('sk-ant-')) {
    try { return await queryAnthropicApi(prompt, settings.anthropicApiKey) } catch (e) { console.warn('[Auto] Anthropic API falló:', e.message) }
  }
  if (settings.openaiApiKey && settings.openaiApiKey.startsWith('sk-')) {
    try {
      return await queryOpenAiCompatibleApi({
        prompt,
        apiKey: settings.openaiApiKey,
        baseUrl: 'https://api.openai.com/v1',
        model: 'gpt-4o',
      })
    } catch (e) { console.warn('[Auto] OpenAI API falló:', e.message) }
  }
  if (settings.geminiApiKey && settings.geminiApiKey.length > 15) {
    try { return await queryGeminiApi(prompt, settings.geminiApiKey) } catch (e) { console.warn('[Auto] Gemini API falló:', e.message) }
  }

  const isAntigravity = Boolean(
    process.env.ANTIGRAVITY_AGENT ||
    process.env.ANTIGRAVITY_LS_VERSION ||
    process.env.ANTIGRAVITY_LS_ADDRESS
  )

  const cliFns = isAntigravity
    ? [queryAgy, queryClaude, queryCodex]
    : [queryAgy, queryClaude, queryCodex]

  for (const fn of cliFns) {
    try {
      return await fn(prompt)
    } catch {}
  }

  throw new Error(
    'No se detectó ningún motor de IA activo (Gemini, Claude, DeepSeek, Kimi o Codex). Puedes configurar una API Key en Mi perfil o usar tu CV base estándar directamente.'
  )
}

export function extractHtml(text) {
  if (!text) return ''
  const m = text.match(/```html\s*([\s\S]*?)```/i)
  if (m && m[1].trim()) return m[1].trim()
  const docMatch = text.match(/(<!DOCTYPE[\s\S]*<\/html>|<html[\s\S]*<\/html>)/i)
  if (docMatch && docMatch[1].trim()) return docMatch[1].trim()
  return text.trim()
}

export async function tailorCvHtml({
  jobTitle,
  company,
  jobDescription,
  profile,
  skillsInventory,
  baseTemplateHtml,
  provider = 'auto',
}) {
  const years = profile?.personal_info?.years_of_experience || 7
  const candidateName = profile?.personal_info?.full_name || 'Candidate'

  const prompt = `${SYSTEM_RULES}

TASK: Adapt the base HTML CV for the following job posting.
CANDIDATE: ${candidateName} (${years}+ years of experience).
TARGET COMPANY: ${company}
TARGET ROLE: ${jobTitle}

JOB DESCRIPTION:
${jobDescription || 'Standard software engineering and QA automation position.'}

MASTER SKILLS INVENTORY:
${skillsInventory || 'Extensive experience in Playwright, TypeScript, REST APIs, CI/CD, Allure TestOps, Postman, MySQL.'}

BASE HTML TEMPLATE:
${baseTemplateHtml}

INSTRUCTIONS:
1. Return ONLY the complete, tailored HTML code enclosed in a \`\`\`html ... \`\`\` block.
2. Keep the exact 1-page visual structure and CSS of the base template.
3. Highlight matching technical skills and projects that align with ${company}'s requirements.
4. Do not invent any tool, company, degree, or date.
5. Strictly adhere to the human writing rules (no AI-isms, no em dashes, no trailing -ing tails).
`

  const response = await queryIsolatedModel(prompt, provider)
  const extracted = extractHtml(response)
  if (!extracted || extracted.length < 100 || !extracted.includes('<html')) {
    console.error('[tailorCvHtml] Respuesta del modelo no válida como HTML. Longitud:', response?.length || 0, 'Snippet:', (response || '').slice(0, 300))
    throw new Error('El modelo generó una respuesta vacía o incompleta para el CV')
  }
  return extracted
}

export async function answerQuestion({
  question,
  jobDescription,
  profile,
  provider = 'auto',
}) {
  const prompt = `${SYSTEM_RULES}

TASK: Write a direct, factual answer for this job application question.
QUESTION: "${question}"
JOB CONTEXT: ${jobDescription || 'N/A'}
CANDIDATE: ${profile?.personal_info?.full_name || 'Candidate'} (${profile?.personal_info?.years_of_experience || 7}+ years of experience in QA / Software Engineering).

Write a concise, professional answer under 120 words. State concrete actions and facts. End sentences with a period.
`

  return queryIsolatedModel(prompt, provider)
}

export async function extractProfileFromCv(cvText, provider = 'auto') {
  const prompt = `${SYSTEM_RULES}

TASK: Extract candidate profile information from this CV text into pure JSON.
Return ONLY valid JSON without markdown code fences, headers, or conversational text.

REQUIRED JSON SCHEMA:
{
  "personal_info": {
    "full_name": "Candidate Full Name",
    "email": "email@example.com",
    "phone": "+123456789",
    "location": "City, Country",
    "linkedin_url": "https://linkedin.com/in/...",
    "github_url": "https://github.com/...",
    "portfolio_url": "https://...",
    "current_company": "Company Name",
    "years_of_experience": 7
  },
  "target_roles": ["Role 1", "Role 2"],
  "keywords": ["Skill 1", "Skill 2"]
}

CV TEXT:
${cvText}
`

  const response = await queryIsolatedModel(prompt, provider)
  let clean = response.trim()
  if (clean.startsWith('```')) {
    const lines = clean.split('\n')
    clean = lines.slice(1, lines[lines.length - 1].startsWith('```') ? -1 : undefined).join('\n').trim()
  }
  const match = clean.match(/\{[\s\S]*\}/)
  if (match) {
    try {
      return JSON.parse(match[0])
    } catch {
      // Fallback
    }
  }
  return JSON.parse(clean)
}
