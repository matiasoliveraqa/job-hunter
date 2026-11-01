import { spawn } from 'node:child_process'
import { createSafeRouter } from '../router-utils.js'
import { PYTHON_BIN, ROOT } from '../context.js'

export const systemRouter = createSafeRouter()

systemRouter.post('/api/system/update', (_req, res) => {
  const child = spawn(PYTHON_BIN, ['-m', 'src.updater'], {
    cwd: ROOT,
    env: process.env,
  })
  let output = ''
  child.stdout.on('data', (d) => { output += d.toString() })
  child.stderr.on('data', (d) => { output += d.toString() })
  child.on('close', (code) => {
    res.json({
      ok: code === 0,
      output: output.trim(),
    })
  })
})
