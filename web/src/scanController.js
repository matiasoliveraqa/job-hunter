import { computed, reactive, ref } from 'vue'
import { api, formatCompanyName } from './api.js'

export const PRESETS = [
  {
    name: 'QA / SDET',
    icon: 'mdi-shield-check',
    roles: [
      'QA',
      'SDET',
      'QA Automation',
      'Test Engineer',
      'Automation Engineer',
      'QA Analyst',
      'Quality Engineer',
      'QE',
      'QC',
      'QIA',
      'Software Tester',
    ],
  },
  {
    name: 'Todos',
    icon: 'mdi-apps',
    roles: [
      'QA',
      'SDET',
      'QA Automation',
      'Test Engineer',
      'Automation Engineer',
      'QA Analyst',
      'Quality Engineer',
      'QE',
      'QC',
      'QIA',
      'Software Tester',
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
const storedMatches = (() => {
  try {
    const raw = localStorage.getItem('job_hunter_matches')
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
})()

export const matches = ref(storedMatches)
export const errorCount = ref(0)
export const logs = ref([])
export const lastScanTime = ref(localStorage.getItem('job_hunter_last_scan_time') || null)

let saveMatchesTimer = null
function saveMatches(immediate = false) {
  if (immediate) {
    if (saveMatchesTimer) {
      clearTimeout(saveMatchesTimer)
      saveMatchesTimer = null
    }
    try {
      localStorage.setItem('job_hunter_matches', JSON.stringify(matches.value))
    } catch {}
    return
  }
  if (!saveMatchesTimer) {
    saveMatchesTimer = setTimeout(() => {
      saveMatchesTimer = null
      try {
        localStorage.setItem('job_hunter_matches', JSON.stringify(matches.value))
      } catch {}
    }, 400)
  }
}

export async function loadPersistedResults(existingApps = []) {
  if (matches.value.length === 0) {
    try {
      const res = await api.getScanResults()
      if (res?.matches?.length) {
        matches.value = res.matches.map((p) => {
          p.company = formatCompanyName(p.company)
          if (!p.matchScore) p.matchScore = calculateMatchScore(p)
          const matchedApp = existingApps.find(
            (a) => a.url === p.url || (a.company?.toLowerCase() === p.company?.toLowerCase() && a.role?.toLowerCase() === p.title?.toLowerCase())
          )
          if (matchedApp?.cv) p.cv = matchedApp.cv
          return p
        })
        saveMatches()
      }
    } catch {}
  }
}

export const LATAM_COUNTRIES = [
  'Argentina',
  'Bolivia',
  'Brasil',
  'Chile',
  'Colombia',
  'Costa Rica',
  'Cuba',
  'Ecuador',
  'El Salvador',
  'Guatemala',
  'Honduras',
  'México',
  'Nicaragua',
  'Panamá',
  'Paraguay',
  'Perú',
  'Puerto Rico',
  'República Dominicana',
  'Uruguay',
  'Venezuela',
]

export const NORTH_AMERICA_COUNTRIES = [
  'Canadá',
  'Estados Unidos',
]

export const WORLDWIDE_COUNTRIES = [
  ...LATAM_COUNTRIES,
  ...NORTH_AMERICA_COUNTRIES,
  'Alemania',
  'Australia',
  'Austria',
  'Bélgica',
  'China',
  'Corea del Sur',
  'Dinamarca',
  'Emiratos Árabes Unidos',
  'España',
  'Filipinas',
  'Finlandia',
  'Francia',
  'India',
  'Irlanda',
  'Israel',
  'Italia',
  'Japón',
  'Noruega',
  'Nueva Zelanda',
  'Países Bajos',
  'Polonia',
  'Portugal',
  'Reino Unido',
  'República Checa',
  'Rumania',
  'Singapur',
  'Sudáfrica',
  'Suecia',
  'Suiza',
  'Ucrania',
]

export function getAvailableCountries(geoScope) {
  if (geoScope === 'latam') return [...LATAM_COUNTRIES]
  if (geoScope === 'latam_na') return [...LATAM_COUNTRIES, ...NORTH_AMERICA_COUNTRIES]
  return [...WORLDWIDE_COUNTRIES]
}

export const form = reactive({
  roles: [],
  platforms: ['ashby', 'greenhouse', 'lever', 'workable', 'breezy', 'recruitee', 'bamboohr'],
  geoScope: 'latam',
  countries: [],
  workModes: ['remote'],
  maxYears: 0,
  allowCaptcha: false,
  concurrency: 50,
})

export function setGeoScope(newScope) {
  form.geoScope = newScope
  const allowed = getAvailableCountries(newScope)
  form.countries = form.countries.filter((c) => allowed.includes(c))
}

let eventSource = null
let currentExistingApps = []

export function connectEventSource(existingApps = []) {
  if (Array.isArray(existingApps) && existingApps.length) {
    currentExistingApps = existingApps
  }
  if (eventSource && eventSource.readyState !== EventSource.CLOSED) {
    return
  }

  eventSource = new EventSource('/api/scan/events')

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      handleEvent(data, currentExistingApps)
    } catch {
      // ignora errores de parseo
    }
  }

  eventSource.onerror = () => {
    // EventSource reconecta de forma automatica
  }
}

export function disconnectEventSource() {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}

export async function initScanSync(existingApps = []) {
  if (Array.isArray(existingApps) && existingApps.length) {
    currentExistingApps = existingApps
  }

  connectEventSource(currentExistingApps)

  try {
    const status = await api.getScanStatus()
    if (status) {
      scanning.value = Boolean(status.isScanning)
      if (typeof status.checked === 'number') progress.checked = status.checked
      if (typeof status.total === 'number') progress.total = status.total
      if (status.platform) progress.platform = status.platform
      if (status.company) progress.company = formatCompanyName(status.company)
      if (typeof status.errorCount === 'number') errorCount.value = status.errorCount

      if (Array.isArray(status.matches) && status.matches.length > 0) {
        for (const p of status.matches) {
          p.company = formatCompanyName(p.company)
          if (!matches.value.some((m) => m.url === p.url)) {
            p.matchScore = calculateMatchScore(p)
            const matchedApp = currentExistingApps.find(
              (a) => a.url === p.url || (a.company?.toLowerCase() === p.company?.toLowerCase() && a.role?.toLowerCase() === p.title?.toLowerCase())
            )
            if (matchedApp?.cv) p.cv = matchedApp.cv
            matches.value.unshift(p)
          }
        }
        saveMatches()
      }
    }
  } catch (err) {
    console.warn('No se pudo sincronizar el estado del escaneo:', err)
  }

  if (matches.value.length === 0) {
    await loadPersistedResults(currentExistingApps)
  }
}

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
  if (
    title.includes('qa') ||
    title.includes('quality') ||
    title.includes('qe') ||
    title.includes('qc') ||
    title.includes('qia') ||
    title.includes('test')
  ) {
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

let pendingProgress = null
let pendingLogs = []
let pendingMatches = []
let progressFlushTimer = null

export function flushBufferedEvents(existingApps = []) {
  if (progressFlushTimer) {
    clearTimeout(progressFlushTimer)
    progressFlushTimer = null
  }
  if (pendingProgress) {
    scanning.value = true
    progress.checked = pendingProgress.checked
    progress.total = pendingProgress.total
    progress.platform = pendingProgress.platform
    progress.company = pendingProgress.company
    pendingProgress = null
  }
  if (pendingLogs.length > 0) {
    logs.value.unshift(...pendingLogs)
    if (logs.value.length > 100) logs.value.length = 100
    pendingLogs = []
  }
  if (pendingMatches.length > 0) {
    const apps = Array.isArray(existingApps) && existingApps.length ? existingApps : currentExistingApps
    for (const p of pendingMatches) {
      if (!matches.value.some((m) => m.url === p.url)) {
        p.matchScore = calculateMatchScore(p)
        const matchedApp = apps.find(
          (a) => a.url === p.url || (a.company?.toLowerCase() === p.company?.toLowerCase() && a.role?.toLowerCase() === p.title?.toLowerCase())
        )
        if (matchedApp?.cv) {
          p.cv = matchedApp.cv
        }
        matches.value.unshift(p)
      }
    }
    pendingMatches = []
    saveMatches(false)
  }
}

function scheduleFlush(existingApps) {
  if (!progressFlushTimer) {
    progressFlushTimer = setTimeout(() => {
      flushBufferedEvents(existingApps)
    }, 80)
  }
}

export function handleEvent(evt, existingApps = []) {
  if (evt.type === 'sync') {
    flushBufferedEvents(existingApps)
    if (evt.scanState) {
      scanning.value = Boolean(evt.scanState.isScanning)
      progress.checked = evt.scanState.checked || 0
      progress.total = evt.scanState.total || 0
      progress.platform = evt.scanState.platform || ''
      progress.company = evt.scanState.company || ''
      errorCount.value = evt.scanState.errorCount || 0
    }
    if (Array.isArray(evt.matches) && evt.matches.length > 0) {
      for (const p of evt.matches) {
        if (!matches.value.some((m) => m.url === p.url)) {
          p.matchScore = calculateMatchScore(p)
          const matchedApp = existingApps.find(
            (a) => a.url === p.url || (a.company?.toLowerCase() === p.company?.toLowerCase() && a.role?.toLowerCase() === p.title?.toLowerCase())
          )
          if (matchedApp?.cv) p.cv = matchedApp.cv
          matches.value.unshift(p)
        }
      }
      saveMatches(true)
    }
  } else if (evt.type === 'start') {
    flushBufferedEvents(existingApps)
    scanning.value = true
    errorCount.value = 0
    Object.assign(progress, { checked: 0, total: 0, platform: '', company: '' })
  } else if (evt.type === 'progress') {
    scanning.value = true
    pendingProgress = {
      checked: evt.checked,
      total: evt.total,
      platform: evt.platform,
      company: formatCompanyName(evt.company),
    }
    scheduleFlush(existingApps)
  } else if (evt.type === 'match') {
    const p = evt.posting
    p.company = formatCompanyName(p.company)
    pendingMatches.push(p)
    scheduleFlush(existingApps)
  } else if (evt.type === 'board_error') {
    errorCount.value++
    pendingLogs.unshift(`[${evt.platform}] ${evt.company}: ${evt.error}`)
    scheduleFlush(existingApps)
  } else if (evt.type === 'log') {
    pendingLogs.unshift(evt.message)
    scheduleFlush(existingApps)
  } else if (evt.type === 'done' || evt.type === 'exit') {
    flushBufferedEvents(existingApps)
    scanning.value = false
    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    lastScanTime.value = timeStr
    try {
      localStorage.setItem('job_hunter_last_scan_time', timeStr)
    } catch {}
    saveMatches(true)
  } else if (evt.type === 'error') {
    flushBufferedEvents(existingApps)
    scanning.value = false
    logs.value.unshift(`[Error] ${evt.error}`)
    saveMatches(true)
  }
}

export async function startScan(existingApps = []) {
  if (!form.roles.length) {
    throw new Error('Ingresa al menos un rol objetivo para buscar')
  }
  if (!form.platforms.length) {
    throw new Error('Selecciona al menos una plataforma ATS')
  }

  if (Array.isArray(existingApps) && existingApps.length) {
    currentExistingApps = existingApps
  }

  flushBufferedEvents(existingApps)
  scanning.value = true
  matches.value = []
  saveMatches(true)
  logs.value = []
  errorCount.value = 0
  Object.assign(progress, { checked: 0, total: 0, platform: '', company: '' })

  const parsedMaxYears = (form.maxYears !== '' && form.maxYears !== null && !isNaN(Number(form.maxYears)))
    ? Number(form.maxYears)
    : 0

  let locations = []
  if (form.geoScope === 'latam') {
    locations = ['remote', 'latam', 'latin america', 'south america', 'worldwide', 'global', 'anywhere', 'americas']
  } else if (form.geoScope === 'latam_na') {
    locations = ['remote', 'latam', 'latin america', 'south america', 'americas', 'north america', 'worldwide', 'global', 'anywhere']
  } else {
    locations = ['remote', 'worldwide', 'global', 'anywhere']
  }

  const payload = {
    roles: form.roles,
    platforms: form.platforms,
    locations,
    geoScope: form.geoScope,
    countries: form.countries,
    workModes: form.workModes,
    maxYears: parsedMaxYears,
    allowCaptcha: form.allowCaptcha,
    concurrency: Number(form.concurrency) || 50,
  }

  connectEventSource(currentExistingApps)
  await api.startScan(payload)
}

export async function stopScan() {
  try {
    await api.stopScan()
  } catch {}
  flushBufferedEvents()
  scanning.value = false
  saveMatches(true)
}
