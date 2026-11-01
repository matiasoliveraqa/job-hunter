<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api, formatCompanyName, STATUS_META } from '../api.js'
import { refreshAppStats } from '../stats.js'
import { t } from '../i18n/index.js'
import ApplicationsKpiCards from '../components/applications/ApplicationsKpiCards.vue'
import ApplicationsStatusTabs from '../components/applications/ApplicationsStatusTabs.vue'
import ApplicationsToolbar from '../components/applications/ApplicationsToolbar.vue'
import ApplicationsTable from '../components/applications/ApplicationsTable.vue'
import ApplicationStatusModal from '../components/applications/ApplicationStatusModal.vue'
import NewApplicationModal from '../components/applications/NewApplicationModal.vue'

const items = ref([])
const files = ref([])
const loading = ref(false)
const syncing = ref(false)
const search = ref('')
const selectedPlatform = ref('all')
const selectedSort = ref('recent')
const filterStatus = ref(null)
const snack = reactive({ show: false, text: '', color: 'success' })

const selectedIds = ref(new Set())
const expandedRows = ref(new Set())

const currentPage = ref(1)
const pageSize = ref(25)

const STATUS_STYLES = computed(() => ({
  pending: {
    bg: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    dot: 'bg-amber-400 animate-pulse',
    icon: 'hourglass_top',
    label: t('status.pending'),
  },
  applied: {
    bg: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    dot: 'bg-sky-400',
    icon: 'send',
    label: t('status.applied'),
  },
  interview: {
    bg: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    dot: 'bg-amber-400',
    icon: 'calendar_month',
    label: t('status.interview'),
  },
  offer: {
    bg: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    dot: 'bg-emerald-400',
    icon: 'verified',
    label: t('status.offer'),
  },
  rejected: {
    bg: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    dot: 'bg-rose-400',
    icon: 'cancel',
    label: t('status.rejected'),
  },
  withdrawn: {
    bg: 'bg-surface-container-high text-outline border-border-subtle',
    dot: 'bg-outline',
    icon: 'undo',
    label: t('status.withdrawn'),
  },
  not_sent: {
    bg: 'bg-surface-container-high text-outline border-border-subtle',
    dot: 'bg-outline',
    icon: 'block',
    label: t('status.not_sent'),
  },
}))

function notify(text, color = 'success') {
  Object.assign(snack, { show: true, text, color })
}

function getAppAts(item) {
  const u = (item.url || '').toLowerCase()
  if (u.includes('greenhouse.io') || u.includes('gh_jid')) return { key: 'greenhouse', label: 'Greenhouse ATS' }
  if (u.includes('lever.co')) return { key: 'lever', label: 'Lever ATS' }
  if (u.includes('ashbyhq.com')) return { key: 'ashby', label: 'Ashby ATS' }
  if (u.includes('workable.com')) return { key: 'workable', label: 'Workable ATS' }
  if (u.includes('breezy.hr')) return { key: 'breezy', label: 'Breezy HR' }
  if (u.includes('recruitee.com')) return { key: 'recruitee', label: 'Recruitee ATS' }
  if (u.includes('bamboohr.com') || u.includes('bamboohr.co.uk')) return { key: 'bamboohr', label: 'BambooHR ATS' }
  return { key: 'direct', label: t('applications.toolbar.directApply') }
}

async function load() {
  loading.value = true
  try {
    ;[items.value, files.value] = await Promise.all([api.listApplications(), api.listFiles()])
    await refreshAppStats()
  } catch (e) {
    notify(e.message, 'error')
  } finally {
    loading.value = false
  }
}

async function handleSync() {
  syncing.value = true
  try {
    await load()
    notify(t('applications.toasts.synced'))
  } finally {
    syncing.value = false
  }
}

onMounted(load)

// ---- Metrics & Real KPI Calculations ----
const nonDemoItems = computed(() => items.value.filter((a) => !a.demo))
const totalCount = computed(() => nonDemoItems.value.length)
const demoCount = computed(() => items.value.filter((a) => a.demo).length)

