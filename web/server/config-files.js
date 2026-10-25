import fs from 'node:fs/promises'
import { existsSync } from 'node:fs'
import path from 'node:path'

const YES_NO = ['Yes', 'No']
const PERIODS = ['monthly', 'annual']
const PLATFORMS = ['ashby', 'greenhouse', 'lever']
const BACKUPS_KEPT = 5

export class ValidationError extends Error {}

export function createConfigFiles({ root }) {
  const configDir = path.join(root, 'config')
  const backupDir = path.join(root, 'output', 'backups')
  const profileFile = path.join(configDir, 'profile.json')
  const exclusionsFile = path.join(configDir, 'exclusions.py')
  const exclusionsJsonFile = path.join(configDir, 'exclusions.json')

  // Read-modify-write cycles on these files are serialized, like the applications store.
  let queue = Promise.resolve()
  const serialize = (fn) => {
    const run = queue.then(fn)
    queue = run.catch(() => {})
    return run
  }

  // personal config lives outside git; backups go to the ignored output/ folder
  async function backup(file) {
    try {
      await fs.mkdir(backupDir, { recursive: true })
      const stamp = new Date().toISOString().replace(/[:.]/g, '-')
      await fs.copyFile(file, path.join(backupDir, `${path.basename(file)}.${stamp}`))
      const mine = (await fs.readdir(backupDir)).filter((n) => n.startsWith(path.basename(file) + '.')).sort()
      for (const old of mine.slice(0, -BACKUPS_KEPT)) await fs.rm(path.join(backupDir, old), { force: true })
    } catch (err) {
      if (err.code !== 'ENOENT') throw err
    }
  }

  async function writeAtomic(file, text) {
    const tmp = `${file}.tmp`
    await fs.writeFile(tmp, text, 'utf-8')
    await fs.rename(tmp, file)
  }

  // ---------------- profile ----------------
  async function readProfile() {
    try {
      return JSON.parse(await fs.readFile(profileFile, 'utf-8'))
    } catch (err) {
      if (err.code !== 'ENOENT') throw err
      return JSON.parse(await fs.readFile(path.join(configDir, 'profile.example.json'), 'utf-8'))
    }
  }

  const str = (v, field, { required = false, max = 300 } = {}) => {
    const s = v === null || v === undefined ? '' : String(v).trim()
    if (required && !s) throw new ValidationError(`"${field}" es obligatorio`)
    if (s.length > max) throw new ValidationError(`"${field}" es demasiado largo`)
    return s
  }
  const oneOf = (v, allowed, field) => {
    if (!allowed.includes(v)) throw new ValidationError(`"${field}" debe ser ${allowed.join(' o ')}`)
    return v
  }
  const intOrNull = (v, field) => {
    if (v === null || v === undefined || v === '') return null
    const n = Number(v)
    if (!Number.isInteger(n) || n < 0) throw new ValidationError(`"${field}" debe ser un entero positivo`)
    return n
  }
  const list = (v, field) => {
    if (!Array.isArray(v)) throw new ValidationError(`"${field}" debe ser una lista`)
    return [...new Set(v.map((x) => str(x, field, { max: 80 })).filter(Boolean))]
  }

  function validateProfile(input) {
    const p = input?.personal_info ?? {}
    const s = input?.search_criteria ?? {}
    const pr = input?.preferences ?? {}
    const a = input?.ats_settings ?? {}
    const platforms = list(a.enabled_platforms ?? [], 'ats_settings.enabled_platforms')
    for (const pl of platforms) oneOf(pl, PLATFORMS, 'ats_settings.enabled_platforms')

    const dependentSalary = intOrNull(pr.dependent_salary_usd ?? pr.desired_salary_usd, 'Salario empleado dependiente')
    const contractorSalary = intOrNull(pr.contractor_salary_usd, 'Salario contractor')
    const desiredSalary = intOrNull(pr.desired_salary_usd ?? dependentSalary, 'Salario deseado')

    return {
      personal_info: {
        full_name: str(p.full_name, 'Nombre completo', { required: true }),
        email: str(p.email, 'Email', { required: true }),
        phone: str(p.phone, 'Teléfono', { required: true }),
        location: str(p.location, 'Ubicación', { required: true }),
        linkedin_url: str(p.linkedin_url, 'LinkedIn', { required: true }),
        github_url: str(p.github_url, 'GitHub'),
        portfolio_url: str(p.portfolio_url, 'Portfolio'),
        current_company: str(p.current_company, 'Empresa actual'),
        years_of_experience: intOrNull(p.years_of_experience, 'Años de experiencia'),
        requires_us_visa_sponsorship: oneOf(p.requires_us_visa_sponsorship ?? 'No', YES_NO, 'requires_us_visa_sponsorship'),
      },
      search_criteria: {
        target_roles: list(s.target_roles ?? [], 'Roles objetivo'),
        keywords: list(s.keywords ?? [], 'Keywords'),
        location_keywords: list(s.location_keywords ?? [], 'Ubicaciones'),
        max_years_of_experience: intOrNull(s.max_years_of_experience, 'Tope máximo de años de experiencia'),
        min_salary_usd: intOrNull(s.min_salary_usd, 'Salario mínimo'),
      },
      preferences: {
        dependent_salary_usd: dependentSalary,
        contractor_salary_usd: contractorSalary,
        desired_salary_usd: desiredSalary,
        salary_period: oneOf(pr.salary_period ?? 'monthly', PERIODS, 'salary_period'),
        notice_period: str(pr.notice_period, 'Disponibilidad', { required: true }),
        english_level: str(pr.english_level, 'Nivel de inglés'),
        legally_authorized_to_work: oneOf(pr.legally_authorized_to_work ?? 'Yes', YES_NO, 'legally_authorized_to_work'),
      },
      ats_settings: {
        enabled_platforms: platforms,
        auto_upload_resume: Boolean(a.auto_upload_resume),
        stealth_mode: Boolean(a.stealth_mode),
      },
    }
  }

  function writeProfile(input) {
    const valid = validateProfile(input)
    return serialize(async () => {
      const current = await readProfile()
      // Keep any keys this form doesn't know about, section by section.
      const merged = { ...current }
      for (const [section, values] of Object.entries(valid)) merged[section] = { ...(current[section] ?? {}), ...values }
      await backup(profileFile)
      await writeAtomic(profileFile, JSON.stringify(merged, null, 2) + '\n')
      return merged
    })
  }

  // ---------------- exclusions (config/exclusions.py) ----------------
  // The file is generated in a fixed shape: one  "slug": "reason",  line per entry.
  const ENTRY_RE = /^\s*"((?:[^"\\]|\\.)*)"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,?\s*(?:#.*)?$/
  const unquote = (s) => JSON.parse(`"${s}"`)

  function parseExclusions(source) {
    const dict = source.match(/EXCLUSION_REASONS\s*(?::[^=\n]+)?=\s*\{([\s\S]*?)^\}/m)
    if (dict) {
      return dict[1]
        .split('\n')
        .map((line) => line.match(ENTRY_RE))
        .filter(Boolean)
        .map((m) => ({ company: unquote(m[1]), reason: unquote(m[2]) }))
    }
    // Legacy format: a plain EXCLUDED_COMPANIES list without reasons.
    const legacy = source.match(/EXCLUDED_COMPANIES\s*(?::[^=\n]+)?=\s*\[([\s\S]*?)^\]/m)
    if (!legacy) return []
    return legacy[1]
      .split('\n')
      .filter((line) => !line.trim().startsWith('#'))
      .flatMap((line) => [...line.matchAll(/"((?:[^"\\]|\\.)*)"/g)].map((m) => ({ company: unquote(m[1]), reason: '' })))
  }

  function renderExclusions(entries) {
    const rows = entries.map((e) => `    ${JSON.stringify(e.company)}: ${JSON.stringify(e.reason)},\n`).join('')
    return `"""
Company Exclusion & Blacklist Configuration.

Each entry is "slug": "reason". A company is excluded when its lowercased name
contains the slug, so keep slugs specific. Managed from the web app ("Exclusiones"
page) and by the agent; one entry per line keeps both in sync.
"""

from typing import Dict, List

# Lowercased company slugs or substrings -> why they are excluded
EXCLUSION_REASONS: Dict[str, str] = {
${rows}}

# Plain list view of the slugs, used by the scanner
EXCLUDED_COMPANIES: List[str] = list(EXCLUSION_REASONS)

def is_excluded_company(company_name: str) -> bool:
    """Returns True if company_name matches any excluded pattern."""
    if not company_name:
        return False
    clean = company_name.lower().strip()
    return any(ex in clean for ex in EXCLUDED_COMPANIES)
`
  }

  async function readExclusions() {
    try {
      if (existsSync(exclusionsJsonFile)) {
        const data = JSON.parse(await fs.readFile(exclusionsJsonFile, 'utf-8'))
        if (Array.isArray(data)) return data
        if (typeof data === 'object' && data) {
          return Object.entries(data).map(([company, reason]) => ({ company, reason: String(reason || '') }))
        }
      }
      return parseExclusions(await fs.readFile(exclusionsFile, 'utf-8'))
    } catch (err) {
      if (err.code === 'ENOENT') return []
      throw err
    }
  }

  function normalizeCompany(value) {
    const company = str(value, 'Empresa', { required: true, max: 100 }).toLowerCase()
    if (/[\r\n]/.test(company)) throw new ValidationError('La empresa no puede tener saltos de línea')
    return company
  }

  // Applies `change(entries)` to the current file contents and writes the result back.
  function mutateExclusions(change) {
    return serialize(async () => {
      const entries = await readExclusions()
      const prevJson = JSON.stringify(entries)
      const result = change(entries)
      const nextJson = JSON.stringify(entries)

      if (prevJson === nextJson) {
        return result
      }

      try {
        if (existsSync(exclusionsJsonFile)) await backup(exclusionsJsonFile)
        else if (existsSync(exclusionsFile)) await backup(exclusionsFile)
      } catch {
        // a missing backup must not block the edit
      }

      await writeAtomic(exclusionsJsonFile, JSON.stringify(entries, null, 2) + '\n')
      await writeAtomic(exclusionsFile, renderExclusions(entries))
      return result
    })
  }

  return {
    readProfile,
    writeProfile,
    readExclusions,

    addExclusion: ({ company, reason }) =>
      mutateExclusions((entries) => {
        const slug = normalizeCompany(company)
        if (entries.some((e) => e.company === slug)) throw new ValidationError(`"${slug}" ya está en la lista`)
        const entry = { company: slug, reason: str(reason, 'Motivo', { max: 300 }) }
        entries.push(entry)
        return entry
      }),

    updateExclusion: (current, { company, reason }) =>
      mutateExclusions((entries) => {
        const entry = entries.find((e) => e.company === String(current).toLowerCase())
        if (!entry) return null
        const slug = company === undefined ? entry.company : normalizeCompany(company)
        if (slug !== entry.company && entries.some((e) => e.company === slug)) {
          throw new ValidationError(`"${slug}" ya está en la lista`)
        }
        entry.company = slug
        if (reason !== undefined) entry.reason = str(reason, 'Motivo', { max: 300 })
        return entry
      }),

    removeExclusion: (company) =>
      mutateExclusions((entries) => {
        const idx = entries.findIndex((e) => e.company === String(company).toLowerCase())
        if (idx === -1) return false
        entries.splice(idx, 1)
        return true
      }),
  }
}
