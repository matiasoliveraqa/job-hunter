import { createSafeRouter } from '../router-utils.js'
import { configFiles } from '../context.js'

export const exclusionsRouter = createSafeRouter()

exclusionsRouter.get('/api/exclusions', async (_req, res) => {
  res.json(await configFiles.readExclusions())
})

exclusionsRouter.post('/api/exclusions', async (req, res) => {
  res.status(201).json(await configFiles.addExclusion(req.body ?? {}))
})

exclusionsRouter.post('/api/exclusions/import', async (req, res) => {
  const items = Array.isArray(req.body) ? req.body : req.body?.items ?? []
  res.json(await configFiles.importExclusions(items))
})

exclusionsRouter.post('/api/exclusions/clear', async (_req, res) => {
  res.json(await configFiles.clearExclusions())
})

exclusionsRouter.put('/api/exclusions/:company', async (req, res) => {
  const entry = await configFiles.updateExclusion(req.params.company, req.body ?? {})
  entry ? res.json(entry) : res.status(404).json({ error: 'No encontrada' })
})

exclusionsRouter.delete('/api/exclusions/:company', async (req, res) => {
  ;(await configFiles.removeExclusion(req.params.company))
    ? res.status(204).end()
    : res.status(404).json({ error: 'No encontrada' })
})