const last7DaysCount = computed(() => {
  const now = new Date()
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
  return nonDemoItems.value.filter((a) => {
    const dateStr = a.appliedAt || a.updatedAt || a.createdAt
    if (!dateStr) return false
    const d = new Date(dateStr)
    return !isNaN(d.getTime()) && d >= sevenDaysAgo
  }).length
})

const activeEnviadasCount = computed(() => nonDemoItems.value.filter((a) => a.status === 'applied').length)
const activePendientesCount = computed(() => nonDemoItems.value.filter((a) => a.status === 'pending').length)
const activeProcesoCount = computed(() => activeEnviadasCount.value + activePendientesCount.value)

const entrevistasCount = computed(() => nonDemoItems.value.filter((a) => a.status === 'interview').length)
const ofertasCount = computed(() => nonDemoItems.value.filter((a) => a.status === 'offer').length)
const responseRatio = computed(() => {
  const sent = activeEnviadasCount.value + entrevistasCount.value + ofertasCount.value + nonDemoItems.value.filter((a) => a.status === 'rejected').length
  if (sent === 0) return 0
  return Math.round(((entrevistasCount.value + ofertasCount.value) / sent) * 1000) / 10
})

const rechazadasCount = computed(() => nonDemoItems.value.filter((a) => a.status === 'rejected').length)
const retiradasCount = computed(() => nonDemoItems.value.filter((a) => a.status === 'withdrawn').length)
const descartadasTotal = computed(() => rechazadasCount.value + retiradasCount.value)

function generateSparklinePoints(filterFn) {
  const days = 7
  const countsByDay = new Array(days).fill(0)
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - (days - 1))

  for (const item of nonDemoItems.value) {
    if (filterFn && !filterFn(item)) continue
    const dateStr = item.appliedAt || item.updatedAt || item.createdAt
    if (!dateStr) continue
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) continue
    const diffDays = Math.floor((d.getTime() - start.getTime()) / (24 * 60 * 60 * 1000))
    if (diffDays >= 0 && diffDays < days) {
      countsByDay[diffDays]++
    }
  }

  const maxVal = Math.max(...countsByDay, 1)
  const coords = countsByDay.map((cnt, idx) => {
    const x = Math.round((idx / (days - 1)) * 100)
    const y = Math.round(28 - (cnt / maxVal) * 22)
    return `${x} ${y}`
  })

  const linePath = coords.map((c, idx) => (idx === 0 ? `M${c}` : `L${c}`)).join(' ')
  const areaPath = `${linePath} L100 32 L0 32 Z`
  return { linePath, areaPath }
}

const totalSparkline = computed(() => generateSparklinePoints())
const activeSparkline = computed(() => generateSparklinePoints((a) => ['pending', 'applied'].includes(a.status)))
const interviewSparkline = computed(() => generateSparklinePoints((a) => a.status === 'interview'))
const discardedSparkline = computed(() => generateSparklinePoints((a) => ['rejected', 'withdrawn'].includes(a.status)))

// ---- Status pills counts ----
const counts = computed(() =>
  Object.keys(STATUS_STYLES.value).map((key) => ({
    key,
    ...STATUS_META[key],
    title: STATUS_STYLES.value[key]?.label || STATUS_META[key]?.title,
    count: items.value.filter((a) => !a.demo && a.status === key).length,
  })),
)

// ---- Filtering and Sorting ----
function getArrivalDate(item) {
  return item.createdAt || item.history?.[0]?.at || item.updatedAt || ''
}

