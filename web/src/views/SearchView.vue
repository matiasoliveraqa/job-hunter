<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { api, formatCompanyName } from '../api.js'
import { refreshAppStats } from '../stats.js'
import {
  PRESETS,
  scanning,
  progress,
  matches,
  errorCount,
  logs,
  form,
  progressPercent,
  startScan,
  stopScan,
  initScanSync,
} from '../scanController.js'

const profile = ref(null)
const loadingProfile = ref(true)
const snack = reactive({ show: false, text: '', color: 'success' })
const showLogs = ref(false)

const newRoleInput = ref('')
const tableSearch = ref('')
const platformFilter = ref('all')

const existingApps = ref([])
const activePreset = ref('QA / SDET')

function notify(text, color = 'success') {
  Object.assign(snack, { show: true, text, color })
}

async function loadExistingApps() {
  try {
    existingApps.value = await api.listApplications()
  } catch {}
}

async function loadProfile() {
  loadingProfile.value = true
  try {
    const data = await api.getProfile()
    profile.value = data
    if (data?.search_criteria?.target_roles?.length) {
      form.roles = [...data.search_criteria.target_roles]
    }
    if (data?.ats_settings?.enabled_platforms?.length) {
      form.platforms = [...data.ats_settings.enabled_platforms]
    }
    if (data?.personal_info?.years_of_experience) {
      form.maxYears = data.personal_info.years_of_experience
    }
    await loadExistingApps()
    await initScanSync(existingApps.value)
  } catch (e) {
    notify('No se pudo cargar el perfil: ' + e.message, 'warning')
  } finally {
    loadingProfile.value = false
  }
}

onMounted(loadProfile)

watch(scanning, (newVal, oldVal) => {
  if (oldVal === true && newVal === false) {
    notify(`Búsqueda finalizada. ${matches.value.length} vacantes encontradas.`)
  }
})

function applyPreset(preset) {
  activePreset.value = preset.name
  form.roles = [...preset.roles]
  notify(`Preset "${preset.name}" aplicado (${preset.roles.length} roles)`)
}

function resetToProfile() {
  activePreset.value = ''
  if (profile.value?.search_criteria?.target_roles?.length) {
    form.roles = [...profile.value.search_criteria.target_roles]
  } else {
    form.roles = ['QA Automation Engineer', 'SDET', 'QA Engineer']
  }
  if (profile.value?.personal_info?.years_of_experience) {
    form.maxYears = profile.value.personal_info.years_of_experience
  }
  notify('Roles restablecidos desde tu perfil')
}

function addRoleTag() {
  const val = newRoleInput.value.trim()
  if (!val) return
  if (!form.roles.includes(val)) {
    form.roles.push(val)
    newRoleInput.value = ''
    activePreset.value = ''
  }
}

function removeRoleTag(idx) {
  form.roles.splice(idx, 1)
  activePreset.value = ''
}

function togglePlatform(plat) {
  const idx = form.platforms.indexOf(plat)
  if (idx > -1) {
    if (form.platforms.length === 1) {
      return notify('Debes mantener al menos una plataforma seleccionada', 'warning')
    }
    form.platforms.splice(idx, 1)
  } else {
    form.platforms.push(plat)
  }
}

async function triggerScan() {
  try {
    await startScan(existingApps.value)
    notify('Búsqueda iniciada en segundo plano...')
  } catch (err) {
    notify('Error en el escaneo: ' + err.message, 'error')
  }
}

// ---- Acciones sobre cada vacante ----
const preparingMap = reactive({})
const preparedMap = reactive({})
const tailoringMap = reactive({})
const tailoredMap = reactive({})
const launchingMap = reactive({})
const openedMap = reactive({})

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

function isSameJobMatch(app, job) {
  const normAppUrl = normalizeJobUrl(app.url)
  const normJobUrl = normalizeJobUrl(job.url)
  if (normAppUrl && normJobUrl && normAppUrl === normJobUrl) return true

  const appComp = (app.company || '').trim().toLowerCase()
  const jobComp = (job.company || '').trim().toLowerCase()
  const appRole = (app.role || '').trim().toLowerCase()
  const jobRole = (job.title || '').trim().toLowerCase()

  if (appComp && jobComp && appRole && jobRole && appComp === jobComp && appRole === jobRole) {
    return true
  }
  return false
}

