<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { api, formatCompanyName } from '../../api.js'
import { refreshAppStats } from '../../stats.js'
import { t } from '../../i18n/index.js'

const props = defineProps({
  matches: {
    type: Array,
    default: () => [],
  },
  existingApps: {
    type: Array,
    default: () => [],
  },
  errorCount: {
    type: Number,
    default: 0,
  },
  logs: {
    type: Array,
    default: () => [],
  },
  scanning: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['notify', 'refresh-apps'])

function notify(text, color = 'success') {
  emit('notify', { text, color })
}

const showLogs = ref(false)
const tableSearchInput = ref('')
const tableSearch = ref('')
const platformFilter = ref('all')
const currentPage = ref(1)
const pageSize = ref(25)
const pageSizeOptions = [25, 50, 100]

let tableSearchDebounceTimer = null
watch(tableSearchInput, (newVal) => {
  clearTimeout(tableSearchDebounceTimer)
  tableSearchDebounceTimer = setTimeout(() => {
    tableSearch.value = newVal
    currentPage.value = 1
  }, 150)
})

watch(platformFilter, () => {
  currentPage.value = 1
})

// ---- Acciones sobre cada vacante ----
const preparingMap = reactive({})
const preparedMap = reactive({})
const tailoringMap = reactive({})
const tailoredMap = reactive({})
const launchingMap = reactive({})
const openedMap = reactive({})

const normUrlCache = new Map()

function normalizeJobUrl(raw) {
  if (!raw || typeof raw !== 'string') return ''
  try {
    const u = new URL(raw)
    const trackingParams = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'ref', 'source', 'gh_src']
    for (const p of trackingParams) {
      u.searchParams.delete(p)
    }
    const pathname = u.pathname.replace(/\/+$/, '')
    u.pathname = pathname
    return u.toString().toLowerCase()
  } catch {
    return raw.trim().toLowerCase().replace(/\/+$/, '')
  }
}

function getNormalizedUrl(raw) {
  if (!raw || typeof raw !== 'string') return ''
  let cached = normUrlCache.get(raw)
  if (cached !== undefined) return cached
  cached = normalizeJobUrl(raw)
  if (normUrlCache.size > 2000) normUrlCache.clear()
  normUrlCache.set(raw, cached)
  return cached
}

const existingAppsIndex = computed(() => {
  const preparedUrls = new Set()
  const preparedCompRoles = new Set()
  const tailoredUrls = new Set()
  const tailoredCompRoles = new Set()
  const appCvMap = new Map()

  for (const a of props.existingApps || []) {
    const norm = getNormalizedUrl(a.url)
    const c = (a.company || '').trim().toLowerCase()
    const r = (a.role || '').trim().toLowerCase()
    const crKey = c && r ? `${c}:::${r}` : ''

    if (norm) preparedUrls.add(norm)
    if (crKey) preparedCompRoles.add(crKey)

    if (a.cv) {
      if (norm) {
        tailoredUrls.add(norm)
        appCvMap.set(norm, a.cv)
      }
      if (crKey) {
        tailoredCompRoles.add(crKey)
        appCvMap.set(crKey, a.cv)
      }
    }
  }

  return {
    preparedUrls,
    preparedCompRoles,
    tailoredUrls,
    tailoredCompRoles,
    appCvMap,
  }
})

function isJobPrepared(job) {
  if (preparedMap[job.url]) return true
  const norm = getNormalizedUrl(job.url)
  const idx = existingAppsIndex.value
  if (norm && idx.preparedUrls.has(norm)) return true
  const c = (job.company || '').trim().toLowerCase()
  const r = (job.title || '').trim().toLowerCase()
  if (c && r && idx.preparedCompRoles.has(`${c}:::${r}`)) return true
  return false
}