const filteredItems = computed(() => {
  const q = search.value.trim().toLowerCase()
  const plat = selectedPlatform.value
  const st = filterStatus.value

  const result = items.value.filter((item) => {
    if (st && item.status !== st) return false

    if (plat !== 'all') {
      const appAts = getAppAts(item).key
      if (appAts !== plat) return false
    }

    if (q) {
      const matchComp = (item.company || '').toLowerCase().includes(q)
      const matchRole = (item.role || '').toLowerCase().includes(q)
      const matchNotes = (item.notes || '').toLowerCase().includes(q)
      const matchReason = (item.reason || '').toLowerCase().includes(q)
      const matchAts = getAppAts(item).label.toLowerCase().includes(q)
      if (!matchComp && !matchRole && !matchNotes && !matchReason && !matchAts) return false
    }

    return true
  })

  result.sort((a, b) => {
    if (selectedSort.value === 'recent') {
      const dateA = getArrivalDate(a)
      const dateB = getArrivalDate(b)
      if (dateB !== dateA) return dateB.localeCompare(dateA)
      return 0
    }
    if (selectedSort.value === 'oldest') {
      const dateA = getArrivalDate(a)
      const dateB = getArrivalDate(b)
      if (dateA !== dateB) return dateA.localeCompare(dateB)
      return 0
    }
    if (selectedSort.value === 'company') {
      return (a.company || '').localeCompare(b.company || '')
    }
    if (selectedSort.value === 'status') {
      return (a.status || '').localeCompare(b.status || '')
    }
    return 0
  })

  return result
})

const totalPages = computed(() => Math.ceil(filteredItems.value.length / pageSize.value) || 1)
const paginatedItems = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredItems.value.slice(start, start + pageSize.value)
})

function prevPage() {
  if (currentPage.value > 1) currentPage.value--
}

function nextPage() {
  if (currentPage.value < totalPages.value) currentPage.value++
}

function resetFilters() {
  search.value = ''
  selectedPlatform.value = 'all'
  selectedSort.value = 'recent'
  filterStatus.value = null
  currentPage.value = 1
  selectedIds.value.clear()
}

// ---- Checkboxes and Batch actions ----
const isAllSelected = computed(() => {
  if (!paginatedItems.value.length) return false
  return paginatedItems.value.every((item) => selectedIds.value.has(item.id))
})

function toggleSelectAll() {
  if (isAllSelected.value) {
    for (const item of paginatedItems.value) {
      selectedIds.value.delete(item.id)
    }
  } else {
    for (const item of paginatedItems.value) {
      selectedIds.value.add(item.id)
    }
  }
}

function toggleSelect(id) {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
}

function clearSelection() {
  selectedIds.value.clear()
}

async function batchMarkApplied() {
  const targets = items.value.filter((a) => selectedIds.value.has(a.id) && a.status === 'pending')
  if (!targets.length) {
    return notify('Ninguna de las postulaciones seleccionadas está pendiente', 'info')
  }
  const today = new Date().toISOString().slice(0, 10)
  for (const app of targets) {
    try {
      const updated = await api.updateApplication(app.id, {
        status: 'applied',
        appliedAt: today,
        event: 'Postulación marcada como enviada por acción en lote',
      })
      if (updated) {
        Object.assign(app, updated)
      } else {
        app.status = 'applied'
        app.appliedAt = today
      }
      if (app.company && !app.demo) {
        await api.addExclusion({ company: app.company, reason: `Ya postulado (${today})` }).catch(() => {})
      }
    } catch {}
  }
  notify(`${targets.length} postulaciones marcadas como enviadas`)
  clearSelection()
  await refreshAppStats()
}

async function batchDelete() {
  const count = selectedIds.value.size
  if (!count) return
  if (!confirm(`¿Eliminar las ${count} postulaciones seleccionadas?`)) return
  for (const id of Array.from(selectedIds.value)) {
    try {
      await api.deleteApplication(id)
      items.value = items.value.filter((a) => a.id !== id)
    } catch {}
  }
  notify(`${count} postulaciones eliminadas`)
  clearSelection()
  await refreshAppStats()
}

// ---- Expandable row ----
function toggleExpandRow(id) {
  if (expandedRows.value.has(id)) {
    expandedRows.value.delete(id)
  } else {
    expandedRows.value.add(id)
  }
}

// ---- Status dialog ----
const statusDialog = reactive({ show: false, item: null, status: 'applied', reason: '', notes: '' })

