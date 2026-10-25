import fs from 'node:fs/promises'
import path from 'node:path'
import { randomUUID } from 'node:crypto'

export const STATUSES = ['pending', 'applied', 'interview', 'offer', 'rejected', 'withdrawn', 'not_sent']

export function createStore(file) {
  let queue = Promise.resolve()

  async function read() {
    try {
      return JSON.parse(await fs.readFile(file, 'utf-8'))
    } catch (err) {
      if (err.code !== 'ENOENT') throw err
      const initial = []
      await write(initial)
      return initial
    }
  }

  async function write(data) {
    await fs.mkdir(path.dirname(file), { recursive: true })
    await fs.writeFile(file, JSON.stringify(data, null, 2), 'utf-8')
  }

  // Serialize read-modify-write cycles so concurrent requests cannot clobber each other.
  function mutate(fn) {
    const run = queue.then(async () => {
      const data = await read()
      const result = await fn(data)
      await write(data)
      return result
    })
    queue = run.catch(() => {})
    return run
  }

  return {
    list: read,

    // Returns { item, created }. A posting with the same url is never duplicated.
    create: (input) =>
      mutate((data) => {
        const existing = input.url && data.find((a) => a.url === input.url)
        if (existing) return { item: existing, created: false }
        const status = input.status === 'pending' ? 'pending' : 'applied'
        const today = new Date().toISOString().slice(0, 10)
        const now = new Date().toISOString()
        const item = {
          id: randomUUID(),
          company: input.company,
          role: input.role,
          url: input.url || '',
          appliedAt: status === 'applied' ? input.appliedAt || today : '',
          status,
          reason: '',
          notes: input.notes || '',
          cv: input.cv || '',
          demo: Boolean(input.demo),
          history: [{ at: now, status, note: status === 'pending' ? 'Publicación cargada desde el chat' : 'Registrada como enviada' }],
          updatedAt: now,
        }
        data.push(item)
        return { item, created: true }
      }),

    update: (id, patch) =>
      mutate((data) => {
        const item = data.find((a) => a.id === id)
        if (!item) return null
        const previousStatus = item.status
        for (const key of ['company', 'role', 'url', 'appliedAt', 'status', 'reason', 'notes', 'cv']) {
          if (patch[key] !== undefined) item[key] = patch[key]
        }
        const now = new Date().toISOString()
        item.history = item.history ?? []
        if (item.status !== previousStatus) {
          if (item.status === 'applied' && !item.appliedAt) item.appliedAt = now.slice(0, 10)
          item.history.push({ at: now, status: item.status, note: patch.event || item.reason || '' })
        } else if (patch.event) {
          item.history.push({ at: now, status: item.status, note: patch.event })
        }
        item.updatedAt = now
        return item
      }),

    remove: (id) =>
      mutate((data) => {
        const idx = data.findIndex((a) => a.id === id)
        if (idx === -1) return false
        data.splice(idx, 1)
        return true
      }),

    removeDemos: () =>
      mutate((data) => {
        const keep = data.filter((a) => !a.demo)
        const removed = data.length - keep.length
        data.splice(0, data.length, ...keep)
        return removed
      }),
  }
}