function isJobTailored(job) {
  if (job.cv || tailoredMap[job.url]) return true
  const norm = getNormalizedUrl(job.url)
  const idx = existingAppsIndex.value
  if (norm && idx.tailoredUrls.has(norm)) {
    if (!job.cv) job.cv = idx.appCvMap.get(norm)
    return true
  }
  const c = (job.company || '').trim().toLowerCase()
  const r = (job.title || '').trim().toLowerCase()
  const crKey = c && r ? `${c}:::${r}` : ''
  if (crKey && idx.tailoredCompRoles.has(crKey)) {
    if (!job.cv) job.cv = idx.appCvMap.get(crKey)
    return true
  }
  return false
}

function isJobOpened(job) {
  return Boolean(openedMap[job.url])
}

async function prepareApplication(posting) {
  const compName = formatCompanyName(posting.company)
  if (isJobPrepared(posting)) {
    return notify(t('search.toasts.prepared') + ` (${compName})`, 'info')
  }
  preparingMap[posting.url] = true
  try {
    const created = await api.createApplication({
      company: compName,
      role: posting.title,
      url: posting.url,
      cv: posting.cv || undefined,
      status: 'pending',
      notes: `Detectada en escaneo ATS (${posting.ats.toUpperCase()})`,
    })
    preparedMap[posting.url] = true
    props.existingApps.unshift(created)
    emit('refresh-apps')
    await refreshAppStats()
    notify(t('search.toasts.prepared') + `: ${compName}`)
  } catch (err) {
    notify(t('search.toasts.prepareError') + err.message, 'error')
  } finally {
    preparingMap[posting.url] = false
  }
}

async function tailorApplication(posting) {
  const compName = formatCompanyName(posting.company)
  tailoringMap[posting.url] = true
  try {
    notify(t('search.toasts.tailorStarted'), 'info')
    const res = await api.tailorCv({
      company: compName,
      role: posting.title,
      url: posting.url,
      description: posting.title,
    })
    if (res?.cv) {
      posting.cv = res.cv
      tailoredMap[posting.url] = true
    }
    emit('refresh-apps')
    await refreshAppStats()
    notify(t('search.toasts.tailorSuccess') + `${compName} (${res.cv})`)
  } catch (err) {
    notify(t('search.toasts.tailorError') + err.message, 'error')
  } finally {
    tailoringMap[posting.url] = false
  }
}

async function openInBrowser(posting) {
  const compName = formatCompanyName(posting.company)
  launchingMap[posting.url] = true
  try {
    notify(t('search.toasts.playwrightLaunching'), 'info')
    await api.launchApply({
      url: posting.url,
      company: compName,
      role: posting.title,
      cv: posting.cv || undefined,
    })
    openedMap[posting.url] = true
    notify(t('search.toasts.playwrightSuccess') + `: ${compName}`)
  } catch (err) {
    notify(t('search.toasts.playwrightError') + err.message, 'error')
  } finally {
    launchingMap[posting.url] = false
  }
}

const filteredMatches = computed(() => {
  const q = tableSearch.value.trim().toLowerCase()
  const p = platformFilter.value
  return props.matches.filter((job) => {
    const matchesQuery = !q || (job.title || '').toLowerCase().includes(q) || (job.company || '').toLowerCase().includes(q)
    const matchesPlat = p === 'all' || (job.ats || '').toLowerCase() === p.toLowerCase()
    return matchesQuery && matchesPlat
  })
})

const totalMatchesCount = computed(() => filteredMatches.value.length)
const totalPages = computed(() => Math.max(1, Math.ceil(totalMatchesCount.value / pageSize.value)))

const paginatedMatches = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredMatches.value.slice(start, start + pageSize.value)
})

const pageStartItem = computed(() => {
  if (!totalMatchesCount.value) return 0
  return (currentPage.value - 1) * pageSize.value + 1
})

const pageEndItem = computed(() => {
  return Math.min(currentPage.value * pageSize.value, totalMatchesCount.value)
})