function openStatus(item) {
  Object.assign(statusDialog, { show: true, item, status: item.status, reason: item.reason || '', notes: item.notes || '' })
}

async function saveStatus() {
  const needsReason = statusDialog.status === 'rejected' && !statusDialog.reason.trim()
  if (needsReason) return notify('Indica el motivo del rechazo', 'error')
  try {
    const updated = await api.updateApplication(statusDialog.item.id, {
      status: statusDialog.status,
      reason: statusDialog.reason,
      notes: statusDialog.notes,
    })
    Object.assign(statusDialog.item, updated)
    statusDialog.show = false
    notify('Estado actualizado')
    await refreshAppStats()
  } catch (e) {
    notify(e.message, 'error')
  }
}

// ---- New application dialog ----
const emptyForm = () => ({ company: '', role: '', url: '', cv: '' })
const newDialog = reactive({ show: false, form: emptyForm() })
const newFormOpened = ref(false)
const cvItems = computed(() => files.value.map((f) => `${f.dir}/${f.name}`))

async function launchForm() {
  try {
    await api.launchApply({
      url: newDialog.form.url,
      company: newDialog.form.company || undefined,
      role: newDialog.form.role || undefined,
      cv: newDialog.form.cv || undefined,
    })
    newFormOpened.value = true
    notify('Formulario abierto en Playwright')
  } catch (e) {
    notify(e.message, 'error')
  }
}

async function register() {
  if (!newDialog.form.company || !newDialog.form.role) {
    return notify('Empresa y puesto son obligatorios', 'error')
  }
  try {
    const created = await api.createApplication(newDialog.form)
    items.value.unshift(created)
    newDialog.show = false
    newDialog.form = emptyForm()
    notify(`Postulación a ${created.company} creada`)
    await refreshAppStats()
  } catch (e) {
    notify(e.message, 'error')
  }
}

// ---- Item actions ----
const openedAppsMap = reactive({})

async function launchItemForm(item) {
  try {
    await api.launchApply({
      url: item.url,
      company: item.company || undefined,
      role: item.role || undefined,
      cv: item.cv || undefined,
      applicationId: item.id,
      demo: item.demo || undefined,
    })
    openedAppsMap[item.id] = true
    await load()
    notify(`Formulario de ${item.company} abierto con Playwright`)
  } catch (e) {
    notify(e.message, 'error')
  }
}

const tailoringMap = reactive({})

async function tailorAppCv(item) {
  tailoringMap[item.id] = true
  try {
    const res = await api.tailorCv({
      company: item.company,
      role: item.role,
      url: item.url || undefined,
      description: item.role,
    })
    if (res?.cv) {
      item.cv = res.cv
      await api.updateApplication(item.id, { cv: res.cv })
      files.value = await api.listFiles().catch(() => files.value)
      notify(`CV adaptado generado para ${item.company} (${res.cv})`)
      await refreshAppStats()
    }
  } catch (err) {
    // If no AI engine is available, fall back to master base CV
    try {
      const fallback = await api.useBaseCv(item.id)
      if (fallback?.cv) {
        item.cv = fallback.cv
        files.value = await api.listFiles().catch(() => files.value)
        notify(`Sin motor de IA activo. Se asignó automáticamente tu CV base (${fallback.cv})`, 'warning')
        await refreshAppStats()
        return
      }
    } catch {}
    notify('Error al adaptar CV: ' + err.message, 'error')
  } finally {
    tailoringMap[item.id] = false
  }
}

async function assignBaseCv(item) {
  try {
    const res = await api.useBaseCv(item.id)
    if (res?.cv) {
      item.cv = res.cv
      files.value = await api.listFiles().catch(() => files.value)
      notify(`CV base asignado a ${item.company}`)
      await refreshAppStats()
    }
  } catch (err) {
    notify('Error al asignar CV base: ' + err.message, 'error')
  }
}

