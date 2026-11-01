import express from 'express'
import path from 'node:path'
import { existsSync } from 'node:fs'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import {
  DIST,
  PORT,
  HOST,
  demo,
  allowedHosts,
  addAllowedPort,
  isAllowedAtsHost,
  ValidationError,
} from './context.js'
import { sanitizeCvHtml, agentRouter } from './routes/agent.js'
import { applicationsRouter } from './routes/applications.js'
import { profileRouter } from './routes/profile.js'
import { exclusionsRouter } from './routes/exclusions.js'
import { filesRouter } from './routes/files.js'
import { applyRouter } from './routes/apply.js'
import { scanRouter } from './routes/scan.js'
import { systemRouter } from './routes/system.js'

const app = express()
app.disable('x-powered-by')

app.use((_req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff')
  res.setHeader('X-Frame-Options', 'SAMEORIGIN')
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin')
  res.setHeader(
    'Content-Security-Policy',
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'",
  )
  next()
})

// Express 4 does not forward rejected promises from async handlers to the error
// middleware (and Node would crash on them), so route registration is wrapped.
for (const method of ['get', 'post', 'put', 'patch', 'delete']) {
  const register = app[method].bind(app)
  app[method] = (route, ...handlers) =>
    register(
      route,
      ...handlers.map((h) =>
        typeof h === 'function' ? (req, res, next) => Promise.resolve(h(req, res, next)).catch(next) : h
      ),
    )
}

// Security: Host and Origin verification to protect local agent and file access.
app.use((req, res, next) => {
  if (!allowedHosts.has(req.headers.host)) return res.status(403).json({ error: 'Host no permitido' })
  if (!['GET', 'HEAD'].includes(req.method)) {
    const origin = req.headers.origin
    if (origin && !allowedHosts.has(new URL(origin).host)) {
      return res.status(403).json({ error: 'Origen no permitido' })
    }
    const hasBody = Number(req.headers['content-length']) > 0 || Boolean(req.headers['transfer-encoding'])
    if (hasBody && !req.is('application/json')) return res.status(415).json({ error: 'Se requiere application/json' })
  }
  next()
})

app.use(express.json({ limit: '15mb' }))

// Mount modular feature routes
app.use(applicationsRouter)
app.use(profileRouter)
app.use(exclusionsRouter)
app.use(filesRouter)
app.use(applyRouter)
app.use(scanRouter)
app.use(agentRouter)
app.use(systemRouter)

// Static client for production
if (existsSync(DIST)) {
  app.use(express.static(DIST))
  app.get('*', (_req, res) => res.sendFile(path.join(DIST, 'index.html')))
}

// Centralized error handler
app.use((err, _req, res, _next) => {
  if (err instanceof ValidationError) return res.status(400).json({ error: err.message })
  res.status(err.status || 500).json({ error: err.status === 400 ? 'Solicitud inválida' : 'Error interno' })
})

function startServer(port = PORT, attemptsLeft = 10) {
  return new Promise((resolve, reject) => {
    function tryPort(p, attempts) {
      const server = app.listen(p, HOST)
      server.on('listening', () => {
        const activePort = server.address().port
        addAllowedPort(activePort)
        demo.setPort(activePort)
        console.log(`Job Hunter web: http://${HOST}:${activePort}`)
        resolve(server)
      })
      server.on('error', (err) => {
        if (err.code === 'EADDRINUSE' && attempts > 0) {
          console.warn(`Port ${p} in use. Trying port ${p + 1}...`)
          tryPort(p + 1, attempts - 1)
        } else {
          console.error(`Failed to start web server: ${err.message}`)
          if (process.env.NODE_ENV === 'test') {
            reject(err)
          } else {
            process.exit(1)
          }
        }
      })
    }
    tryPort(port, attemptsLeft)
  })
}

function printReadyBanner(url) {
  const line = '='.repeat(52)
  console.log(`\n${line}`)
  console.log('  Job Hunter is ready.')
  console.log(`  Open this address in your browser:  ${url}`)
  console.log('  Press Ctrl+C here to stop the server.')
  console.log(`${line}\n`)
}

function openInBrowser(url) {
  if (process.env.JOBHUNTER_NO_OPEN) return
  const [cmd, args] =
    process.platform === 'win32'
      ? ['cmd', ['/c', 'start', '', url]]
      : process.platform === 'darwin'
        ? ['open', [url]]
        : ['xdg-open', [url]]
  try {
    const child = spawn(cmd, args, { stdio: 'ignore', detached: true })
    child.on('error', () => {})
    child.unref()
  } catch {}
}

const isDirectExecution = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
if (isDirectExecution && process.env.NODE_ENV !== 'test') {
  startServer(PORT).then((server) => {
    const url = `http://${HOST}:${server.address().port}`
    printReadyBanner(url)
    openInBrowser(url)
  })
}

export { app, startServer, addAllowedPort, sanitizeCvHtml, isAllowedAtsHost }
