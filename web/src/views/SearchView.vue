<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { api } from '../api.js'

const profile = ref(null)
const loadingProfile = ref(true)
const scanning = ref(false)
const progress = reactive({ checked: 0, total: 0, platform: '', company: '' })
const matches = ref([])
const errorCount = ref(0)
const snack = reactive({ show: false, text: '', color: 'success' })
const logs = ref([])
const showLogs = ref(false)

let abortController = null

const form = reactive({
  roles: [],
  platforms: ['ashby', 'greenhouse', 'lever'],
  latamOnly: true,
  maxYears: 7,
  allowCaptcha: false,
  concurrency: 50,
})

const PRESETS = [
  {
    name: 'QA / SDET',
    icon: 'mdi-shield-check',
    roles: ['QA Automation Engineer', 'Senior QA Engineer', 'SDET', 'Software Engineer in Test', 'QA Engineer'],
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
  {
    name: 'Data / AI',
    icon: 'mdi-brain',
    roles: ['Data Engineer', 'Machine Learning Engineer', 'AI Engineer'],
  },
]

function notify(text, color = 'success') {
  Object.assign(snack, { show: true, text, color })
}

function applyPreset(preset) {
  form.roles = [...preset.roles]
  notify(`Preset "${preset.name}" aplicado (${preset.roles.length} roles)`)
}

function resetToProfile() {
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

const existingApps = ref([])

async function loadExistingApps() {
  try {
    existingApps.value = await api.getApplications()
  } catch {}
}

async function loadProfile() {
  loadingProfile.value = true
  try {
    const data = await api.getProfile()
    profile.value = data
    if (data?.search_criteria?.target_roles?.length) {
      form.roles = [...data.search_criteria.target_roles]
    } else {
      form.roles = ['QA Automation Engineer', 'SDET', 'QA Engineer']
    }
    if (data?.ats_settings?.enabled_platforms?.length) {
      form.platforms = [...data.ats_settings.enabled_platforms]
    }
    if (data?.personal_info?.years_of_experience) {
      form.maxYears = data.personal_info.years_of_experience
    }
    await loadExistingApps()
  } catch (e) {
    notify('No se pudo cargar el perfil: ' + e.message, 'warning')
  } finally {
    loadingProfile.value = false
  }
}

onMounted(loadProfile)
onUnmounted(() => {
  if (scanning.value) stopScan()
})

const progressPercent = computed(() => {
  if (!progress.total) return 0
  return Math.min(100, Math.round((progress.checked / progress.total) * 100))
})

async function startScan() {
  if (!form.roles.length) {
    return notify('Ingresa al menos un rol objetivo para buscar', 'error')
  }
  if (!form.platforms.length) {
    return notify('Selecciona al menos una plataforma ATS', 'error')
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
          handleEvent(evt)
        } catch {
          // ignora chunks incompletos
        }
      }
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      notify('Error en el escaneo: ' + err.message, 'error')
    }
  } finally {
    scanning.value = false
  }
}