watch([totalMatchesCount, pageSize], () => {
  if (currentPage.value > totalPages.value) {
    currentPage.value = totalPages.value
  }
})

function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

function nextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

function getPlatformBadgeClass(ats) {
  const low = String(ats || '').toLowerCase()
  if (low === 'greenhouse') return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
  if (low === 'ashby') return 'bg-purple-500/10 text-purple-400 border-purple-500/20'
  if (low === 'lever') return 'bg-amber-500/10 text-amber-400 border-amber-500/20'
  if (low === 'workable') return 'bg-blue-500/10 text-blue-400 border-blue-500/20'
  if (low === 'breezy') return 'bg-teal-500/10 text-teal-400 border-teal-500/20'
  if (low === 'recruitee') return 'bg-rose-500/10 text-rose-400 border-rose-500/20'
  if (low === 'bamboohr') return 'bg-lime-500/10 text-lime-400 border-lime-500/20'
  return 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20'
}

function resolveWorkMode(job) {
  if (job?.work_mode) return String(job.work_mode).toLowerCase().trim()
  if (job?.workMode) return String(job.workMode).toLowerCase().trim()
  const loc = (job?.location || '').toLowerCase()
  const title = (job?.title || '').toLowerCase()
  const combined = `${title} ${loc}`
  if (/hybrid|h[ií]brid[oa]/i.test(combined)) return 'hybrid'
  if (/\b(remote|remoto|worldwide|global|anywhere)\b/i.test(combined)) return 'remote'
  if (/\b(onsite|on-site|presencial)\b/i.test(combined)) return 'onsite'
  return loc ? 'onsite' : 'remote'
}

function getWorkModeBadgeClass(mode) {
  switch (mode) {
    case 'remote':
      return 'bg-sky-500/10 text-sky-400 border-sky-500/20'
    case 'hybrid':
      return 'bg-amber-500/10 text-amber-400 border-amber-500/20'
    case 'onsite':
      return 'bg-purple-500/10 text-purple-400 border-purple-500/20'
    default:
      return 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20'
  }
}

function getWorkModeIcon(mode) {
  switch (mode) {
    case 'remote':
      return 'wifi'
    case 'hybrid':
      return 'sync_alt'
    case 'onsite':
      return 'business'
    default:
      return 'work'
  }
}

function getWorkModeLabel(mode) {
  switch (mode) {
    case 'hybrid':
      return t('search.table.modeHybrid')
    case 'onsite':
      return t('search.table.modeOnsite')
    default:
      return t('search.table.modeRemote')
  }
}
</script>

