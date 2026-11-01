import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { existsSync } from 'node:fs'
import { createStore, STATUSES } from './store.js'
import { createDemo } from './demo.js'
import { createConfigFiles, ValidationError } from './config-files.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
export const ROOT = path.resolve(__dirname, '..', '..')
export const DIST = path.resolve(__dirname, '..', 'dist')
export const PORT = Number(process.env.PORT) || 3100
export const HOST = '127.0.0.1'

export function detectPythonBin(root) {
  if (process.env.PYTHON_BIN) return process.env.PYTHON_BIN
  const candidates = [
    path.join(root, 'venv', 'Scripts', 'python.exe'),
    path.join(root, 'venv', 'bin', 'python3'),
    path.join(root, 'venv', 'bin', 'python'),
    path.join(root, '.venv', 'Scripts', 'python.exe'),
    path.join(root, '.venv', 'bin', 'python3'),
    path.join(root, '.venv', 'bin', 'python'),
  ]
  for (const candidate of candidates) {
    if (existsSync(candidate)) return candidate
  }
  return process.platform === 'win32' ? 'python' : 'python3'
}

export const PYTHON_BIN = detectPythonBin(ROOT)

export const FILE_DIRS = {
  applications: path.join(ROOT, 'output', 'applications'),
  cvs: path.join(ROOT, 'output', 'cvs'),
  output: path.join(ROOT, 'output'),
  my_cv: path.join(ROOT, 'my_cv'),
}

export const demo = createDemo({ root: ROOT, host: HOST, port: PORT })
export const configFiles = createConfigFiles({ root: ROOT })
export const store = createStore(path.join(ROOT, 'output', 'applications.json'))

export const allowedHosts = new Set(
  [PORT, 5173].flatMap((p) => [`127.0.0.1:${p}`, `localhost:${p}`]),
)

export function addAllowedPort(p) {
  const portNum = Number(p)
  if (portNum > 0) {
    allowedHosts.add(`127.0.0.1:${portNum}`)
    allowedHosts.add(`localhost:${portNum}`)
  }
}

export const ALLOWED_ATS_DOMAINS = [
  'greenhouse.io',
  'boards.greenhouse.io',
  'job-boards.greenhouse.io',
  'ashbyhq.com',
  'jobs.ashbyhq.com',
  'lever.co',
  'jobs.lever.co',
  'workable.com',
  'apply.workable.com',
  'jobs.workable.com',
  'breezy.hr',
  'recruitee.com',
  'careers.recruitee.com',
  'bamboohr.com',
  'bamboohr.co.uk',
]

export function isAllowedAtsHost(urlString) {
  try {
    const parsed = new URL(urlString)
    const hostname = parsed.hostname.toLowerCase()
    return ALLOWED_ATS_DOMAINS.some((allowed) => hostname === allowed || hostname.endsWith(`.${allowed}`))
  } catch {
    return false
  }
}

export function isHttpUrl(value) {
  try {
    return ['http:', 'https:'].includes(new URL(value).protocol)
  } catch {
    return false
  }
}

export function isSafePdfRelPath(rel) {
  if (!rel || typeof rel !== 'string') return false
  const parts = rel.split('/')
  if (parts.length < 1 || parts.length > 2) return false
  if (!parts.every((p) => /^[\w.\- ]+$/.test(p) && p !== '.' && p !== '..')) return false
  return parts[parts.length - 1].toLowerCase().endsWith('.pdf')
}

export function resolveCv(ref) {
  if (!ref) return null
  if (path.isAbsolute(ref)) {
    const norm = path.normalize(ref)
    const allowedRoots = [FILE_DIRS.applications, FILE_DIRS.cvs]
    const isUnderAllowed = allowedRoots.some((r) => norm.startsWith(r))
    if (isUnderAllowed && norm.toLowerCase().endsWith('.pdf') && existsSync(norm)) {
      return norm
    }
  }
  let parts = String(ref).replace(/\\/g, '/').split('/').filter(Boolean)
  if (parts[0] === 'output' && (parts[1] === 'applications' || parts[1] === 'cvs')) {
    parts = parts.slice(1)
  }
  const [dir, ...rest] = parts
  const rel = rest.join('/')
  const base = FILE_DIRS[dir]
  if (!base || !isSafePdfRelPath(rel)) return null
  const full = path.join(base, ...rest)
  return existsSync(full) ? full : null
}

export { STATUSES, ValidationError }