function handleEvent(evt) {
  if (evt.type === 'progress') {
    progress.checked = evt.checked
    progress.total = evt.total
    progress.platform = evt.platform
    progress.company = evt.company
  } else if (evt.type === 'match') {
    const p = evt.posting
    // Prevenir duplicados en la lista local
    if (!matches.value.some((m) => m.url === p.url)) {
      const matchedApp = existingApps.value.find(
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
    notify(`Búsqueda finalizada. ${evt.total_matches} vacantes encontradas.`)
    scanning.value = false
  } else if (evt.type === 'exit') {
    scanning.value = false
  }
}

async function stopScan() {
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
  notify('Búsqueda detenida por el usuario', 'info')
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
  if (isJobPrepared(posting)) {
    return notify(`"${posting.company}" ya está en tu lista de postulaciones`, 'info')
  }
  preparingMap[posting.url] = true
  try {
    const created = await api.createApplication({
      company: posting.company,
      role: posting.title,
      url: posting.url,
      cv: posting.cv || undefined,
      status: 'pending',
      notes: `Detectada en escaneo ATS (${posting.ats.toUpperCase()})`,
    })
    preparedMap[posting.url] = true
    existingApps.value.unshift(created)
    notify(`Postulación agregada a "Pendiente de envío" para ${posting.company}`)
  } catch (err) {
    notify('No se pudo guardar la postulación: ' + err.message, 'error')
  } finally {
    preparingMap[posting.url] = false
  }
}

async function tailorApplication(posting) {
  tailoringMap[posting.url] = true
  try {
    const res = await api.tailorCv({
      company: posting.company,
      role: posting.title,
      url: posting.url,
      description: posting.title,
    })
    if (res?.cv) {
      posting.cv = res.cv
      tailoredMap[posting.url] = true
    }
    await loadExistingApps()
    notify(`CV adaptado generado para ${posting.company} (${res.cv})`)
  } catch (err) {
    notify('Error al adaptar CV con agente: ' + err.message, 'error')
  } finally {
    tailoringMap[posting.url] = false
  }
}

async function openInBrowser(posting) {
  launchingMap[posting.url] = true
  try {
    await api.launchApply({
      url: posting.url,
      company: posting.company,
      role: posting.title,
      cv: posting.cv || undefined,
    })
    openedMap[posting.url] = true
    notify(`Navegador lanzado con Playwright para ${posting.company}`)
  } catch (err) {
    notify('Error al abrir navegador: ' + err.message, 'error')
  } finally {
    launchingMap[posting.url] = false
  }
}

function platformColor(ats) {
  const low = String(ats || '').toLowerCase()
  if (low === 'greenhouse') return 'green'
  if (low === 'ashby') return 'purple'
  if (low === 'lever') return 'blue'
  return 'grey'
}
</script>

<template>
  <v-container fluid class="pa-6" style="max-width: 1400px">
    <!-- Encabezado -->
    <div class="d-flex align-center justify-space-between mb-4 flex-wrap gap-2">
      <div>
        <h1 class="text-h5 font-weight-bold d-flex align-center">
          <v-icon icon="mdi-magnify" class="mr-2" color="primary" />
          Búsqueda y Preparación de Vacantes
        </h1>
        <div class="text-subtitle-2 text-medium-emphasis">
          Escaneo directo en APIs de Ashby, Greenhouse y Lever con filtrado estricto por residencia y experiencia.
        </div>
      </div>
      <div class="d-flex gap-2">
        <v-btn
          v-if="!scanning"
          color="primary"
          prepend-icon="mdi-play"
          size="large"
          elevation="2"
          :loading="loadingProfile"
          @click="startScan"
        >
          Buscar vacantes
        </v-btn>
        <v-btn
          v-else
          color="error"
          prepend-icon="mdi-stop"
          size="large"
          elevation="2"
          @click="stopScan"
        >
          Detener búsqueda
        </v-btn>
      </div>
    </div>

    <!-- Panel de Filtros -->
    <v-card class="mb-6" elevation="1">
      <v-card-text>
        <!-- Fila de Presets rápidos -->
        <div class="mb-3">
          <div class="text-caption text-medium-emphasis mb-1 font-weight-bold">
            PRESETS RÁPIDOS (1 CLIC PARA CONFIGURAR CARGOS):
          </div>
          <div class="d-flex flex-wrap gap-2 align-center">
            <v-btn
              v-for="p in PRESETS"
              :key="p.name"
              size="small"
              variant="tonal"
              color="primary"
              :prepend-icon="p.icon"
              @click="applyPreset(p)"
            >
              {{ p.name }}
            </v-btn>
            <v-btn
              size="small"
              variant="outlined"
              color="secondary"
              prepend-icon="mdi-refresh"
              @click="resetToProfile"
            >
              Restablecer de mi perfil
            </v-btn>
            <v-btn
              v-if="form.roles.length"
              size="small"
              variant="text"
              color="error"
              @click="form.roles = []"
            >
              Limpiar
            </v-btn>
          </div>
        </div>

        <!-- Entrada de Cargos con Chips -->
        <v-combobox
          v-model="form.roles"
          label="Cargos o palabras clave a buscar (Escribe y presiona Enter)"
          multiple
          chips
          closable-chips
          variant="outlined"
          density="comfortable"
          hint="Ej: QA Automation Engineer, SDET, Backend Engineer, Playwright"
          persistent-hint
          class="mb-4"
        />

        <!-- Controles secundarios -->
        <v-row density="compact" class="mt-1">
          <!-- Plataformas ATS -->
          <v-col cols="12" sm="6" md="3">
            <div class="text-caption text-medium-emphasis mb-1 font-weight-bold">PLATAFORMAS ATS:</div>
            <div class="d-flex flex-wrap gap-2">
              <v-checkbox
                v-model="form.platforms"
                value="greenhouse"
                label="Greenhouse"
                density="compact"
                hide-details
                color="green"
              />
              <v-checkbox
                v-model="form.platforms"
                value="ashby"
                label="Ashby"
                density="compact"
                hide-details
                color="purple"
              />
              <v-checkbox
                v-model="form.platforms"
                value="lever"
                label="Lever"
                density="compact"
                hide-details
                color="blue"
              />
            </div>
          </v-col>

          <!-- Filtro de residencia -->
          <v-col cols="12" sm="6" md="3">
            <div class="text-caption text-medium-emphasis mb-1 font-weight-bold">UBICACIÓN Y RESIDENCIA:</div>
            <v-switch
              v-model="form.latamOnly"
              color="primary"
              density="compact"
              hide-details
              :label="form.latamOnly ? 'Solo LATAM / Global' : 'Cualquier remoto'"
            />
            <div class="text-caption text-medium-emphasis mt-1">
              {{ form.latamOnly ? 'Descarta vacantes que exigen residencia en EE. UU., Europa o Asia.' : 'Permite vacantes remotas de cualquier país.' }}
            </div>
          </v-col>

          <!-- Experiencia máxima -->
          <v-col cols="12" sm="6" md="3">
            <div class="text-caption text-medium-emphasis mb-1 font-weight-bold">EXPERIENCIA MÁXIMA:</div>
            <v-text-field
              v-model.number="form.maxYears"
              type="number"
              variant="outlined"
              density="compact"
              suffix="años"
              hint="Descarta ofertas que exijan más años"
              persistent-hint
            />
          </v-col>

          <!-- Filtro de captcha -->
          <v-col cols="12" sm="6" md="3">
            <div class="text-caption text-medium-emphasis mb-1 font-weight-bold">VACANTES CON CAPTCHA:</div>
            <v-switch
              v-model="form.allowCaptcha"
              color="primary"
              density="compact"
              hide-details
              :label="form.allowCaptcha ? 'Permitir (con evasión)' : 'Ocultar vacantes'"
            />
            <div class="text-caption text-medium-emphasis mt-1">
              {{ form.allowCaptcha ? 'Permite vacantes con captcha (ej. Lever con hCaptcha).' : 'Descarta vacantes con captcha por defecto.' }}
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Estado y Progreso en vivo -->
    <v-card v-if="scanning || progress.total > 0" class="mb-6" elevation="1">
      <v-card-text>
        <div class="d-flex align-center justify-space-between mb-2">
          <div class="d-flex align-center">
            <v-progress-circular
              v-if="scanning"
              indeterminate
              color="primary"
              size="20"
              width="2"
              class="mr-2"
            />
            <span class="font-weight-medium">
              {{ scanning ? 'Escaneando bolsas de empleo...' : 'Escaneo finalizado' }}
            </span>
            <span v-if="progress.company" class="text-caption text-medium-emphasis ml-2">
              Analizando: {{ progress.platform.toUpperCase() }} / {{ progress.company }}
            </span>
          </div>
          <div class="text-caption font-weight-bold">
            {{ progress.checked }} / {{ progress.total }} empresas ({{ progressPercent }}%)
          </div>
        </div>

        <v-progress-linear
          :model-value="progressPercent"
          color="primary"
          height="8"
          rounded
          class="mb-3"
        />

        <!-- Métricas rápidas -->
        <v-row density="compact">
          <v-col cols="4">
            <v-card variant="tonal" color="primary" class="pa-2 text-center">
              <div class="text-caption">EMPRESAS ANALIZADAS</div>
              <div class="text-h6 font-weight-bold">{{ progress.checked }}</div>
            </v-card>
          </v-col>
          <v-col cols="4">
            <v-card variant="tonal" color="success" class="pa-2 text-center">
              <div class="text-caption">VACANTES ENCONTRADAS</div>
              <div class="text-h6 font-weight-bold">{{ matches.length }}</div>
            </v-card>
          </v-col>
          <v-col cols="4">
            <v-card variant="tonal" color="warning" class="pa-2 text-center">
              <div class="text-caption">ERRORES HTTP / 404</div>
              <div class="text-h6 font-weight-bold">{{ errorCount }}</div>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Tabla de Vacantes Encontradas -->
    <v-card elevation="1">
      <v-card-title class="d-flex align-center justify-space-between flex-wrap py-3">
        <div class="d-flex align-center">
          <span>Vacantes encontradas</span>
          <v-chip size="small" color="success" class="ml-2 font-weight-bold">
            {{ matches.length }}
          </v-chip>
        </div>
        <v-btn
          v-if="logs.length"
          size="small"
          variant="text"
          :prepend-icon="showLogs ? 'mdi-chevron-up' : 'mdi-chevron-down'"
          @click="showLogs = !showLogs"
        >
          {{ showLogs ? 'Ocultar registro de errores' : `Ver errores (${errorCount})` }}
        </v-btn>
      </v-card-title>

      <!-- Panel desplegable de logs de error -->
      <v-expand-transition>
        <div v-if="showLogs" class="pa-4 bg-grey-lighten-4 border-b">
          <div class="text-caption text-medium-emphasis mb-1 font-weight-bold">ÚLTIMOS ERRORES DE CONEXIÓN:</div>
          <div style="max-height: 150px; overflow-y: auto; font-family: monospace; font-size: 11px">
            <div v-for="(log, idx) in logs" :key="idx" class="text-error">
              {{ log }}
            </div>
          </div>
        </div>
      </v-expand-transition>

      <v-divider />

      <v-table v-if="matches.length" hover density="comfortable">
        <thead>
          <tr>
            <th>Plataforma</th>
            <th>Empresa</th>
            <th>Puesto</th>
            <th>Ubicación</th>
            <th>Exp. requerida</th>
            <th class="text-end" style="min-width: 330px">Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="job in matches" :key="job.url">
            <td>
              <v-chip size="x-small" :color="platformColor(job.ats)" class="text-uppercase font-weight-bold">
                {{ job.ats }}
              </v-chip>
            </td>
            <td class="font-weight-medium">
              {{ job.company }}
              <v-chip
                v-if="job.has_captcha"
                size="x-small"
                color="warning"
                variant="tonal"
                class="ml-1"
                prepend-icon="mdi-shield-alert-outline"
                title="Esta vacante requiere resolver un captcha (hCaptcha / Turnstile)"
              >
                Captcha
              </v-chip>
            </td>
            <td>
              <a :href="job.url" target="_blank" rel="noopener noreferrer" class="text-primary text-decoration-none font-weight-medium">
                {{ job.title }}
                <v-icon icon="mdi-open-in-new" size="x-small" class="ml-1" />
              </a>
            </td>
            <td class="text-body-2">{{ job.location || 'Remote' }}</td>
            <td>
              <v-chip v-if="job.required_years" size="x-small" color="info" variant="tonal">
                {{ job.required_years }}+ años
              </v-chip>
              <span v-else class="text-medium-emphasis text-caption">-</span>
            </td>
            <td class="text-end" style="min-width: 350px; white-space: nowrap">
              <div class="d-flex align-center justify-end ga-2 flex-nowrap">
                <v-btn
                  size="small"
                  variant="tonal"
                  :color="isJobPrepared(job) ? 'success' : 'primary'"
                  :prepend-icon="isJobPrepared(job) ? 'mdi-check' : 'mdi-plus'"
                  :loading="preparingMap[job.url]"
                  @click="prepareApplication(job)"
                >
                  {{ isJobPrepared(job) ? 'Preparado' : 'Preparar' }}
                </v-btn>
                <v-btn
                  size="small"
                  variant="tonal"
                  :color="isJobTailored(job) ? 'success' : 'info'"
                  :prepend-icon="isJobTailored(job) ? 'mdi-check-circle' : 'mdi-file-document-edit'"
                  :loading="tailoringMap[job.url]"
                  @click="tailorApplication(job)"
                >
                  {{ isJobTailored(job) ? 'CV Adaptado' : 'Adaptar CV' }}
                </v-btn>
                <v-btn
                  size="small"
                  :variant="isJobOpened(job) ? 'tonal' : 'outlined'"
                  :color="isJobOpened(job) ? 'success' : 'secondary'"
                  :prepend-icon="isJobOpened(job) ? 'mdi-check-all' : 'mdi-web'"
                  :loading="launchingMap[job.url]"
                  @click="openInBrowser(job)"
                >
                  {{ isJobOpened(job) ? 'Formulario abierto' : 'Abrir form' }}
                </v-btn>
              </div>
              <div v-if="job.cv" class="text-caption text-success mt-1 d-flex align-center justify-end">
                <v-icon icon="mdi-check-circle" size="x-small" color="success" class="mr-1" />
                <span>CV listo: {{ job.cv.split('/').pop() }}</span>
              </div>
            </td>
          </tr>
        </tbody>
      </v-table>

      <!-- Estado vacío -->
      <div v-else class="pa-10 text-center text-medium-emphasis">
        <v-icon icon="mdi-text-box-search-outline" size="48" class="mb-2" />
        <div class="text-body-1 font-weight-medium">
          {{ scanning ? 'Buscando ofertas que coincidan con tus filtros...' : 'No hay ofertas escaneadas todavía' }}
        </div>
        <div class="text-caption mt-1">
          {{ scanning ? 'Las ofertas aparecerán aquí en tiempo real a medida que sean descubiertas.' : 'Configura tus roles y presiona "Buscar vacantes" para iniciar el escaneo.' }}
        </div>
      </div>
    </v-card>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="3500">
      {{ snack.text }}
    </v-snackbar>
  </v-container>
</template>

<style scoped>
.gap-2 {
  gap: 8px;
}
.gap-4 {
  gap: 16px;
}
</style>
