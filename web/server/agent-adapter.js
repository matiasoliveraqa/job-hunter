import { spawn } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { existsSync } from 'node:fs'
import fs from 'node:fs/promises'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, '..', '..')

const SYSTEM_RULES = `You are a professional ATS resume specialist.
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

async function queryClaude(prompt) {
  const bin = process.env.CLAUDE_BIN || 'claude'
  const args = [
    '-p',
    '--output-format', 'text',
    '--tools', '', // Disables all execution tools completely
    '--no-session-persistence',
  ]
  return runTextCommand(bin, args, prompt)
}

async function queryAgy(prompt) {
  const bin = process.env.AGY_BIN || 'agy'
  const args = [
    '--output-format', 'text',
    '--disable-slash-commands',
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
  const provider = preferredProvider === 'auto'
    ? (process.env.AGENT_PROVIDER || 'claude')
    : preferredProvider

  if (provider === 'agy') {
    try {
      return await queryAgy(prompt)
    } catch (e) {
      return queryClaude(prompt)
    }
  }

  if (provider === 'codex') {
    try {
      return await queryCodex(prompt)
    } catch {
      // Fallback to claude or agy
      try {
        return await queryClaude(prompt)
      } catch {
        return queryAgy(prompt)
      }
    }
  }

  // Default: claude with fallback to agy
  try {
    return await queryClaude(prompt)
  } catch (err) {
    if (provider === 'auto' || /not logged in|not found|enoent/i.test(err.message)) {
      return queryAgy(prompt)
    }
    throw err
  }
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
