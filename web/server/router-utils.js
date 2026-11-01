import express from 'express'

export function createSafeRouter() {
  const router = express.Router()
  for (const method of ['get', 'post', 'put', 'patch', 'delete']) {
    const orig = router[method].bind(router)
    router[method] = (path, ...handlers) =>
      orig(
        path,
        ...handlers.map((h) =>
          typeof h === 'function' ? (req, res, next) => Promise.resolve(h(req, res, next)).catch(next) : h
        ),
      )
  }
  return router
}
