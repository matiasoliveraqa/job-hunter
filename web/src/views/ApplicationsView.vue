<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api, formatCompanyName, STATUS_META } from '../api.js'
import { refreshAppStats } from '../stats.js'

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

const STATUS_STYLES = {
  pending: {
    bg: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    dot: 'bg-amber-400 animate-pulse',
    icon: 'hourglass_top',
    label: 'Pendiente de envío',
  },
  applied: {
    bg: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    dot: 'bg-sky-400',
    icon: 'send',
    label: 'Enviada',
  },
  interview: {
    bg: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
    dot: 'bg-amber-400',
    icon: 'calendar_month',
    label: 'Entrevista',
  },
  offer: {
    bg: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    dot: 'bg-emerald-400',
    icon: 'verified',
    label: 'Oferta / aceptada',
  },
  rejected: {
    bg: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
    dot: 'bg-rose-400',
    icon: 'cancel',
    label: 'Rechazada',
  },
  withdrawn: {
    bg: 'bg-surface-container-high text-outline border-border-subtle',
    dot: 'bg-outline',
    icon: 'undo',
    label: 'Retirada',
  },
  not_sent: {
    bg: 'bg-surface-container-high text-outline border-border-subtle',
    dot: 'bg-outline',
    icon: 'block',
    label: 'No enviada',
  },
}

function notify(text, color = 'success') {
  Object.assign(snack, { show: true, text, color })
}

