import { computed, reactive, ref } from 'vue'
import { api } from './api.js'

export const PRESETS = [
  {
    name: 'QA / SDET',
    icon: 'mdi-shield-check',
    roles: ['QA Automation Engineer', 'Senior QA Engineer', 'SDET', 'Software Engineer in Test', 'QA Engineer'],
  },
  {
    name: 'Todos',
    icon: 'mdi-apps',
    roles: [
      'QA Automation Engineer',
      'Senior QA Engineer',
      'SDET',
      'Quality Engineer',
      'Software Engineer in Test',
      'QA Engineer',
      'Backend Engineer',
      'Frontend Engineer',
      'Full Stack Engineer',
      'DevOps Engineer',
    ],
  },
  {
    name: 'Backend',
    icon: 'mdi-server',
    roles: ['Backend Engineer', 'Senior Backend Engineer', 'Python Developer', 'Go Developer', 'Node.js Developer'],
  },
  {
    name: 'Frontend',
    icon: 'mdi-laptop',
    roles: ['Frontend Engineer', 'Senior Frontend Engineer', 'React Developer', 'Vue Developer'],
  },
  {
    name: 'Full Stack',
    icon: 'mdi-layers-triple',
    roles: ['Full Stack Engineer', 'Senior Full Stack Engineer', 'Software Engineer'],
  },
  {
    name: 'DevOps / SRE',
    icon: 'mdi-cloud-cog',
    roles: ['DevOps Engineer', 'Site Reliability Engineer', 'Cloud Engineer'],
  },
]

export const scanning = ref(false)
export const progress = reactive({ checked: 0, total: 0, platform: '', company: '' })
export const matches = ref([])
export const errorCount = ref(0)
export const logs = ref([])
export const lastScanTime = ref(null)

export const form = reactive({
  roles: ['QA Automation Engineer', 'Senior QA Engineer', 'SDET', 'Quality Engineer', 'Software Engineer in Test', 'QA Engineer'],
  platforms: ['ashby', 'greenhouse', 'lever'],
  latamOnly: true,
  maxYears: 7,
  allowCaptcha: false,
  concurrency: 50,
})

let abortController = null

export const progressPercent = computed(() => {
  if (!progress.total) return 0
  return Math.min(100, Math.round((progress.checked / progress.total) * 100))
})

export function calculateMatchScore(posting, profile) {
  let score = 84
  const title = (posting.title || '').toLowerCase()
  const loc = (posting.location || '').toLowerCase()

  // Keyword relevance
  if (title.includes('sdet') || title.includes('automation')) {
    score += 6
  }
  if (title.includes('senior') || title.includes('lead')) {
    score += 3
  }
  if (title.includes('qa') || title.includes('quality')) {
    score += 3
  }

  // Location relevance
  if (loc.includes('latam') || loc.includes('south america') || loc.includes('uruguay')) {
    score += 4
  } else if (loc.includes('remote') || loc.includes('worldwide') || loc.includes('global')) {
    score += 2
  }

  // Experience fit
  if (posting.required_years) {
    if (posting.required_years <= 5) score += 2
    else if (posting.required_years <= 7) score += 1
  }

  return Math.min(98, Math.max(78, score))
}

export function handleEvent(evt, existingApps = []) {
  if (evt.type === 'progress') {
    progress.checked = evt.checked
    progress.total = evt.total
    progress.platform = evt.platform
    progress.company = evt.company
  } else if (evt.type === 'match') {
    const p = evt.posting
    if (!matches.value.some((m) => m.url === p.url)) {
      p.matchScore = calculateMatchScore(p)
      const matchedApp = existingApps.find(
        (a) => a.url === p.url || (a.company?.toLowerCase() === p.company?.toLowerCase() && a.role?.toLowerCase() === p.title?.toLowerCase())
      )
      if (matchedApp?.cv) {
        p.cv = matchedApp.cv
      }
      matches.value.unshift(p)
    }
  } else if (evt.type === 'board_error') {
    errorCount.value++
    logs.value.unshift(`[${evt.platform}] ${evt.company}: ${evt.error}`)
    if (logs.value.length > 100) logs.value.pop()
  } else if (evt.type === 'done') {
    scanning.value = false
    lastScanTime.value = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } else if (evt.type === 'exit') {
    scanning.value = false
  }
}

export async function startScan(existingApps = []) {
  if (!form.roles.length) {
    throw new Error('Ingresa al menos un rol objetivo para buscar')
  }
  if (!form.platforms.length) {
    throw new Error('Selecciona al menos una plataforma ATS')
  }

  scanning.value = true
  matches.value = []
  logs.value = []
  errorCount.value = 0
  Object.assign(progress, { checked: 0, total: 0, platform: '', company: '' })

  abortController = new AbortController()

  const parsedMaxYears = (form.maxYears !== '' && form.maxYears !== null && !isNaN(Number(form.maxYears)))
    ? Number(form.maxYears)
    : null

  const payload = {
    roles: form.roles,
    platforms: form.platforms,
    locations: form.latamOnly ? ['remote', 'latam', 'latin america', 'worldwide', 'global', 'anywhere', 'americas'] : [],
    maxYears: parsedMaxYears,
    allowCaptcha: form.allowCaptcha,
    concurrency: Number(form.concurrency) || 50,
  }

  try {
    const res = await fetch('/api/scan/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: abortController.signal,
    })

    if (!res.ok) {
      throw new Error(`Error en el servidor (${res.status})`)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      let nl
      while ((nl = buffer.indexOf('\n')) !== -1) {
        const line = buffer.slice(0, nl).trim()
        buffer = buffer.slice(nl + 1)
        if (!line.startsWith('data:')) continue

        const jsonStr = line.slice(5).trim()
        if (!jsonStr) continue

        try {
          const evt = JSON.parse(jsonStr)
          handleEvent(evt, existingApps)
        } catch {
          // ignora chunks incompletos
        }
      }
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      throw err
    }
  } finally {
    scanning.value = false
    lastScanTime.value = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
}

export async function stopScan() {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
  try {
    await api.stopScan()
  } catch {
    // ignorar
  }
  scanning.value = false
}