async function confirmSent(item) {
  const compName = formatCompanyName(item.company)
  if (!item.cv) {
    const ok = window.confirm(`"${compName}" no tiene un CV adaptado. Se registrará utilizando tu CV base estándar.\n¿Deseas confirmar el envío?`)
    if (!ok) return
  }
  const today = new Date().toISOString().slice(0, 10)
  try {
    const updated = await api.updateApplication(item.id, {
      status: 'applied',
      appliedAt: today,
      event: 'Postulación confirmada y enviada manualmente por el candidato',
    })
    if (updated) {
      Object.assign(item, updated)
    } else {
      item.status = 'applied'
      item.appliedAt = today
    }
    if (item.company && !item.demo) {
      await api.addExclusion({ company: item.company, reason: `Ya postulado (${today})` }).catch(() => {})
    }
    notify(`Postulación a ${compName} confirmada y agregada a exclusiones`)
    await refreshAppStats()
  } catch (e) {
    notify(e.message, 'error')
  }
}

async function openAppFolder(item) {
  try {
    const res = await api.openApplicationFolder(item.id)
    notify(t('applications.table.folderOpened', { folder: res.folderName || item.company }))
  } catch (err) {
    notify(err.message, 'error')
  }
}

async function remove(item) {
  const compName = formatCompanyName(item.company)
  if (!confirm(`¿Eliminar la postulación a ${compName}?`)) return
  await api.deleteApplication(item.id)
  items.value = items.value.filter((a) => a.id !== item.id)
  selectedIds.value.delete(item.id)
  expandedRows.value.delete(item.id)
  notify(`Postulación a ${compName} eliminada`)
  await refreshAppStats()
}

async function clearDemos() {
  if (!confirm(`¿Eliminar las ${demoCount.value} postulaciones de demostración?`)) return
  await api.clearDemos()
  items.value = items.value.filter((a) => !a.demo)
  notify('Postulaciones de prueba eliminadas')
  await refreshAppStats()
}
</script>