function fmtDate(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return iso
    return d.toLocaleDateString([], {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function getAppAts(item) {
  const u = (item.url || '').toLowerCase()
  if (u.includes('greenhouse.io')) return { key: 'greenhouse', label: 'Greenhouse ATS' }
  if (u.includes('lever.co')) return { key: 'lever', label: 'Lever ATS' }
  if (u.includes('ashbyhq.com')) return { key: 'ashby', label: 'Ashby ATS' }
  return { key: 'direct', label: 'Postulación directa' }
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
    notify('Postulaciones sincronizadas')
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
  Object.keys(STATUS_META).map((key) => ({
    key,
    ...STATUS_META[key],
    count: items.value.filter((a) => !a.demo && a.status === key).length,
  })),
)

function toggleStatusFilter(key) {
  filterStatus.value = filterStatus.value === key ? null : key
  currentPage.value = 1
}

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

function isAppOpened(item) {
  if (openedAppsMap[item.id]) return true
  return Boolean(
    item.history?.some((h) =>
      h.note?.toLowerCase().includes('formulario abierto') ||
      h.note?.toLowerCase().includes('playwright')
    )
  )
}

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
    // If no AI engine is available, seamlessly fall back to master base CV
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
          <h1 class="text-2xl font-semibold text-on-surface tracking-tight">Postulaciones</h1>
          <span class="px-2 py-0.5 rounded-full bg-surface-container-high text-on-surface-variant text-[11px] font-mono border border-border-subtle">
            {{ totalCount }} en seguimiento
          </span>
        </div>
        <p class="text-xs text-on-surface-variant">
          Seguimiento de candidaturas enviadas, entrevistas, respuestas ATS y carpetas de CV generadas.
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
          <span>Limpiar demos ({{ demoCount }})</span>
        </button>

        <button
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high border border-border-subtle text-xs font-medium transition-colors"
          :class="{ 'opacity-70 cursor-wait': syncing }"
          :disabled="syncing"
          title="Sincronizar cambios con el servidor"
          type="button"
          @click="handleSync"
        >
          <span :class="['material-symbols-outlined text-[16px]', syncing ? 'animate-spin text-accent' : '']">sync</span>
          <span>Sincronizar</span>
        </button>

        <button
          class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-accent hover:bg-accent-hover text-white text-xs font-medium shadow-sm transition-all active:scale-[0.98]"
          type="button"
          @click="newDialog.show = true; newFormOpened = false"
        >
          <span class="material-symbols-outlined text-[17px]">add</span>
          <span>Nueva postulación</span>
        </button>
      </div>
    </div>

    <!-- KPI SUMMARY CARDS WITH REAL DATA & SPARKLINES -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Card 1: Total Postulaciones -->
      <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
        <div class="flex items-start justify-between">
          <div class="flex flex-col">
            <span class="text-[11px] uppercase tracking-wider text-outline font-mono">Total Registradas</span>
            <span class="text-[26px] font-semibold text-on-surface tracking-tight mt-1 group-hover:text-primary transition-colors">
              {{ totalCount }}
            </span>
          </div>
          <div class="p-2 rounded-lg bg-surface-container text-accent">
            <span class="material-symbols-outlined text-[20px]">send</span>
          </div>
        </div>
        <div class="flex items-end justify-between mt-4">
          <div class="flex items-center gap-1 text-[11px] text-emerald-400 font-mono">
            <span class="material-symbols-outlined text-[14px]">trending_up</span>
            <span>+{{ last7DaysCount }} esta semana</span>
          </div>
          <svg class="w-24 h-8 text-accent overflow-visible" fill="none" viewBox="0 0 100 32">
            <path :d="totalSparkline.linePath" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
            <path :d="totalSparkline.areaPath" fill="currentColor" fill-opacity="0.08" />
          </svg>
        </div>
      </div>

      <!-- Card 2: En Proceso Activo -->
      <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
        <div class="flex items-start justify-between">
          <div class="flex flex-col">
            <span class="text-[11px] uppercase tracking-wider text-outline font-mono">En Proceso Activo</span>
            <span class="text-[26px] font-semibold text-on-surface tracking-tight mt-1">
              {{ activeProcesoCount }}
            </span>
          </div>
          <div class="p-2 rounded-lg bg-surface-container text-sky-400">
            <span class="material-symbols-outlined text-[20px]">hourglass_top</span>
          </div>
        </div>
        <div class="flex items-end justify-between mt-4">
          <div class="flex items-center gap-1 text-[11px] text-on-surface-variant font-mono">
            <span class="text-sky-400 font-semibold">{{ activeEnviadasCount }}</span> enviadas • <span class="text-amber-400 font-semibold">{{ activePendientesCount }}</span> pend.
          </div>
          <svg class="w-24 h-8 text-sky-400 overflow-visible" fill="none" viewBox="0 0 100 32">
            <path :d="activeSparkline.linePath" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
            <path :d="activeSparkline.areaPath" fill="currentColor" fill-opacity="0.08" />
          </svg>
        </div>
      </div>

      <!-- Card 3: Entrevistas / Ofertas -->
      <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
        <div class="flex items-start justify-between">
          <div class="flex flex-col">
            <span class="text-[11px] uppercase tracking-wider text-outline font-mono">Entrevistas Agendadas</span>
            <span class="text-[26px] font-semibold text-amber-400 tracking-tight mt-1">
              {{ entrevistasCount }}
            </span>
          </div>
          <div class="p-2 rounded-lg bg-surface-container text-amber-400">
            <span class="material-symbols-outlined text-[20px]">calendar_month</span>
          </div>
        </div>
        <div class="flex items-end justify-between mt-4">
          <div class="flex items-center gap-1 text-[11px] text-amber-400 font-mono">
            <span class="material-symbols-outlined text-[14px]">forum</span>
            <span>{{ responseRatio }}% ratio respuesta</span>
          </div>
          <svg class="w-24 h-8 text-amber-400 overflow-visible" fill="none" viewBox="0 0 100 32">
            <path :d="interviewSparkline.linePath" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
            <path :d="interviewSparkline.areaPath" fill="currentColor" fill-opacity="0.08" />
          </svg>
        </div>
      </div>

      <!-- Card 4: Descartadas / Retiradas -->
      <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
        <div class="flex items-start justify-between">
          <div class="flex flex-col">
            <span class="text-[11px] uppercase tracking-wider text-outline font-mono">Descartadas / Retiradas</span>
            <span class="text-[26px] font-semibold text-on-surface tracking-tight mt-1">
              {{ descartadasTotal }}
            </span>
          </div>
          <div class="p-2 rounded-lg bg-surface-container text-outline">
            <span class="material-symbols-outlined text-[20px]">do_not_disturb_on</span>
          </div>
        </div>
        <div class="flex items-end justify-between mt-4">
          <div class="flex items-center gap-1 text-[11px] text-outline font-mono">
            <span>{{ rechazadasCount }} rechazada • {{ retiradasCount }} retirada</span>
          </div>
          <svg class="w-24 h-8 text-rose-500/60 overflow-visible" fill="none" viewBox="0 0 100 32">
            <path :d="discardedSparkline.linePath" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
            <path :d="discardedSparkline.areaPath" fill="currentColor" fill-opacity="0.08" />
          </svg>
        </div>
      </div>
    </section>

    <!-- STATUS PILLS / FILTER TABS -->
    <div class="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-border-subtle text-xs font-medium">
      <button
        type="button"
        :class="[
          'px-3 py-1.5 rounded-lg flex items-center gap-2 transition-colors whitespace-nowrap',
          filterStatus === null
            ? 'bg-surface-container-highest text-on-surface shadow-sm'
            : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
        ]"
        @click="filterStatus = null; currentPage = 1"
      >
        <span>Todas</span>
        <span class="px-1.5 py-0.2 rounded-md bg-surface-dim text-[11px] font-mono text-outline">{{ totalCount }}</span>
      </button>

      <button
        v-for="c in counts"
        :key="c.key"
        type="button"
        :class="[
          'px-3 py-1.5 rounded-lg flex items-center gap-2 transition-colors whitespace-nowrap',
          filterStatus === c.key
            ? 'bg-surface-container-highest text-on-surface shadow-sm'
            : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
        ]"
        @click="toggleStatusFilter(c.key)"
      >
        <span :class="['w-2 h-2 rounded-full', STATUS_STYLES[c.key]?.dot || 'bg-outline']"></span>
        <span>{{ c.title }}</span>
        <span class="px-1.5 py-0.2 rounded-md bg-surface-container text-[11px] font-mono text-outline">{{ c.count }}</span>
      </button>
    </div>

    <!-- CONTROLS & SEARCH TOOLBAR -->
    <div class="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
      <!-- Search Input -->
      <div class="relative flex-1 max-w-lg">
        <span class="material-symbols-outlined absolute left-3 top-2.5 text-[17px] text-outline pointer-events-none">search</span>
        <input
          v-model="search"
          class="w-full pl-9 pr-12 py-2 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:border-accent focus:outline-none placeholder:text-outline transition-colors"
          placeholder="Buscar por empresa, puesto, ATS o notas..."
          type="text"
          @input="currentPage = 1"
        />
        <span v-if="search" class="absolute right-3 top-2.5 text-outline hover:text-on-surface cursor-pointer text-xs" @click="search = ''">✕</span>
      </div>

      <!-- Filters & Actions -->
      <div class="flex items-center gap-2.5 flex-wrap">
        <!-- ATS Selector -->
        <div class="relative">
          <select
            v-model="selectedPlatform"
            class="appearance-none pl-3 pr-8 py-2 rounded-lg bg-surface-container text-on-surface-variant text-xs border border-border-subtle hover:border-border-muted focus:border-accent focus:outline-none transition-colors cursor-pointer"
            @change="currentPage = 1"
          >
            <option value="all">Portal / ATS: Todos</option>
            <option value="greenhouse">Greenhouse ATS</option>
            <option value="lever">Lever ATS</option>
            <option value="ashby">Ashby ATS</option>
            <option value="direct">Postulación directa</option>
          </select>
          <span class="material-symbols-outlined absolute right-2 top-2.5 text-[16px] text-outline pointer-events-none">arrow_drop_down</span>
        </div>

        <!-- Sorting Selector -->
        <div class="relative">
          <select
            v-model="selectedSort"
            class="appearance-none pl-3 pr-8 py-2 rounded-lg bg-surface-container text-on-surface-variant text-xs border border-border-subtle hover:border-border-muted focus:border-accent focus:outline-none transition-colors cursor-pointer"
          >
            <option value="recent">Más recientes primero</option>
            <option value="oldest">Más antiguas primero</option>
            <option value="company">Empresa (A-Z)</option>
            <option value="status">Por estado</option>
          </select>
          <span class="material-symbols-outlined absolute right-2 top-2.5 text-[16px] text-outline pointer-events-none">sort</span>
        </div>

        <!-- Reset button -->
        <button
          class="px-2.5 py-2 rounded-lg bg-surface-container text-outline hover:text-on-surface border border-border-subtle text-xs transition-colors"
          title="Restablecer filtros"
          type="button"
          @click="resetFilters"
        >
          <span class="material-symbols-outlined text-[16px] block">filter_alt_off</span>
        </button>
      </div>
    </div>

    <!-- BATCH ACTIONS FLOATING BAR -->
    <div
      v-if="selectedIds.size > 0"
      class="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-accent/10 border border-accent/30 text-on-surface text-xs animate-in fade-in duration-150"
    >
      <span class="font-mono text-accent font-semibold">{{ selectedIds.size }} seleccionadas</span>
      <span class="text-border-muted">•</span>
      <button
        class="hover:text-accent font-medium transition-colors inline-flex items-center gap-1.5"
        type="button"
        @click="batchMarkApplied"
      >
        <span class="material-symbols-outlined text-[15px]">done_all</span>
        Marcar como enviadas
      </button>
      <span class="text-border-muted">•</span>
      <button
        class="hover:text-rose-400 font-medium transition-colors inline-flex items-center gap-1.5"
        type="button"
        @click="batchDelete"
      >
        <span class="material-symbols-outlined text-[15px]">delete</span>
        Eliminar seleccionadas
      </button>
      <button
        class="text-outline hover:text-on-surface ml-auto p-1 rounded hover:bg-surface-container transition-colors"
        title="Deseleccionar todas"
        type="button"
        @click="clearSelection"
      >
        <span class="material-symbols-outlined text-[16px] block">close</span>
      </button>
    </div>

    <!-- APPLICATIONS TABLE -->
    <div class="w-full bg-surface-card rounded-xl border border-border-subtle overflow-hidden shadow-sm">
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse table-auto">
          <thead>
            <tr class="border-b border-border-subtle bg-surface-container/60 text-outline text-[11px] uppercase tracking-wider font-mono">
              <th class="w-10 px-3.5 py-3 text-center">
                <input
                  class="rounded bg-surface-container border border-border-muted text-accent focus:ring-0 focus:ring-offset-0 w-3.5 h-3.5 cursor-pointer"
                  :checked="isAllSelected"
                  type="checkbox"
                  @change="toggleSelectAll"
                />
              </th>
              <th class="px-4 py-3 w-[22%]">Empresa</th>
              <th class="px-4 py-3 w-[36%]">Puesto & CV</th>
              <th class="px-3 py-3 w-[11%] whitespace-nowrap">Fecha Envío</th>
              <th class="px-3 py-3 w-[13%] whitespace-nowrap">Estado</th>
              <th class="px-4 py-3 text-right w-[18%] whitespace-nowrap">Acciones</th>
            </tr>
          </thead>

          <tbody class="divide-y divide-border-subtle text-xs text-on-surface">
            <template v-for="item in paginatedItems" :key="item.id">
              <tr
                class="hover:bg-surface-container/50 transition-colors group"
                :class="{ 'bg-surface-container/20': selectedIds.has(item.id) }"
              >
                <!-- Checkbox -->
                <td class="px-3.5 py-3 text-center">
                  <input
                    class="rounded bg-surface-container border border-border-muted text-accent focus:ring-0 focus:ring-offset-0 w-3.5 h-3.5 cursor-pointer"
                    :checked="selectedIds.has(item.id)"
                    type="checkbox"
                    @change="toggleSelect(item.id)"
                  />
                </td>

                <!-- Empresa -->
                <td class="px-4 py-3">
                  <div class="flex flex-col min-w-0">
                    <span class="font-medium text-on-surface truncate" :title="formatCompanyName(item.company)">
                      {{ formatCompanyName(item.company) }}
                    </span>
                    <span class="text-[11px] font-mono text-outline">{{ getAppAts(item).label }}</span>
                  </div>
                </td>

                <!-- Puesto & CV Adaptado -->
                <td class="px-4 py-3">
                  <div class="flex flex-col min-w-0">
                    <span class="font-medium text-on-surface truncate" :title="item.role">{{ item.role }}</span>
                    <div v-if="item.cv" class="flex items-center gap-1.5 font-mono text-[11px] text-emerald-400 mt-0.5 min-w-0">
                      <span class="material-symbols-outlined text-[14px] shrink-0">picture_as_pdf</span>
                      <a
                        class="hover:underline truncate"
                        :href="'/files/' + item.cv"
                        rel="noopener noreferrer"
                        target="_blank"
                        :title="'Abrir ' + item.cv"
                      >
                        {{ item.cv.split('/').pop() }}
                      </a>
                    </div>
                    <span v-else-if="item.notes" class="text-[11px] text-on-surface-variant truncate mt-0.5" :title="item.notes">
                      {{ item.notes }}
                    </span>
                    <span v-else class="text-[11px] text-outline font-mono mt-0.5">
                      Sin CV adaptado
                    </span>
                  </div>
                </td>

                <!-- Fecha Envío -->
                <td class="px-3 py-3 font-mono text-on-surface-variant text-[11px] whitespace-nowrap">
                  {{ item.appliedAt || '—' }}
                </td>

                <!-- Estado -->
                <td class="px-3 py-3 whitespace-nowrap">
                  <span
                    :class="[
                      'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium border',
                      STATUS_STYLES[item.status]?.bg || 'bg-surface-container text-outline border-border-subtle'
                    ]"
                  >
                    <span :class="['w-1.5 h-1.5 rounded-full', STATUS_STYLES[item.status]?.dot || 'bg-outline']"></span>
                    <span>{{ STATUS_META[item.status]?.title || item.status }}</span>
                  </span>
                </td>

                <!-- Acciones -->
                <td class="px-4 py-3 text-right whitespace-nowrap">
                  <div class="inline-flex items-center justify-end gap-1.5">
                    <!-- Adaptar CV con IA (solo cuando está pendiente y aún no tiene CV) -->
                    <button
                      v-if="item.status === 'pending' && !item.cv"
                      :class="[
                        'inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium transition-all duration-200 border',
                        tailoringMap[item.id]
                          ? 'bg-accent/20 text-accent border-accent/40 cursor-wait'
                          : 'bg-accent-subtle hover:bg-accent/20 text-accent border-transparent'
                      ]"
                      :disabled="tailoringMap[item.id]"
                      title="Generar CV adaptado para esta postulación"
                      type="button"
                      @click="tailorAppCv(item)"
                    >
                      <svg
                        v-if="tailoringMap[item.id]"
                        class="animate-spin h-3 w-3 text-accent shrink-0"
                        fill="none"
                        viewBox="0 0 24 24"
                        xmlns="http://www.w3.org/2000/svg"
                      >
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" fill="currentColor"></path>
                      </svg>
                      <span v-else class="material-symbols-outlined text-[13px] leading-none text-accent">auto_fix_high</span>
                      <span>{{ tailoringMap[item.id] ? 'Adaptando...' : 'Adaptar CV' }}</span>
                    </button>

                    <!-- Usar CV base directamente sin IA (solo cuando está pendiente y aún no tiene CV) -->
                    <button
                      v-if="item.status === 'pending' && !item.cv"
                      class="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium bg-surface-container hover:bg-surface-container-high text-on-surface border border-border-subtle transition-colors"
                      title="Asignar tu CV base estándar sin modificar con IA"
                      type="button"
                      @click="assignBaseCv(item)"
                    >
                      <span class="material-symbols-outlined text-[13px] leading-none text-outline">description</span>
                      <span>CV base</span>
                    </button>

                    <!-- Abrir Formulario Playwright -->
                    <button
                      v-if="item.url"
                      :class="[
                        'inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium transition-colors border',
                        isAppOpened(item)
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : 'bg-surface-container hover:bg-surface-container-high border-border-subtle text-on-surface'
                      ]"
                      :title="isAppOpened(item) ? 'Formulario abierto previamente' : 'Abrir y pre-rellenar formulario con Playwright'"
                      type="button"
                      @click="launchItemForm(item)"
                    >
                      <span class="material-symbols-outlined text-[13px]">{{ isAppOpened(item) ? 'check' : 'open_in_new' }}</span>
                      <span>{{ isAppOpened(item) ? 'Abierto' : 'Abrir form' }}</span>
                    </button>

                    <!-- Confirmar postulación enviada -->
                    <button
                      v-if="item.status === 'pending'"
                      class="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 transition-colors"
                      title="Confirmar postulación enviada y registrar exclusión"
                      type="button"
                      @click="confirmSent(item)"
                    >
                      <span class="material-symbols-outlined text-[13px]">done_all</span>
                      <span>Marcar</span>
                    </button>

                    <!-- Cambiar estado / notas -->
                    <button
                      class="p-1 rounded text-outline hover:text-on-surface hover:bg-surface-container transition-colors"
                      title="Cambiar estado o editar notas"
                      type="button"
                      @click="openStatus(item)"
                    >
                      <span class="material-symbols-outlined text-[15px] block">flag</span>
                    </button>

                    <!-- Desplegar historial -->
                    <button
                      :class="[
                        'p-1 rounded text-outline hover:text-on-surface hover:bg-surface-container transition-colors',
                        expandedRows.has(item.id) ? 'text-accent bg-surface-container' : ''
                      ]"
                      :title="expandedRows.has(item.id) ? 'Ocultar historial' : 'Ver historial de eventos y notas'"
                      type="button"
                      @click="toggleExpandRow(item.id)"
                    >
                      <span class="material-symbols-outlined text-[16px] block transition-transform duration-150" :class="{ 'rotate-180': expandedRows.has(item.id) }">
                        expand_more
                      </span>
                    </button>

                    <!-- Eliminar -->
                    <button
                      class="p-1 rounded text-outline hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                      title="Eliminar postulación"
                      type="button"
                      @click="remove(item)"
                    >
                      <span class="material-symbols-outlined text-[15px] block">delete</span>
                    </button>
                  </div>
                </td>
              </tr>

              <!-- EXPANDED ROW (Historial de eventos y notas) -->
              <tr v-if="expandedRows.has(item.id)" class="bg-surface-container/20 border-b border-border-subtle">
                <td class="px-6 py-4" colspan="6">
                  <div class="flex flex-col gap-3">
                    <div class="flex items-center justify-between border-b border-border-subtle pb-2">
                      <span class="font-mono text-[11px] uppercase tracking-wider text-outline flex items-center gap-1.5">
                        <span class="material-symbols-outlined text-[14px]">history</span>
                        Historial de eventos y notas
                      </span>
                      <button
                        class="text-[11px] text-accent hover:underline flex items-center gap-1"
                        type="button"
                        @click="openStatus(item)"
                      >
                        <span class="material-symbols-outlined text-[13px]">edit</span>
                        Editar estado / notas
                      </button>
                    </div>

                    <!-- Motivo de rechazo -->
                    <div v-if="item.reason" class="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
                      <span class="material-symbols-outlined text-[16px] text-rose-400 shrink-0 mt-0.5">priority_high</span>
                      <div>
                        <span class="font-semibold">Motivo de rechazo:</span> {{ item.reason }}
                      </div>
                    </div>

                    <!-- Notas -->
                    <div v-if="item.notes" class="text-xs text-on-surface-variant flex items-start gap-2">
                      <span class="material-symbols-outlined text-[15px] text-outline shrink-0 mt-0.5">notes</span>
                      <span><strong class="text-on-surface">Notas:</strong> {{ item.notes }}</span>
                    </div>

                    <!-- Eventos cronológicos -->
                    <div v-if="item.history?.length" class="flex flex-col gap-1.5 pt-1">
                      <div
                        v-for="(h, idx) in item.history"
                        :key="idx"
                        class="flex items-center gap-2 text-xs text-on-surface-variant font-mono"
                      >
                        <span class="w-1.5 h-1.5 rounded-full bg-accent shrink-0"></span>
                        <span class="px-1.5 py-0.5 rounded text-[10px] bg-surface-container border border-border-subtle text-outline">
                          {{ fmtDate(h.at) }}
                        </span>
                        <span class="text-on-surface">{{ h.note }}</span>
                      </div>
                    </div>
                    <div v-else class="text-xs text-outline italic">
                      Sin eventos registrados en la bitácora todavía.
                    </div>
                  </div>
                </td>
              </tr>
            </template>

            <!-- Estado vacío -->
            <tr v-if="paginatedItems.length === 0">
              <td class="py-12 text-center text-outline" colspan="6">
                <div class="flex flex-col items-center justify-center gap-2">
                  <span class="material-symbols-outlined text-[36px] text-outline/50">inbox</span>
                  <span class="text-xs">No se encontraron postulaciones con los filtros activos</span>
                  <button
                    class="mt-2 text-xs text-accent hover:underline font-medium"
                    type="button"
                    @click="resetFilters"
                  >
                    Restablecer filtros
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- TABLE FOOTER / PAGINATION -->
      <div class="px-4 py-3 border-t border-border-subtle bg-surface-container/30 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-outline font-mono">
        <div class="flex items-center gap-1.5">
          <span>Mostrando</span>
          <span class="text-on-surface font-medium">
            {{ filteredItems.length ? (currentPage - 1) * pageSize + 1 : 0 }} - {{ Math.min(currentPage * pageSize, filteredItems.length) }}
          </span>
          <span>de</span>
          <span class="text-on-surface font-medium">{{ filteredItems.length }}</span>
          <span>postulaciones</span>
        </div>

        <div class="flex items-center gap-1.5">
          <button
            class="px-2.5 py-1 rounded-md bg-surface-container border border-border-subtle text-outline hover:text-on-surface hover:bg-surface-container-high transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            :disabled="currentPage <= 1"
            type="button"
            @click="prevPage"
          >
            Anterior
          </button>
          <span class="px-2 text-on-surface font-medium">Página {{ currentPage }} de {{ totalPages }}</span>
          <button
            class="px-2.5 py-1 rounded-md bg-surface-container border border-border-subtle text-on-surface hover:bg-surface-container-high transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            :disabled="currentPage >= totalPages"
            type="button"
            @click="nextPage"
          >
            Siguiente
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL CAMBIAR ESTADO -->
    <div
      v-if="statusDialog.show"
      class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <div class="bg-surface-card border border-border-muted w-full max-w-md rounded-xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div class="px-5 py-4 border-b border-border-subtle flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-accent text-[20px]">flag</span>
            <div class="flex flex-col leading-tight">
              <h3 class="text-sm font-semibold text-on-surface">{{ statusDialog.item?.company }}</h3>
              <span class="text-[11px] text-outline">{{ statusDialog.item?.role }}</span>
            </div>
          </div>
          <button class="text-outline hover:text-on-surface p-1 rounded-md hover:bg-surface-container transition-colors" type="button" @click="statusDialog.show = false">
            <span class="material-symbols-outlined text-[18px] block">close</span>
          </button>
        </div>

        <form class="p-5 flex flex-col gap-4 text-xs" @submit.prevent="saveStatus">
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-outline mb-1.5">Estado</label>
            <select
              v-model="statusDialog.status"
              class="w-full px-3 py-2 rounded-lg bg-surface-container border border-border-subtle text-on-surface text-xs focus:border-accent focus:outline-none cursor-pointer"
            >
              <option value="pending">Pendiente de envío</option>
              <option value="applied">Enviada</option>
              <option value="interview">Entrevista</option>
              <option value="offer">Oferta / aceptada</option>
              <option value="rejected">Rechazada</option>
              <option value="withdrawn">Retirada</option>
              <option value="not_sent">No enviada</option>
            </select>
          </div>

          <div v-if="statusDialog.status === 'rejected'">
            <label class="block text-[11px] font-mono uppercase tracking-wider text-rose-400 mb-1.5">
              Motivo del rechazo (obligatorio)
            </label>
            <textarea
              v-model="statusDialog.reason"
              class="w-full px-3 py-2 rounded-lg bg-surface-container border border-rose-500/30 text-on-surface text-xs focus:border-rose-400 focus:outline-none"
              placeholder="Ej: Requisito de residencia US no cumplido, nivel de inglés..."
              rows="2"
            ></textarea>
          </div>

          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-outline mb-1.5">Notas adicionales</label>
            <textarea
              v-model="statusDialog.notes"
              class="w-full px-3 py-2 rounded-lg bg-surface-container border border-border-subtle text-on-surface text-xs focus:border-accent focus:outline-none"
              placeholder="Detalles de entrevistas, contacto con recruiter, seguimiento..."
              rows="3"
            ></textarea>
          </div>

          <div class="pt-3 border-t border-border-subtle flex items-center justify-end gap-2">
            <button
              class="px-3 py-1.5 rounded-lg text-outline hover:text-on-surface hover:bg-surface-container transition-colors"
              type="button"
              @click="statusDialog.show = false"
            >
              Cancelar
            </button>
            <button
              class="px-4 py-1.5 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium shadow-sm transition-colors"
              type="submit"
            >
              Guardar cambios
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- MODAL NUEVA POSTULACIÓN -->
    <div
      v-if="newDialog.show"
      class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
    >
      <div class="bg-surface-card border border-border-muted w-full max-w-lg rounded-xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        <div class="px-5 py-4 border-b border-border-subtle flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-accent text-[20px]">add_circle</span>
            <h3 class="text-sm font-semibold text-on-surface">Registrar Nueva Postulación</h3>
          </div>
          <button class="text-outline hover:text-on-surface p-1 rounded-md hover:bg-surface-container transition-colors" type="button" @click="newDialog.show = false">
            <span class="material-symbols-outlined text-[18px] block">close</span>
          </button>
        </div>

        <form class="p-5 flex flex-col gap-4 text-xs" @submit.prevent="register">
          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-outline mb-1.5">Empresa *</label>
            <input
              v-model="newDialog.form.company"
              class="w-full px-3 py-2 rounded-lg bg-surface-container border border-border-subtle text-on-surface text-xs focus:border-accent focus:outline-none"
              placeholder="Ej: MercadoLibre, Automattic, GitLab..."
              required
              type="text"
            />
          </div>

          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-outline mb-1.5">Puesto *</label>
            <input
              v-model="newDialog.form.role"
              class="w-full px-3 py-2 rounded-lg bg-surface-container border border-border-subtle text-on-surface text-xs focus:border-accent focus:outline-none"
              placeholder="Ej: QA Automation Engineer"
              required
              type="text"
            />
          </div>

          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-outline mb-1.5">Enlace de la vacante / formulario</label>
            <input
              v-model="newDialog.form.url"
              class="w-full px-3 py-2 rounded-lg bg-surface-container border border-border-subtle text-on-surface text-xs focus:border-accent focus:outline-none"
              placeholder="https://boards.greenhouse.io/..."
              type="url"
            />
          </div>

          <div>
            <label class="block text-[11px] font-mono uppercase tracking-wider text-outline mb-1.5">CV a adjuntar</label>
            <select
              v-model="newDialog.form.cv"
              class="w-full px-3 py-2 rounded-lg bg-surface-container border border-border-subtle text-on-surface text-xs focus:border-accent focus:outline-none cursor-pointer"
            >
              <option value="">Ninguno / Por defecto</option>
              <option v-for="cv in cvItems" :key="cv" :value="cv">{{ cv }}</option>
            </select>
          </div>

          <div class="p-3 rounded-lg bg-surface-container/60 border border-border-subtle flex items-start gap-2.5">
            <span class="material-symbols-outlined text-accent text-[17px] shrink-0 mt-0.5">info</span>
            <span class="text-[11px] text-on-surface-variant leading-relaxed">
              Puedes abrir el navegador de Playwright para que complete el formulario automáticamente, o registrar la postulación directamente en tu lista.
            </span>
          </div>

          <div class="pt-3 border-t border-border-subtle flex items-center justify-between gap-2">
            <button
              class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors"
              :class="[
                newFormOpened
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : 'bg-surface-container hover:bg-surface-container-high border-border-subtle text-on-surface'
              ]"
              :disabled="!newDialog.form.url"
              type="button"
              @click="launchForm"
            >
              <span class="material-symbols-outlined text-[15px]">{{ newFormOpened ? 'check' : 'open_in_browser' }}</span>
              <span>{{ newFormOpened ? 'Formulario abierto' : 'Abrir formulario' }}</span>
            </button>

            <div class="flex items-center gap-2">
              <button
                class="px-3 py-1.5 rounded-lg text-outline hover:text-on-surface hover:bg-surface-container transition-colors"
                type="button"
                @click="newDialog.show = false"
              >
                Cancelar
              </button>
              <button
                class="px-4 py-1.5 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium shadow-sm transition-colors"
                type="submit"
              >
                Guardar postulación
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>

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
