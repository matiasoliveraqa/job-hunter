import path from 'node:path'
import { existsSync } from 'node:fs'
import fs from 'node:fs/promises'
import {
  ROOT,
  checkCommandAvailable,
  queryAnthropicApi,
  queryOpenAiCompatibleApi,
  queryGeminiApi,
  queryClaude,
  queryAgy,
  queryCodex,
} from './api-clients.js'

export const AI_SETTINGS_FILE = path.join(ROOT, 'config', 'ai_settings.json')

export async function readAiSettings() {
  try {
    if (existsSync(AI_SETTINGS_FILE)) {
      return JSON.parse(await fs.readFile(AI_SETTINGS_FILE, 'utf-8'))
    }
  } catch (e) {
    console.warn('[AI Settings] Failed to read ai_settings.json:', e.message)
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

export async function checkBaseCv() {
  const myCvDir = path.join(ROOT, 'my_cv')
  if (existsSync(myCvDir)) {
    try {
      const files = await fs.readdir(myCvDir)
      const pdfs = files.filter((f) => f.toLowerCase().endsWith('.pdf') && !f.startsWith('skills_inventory'))
      if (pdfs.length) {
        return {
          exists: true,
          filename: pdfs[0],
          relPath: `my_cv/${pdfs[0]}`,
        }
      }
    } catch {
      // Fall through to demo CV fallback
    }
  }

  // Fallback to tracked demo CV when no user CV is present (e.g. CI environments, fresh clones)
  const demoCv = path.join(ROOT, 'web', 'demo', 'demo_cv.pdf')
  if (existsSync(demoCv)) {
    return {
      exists: true,
      filename: 'demo_cv.pdf',
      relPath: 'web/demo/demo_cv.pdf',
    }
  }

  return { exists: false, filename: null, relPath: null }
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
    } catch (e) { console.warn('[Auto] DeepSeek API failed:', e.message) }
  }

  if (settings.kimiApiKey && settings.kimiApiKey.startsWith('sk-')) {
    try {
      return await queryOpenAiCompatibleApi({
        prompt,
        apiKey: settings.kimiApiKey,
        baseUrl: 'https://api.moonshot.cn/v1',
        model: 'moonshot-v1-8k',
      })
    } catch (e) { console.warn('[Auto] Kimi API failed:', e.message) }
  }

  if (settings.customOpenAiBaseUrl) {
    try {
      return await queryOpenAiCompatibleApi({
        prompt,
        apiKey: settings.customOpenAiApiKey,
        baseUrl: settings.customOpenAiBaseUrl,
        model: settings.customOpenAiModel || 'gpt-4o',
      })
    } catch (e) { console.warn('[Auto] Custom OpenAI API failed:', e.message) }
  }

  if (settings.anthropicApiKey && settings.anthropicApiKey.startsWith('sk-ant-')) {
    try { return await queryAnthropicApi(prompt, settings.anthropicApiKey) } catch (e) { console.warn('[Auto] Anthropic API failed:', e.message) }
  }
  if (settings.openaiApiKey && settings.openaiApiKey.startsWith('sk-')) {
    try {
      return await queryOpenAiCompatibleApi({
        prompt,
        apiKey: settings.openaiApiKey,
        baseUrl: 'https://api.openai.com/v1',
        model: 'gpt-4o',
      })
    } catch (e) { console.warn('[Auto] OpenAI API failed:', e.message) }
  }
  if (settings.geminiApiKey && settings.geminiApiKey.length > 15) {
    try { return await queryGeminiApi(prompt, settings.geminiApiKey) } catch (e) { console.warn('[Auto] Gemini API failed:', e.message) }
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