<template>
  <div class="p-6 flex flex-col gap-6 max-w-[1580px] w-full mx-auto">
    <!-- TOP HEADER / ACTION BAR -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-border-subtle">
      <div class="flex flex-col gap-1">
        <div class="flex items-center gap-3">
          <h1 class="text-2xl font-semibold text-on-surface tracking-tight">{{ $t('applications.title') }}</h1>
          <span class="px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant text-[11px] font-mono border border-border-subtle">
            {{ $t('applications.trackingCount', { count: totalCount }) }}
          </span>
        </div>
        <p class="text-xs text-on-surface-variant">
          {{ $t('applications.subtitle') }}
        </p>
      </div>

      <!-- Header actions -->
      <div class="flex items-center gap-2.5 flex-wrap">
        <button
          v-if="demoCount"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 border border-amber-500/20 text-xs font-medium transition-colors"
          type="button"
          @click="clearDemos"
        >
          <span class="material-symbols-outlined text-[15px]">science</span>
          <span>{{ $t('applications.clearDemos', { count: demoCount }) }}</span>
        </button>

        <button
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high border border-border-subtle text-xs font-medium transition-colors"
          :class="{ 'opacity-70 cursor-wait': syncing }"
          :disabled="syncing"
          :title="$t('applications.syncTip')"
          type="button"
          @click="handleSync"
        >
          <span :class="['material-symbols-outlined text-[16px]', syncing ? 'animate-spin text-accent' : '']">sync</span>
          <span>{{ $t('applications.sync') }}</span>
        </button>

        <button
          class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-accent hover:bg-accent-hover text-white text-xs font-medium shadow-sm transition-all active:scale-[0.98]"
          type="button"
          @click="newDialog.show = true; newFormOpened = false"
        >
          <span class="material-symbols-outlined text-[17px]">add</span>
          <span>{{ $t('applications.newApplication') }}</span>
        </button>
      </div>
    </div>

    <!-- KPI SUMMARY CARDS WITH REAL DATA & SPARKLINES -->
    <ApplicationsKpiCards
      :total-count="totalCount"
      :last-7-days-count="last7DaysCount"
      :total-sparkline="totalSparkline"
      :active-proceso-count="activeProcesoCount"
      :active-enviadas-count="activeEnviadasCount"
      :active-pendientes-count="activePendientesCount"
      :active-sparkline="activeSparkline"
      :entrevistas-count="entrevistasCount"
      :response-ratio="responseRatio"
      :interview-sparkline="interviewSparkline"
      :descartadas-total="descartadasTotal"
      :rechazadas-count="rechazadasCount"
      :retiradas-count="retiradasCount"
      :discarded-sparkline="discardedSparkline"
    />

    <!-- STATUS PILLS / FILTER TABS -->
    <ApplicationsStatusTabs
      v-model:filter-status="filterStatus"
      :counts="counts"
      :total-count="totalCount"
      :status-styles="STATUS_STYLES"
      @update:filter-status="currentPage = 1"
    />

    <!-- CONTROLS & SEARCH TOOLBAR -->
    <ApplicationsToolbar
      v-model:search="search"
      v-model:selected-platform="selectedPlatform"
      v-model:selected-sort="selectedSort"
      :selected-count="selectedIds.size"
      @reset-filters="resetFilters"
      @batch-mark-applied="batchMarkApplied"
      @batch-delete="batchDelete"
      @clear-selection="clearSelection"
    />

    <!-- APPLICATIONS TABLE -->
    <ApplicationsTable
      :paginated-items="paginatedItems"
      :filtered-items-count="filteredItems.length"
      :selected-ids="selectedIds"
      :is-all-selected="isAllSelected"
      :expanded-rows="expandedRows"
      :current-page="currentPage"
      :page-size="pageSize"
      :total-pages="totalPages"
      :status-styles="STATUS_STYLES"
      :tailoring-map="tailoringMap"
      :opened-apps-map="openedAppsMap"
      @toggle-select-all="toggleSelectAll"
      @toggle-select="toggleSelect"
      @toggle-expand-row="toggleExpandRow"
      @tailor-cv="tailorAppCv"
      @assign-base-cv="assignBaseCv"
      @launch-form="launchItemForm"
      @confirm-sent="confirmSent"
      @open-folder="openAppFolder"
      @open-status="openStatus"
      @remove="remove"
      @prev-page="prevPage"
      @next-page="nextPage"
      @reset-filters="resetFilters"
    />

    <!-- MODAL CAMBIAR ESTADO -->
    <ApplicationStatusModal
      :show="statusDialog.show"
      :dialog="statusDialog"
      :status-styles="STATUS_STYLES"
      @close="statusDialog.show = false"
      @save="saveStatus"
    />

    <!-- MODAL NUEVA POSTULACIÓN -->
    <NewApplicationModal
      :show="newDialog.show"
      :dialog="newDialog"
      :cv-items="cvItems"
      :new-form-opened="newFormOpened"
      @close="newDialog.show = false"
      @register="register"
      @launch-form="launchForm"
    />

    <!-- NOTIFICACIONES TOAST -->
    <div
      v-if="snack.show"
      class="fixed bottom-5 right-5 z-50 px-4 py-2.5 rounded-lg shadow-xl text-xs font-medium flex items-center gap-2 border animate-in slide-in-from-bottom-2 duration-150"
      :class="[
        snack.color === 'error'
          ? 'bg-rose-950/90 text-rose-200 border-rose-800'
          : snack.color === 'warning'
            ? 'bg-amber-950/90 text-amber-200 border-amber-800'
            : 'bg-surface-card text-on-surface border-border-muted'
      ]"
    >
      <span class="material-symbols-outlined text-[16px]">
        {{ snack.color === 'error' ? 'error' : snack.color === 'warning' ? 'warning' : 'check_circle' }}
      </span>
      <span>{{ snack.text }}</span>
      <button class="ml-2 text-outline hover:text-on-surface" type="button" @click="snack.show = false">✕</button>
    </div>
  </div>
</template>