function isJobPrepared(job) {
  if (preparedMap[job.url]) return true
  return existingApps.value.some((a) => isSameJobMatch(a, job))
}

function isJobTailored(job) {
  if (job.cv || tailoredMap[job.url]) return true
  const match = existingApps.value.find((a) => isSameJobMatch(a, job))
  if (match?.cv) {
    if (!job.cv) job.cv = match.cv
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
    return notify(`"${compName}" ya está en tu lista de postulaciones`, 'info')
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
    existingApps.value.unshift(created)
    await refreshAppStats()
    notify(`Postulación agregada a "Pendiente de envío" para ${compName}`)
  } catch (err) {
    notify('No se pudo guardar la postulación: ' + err.message, 'error')
  } finally {
    preparingMap[posting.url] = false
  }
}

async function tailorApplication(posting) {
  const compName = formatCompanyName(posting.company)
  tailoringMap[posting.url] = true
  try {
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
    await loadExistingApps()
    await refreshAppStats()
    notify(`CV adaptado generado para ${compName} (${res.cv})`)
  } catch (err) {
    notify('Error al adaptar CV con agente: ' + err.message, 'error')
  } finally {
    tailoringMap[posting.url] = false
  }
}

async function openInBrowser(posting) {
  const compName = formatCompanyName(posting.company)
  launchingMap[posting.url] = true
  try {
    await api.launchApply({
      url: posting.url,
      company: compName,
      role: posting.title,
      cv: posting.cv || undefined,
    })
    openedMap[posting.url] = true
    notify(`Navegador lanzado con Playwright para ${compName}`)
  } catch (err) {
    notify('Error al abrir navegador: ' + err.message, 'error')
  } finally {
    launchingMap[posting.url] = false
  }
}

const filteredMatches = computed(() => {
  const q = tableSearch.value.trim().toLowerCase()
  const p = platformFilter.value
  return matches.value.filter((job) => {
    const matchesQuery = !q || (job.title || '').toLowerCase().includes(q) || (job.company || '').toLowerCase().includes(q)
    const matchesPlat = p === 'all' || (job.ats || '').toLowerCase() === p.toLowerCase()
    return matchesQuery && matchesPlat
  })
})

function getPlatformBadgeClass(ats) {
  const low = String(ats || '').toLowerCase()
  if (low === 'greenhouse') return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
  if (low === 'ashby') return 'bg-purple-500/10 text-purple-400 border-purple-500/20'
  if (low === 'lever') return 'bg-amber-500/10 text-amber-400 border-amber-500/20'
  return 'bg-zinc-500/10 text-zinc-400 border-zinc-500/20'
}
</script>

