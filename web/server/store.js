import fs from 'node:fs/promises'
import path from 'node:path'
import { randomUUID } from 'node:crypto'

export const STATUSES = ['pending', 'applied', 'interview', 'offer', 'rejected', 'withdrawn', 'not_sent']

const SEED_DATE = '2026-10-22'
const seed = [
  ['Asteria AI', 'Senior Frontend Engineer', 'https://jobs.ashbyhq.com/asteriai/9a6bdb80-2d2e-47b1-97b2-bca567dd3d7b'],
  ['Double', 'Senior Fullstack Engineer (ARG/UY based only)', 'https://jobs.ashbyhq.com/double/e0dafdfc-19f9-4613-9fdf-e6610a32278c'],
  ['Airtm', 'Senior Software Engineer (Full-stack Node + React)', 'https://jobs.lever.co/airtm/d8b10545-45f5-42f3-a483-c03a36d6f288'],
  ['Admios', 'Fullstack JavaScript Engineer', 'https://job-boards.greenhouse.io/admios/jobs/5322920002'],
  ['Arionkoder', 'Senior React Engineer', 'https://job-boards.greenhouse.io/arionkoder/jobs/4122089008'],
  ['Amplemarket', 'Frontend Software Engineer', 'https://job-boards.eu.greenhouse.io/amplemarket/jobs/4488062101'],
  ['Canary Technologies', 'Senior Software Engineer', 'https://jobs.lever.co/canarytechnologies/0e1532cc-85e4-4f9d-a78c-defc089b14c8'],
  ['GridVerify', 'Senior Frontend Engineer', 'https://jobs.ashbyhq.com/gridverify/36c3d721-9a2c-4960-99c0-6fce975766cb'],
  ['Coperniq', 'Senior Full-Stack Engineer', 'https://jobs.ashbyhq.com/coperniq/2791caa3-e47a-44a6-a01a-c8d069c28c64'],
].map(([company, role, url]) => ({
  id: randomUUID(),
  company,
  role,
  url,
  appliedAt: SEED_DATE,
  status: 'applied',
  reason: '',
  notes: '',
  cv: '',
  updatedAt: new Date().toISOString(),
}))

export function createStore(file) {
  let queue = Promise.resolve()

  async function read() {
    try {
      return JSON.parse(await fs.readFile(file, 'utf-8'))
    } catch (err) {
      if (err.code !== 'ENOENT') throw err
      await write(seed)
      return seed
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