<template>
  <section class="bg-surface border border-border-subtle rounded-xl flex flex-col overflow-hidden shadow-sm">
    <!-- Barra superior de búsqueda y filtro de la tabla -->
    <div class="p-3 border-b border-border-subtle flex flex-col md:flex-row md:items-center justify-between gap-3">
      <div class="relative flex items-center flex-1 max-w-sm">
        <span class="material-symbols-outlined absolute left-2.5 text-[16px] text-outline">search</span>
        <input
          v-model="tableSearchInput"
          class="w-full pl-8 pr-8 py-1.5 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle placeholder:text-outline focus:outline-none focus:border-accent transition-colors"
          :placeholder="$t('search.table.searchPlaceholder')"
          type="text"
          @keydown.enter="tableSearch = tableSearchInput; currentPage = 1"
        />
        <button
          v-if="tableSearchInput"
          aria-label="Clear search"
          class="absolute right-2 text-outline hover:text-on-surface p-0.5 transition-colors"
          type="button"
          @click="tableSearchInput = ''; tableSearch = ''; currentPage = 1"
        >
          <span class="material-symbols-outlined text-[14px] block">close</span>
        </button>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <select
          v-model="platformFilter"
          class="px-2.5 py-1.5 rounded-lg bg-surface-container border border-border-subtle text-xs text-on-surface focus:outline-none cursor-pointer"
        >
          <option value="all">{{ $t('search.table.allPlatforms', { count: matches.length }) }}</option>
          <option value="greenhouse">Greenhouse</option>
          <option value="ashby">Ashby</option>
          <option value="lever">Lever</option>
          <option value="workable">Workable</option>
          <option value="breezy">Breezy HR</option>
          <option value="recruitee">Recruitee</option>
          <option value="bamboohr">BambooHR</option>
        </select>
        <button
          v-if="errorCount > 0"
          class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-surface-container border border-border-subtle text-xs text-amber-400 hover:text-amber-300 transition-colors"
          type="button"
          @click="showLogs = !showLogs"
        >
          <span class="material-symbols-outlined text-[15px]">warning</span>
          <span>{{ showLogs ? $t('search.table.hideErrors') : $t('search.table.viewErrors', { count: errorCount }) }}</span>
        </button>
      </div>
    </div>

    <!-- Logs desplegables de errores -->
    <div v-if="showLogs && logs.length" class="p-3 bg-surface-container-lowest border-b border-border-subtle max-h-40 overflow-y-auto font-mono text-[11px] text-rose-400 flex flex-col gap-1">
      <div v-for="(log, idx) in logs" :key="idx" class="truncate">
        {{ log }}
      </div>
    </div>

    <!-- Tabla -->
    <div class="overflow-x-auto w-full">
      <table class="w-full text-left border-collapse text-xs">
        <thead>
          <tr class="border-b border-border-subtle bg-surface-card text-outline uppercase tracking-wider text-[11px] font-mono">
            <th class="py-2.5 px-3 font-medium">{{ $t('search.table.colAts') }}</th>
            <th class="py-2.5 px-3 font-medium">{{ $t('search.table.colCompany') }}</th>
            <th class="py-2.5 px-3 font-medium">{{ $t('search.table.colRole') }}</th>
            <th class="py-2.5 px-3 font-medium">{{ $t('search.table.colLocation') }}</th>
            <th class="py-2.5 px-3 font-medium">{{ $t('search.table.colWorkMode') }}</th>
            <th class="py-2.5 px-3 font-medium">{{ $t('search.table.colExp') }}</th>
            <th class="py-2.5 px-3 font-medium">{{ $t('search.table.colMatch') }}</th>
            <th class="py-2.5 px-3 font-medium text-right pr-4">{{ $t('search.table.colActions') }}</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-border-subtle">
          <tr
            v-for="job in paginatedMatches"
            :key="job.url"
            class="hover:bg-surface-container/50 transition-colors group"
          >
            <!-- ATS / ID -->
            <td class="py-3 px-3">
              <span
                class="px-2 py-0.5 rounded font-mono text-[10px] border capitalize"
                :class="getPlatformBadgeClass(job.ats)"
              >
                {{ job.ats }}
              </span>
            </td>

            <!-- Empresa -->
            <td class="py-3 px-3 font-medium text-on-surface">
              <div class="flex items-center gap-1.5">
                <span>{{ formatCompanyName(job.company) }}</span>
                <span
                  v-if="job.has_captcha"
                  class="px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 font-mono text-[9px] border border-amber-500/20"
                  :title="$t('search.table.captchaRequired')"
                >
                  Captcha
                </span>
              </div>
            </td>

            <!-- Puesto de trabajo -->
            <td class="py-3 px-3">
              <a
                :href="job.url"
                class="text-on-surface font-medium hover:text-accent cursor-pointer transition-colors"
                rel="noopener noreferrer"
                target="_blank"
              >
                {{ job.title }}
              </a>
            </td>

            <!-- Ubicación -->
            <td class="py-3 px-3">
              <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-container text-on-surface-variant font-mono text-[11px]">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                {{ job.location || $t('common.remote') }}
              </span>
            </td>

            <!-- Modalidad -->
            <td class="py-3 px-3">
              <span
                class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded font-mono text-[10.5px] border capitalize"
                :class="getWorkModeBadgeClass(resolveWorkMode(job))"
              >
                <span class="material-symbols-outlined text-[13px] leading-none">{{ getWorkModeIcon(resolveWorkMode(job)) }}</span>
                <span>{{ getWorkModeLabel(resolveWorkMode(job)) }}</span>
              </span>
            </td>

            <!-- Exp. requerida -->
            <td class="py-3 px-3 font-mono text-on-surface-variant">
              {{ job.required_years ? $t('search.table.expYears', { count: job.required_years }) : $t('search.table.expNotSpecified') }}
            </td>

            <!-- Match -->
            <td class="py-3 px-3">
              <div class="flex items-center gap-2">
                <div class="w-14 bg-surface-container h-1.5 rounded-full overflow-hidden">
                  <div
                    class="bg-accent h-full rounded-full transition-all duration-300"
                    :style="{ width: (job.matchScore || 85) + '%' }"
                  ></div>
                </div>
                <span class="font-mono text-on-surface font-medium text-[11px]">
                  {{ job.matchScore || 85 }}%
                </span>
              </div>
            </td>

            <!-- Acciones -->
            <td class="py-3 px-3 text-right pr-4">
              <div class="flex items-center justify-end gap-1.5">
                <!-- Preparar postulación -->
                <button
                  :class="[
                    'inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-medium transition-colors',
                    isJobPrepared(job)
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      : preparingMap[job.url]
                        ? 'bg-surface-container border border-border-subtle text-on-surface cursor-wait'
                        : 'bg-surface-container hover:bg-surface-container-high border border-border-subtle text-on-surface'
                  ]"
                  :disabled="preparingMap[job.url]"
                  type="button"
                  @click="prepareApplication(job)"
                >
                  <svg
                    v-if="preparingMap[job.url]"
                    class="animate-spin h-3 w-3 text-outline shrink-0"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span>{{ preparingMap[job.url] ? $t('search.table.btnPreparing') : (isJobPrepared(job) ? $t('search.table.btnPrepared') : $t('search.table.btnPrepare')) }}</span>
                </button>

                <!-- Adaptar CV con agente IA -->
                <button
                  :class="[
                    'inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-medium transition-all duration-200',
                    tailoringMap[job.url]
                      ? 'bg-accent/20 text-accent border border-accent/40 cursor-wait'
                      : isJobTailored(job)
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-accent-subtle hover:bg-accent/20 text-accent border border-transparent'
                  ]"
                  :disabled="tailoringMap[job.url]"
                  :title="tailoringMap[job.url] ? $t('search.table.tailorTipInProgress') : (job.cv ? $t('search.table.tailorTipReady', { cv: job.cv }) : $t('search.table.tailorTipDefault'))"
                  type="button"
                  @click="tailorApplication(job)"
                >
                  <svg
                    v-if="tailoringMap[job.url]"
                    class="animate-spin h-3 w-3 text-accent shrink-0"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span
                    v-else-if="isJobTailored(job)"
                    class="material-symbols-outlined text-[13px] leading-none text-emerald-400"
                  >check_circle</span>
                  <span
                    v-else
                    class="material-symbols-outlined text-[13px] leading-none text-accent"
                  >auto_fix_high</span>

                  <span>{{ tailoringMap[job.url] ? $t('search.table.btnTailoring') : (isJobTailored(job) ? $t('search.table.btnTailored') : $t('search.table.btnTailor')) }}</span>
                </button>

                <!-- Abrir formulario Playwright -->
                <button
                  :class="[
                    'p-1.5 rounded text-[11px] font-medium transition-colors border',
                    launchingMap[job.url]
                      ? 'bg-surface-container border-accent/40 text-accent cursor-wait'
                      : isJobOpened(job)
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-surface-container hover:bg-surface-container-high border-border-subtle text-outline hover:text-on-surface'
                  ]"
                  :disabled="launchingMap[job.url]"
                  :title="$t('search.table.openPlaywright')"
                  type="button"
                  @click="openInBrowser(job)"
                >
                  <svg
                    v-if="launchingMap[job.url]"
                    class="animate-spin h-3.5 w-3.5 text-accent block"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <span v-else class="material-symbols-outlined text-[14px] block">web</span>
                </button>

                <a
                  :href="job.url"
                  class="p-1 rounded text-outline hover:text-on-surface transition-colors"
                  rel="noopener noreferrer"
                  target="_blank"
                  :title="$t('search.table.openExternal')"
                >
                  <span class="material-symbols-outlined text-[15px] block">open_in_new</span>
                </a>
              </div>
            </td>
          </tr>

          <!-- Estado vacío -->
          <tr v-if="!filteredMatches.length">
            <td class="py-12 px-4 text-center text-outline" colspan="8">
              <div class="flex flex-col items-center justify-center gap-2">
                <span class="material-symbols-outlined text-[36px] text-outline opacity-60">search_off</span>
                <p class="text-xs font-medium text-on-surface">
                  {{ scanning ? $t('search.table.emptyTitleScanning') : $t('search.table.emptyTitleIdle') }}
                </p>
                <p class="text-[11px] text-outline max-w-sm">
                  {{ scanning ? $t('search.table.emptyDescScanning') : $t('search.table.emptyDescIdle') }}
                </p>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pie de tabla / Resumen y Paginación -->
    <div class="p-3 border-t border-border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-outline">
      <div class="flex items-center gap-3 flex-wrap">
        <span v-if="totalMatchesCount > 0">
          {{ $t('search.table.showingRange', { start: pageStartItem, end: pageEndItem, total: totalMatchesCount }) }}
        </span>
        <span v-else>
          {{ $t('search.table.showingFooter', { shown: 0, total: matches.length }) }}
        </span>

        <div v-if="totalMatchesCount > pageSizeOptions[0]" class="flex items-center gap-1.5">
          <span class="text-[11px] text-outline">·</span>
          <select
            v-model.number="pageSize"
            class="px-2 py-0.5 rounded bg-surface-container border border-border-subtle text-[11px] text-on-surface focus:outline-none cursor-pointer"
          >
            <option v-for="opt in pageSizeOptions" :key="opt" :value="opt">
              {{ opt }} {{ $t('search.table.perPage') }}
            </option>
          </select>
        </div>
      </div>

      <!-- Controles de paginación -->
      <div v-if="totalPages > 1" class="flex items-center gap-2 self-end sm:self-auto">
        <button
          class="inline-flex items-center justify-center px-2.5 py-1 rounded bg-surface-container border border-border-subtle hover:bg-surface-container-high disabled:opacity-30 disabled:cursor-not-allowed text-on-surface transition-colors text-xs"
          :disabled="currentPage <= 1"
          type="button"
          @click="prevPage"
        >
          <span class="material-symbols-outlined text-[14px]">chevron_left</span>
          <span class="ml-0.5">{{ $t('search.table.prevPage') }}</span>
        </button>

        <span class="font-mono text-[11px] text-on-surface px-1">
          {{ $t('search.table.pageInfo', { page: currentPage, total: totalPages }) }}
        </span>

        <button
          class="inline-flex items-center justify-center px-2.5 py-1 rounded bg-surface-container border border-border-subtle hover:bg-surface-container-high disabled:opacity-30 disabled:cursor-not-allowed text-on-surface transition-colors text-xs"
          :disabled="currentPage >= totalPages"
          type="button"
          @click="nextPage"
        >
          <span class="mr-0.5">{{ $t('search.table.nextPage') }}</span>
          <span class="material-symbols-outlined text-[14px]">chevron_right</span>
        </button>
      </div>
    </div>
  </section>
</template>