<template>
  <div class="flex flex-col gap-6 w-full">
    <!-- TITULO DE PAGINA Y SUBTITULO -->
    <div class="flex flex-col gap-1">
      <div class="flex items-center justify-between flex-wrap gap-2">
        <h1 class="text-xl font-semibold text-on-surface tracking-tight">
          Vacantes detectadas
        </h1>
        <div class="flex items-center gap-2">
          <span class="inline-flex items-center gap-1.5 text-xs text-outline font-mono">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            Ashby • Greenhouse • Lever
          </span>
        </div>
      </div>
      <p class="text-xs text-on-surface-variant">
        Supervisión y preparación de posiciones filtradas en tiempo real sin requerimientos de residencia excluyentes.
      </p>
    </div>

    <!-- 4 TARJETAS KPI CON SPARKLINES DINAMICOS -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
      <!-- KPI 1: Total analizadas -->
      <div class="p-4 rounded-xl bg-surface border border-border-subtle flex flex-col justify-between relative overflow-hidden shadow-sm">
        <div class="flex items-center justify-between text-on-surface-variant mb-2">
          <span class="text-xs font-medium">Total analizadas</span>
          <span class="material-symbols-outlined text-[15px] text-outline">analytics</span>
        </div>
        <div class="flex items-end justify-between">
          <div class="flex flex-col">
            <span class="text-2xl font-bold font-mono tracking-tight text-on-surface">
              {{ progress.total || (scanning ? progress.checked : 0) }}
            </span>
            <div class="flex items-center gap-1 text-[11px] font-mono text-emerald-400 mt-0.5">
              <span class="material-symbols-outlined text-[13px]">
                {{ scanning ? 'sync' : 'arrow_upward' }}
              </span>
              <span>{{ progressPercent }}% completado</span>
            </div>
          </div>
          <!-- Sparkline SVG -->
          <div class="w-24 h-10">
            <svg class="w-full h-full stroke-emerald-500 fill-none" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" viewBox="0 0 100 35">
              <path d="M 0 30 Q 15 28, 25 20 T 50 15 T 75 8 T 100 2"></path>
            </svg>
          </div>
        </div>
      </div>

      <!-- KPI 2: Vacantes encontradas -->
      <div class="p-4 rounded-xl bg-surface border border-border-subtle flex flex-col justify-between relative overflow-hidden shadow-sm">
        <div class="flex items-center justify-between text-on-surface-variant mb-2">
          <span class="text-xs font-medium">Vacantes encontradas</span>
          <span class="material-symbols-outlined text-[15px] text-outline">travel_explore</span>
        </div>
        <div class="flex items-end justify-between">
          <div class="flex flex-col">
            <span class="text-2xl font-bold font-mono tracking-tight text-accent">
              {{ matches.length }}
            </span>
            <div class="flex items-center gap-1 text-[11px] font-mono text-accent mt-0.5">
              <span class="material-symbols-outlined text-[13px]">add</span>
              <span>{{ matches.length }} calificadas</span>
            </div>
          </div>
          <!-- Sparkline SVG -->
          <div class="w-24 h-10">
            <svg class="w-full h-full stroke-blue-500 fill-none" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" viewBox="0 0 100 35">
              <path d="M 0 25 L 20 28 L 40 16 L 60 22 L 80 8 L 100 4"></path>
            </svg>
          </div>
        </div>
      </div>

      <!-- KPI 3: Empresas activas / analizadas -->
      <div class="p-4 rounded-xl bg-surface border border-border-subtle flex flex-col justify-between relative overflow-hidden shadow-sm">
        <div class="flex items-center justify-between text-on-surface-variant mb-2">
          <span class="text-xs font-medium">Empresas analizadas</span>
          <span class="material-symbols-outlined text-[15px] text-outline">domain</span>
        </div>
        <div class="flex items-end justify-between">
          <div class="flex flex-col">
            <span class="text-2xl font-bold font-mono tracking-tight text-on-surface">
              {{ progress.checked }}
            </span>
            <div class="flex items-center gap-1 text-[11px] font-mono text-amber-400 mt-0.5">
              <span class="material-symbols-outlined text-[13px]">trending_up</span>
              <span>{{ progress.platform ? progress.platform.toUpperCase() : 'Bolsas ATS' }}</span>
            </div>
          </div>
          <!-- Sparkline SVG -->
          <div class="w-24 h-10">
            <svg class="w-full h-full stroke-amber-500 fill-none" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" viewBox="0 0 100 35">
              <path d="M 0 32 Q 25 10, 45 22 T 80 18 T 100 12"></path>
            </svg>
          </div>
        </div>
      </div>

      <!-- KPI 4: Errores / descartadas -->
      <div class="p-4 rounded-xl bg-surface border border-border-subtle flex flex-col justify-between relative overflow-hidden shadow-sm">
        <div class="flex items-center justify-between text-on-surface-variant mb-2">
          <span class="text-xs font-medium">Errores / descartadas</span>
          <span class="material-symbols-outlined text-[15px] text-outline">error_outline</span>
        </div>
        <div class="flex items-end justify-between">
          <div class="flex flex-col">
            <span class="text-2xl font-bold font-mono tracking-tight text-on-surface">
              {{ errorCount }}
            </span>
            <div class="flex items-center gap-1 text-[11px] font-mono text-outline mt-0.5">
              <span class="material-symbols-outlined text-[13px]">
                {{ errorCount === 0 ? 'check_circle' : 'warning' }}
              </span>
              <span>{{ errorCount === 0 ? '0.00% tasa fallas' : `${errorCount} incidencias` }}</span>
            </div>
          </div>
          <!-- Sparkline SVG -->
          <div class="w-24 h-10">
            <svg class="w-full h-full stroke-zinc-600 fill-none" stroke-linecap="round" stroke-width="2" viewBox="0 0 100 35">
              <path d="M 0 30 L 30 30 L 50 30 L 70 30 L 100 30"></path>
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- PANEL DE FILTROS (OBSIDIAN STYLE) -->
    <section class="bg-surface border border-border-subtle rounded-xl flex flex-col gap-3.5 shadow-sm p-5">
      <!-- 1. BLOQUE SUPERIOR: PRESETS DE ROL Y ESTADO GENERAL -->
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border-subtle">
        <div class="flex flex-col gap-1.5">
          <div class="flex items-center gap-2">
            <span class="text-[11px] font-mono uppercase tracking-wider text-outline font-semibold">
              Presets de especialidad
            </span>
            <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-container-high text-accent border border-border-subtle">
              Filtros sincronizados
            </span>
          </div>
          <div class="flex items-center gap-1.5 overflow-x-auto py-1">
            <button
              v-for="p in PRESETS"
              :key="p.name"
              :class="[
                'px-3 py-1 rounded-md text-xs font-medium transition-colors shrink-0',
                activePreset === p.name
                  ? 'bg-surface-container-highest text-on-surface shadow-sm'
                  : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
              ]"
              type="button"
              @click="applyPreset(p)"
            >
              {{ p.name }}
            </button>
          </div>
        </div>

        <div class="flex items-center gap-3 self-end md:self-auto">
          <div class="flex items-center gap-1.5 text-xs text-outline font-mono bg-surface-container px-2.5 py-1.5 rounded-lg border border-border-subtle">
            <span class="w-1.5 h-1.5 rounded-full bg-accent animate-pulse"></span>
            <span>Match activo: <strong class="text-on-surface font-semibold">{{ form.roles.length }} títulos</strong></span>
          </div>
          <button
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border-subtle bg-surface-container hover:bg-surface-container-high text-on-surface text-xs font-medium transition-colors shadow-sm"
            type="button"
            @click="resetToProfile"
          >
            <span class="material-symbols-outlined text-[15px] text-outline">restart_alt</span>
            <span>Restablecer</span>
          </button>
        </div>
      </div>

      <!-- 2. BLOQUE CENTRAL: PARÁMETROS CLAVE & TOGGLES CON TOOLTIPS -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 py-1">
        <!-- Parámetro 1: Plataformas ATS -->
        <div class="flex flex-col gap-1.5 p-3 rounded-lg bg-surface-container border border-border-subtle group hover:border-border-muted transition-colors relative">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-1">
              <label class="text-[11px] font-medium text-outline uppercase tracking-wider">Plataformas ATS</label>
              <div class="relative group/tip flex items-center cursor-help">
                <span class="material-symbols-outlined text-[14px] text-outline hover:text-on-surface">help</span>
                <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover/tip:flex flex-col w-56 p-2 rounded-lg bg-surface-container-highest border border-border-muted shadow-lg z-50 text-[11px] text-on-surface leading-snug pointer-events-none">
                  <div class="font-semibold text-accent mb-0.5 flex items-center gap-1">
                    <span class="material-symbols-outlined text-[13px]">hub</span> APIs Oficiales
                  </div>
                  Escaneo directo en APIs públicas de Greenhouse, Ashby y Lever.
                </div>
              </div>
            </div>
            <span class="px-1.5 py-0.2 rounded bg-surface-container-high text-[10px] font-mono text-accent">
              {{ form.platforms.length }} activas
            </span>
          </div>
          <div class="flex items-center gap-1.5 pt-1 flex-wrap">
            <button
              v-for="plat in ['greenhouse', 'ashby', 'lever']"
              :key="plat"
              :class="[
                'px-2 py-0.5 rounded text-[11px] font-mono capitalize border transition-colors',
                form.platforms.includes(plat)
                  ? 'bg-accent/10 border-accent/30 text-accent font-medium'
                  : 'bg-surface-card border-border-subtle text-outline line-through opacity-60'
              ]"
              type="button"
              @click="togglePlatform(plat)"
            >
              {{ plat }}
            </button>
          </div>
        </div>

        <!-- Parámetro 2: Experiencia Máxima -->
        <div class="flex flex-col gap-1.5 p-3 rounded-lg bg-surface-container border border-border-subtle group hover:border-border-muted transition-colors relative">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-1">
              <label class="text-[11px] font-medium text-outline uppercase tracking-wider">Experiencia Máx.</label>
              <div class="relative group/tip flex items-center cursor-help">
                <span class="material-symbols-outlined text-[14px] text-outline hover:text-on-surface">help</span>
                <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover/tip:flex flex-col w-56 p-2 rounded-lg bg-surface-container-highest border border-border-muted shadow-lg z-50 text-[11px] text-on-surface leading-snug pointer-events-none">
                  <div class="font-semibold text-accent mb-0.5 flex items-center gap-1">
                    <span class="material-symbols-outlined text-[13px]">work_history</span> Límite de años
                  </div>
                  Descarta ofertas que exijan más años de experiencia de los configurados.
                </div>
              </div>
            </div>
            <span class="text-[10px] font-mono text-outline">Rango 1-15</span>
          </div>
          <div class="flex items-center justify-between pt-1">
            <span class="text-xs text-on-surface-variant font-medium">Hasta</span>
            <div class="flex items-center gap-2">
              <input
                v-model.number="form.maxYears"
                class="w-14 py-1 text-center font-mono font-medium text-xs bg-surface-card border border-border-muted rounded text-on-surface focus:outline-none focus:border-accent transition-colors shadow-sm"
                max="15"
                min="1"
                type="number"
              />
              <span class="text-xs text-outline font-mono">años</span>
            </div>
          </div>
        </div>

        <!-- Toggle 1: Solo LATAM / Global -->
        <div class="flex items-center justify-between p-3 rounded-lg bg-surface-container border border-border-subtle group hover:border-border-muted transition-colors relative">
          <div class="flex flex-col gap-0.5">
            <div class="flex items-center gap-1">
              <span class="text-xs font-medium text-on-surface">Solo LATAM / Global</span>
              <div class="relative group/tip flex items-center cursor-help">
                <span class="material-symbols-outlined text-[14px] text-outline hover:text-on-surface">help</span>
                <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover/tip:flex flex-col w-60 p-2.5 rounded-lg bg-surface-container-highest border border-border-muted shadow-lg z-50 text-[11px] text-on-surface leading-snug pointer-events-none">
                  <div class="font-semibold text-accent mb-0.5 flex items-center gap-1">
                    <span class="material-symbols-outlined text-[13px]">public</span> Filtro de Residencia
                  </div>
                  Descarta vacantes que exigen residencia en EE. UU., Europa o Asia.
                </div>
              </div>
            </div>
            <span class="text-[11px] text-outline leading-tight">Filtro territorial estricto</span>
          </div>
          <label class="relative inline-flex items-center cursor-pointer ml-3">
            <input
              v-model="form.latamOnly"
              class="sr-only peer"
              type="checkbox"
            />
            <div class="w-8 h-4 bg-surface-container-highest peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-accent"></div>
          </label>
        </div>

        <!-- Toggle 2: Anti-CAPTCHA -->
        <div class="flex items-center justify-between p-3 rounded-lg bg-surface-container border border-border-subtle group hover:border-border-muted transition-colors relative">
          <div class="flex flex-col gap-0.5">
            <div class="flex items-center gap-1">
              <span class="text-xs font-medium text-on-surface">Anti-CAPTCHA</span>
              <div class="relative group/tip flex items-center cursor-help">
                <span class="material-symbols-outlined text-[14px] text-outline hover:text-on-surface">help</span>
                <div class="absolute bottom-full right-0 mb-2 hidden group-hover/tip:flex flex-col w-64 p-2.5 rounded-lg bg-surface-container-highest border border-border-muted shadow-lg z-50 text-[11px] text-on-surface leading-snug pointer-events-none">
                  <div class="font-semibold text-accent mb-0.5 flex items-center gap-1">
                    <span class="material-symbols-outlined text-[13px]">security</span> Protección Cloudflare
                  </div>
                  Oculta ofertas protegidas por Cloudflare Turnstile o reCAPTCHA invasivo.
                </div>
              </div>
            </div>
            <span class="text-[11px] text-outline leading-tight">Ocultar Turnstile / v3</span>
          </div>
          <label class="relative inline-flex items-center cursor-pointer ml-3">
            <input
              v-model="form.allowCaptcha"
              class="sr-only peer"
              type="checkbox"
            />
            <div class="w-8 h-4 bg-surface-container-highest peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-accent"></div>
          </label>
        </div>
      </div>

      <!-- 3. BLOQUE INFERIOR: TÍTULOS Y ROLES ATS -->
      <div class="flex flex-col gap-3 pt-3 border-t border-border-subtle">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div class="flex items-center gap-2">
            <span class="text-[12px] font-semibold text-on-surface tracking-tight">
              Cargos y Títulos ATS a buscar
            </span>
            <span class="text-[11px] font-mono text-outline">({{ form.roles.length }} agregados)</span>
          </div>
          <span class="text-[11px] text-outline font-mono">Presiona Enter o Añadir para sumar variantes</span>
        </div>

        <div class="flex items-center gap-2">
          <div class="relative flex-1 flex items-center">
            <span class="material-symbols-outlined absolute left-3 text-[16px] text-outline">label</span>
            <input
              v-model="newRoleInput"
              class="w-full pl-9 pr-4 py-2 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle placeholder:text-outline focus:outline-none focus:border-accent transition-colors shadow-sm"
              placeholder="Escribe un rol o palabra clave y presiona Enter o Añadir..."
              type="text"
              @keydown.enter.prevent="addRoleTag"
            />
          </div>
          <button
            class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-surface-container-highest hover:bg-surface-container-high border border-border-muted text-xs font-medium text-on-surface transition-colors shadow-sm shrink-0"
            type="button"
            @click="addRoleTag"
          >
            <span class="material-symbols-outlined text-[15px] text-accent">add</span>
            <span>Añadir título</span>
          </button>
        </div>

        <!-- Tags activos -->
        <div class="flex items-center flex-wrap gap-2 pt-1">
          <span
            v-for="(r, idx) in form.roles"
            :key="r"
            class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-container text-xs text-on-surface border border-border-subtle hover:border-border-muted transition-colors shadow-sm"
          >
            <span>{{ r }}</span>
            <button
              aria-label="Eliminar tag"
              class="text-outline hover:text-on-surface p-0.5 transition-colors"
              type="button"
              @click="removeRoleTag(idx)"
            >
              <span class="material-symbols-outlined text-[13px] block">close</span>
            </button>
          </span>
        </div>
      </div>
    </section>

    <!-- ESTADO DE PROGRESO EN VIVO (DURANTE ESCANEO) -->
    <div
      v-if="scanning"
      class="p-4 rounded-xl bg-surface border border-accent/30 flex flex-col gap-3 shadow-sm"
    >
      <div class="flex items-center justify-between flex-wrap gap-2">
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-accent animate-ping"></span>
          <span class="text-xs font-semibold text-on-surface">Escaneando bolsas ATS en tiempo real...</span>
          <span v-if="progress.company" class="text-xs font-mono text-outline">
            [{{ progress.platform.toUpperCase() }}] {{ formatCompanyName(progress.company) }}
          </span>
        </div>
        <div class="text-xs font-mono text-on-surface-variant">
          {{ progress.checked }} / {{ progress.total }} empresas ({{ progressPercent }}%)
        </div>
      </div>
      <div class="w-full bg-surface-container h-2 rounded-full overflow-hidden">
        <div
          class="bg-accent h-full rounded-full transition-all duration-300"
          :style="{ width: progressPercent + '%' }"
        ></div>
      </div>
    </div>

    <!-- TABLA DE VACANTES DETECTADAS (OBSIDIAN STYLE) -->
    <section class="bg-surface border border-border-subtle rounded-xl flex flex-col overflow-hidden shadow-sm">
      <!-- Barra superior de búsqueda y filtro de la tabla -->
      <div class="p-3 border-b border-border-subtle flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div class="relative flex items-center flex-1 max-w-sm">
          <span class="material-symbols-outlined absolute left-2.5 text-[16px] text-outline">search</span>
          <input
            v-model="tableSearch"
            class="w-full pl-8 pr-3 py-1.5 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle placeholder:text-outline focus:outline-none focus:border-accent transition-colors"
            placeholder="Filtrar por puesto o empresa..."
            type="text"
          />
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <select
            v-model="platformFilter"
            class="px-2.5 py-1.5 rounded-lg bg-surface-container border border-border-subtle text-xs text-on-surface focus:outline-none cursor-pointer"
          >
            <option value="all">Todas las plataformas ({{ matches.length }})</option>
            <option value="greenhouse">Greenhouse</option>
            <option value="ashby">Ashby</option>
            <option value="lever">Lever</option>
          </select>
          <button
            v-if="errorCount > 0"
            class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-surface-container border border-border-subtle text-xs text-amber-400 hover:text-amber-300 transition-colors"
            type="button"
            @click="showLogs = !showLogs"
          >
            <span class="material-symbols-outlined text-[15px]">warning</span>
            <span>{{ showLogs ? 'Ocultar errores' : `Ver errores (${errorCount})` }}</span>
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
              <th class="py-2.5 px-3 font-medium">ATS / ID</th>
              <th class="py-2.5 px-3 font-medium">Empresa</th>
              <th class="py-2.5 px-3 font-medium">Puesto de trabajo</th>
              <th class="py-2.5 px-3 font-medium">Ubicación</th>
              <th class="py-2.5 px-3 font-medium">Exp. requerida</th>
              <th class="py-2.5 px-3 font-medium">Match</th>
              <th class="py-2.5 px-3 font-medium text-right pr-4">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-subtle">
            <tr
              v-for="job in filteredMatches"
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
                    title="Esta vacante requiere resolver captcha"
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
                  {{ job.location || 'Remote' }}
                </span>
              </td>

              <!-- Exp. requerida -->
              <td class="py-3 px-3 font-mono text-on-surface-variant">
                {{ job.required_years ? `${job.required_years}+ años` : 'No especificada' }}
              </td>

              <!-- Match (Punto 1 implementado) -->
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
                    <span>{{ preparingMap[job.url] ? 'Preparando...' : (isJobPrepared(job) ? 'Preparado' : 'Preparar') }}</span>
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
                    :title="tailoringMap[job.url] ? 'El agente está adaptando el CV para esta vacante...' : (job.cv ? `CV generado: ${job.cv}` : 'Generar CV adaptado a medida para esta vacante')"
                    type="button"
                    @click="tailorApplication(job)"
                  >
                    <!-- Animación de carga durante la adaptación -->
                    <svg
                      v-if="tailoringMap[job.url]"
                      class="animate-spin h-3 w-3 text-accent shrink-0"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        class="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        stroke-width="4"
                      ></circle>
                      <path
                        class="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    <!-- Icono cuando ya está generado -->
                    <span
                      v-else-if="isJobTailored(job)"
                      class="material-symbols-outlined text-[13px] leading-none text-emerald-400"
                    >check_circle</span>
                    <!-- Icono cuando está pendiente -->
                    <span
                      v-else
                      class="material-symbols-outlined text-[13px] leading-none text-accent"
                    >auto_fix_high</span>

                    <span>{{ tailoringMap[job.url] ? 'Adaptando CV...' : (isJobTailored(job) ? 'CV Adaptado' : 'Adaptar CV') }}</span>
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
                    title="Abrir formulario en navegador Playwright"
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
                    title="Abrir vacante externa"
                  >
                    <span class="material-symbols-outlined text-[15px] block">open_in_new</span>
                  </a>
                </div>
              </td>
            </tr>

            <!-- Estado vacío -->
            <tr v-if="!filteredMatches.length">
              <td class="py-12 px-4 text-center text-outline" colspan="7">
                <div class="flex flex-col items-center justify-center gap-2">
                  <span class="material-symbols-outlined text-[36px] text-outline opacity-60">search_off</span>
                  <p class="text-xs font-medium text-on-surface">
                    {{ scanning ? 'Buscando ofertas que coincidan con tus filtros...' : 'No hay vacantes en esta vista' }}
                  </p>
                  <p class="text-[11px] text-outline max-w-sm">
                    {{ scanning ? 'Las ofertas aparecerán aquí en tiempo real a medida que sean descubiertas.' : 'Inicia un nuevo escaneo desde el botón superior o amplía tus filtros de búsqueda.' }}
                  </p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pie de tabla / Resumen -->
      <div class="p-3 border-t border-border-subtle flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-outline">
        <div class="flex items-center gap-2">
          <span>
            Mostrando <span class="text-on-surface font-medium">{{ filteredMatches.length }}</span> de <span class="text-on-surface font-medium">{{ matches.length }}</span> vacantes
          </span>
        </div>
      </div>
    </section>

    <!-- NOTIFICACIONES TOAST -->
    <v-snackbar v-model="snack.show" :color="snack.color" timeout="3500">
      {{ snack.text }}
    </v-snackbar>
  </div>
</template>
