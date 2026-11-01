import path from 'node:path'
import fs from 'node:fs/promises'
import { existsSync, readFileSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { createSafeRouter } from '../router-utils.js'
import { ROOT, PYTHON_BIN } from '../context.js'

export const scanRouter = createSafeRouter()

let activeScanChild = null
let latestScanMatches = []
const initialScanResultsPath = path.join(ROOT, 'output', 'scan_results.json')
try {
  if (existsSync(initialScanResultsPath)) {
    const rawData = JSON.parse(readFileSync(initialScanResultsPath, 'utf-8'))
    if (Array.isArray(rawData)) latestScanMatches = rawData
  }
} catch {}

const scanState = {
  isScanning: false,
  checked: 0,
  total: 0,
  platform: '',
  company: '',
  errorCount: 0,
  startedAt: null,
}
const scanSubscribers = new Set()

export function broadcastScanEvent(evt) {
  const line = `data: ${JSON.stringify(evt)}\n\n`
  for (const res of scanSubscribers) {
    try {
      if (res.writable && !res.writableEnded) {
        res.write(line)
      } else {
        scanSubscribers.delete(res)
      }
    } catch {
      scanSubscribers.delete(res)
    }
  }
}

export function launchScanProcess({ roles, platforms, locations, maxYears, concurrency, allowCaptcha, geoScope, countries, workModes }) {
  if (activeScanChild) {
    try { activeScanChild.kill('SIGTERM') } catch {}
    activeScanChild = null
  }

  const args = ['-m', 'src.cli', 'scan', '--stream-json']
  if (Array.isArray(roles) && roles.length) {
    args.push('--roles', roles.join(','))
  }
  if (Array.isArray(platforms) && platforms.length) {
    args.push('--platforms', platforms.join(','))
  }
  if (Array.isArray(locations) && locations.length) {
    args.push('--locations', locations.join(','))
  }
  if (typeof maxYears === 'number' && maxYears >= 0) {
    args.push('--max-years', String(maxYears))
  }
  if (typeof concurrency === 'number' && concurrency > 0) {
    args.push('--concurrency', String(concurrency))
  }
  if (allowCaptcha === true) {
    args.push('--allow-captcha')
  }
  if (geoScope) {
    args.push('--geo-scope', String(geoScope))
  }
  if (Array.isArray(countries) && countries.length) {
    args.push('--countries', countries.join(','))
  }
  if (Array.isArray(workModes) && workModes.length) {
    args.push('--work-modes', workModes.join(','))
  }

  latestScanMatches = []
  Object.assign(scanState, {
    isScanning: true,
    checked: 0,
    total: 0,
    platform: '',
    company: '',
    errorCount: 0,
    startedAt: new Date().toISOString(),
  })

  broadcastScanEvent({ type: 'start' })

  const child = spawn(PYTHON_BIN, args, { cwd: ROOT, env: process.env, stdio: ['ignore', 'pipe', 'pipe'] })
  activeScanChild = child

  let stdoutBuf = ''
  child.stdout.on('data', (chunk) => {
    stdoutBuf += chunk.toString('utf-8')
    let nl
    while ((nl = stdoutBuf.indexOf('\n')) !== -1) {
      const line = stdoutBuf.slice(0, nl).trim()
      stdoutBuf = stdoutBuf.slice(nl + 1)
      if (!line) continue
      try {
        const parsed = JSON.parse(line)
        if (parsed.type === 'progress') {
          scanState.checked = parsed.checked
          scanState.total = parsed.total
          scanState.platform = parsed.platform
          scanState.company = parsed.company
        } else if (parsed.type === 'match' && parsed.posting) {
          latestScanMatches.push(parsed.posting)
        } else if (parsed.type === 'board_error') {
          scanState.errorCount++
        } else if (parsed.type === 'done') {
          scanState.isScanning = false
        }
        broadcastScanEvent(parsed)
      } catch {
        broadcastScanEvent({ type: 'raw', text: line })
      }
    }
  })

  child.stderr.on('data', (chunk) => {
    const errText = chunk.toString('utf-8').trim()
    if (errText) broadcastScanEvent({ type: 'log', message: errText })
  })

  child.on('close', (code) => {
    if (activeScanChild === child) {
      activeScanChild = null
      scanState.isScanning = false
    }
    broadcastScanEvent({ type: 'exit', code })
  })

  child.on('error', (err) => {
    if (activeScanChild === child) {
      activeScanChild = null
      scanState.isScanning = false
    }
    broadcastScanEvent({ type: 'error', error: err.message })
  })

  return child
}

scanRouter.get('/api/scan/status', (_req, res) => {
  res.json({
    ...scanState,
    matches: latestScanMatches,
  })
})

scanRouter.get('/api/scan/results', async (_req, res) => {
  const scanResultsPath = path.join(ROOT, 'output', 'scan_results.json')
  if (latestScanMatches.length > 0) {
    return res.json({ matches: latestScanMatches })
  }
  if (existsSync(scanResultsPath)) {
    try {
      const data = JSON.parse(await fs.readFile(scanResultsPath, 'utf-8'))
      return res.json({ matches: Array.isArray(data) ? data : [] })
    } catch {}
  }
  res.json({ matches: [] })
})

scanRouter.get('/api/scan/events', (req, res) => {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
  })

  scanSubscribers.add(res)
  res.write(`data: ${JSON.stringify({ type: 'sync', scanState, matches: latestScanMatches })}\n\n`)

  req.on('close', () => {
    scanSubscribers.delete(res)
  })
})

scanRouter.post('/api/scan/start', (req, res) => {
  launchScanProcess(req.body ?? {})
  res.json({ started: true })
})

scanRouter.post('/api/scan/stream', (req, res) => {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    Connection: 'keep-alive',
  })

  scanSubscribers.add(res)
  launchScanProcess(req.body ?? {})

  req.on('close', () => {
    scanSubscribers.delete(res)
  })
})

scanRouter.post('/api/scan/stop', (_req, res) => {
  if (activeScanChild) {
    try { activeScanChild.kill('SIGTERM') } catch {}
    activeScanChild = null
    scanState.isScanning = false
    broadcastScanEvent({ type: 'exit', code: 0 })
    return res.json({ stopped: true })
  }
  scanState.isScanning = false
  res.json({ stopped: false })
})
