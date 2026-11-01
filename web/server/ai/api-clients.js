import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { existsSync } from 'node:fs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
export const ROOT = path.resolve(__dirname, '..', '..', '..')

export function buildCleanEnv() {
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

export async function runTextCommand(bin, args, input = '', timeoutMs = 180000) {
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

export async function checkCommandAvailable(bin, args = ['--version'], timeoutMs = 2500) {
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

export async function queryAnthropicApi(prompt, apiKey) {
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

export async function queryOpenAiCompatibleApi({ prompt, apiKey, baseUrl, model }) {
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

export async function queryGeminiApi(prompt, apiKey) {
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

export async function queryClaude(prompt) {
  const bin = process.env.CLAUDE_BIN || 'claude'
  const args = [
    '-p',
    '--output-format', 'text',
    '--tools', '',
    '--no-session-persistence',
  ]
  return runTextCommand(bin, args, prompt)
}

export async function queryAgy(prompt) {
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

export async function queryCodex(prompt) {
  const bin = process.env.CODEX_BIN || 'codex'
  const args = ['exec', '--no-tools', prompt]
  return runTextCommand(bin, args)
}
