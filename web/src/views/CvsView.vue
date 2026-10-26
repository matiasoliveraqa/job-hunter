<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api.js'
import { t } from '../i18n/index.js'

const router = useRouter()

const rawFiles = ref([])
const rawApplications = ref([])
const candidateName = ref('')
const loading = ref(true)
const search = ref('')
const selectedPlatform = ref('all')
const selectedCv = ref(null)
const openingFolder = ref(false)

const snack = reactive({ show: false, text: '', color: 'success' })

function showSnack(text, color = 'success') {
  snack.text = text
  snack.color = color
  snack.show = true
  setTimeout(() => {
    snack.show = false
  }, 4000)
}

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 KB'
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  return `${(kb / 1024).toFixed(2)} MB`
}

function formatDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diffHours = (now - d) / (1000 * 60 * 60)
  if (diffHours < 24 && d.getDate() === now.getDate()) {
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  if (diffHours < 48) {
    return t('common.yesterday')
  }
  return d.toLocaleDateString([], { day: 'numeric', month: 'short' })
}

function formatFullDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleString()
}

function enrichFile(f, applications = []) {
  const parts = String(f.name).split('/')
  const fileName = parts[parts.length - 1]
  const folder = parts.length > 1 ? parts[0] : ''

  const matchedApp =
    applications.find((a) => {
      if (a.cv && (a.cv.endsWith(f.name) || `${f.dir}/${f.name}`.endsWith(a.cv) || a.cv.endsWith(fileName))) {
        return true
      }
      if (folder && a.notes && a.notes.includes(folder)) {
        return true
      }
      return false
    }) || null

  let company = matchedApp?.company || ''
  let role = matchedApp?.role || ''

  if (!company) {
    if (folder) {
      const folderClean = folder.replace(/^\d{4}-\d{2}_/, '')
      const folderParts = folderClean.split('_')
      company = folderParts[0] || ''
    } else {
      const fnMatch = fileName.match(
        /Matias_Olivera_(?:QA_Automation_Engineer|QA_Engineer|QA_Specialist|SDET)_([A-Za-z0-9_-]+)\.pdf/i,
      )
      if (fnMatch) {
        company = fnMatch[1].replace(/_/g, ' ')
      }
    }
  }

  if (!role) {
    if (fileName.toLowerCase().includes('automation')) {
      role = 'QA Automation Engineer'
    } else if (fileName.toLowerCase().includes('sdet')) {
      role = 'SDET'
    } else if (f.dir === 'my_cv' || fileName.includes('Matias_Olivera_QA_CV')) {
      role = 'QA Automation / SDET'
    } else {
      role = 'QA Engineer'
    }
  }

  let platform = 'Directo'
  const appUrl = (matchedApp?.url || '').toLowerCase()
  if (appUrl.includes('greenhouse.io')) {
    platform = 'Greenhouse'
  } else if (appUrl.includes('lever.co')) {
    platform = 'Lever'
  } else if (appUrl.includes('ashbyhq.com')) {
    platform = 'Ashby'
  } else if (appUrl.includes('workable.com')) {
    platform = 'Workable'
  } else if (appUrl.includes('breezy.hr')) {
    platform = 'Breezy'
  } else if (appUrl.includes('recruitee.com')) {
    platform = 'Recruitee'
  } else if (appUrl.includes('bamboohr.com')) {
    platform = 'BambooHR'
  } else if (f.dir === 'my_cv' || fileName.includes('Matias_Olivera_QA_CV')) {
    platform = 'Base'
  } else if (folder.toLowerCase().includes('greenhouse')) {
    platform = 'Greenhouse'
  } else if (folder.toLowerCase().includes('lever')) {
    platform = 'Lever'
  } else if (folder.toLowerCase().includes('ashby')) {
    platform = 'Ashby'
  } else if (folder.toLowerCase().includes('workable')) {
    platform = 'Workable'
  } else if (folder.toLowerCase().includes('breezy')) {
    platform = 'Breezy'
  } else if (folder.toLowerCase().includes('recruitee')) {
    platform = 'Recruitee'
  } else if (folder.toLowerCase().includes('bamboohr')) {
    platform = 'BambooHR'
  }

  const isBase = platform === 'Base' || f.dir === 'my_cv'
  const isActiveApp = Boolean(
    matchedApp && ['pending', 'applied', 'interview', 'offer'].includes(matchedApp.status),
  )

  const encodedPath = String(f.name)
    .split('/')
    .map((p) => encodeURIComponent(p))
    .join('/')
  const downloadUrl = `/files/${encodeURIComponent(f.dir)}/${encodedPath}`

  return {
    ...f,
    key: `${f.dir}/${f.name}`,
    fileName,
    folder,
    company: company || (isBase ? candidateName.value || t('cvs.detail.baseCv') : 'General'),
    role,
    platform,
    isBase,
    application: matchedApp,
    applicationId: matchedApp?.id || null,
    applicationStatus: matchedApp?.status || null,
    applicationUrl: matchedApp?.url || null,
    isActiveApp,
    downloadUrl,
    formattedSize: formatBytes(f.size),
    formattedDate: formatDate(f.modifiedAt),
    fullDate: formatFullDate(f.modifiedAt),
  }
}

const enrichedFiles = computed(() => {
  return rawFiles.value.map((f) => enrichFile(f, rawApplications.value))
})

const stats = computed(() => {
  const total = enrichedFiles.value.length
  if (total === 0) {
    return {
      total: 0,
      recentWeek: 0,
      tailored: 0,
      tailoredRatio: '0.0',
      activeCount: 0,
      activeRatio: '0.0',
      totalMb: '0.0',
      avgKb: 0,
      greenhouse: 0,
      lever: 0,
      ashby: 0,
      workable: 0,
      breezy: 0,
      recruitee: 0,
      bamboohr: 0,
      base: 0,
    }
  }

  const now = Date.now()
  const weekMs = 7 * 24 * 60 * 60 * 1000
  let recentWeek = 0
  let tailored = 0
  let activeCount = 0
  let totalBytes = 0
  let greenhouse = 0
  let lever = 0
  let ashby = 0
  let workable = 0
  let breezy = 0
  let recruitee = 0
  let bamboohr = 0
  let base = 0

  for (const item of enrichedFiles.value) {
    totalBytes += item.size || 0
    if (item.modifiedAt && now - new Date(item.modifiedAt).getTime() <= weekMs) {
      recentWeek++
    }
    if (!item.isBase) {
      tailored++
    }
    if (item.isActiveApp) {
      activeCount++
    }
    if (item.platform === 'Greenhouse') greenhouse++
    else if (item.platform === 'Lever') lever++
    else if (item.platform === 'Ashby') ashby++
    else if (item.platform === 'Workable') workable++
    else if (item.platform === 'Breezy') breezy++
    else if (item.platform === 'Recruitee') recruitee++
    else if (item.platform === 'BambooHR') bamboohr++
    else if (item.platform === 'Base') base++
  }

  const tailoredRatio = ((tailored / total) * 100).toFixed(1)
  const activeRatio = ((activeCount / total) * 100).toFixed(1)
  const totalMb = (totalBytes / (1024 * 1024)).toFixed(1)
  const avgKb = Math.round(totalBytes / 1024 / total)

  return {
    total,
    recentWeek,
    tailored,
    tailoredRatio,
    activeCount,
    activeRatio,
    totalMb,
    avgKb,
    greenhouse,
    lever,
    ashby,
    workable,
    breezy,
    recruitee,
    bamboohr,
    base,
  }
})

function generateSparkline(filterFn) {
  const days = 14
  const countsByDay = new Array(days).fill(0)
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate() - (days - 1))

  for (const item of enrichedFiles.value) {
    if (filterFn && !filterFn(item)) continue
    if (!item.modifiedAt) continue
    const d = new Date(item.modifiedAt)
    if (isNaN(d.getTime())) continue
    const diffDays = Math.floor((d.getTime() - start.getTime()) / (24 * 60 * 60 * 1000))
    if (diffDays >= 0 && diffDays < days) {
      countsByDay[diffDays]++
    }
  }

  const maxVal = Math.max(...countsByDay, 1)
  const coords = countsByDay.map((cnt, idx) => {
    const x = Math.round((idx / (days - 1)) * 100)
    const y = Math.round(24 - (cnt / maxVal) * 20)
    return `${x} ${y}`
  })

  const linePath = coords.map((c, idx) => (idx === 0 ? `M${c}` : `L${c}`)).join(' ')
  const areaPath = `${linePath} L100 28 L0 28 Z`
  return { linePath, areaPath }
}

const totalSparkline = computed(() => generateSparkline())
const tailoredSparkline = computed(() => generateSparkline((item) => !item.isBase))
const activeSparkline = computed(() => generateSparkline((item) => item.isActiveApp))

const filteredFiles = computed(() => {
  const q = search.value.toLowerCase().trim()
  const plat = selectedPlatform.value

  return enrichedFiles.value.filter((item) => {
    if (plat !== 'all' && item.platform !== plat) {
      return false
    }
    if (!q) return true
    const haystack = `${item.company} ${item.role} ${item.fileName} ${item.platform} ${item.formattedDate}`.toLowerCase()
    return haystack.includes(q)
  })
})

async function loadData() {
  loading.value = true
  try {
    const [filesRes, appsRes, profileRes] = await Promise.all([
      api.listFiles().catch(() => []),
      api.listApplications().catch(() => []),
      api.getProfile().catch(() => null),
    ])
    rawFiles.value = filesRes
    rawApplications.value = appsRes
    candidateName.value = profileRes?.personal_info?.full_name || ''

    if (!selectedCv.value && enrichedFiles.value.length > 0) {
      selectedCv.value = enrichedFiles.value[0]
    } else if (selectedCv.value) {
      const match = enrichedFiles.value.find((f) => f.key === selectedCv.value.key)
      selectedCv.value = match || enrichedFiles.value[0] || null
    }
  } catch (err) {
    showSnack(`${t('cvs.toasts.loadError')}${err.message}`, 'error')
  } finally {
    loading.value = false
  }
}

function selectItem(item) {
  selectedCv.value = item
}

async function openLocalFolder() {
  openingFolder.value = true
  try {
    const res = await api.openFolder('applications')
    if (res?.path && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(res.path).catch(() => {})
    }
    showSnack(t('cvs.toasts.folderOpened', { path: res?.path || 'output/applications' }), 'success')
  } catch (err) {
    showSnack(`${t('cvs.toasts.folderError')}${err.message}`, 'error')
  } finally {
    openingFolder.value = false
  }
}

async function copyPath(item) {
  if (!item) return
  const fullPath = `/home/kraper/Documents/job-hunter/${item.dir}/${item.name}`
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(fullPath)
      showSnack(t('cvs.toasts.pathCopied', { file: item.fileName }), 'success')
    }
  } catch {
    showSnack(t('cvs.toasts.pathInfo', { path: fullPath }), 'info')
  }
}

function downloadPdf(item) {
  if (!item?.downloadUrl) return
  const a = document.createElement('a')
  a.href = item.downloadUrl
  a.download = item.fileName || 'cv.pdf'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

function openAssociatedVacancy(item) {
  if (!item?.applicationUrl) return
  window.open(item.applicationUrl, '_blank', 'noopener,noreferrer')
}

function goToApplications(item) {
  if (!item?.applicationId) return
  router.push('/applications')
}

function openInNewTab(item) {
  if (!item?.downloadUrl) return
  window.open(item.downloadUrl, '_blank', 'noopener,noreferrer')
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="p-6 flex flex-col gap-6 max-w-[1680px] w-full mx-auto font-sans">
    <!-- SUBHEADER / VIEW CONTROLS -->
    <section class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-border-subtle">
      <div class="flex flex-col gap-1">
        <div class="flex items-center gap-3">
          <h1 class="text-2xl font-semibold text-on-surface tracking-tight">{{ $t('cvs.title') }}</h1>
          <div class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-surface-container-high text-accent font-mono text-xs border border-border-subtle">
            <span class="w-1.5 h-1.5 rounded-full bg-accent animate-pulse"></span>
            <span>{{ $t('cvs.documentsCount', { count: stats.total }) }}</span>
          </div>
        </div>
        <p class="text-xs text-on-surface-variant max-w-2xl">
          {{ $t('cvs.subtitle') }}
        </p>
      </div>

      <!-- Quick action buttons (cross-platform open folder, refresh) -->
      <div class="flex items-center gap-2 self-start sm:self-auto flex-wrap">
        <button
          class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface text-xs font-medium border border-border-subtle transition-colors shadow-sm active:scale-[0.98]"
          :disabled="openingFolder"
          :title="$t('cvs.openFolderTip')"
          type="button"
          @click="openLocalFolder"
        >
          <span :class="['material-symbols-outlined text-[16px] text-outline', openingFolder ? 'animate-spin text-accent' : '']">
            {{ openingFolder ? 'sync' : 'folder_open' }}
          </span>
          <span>{{ $t('cvs.openLocalFolder') }}</span>
        </button>

        <button
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface text-xs font-medium border border-border-subtle transition-colors shadow-sm active:scale-[0.98]"
          :title="$t('cvs.refreshTip')"
          type="button"
          @click="loadData"
        >
          <span class="material-symbols-outlined text-[16px] text-outline">refresh</span>
          <span>{{ $t('cvs.refresh') }}</span>
        </button>
      </div>
    </section>

    <!-- METRICS / KPIS ROW (OBSIDIAN PRECISION) -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- KPI 1: TOTAL CVS GENERADOS -->
      <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-mono uppercase tracking-wider text-outline">{{ $t('cvs.kpi.totalGenerated') }}</span>
          <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-container-high text-accent font-mono text-[11px]">
            {{ $t('cvs.kpi.thisWeek', { count: stats.recentWeek }) }}
          </span>
        </div>
        <div class="flex items-baseline justify-between mt-3 mb-1">
          <span class="text-2xl font-semibold text-on-surface tracking-tight">{{ stats.total }}</span>
          <span class="font-mono text-xs text-outline">output/applications/*</span>
        </div>
        <div class="h-7 w-full mt-1">
          <svg class="w-full h-full text-accent overflow-visible" fill="none" preserveAspectRatio="none" viewBox="0 0 100 28">
            <path :d="totalSparkline.linePath" stroke="currentColor" stroke-linecap="round" stroke-width="1.75" />
            <path :d="totalSparkline.areaPath" fill="currentColor" fill-opacity="0.08" />
          </svg>
        </div>
      </div>

      <!-- KPI 2: ADAPTACIONES ATS -->
      <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-mono uppercase tracking-wider text-outline">{{ $t('cvs.kpi.atsTailored') }}</span>
          <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-container-high text-sky-400 font-mono text-[11px]">
            {{ $t('cvs.kpi.atsPlatforms') }}
          </span>
        </div>
        <div class="flex items-baseline justify-between mt-3 mb-1">
          <span class="text-2xl font-semibold text-on-surface tracking-tight">
            {{ stats.tailored }} <span class="text-xs text-outline font-normal">/ {{ stats.total }}</span>
          </span>
          <span class="font-mono text-xs text-sky-400">{{ $t('cvs.kpi.tailoredRatio', { ratio: stats.tailoredRatio }) }}</span>
        </div>
        <div class="h-7 w-full mt-1">
          <svg class="w-full h-full text-sky-400 overflow-visible" fill="none" preserveAspectRatio="none" viewBox="0 0 100 28">
            <path :d="tailoredSparkline.linePath" stroke="currentColor" stroke-linecap="round" stroke-width="1.75" />
            <path :d="tailoredSparkline.areaPath" fill="currentColor" fill-opacity="0.08" />
          </svg>
        </div>
      </div>

      <!-- KPI 3: POSTULACIONES ACTIVAS -->
      <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-mono uppercase tracking-wider text-outline">{{ $t('cvs.kpi.activeApps') }}</span>
          <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-container-high text-amber-400 font-mono text-[11px]">
            {{ $t('cvs.kpi.inTracking') }}
          </span>
        </div>
        <div class="flex items-baseline justify-between mt-3 mb-1">
          <span class="text-2xl font-semibold text-amber-400 tracking-tight">{{ stats.activeCount }}</span>
          <span class="font-mono text-xs text-outline">{{ $t('cvs.kpi.inProcessRatio', { ratio: stats.activeRatio }) }}</span>
        </div>
        <div class="h-7 w-full mt-1">
          <svg class="w-full h-full text-amber-400 overflow-visible" fill="none" preserveAspectRatio="none" viewBox="0 0 100 28">
            <path :d="activeSparkline.linePath" stroke="currentColor" stroke-linecap="round" stroke-width="1.75" />
            <path :d="activeSparkline.areaPath" fill="currentColor" fill-opacity="0.08" />
          </svg>
        </div>
      </div>

      <!-- KPI 4: ALMACENAMIENTO LOCAL -->
      <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-mono uppercase tracking-wider text-outline">{{ $t('cvs.kpi.localStorage') }}</span>
          <span class="inline-flex items-center gap-1.5 text-emerald-400 font-mono text-[11px]">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            {{ $t('cvs.kpi.synced') }}
          </span>
        </div>
        <div class="flex items-baseline justify-between mt-3 mb-1">
          <span class="text-2xl font-semibold text-on-surface tracking-tight">
            {{ stats.totalMb }} <span class="text-xs text-outline font-normal">MB</span>
          </span>
          <span class="font-mono text-xs text-outline">{{ $t('cvs.kpi.avgPerPdf', { avg: stats.avgKb }) }}</span>
        </div>
        <div class="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden mt-3">
          <div class="bg-accent h-full rounded-full transition-all" style="width: 28%;"></div>
        </div>
      </div>
    </section>

    <!-- MASTER-DETAIL MAIN SECTION: SPLIT PANE -->
    <section class="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
      <!-- LEFT COLUMN: CV LIST (xl:col-span-5 2xl:col-span-4) -->
      <div class="xl:col-span-5 2xl:col-span-4 flex flex-col gap-3 bg-surface-card border border-border-subtle p-3.5 rounded-xl">
        <!-- Search and filter box -->
        <div class="flex flex-col gap-2">
          <div class="relative flex items-center">
            <span class="material-symbols-outlined absolute left-3 text-[17px] text-outline">search</span>
            <input
              v-model="search"
              class="w-full pl-9 pr-8 py-1.5 rounded-lg bg-surface-container text-on-surface text-xs placeholder:text-outline border border-border-subtle focus:outline-none focus:border-accent transition-colors"
              :placeholder="$t('cvs.list.searchPlaceholder')"
              type="text"
            />
            <button
              v-if="search"
              class="absolute right-2 text-outline hover:text-on-surface text-xs"
              type="button"
              @click="search = ''"
            >
              ✕
            </button>
          </div>

          <!-- Filter Tabs / Pills -->
          <div class="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
            <button
              class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
              :class="[
                selectedPlatform === 'all'
                  ? 'bg-surface-container-high text-on-surface border border-border-muted font-semibold'
                  : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
              ]"
              type="button"
              @click="selectedPlatform = 'all'"
            >
              {{ $t('common.all') }} ({{ stats.total }})
            </button>

            <button
              class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
              :class="[
                selectedPlatform === 'Greenhouse'
                  ? 'bg-surface-container-high text-sky-400 border border-sky-500/30 font-semibold'
                  : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
              ]"
              type="button"
              @click="selectedPlatform = 'Greenhouse'"
            >
              Greenhouse ({{ stats.greenhouse }})
            </button>

            <button
              class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
              :class="[
                selectedPlatform === 'Lever'
                  ? 'bg-surface-container-high text-amber-400 border border-amber-500/30 font-semibold'
                  : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
              ]"
              type="button"
              @click="selectedPlatform = 'Lever'"
            >
              Lever ({{ stats.lever }})
            </button>

            <button
              class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
              :class="[
                selectedPlatform === 'Ashby'
                  ? 'bg-surface-container-high text-emerald-400 border border-emerald-500/30 font-semibold'
                  : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
              ]"
              type="button"
              @click="selectedPlatform = 'Ashby'"
            >
              Ashby ({{ stats.ashby }})
            </button>

            <button
              class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
              :class="[
                selectedPlatform === 'Workable'
                  ? 'bg-surface-container-high text-blue-400 border border-blue-500/30 font-semibold'
                  : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
              ]"
              type="button"
              @click="selectedPlatform = 'Workable'"
            >
              Workable ({{ stats.workable }})
            </button>

            <button
              class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
              :class="[
                selectedPlatform === 'Breezy'
                  ? 'bg-surface-container-high text-teal-400 border border-teal-500/30 font-semibold'
                  : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
              ]"
              type="button"
              @click="selectedPlatform = 'Breezy'"
            >
              Breezy ({{ stats.breezy }})
            </button>

            <button
              class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
              :class="[
                selectedPlatform === 'Recruitee'
                  ? 'bg-surface-container-high text-rose-400 border border-rose-500/30 font-semibold'
                  : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
              ]"
              type="button"
              @click="selectedPlatform = 'Recruitee'"
            >
              Recruitee ({{ stats.recruitee }})
            </button>

            <button
              class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
              :class="[
                selectedPlatform === 'BambooHR'
                  ? 'bg-surface-container-high text-lime-400 border border-lime-500/30 font-semibold'
                  : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
              ]"
              type="button"
              @click="selectedPlatform = 'BambooHR'"
            >
              BambooHR ({{ stats.bamboohr }})
            </button>

            <button
              class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
              :class="[
                selectedPlatform === 'Base'
                  ? 'bg-surface-container-high text-primary border border-primary/30 font-semibold'
                  : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
              ]"
              type="button"
              @click="selectedPlatform = 'Base'"
            >
              Base ({{ stats.base }})
            </button>
          </div>
        </div>

        <!-- Scrollable List of CV Cards -->
        <div class="flex flex-col gap-1.5 max-h-[calc(100vh-340px)] min-h-[520px] overflow-y-auto pr-1">
          <div
            v-if="!filteredFiles.length && !loading"
            class="p-6 text-center text-xs text-outline font-mono bg-surface-container/30 rounded-lg border border-border-subtle"
          >
            {{ $t('cvs.list.emptySearch') }}
          </div>

          <div
            v-for="item in filteredFiles"
            :key="item.key"
            class="p-3 rounded-lg border transition-all flex items-start gap-3 relative group cursor-pointer"
            :class="[
              selectedCv && selectedCv.key === item.key
                ? 'bg-surface-container-high border-accent shadow-sm'
                : 'bg-surface-container/50 border-border-subtle hover:bg-surface-container hover:border-border-muted'
            ]"
            @click="selectItem(item)"
          >
            <!-- PDF Icon Box -->
            <div
              class="w-7 h-8 rounded flex flex-col items-center justify-center shrink-0 transition-colors"
              :class="[
                selectedCv && selectedCv.key === item.key
                  ? 'bg-accent/20 text-accent'
                  : 'bg-surface-container-highest text-outline group-hover:text-on-surface'
              ]"
            >
              <span class="material-symbols-outlined text-[17px]">picture_as_pdf</span>
            </div>

            <!-- Card Content -->
            <div class="flex flex-col min-w-0 flex-1">
              <div class="flex items-center justify-between gap-2">
                <span
                  class="text-xs font-medium truncate"
                  :class="[selectedCv && selectedCv.key === item.key ? 'text-accent font-semibold' : 'text-on-surface']"
                >
                  {{ item.company }} · {{ item.role }}
                </span>
                <span class="font-mono text-[11px] text-outline shrink-0">{{ item.formattedDate }}</span>
              </div>

              <p class="font-mono text-[11px] text-on-surface-variant truncate mt-0.5">
                {{ item.fileName }}
              </p>

              <div class="flex items-center gap-2 mt-2 font-mono text-[11px] text-outline flex-wrap">
                <span
                  class="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-sans"
                  :class="[
                    item.platform === 'Greenhouse'
                      ? 'bg-sky-500/10 text-sky-400'
                      : item.platform === 'Lever'
                        ? 'bg-amber-500/10 text-amber-400'
                        : item.platform === 'Ashby'
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : item.platform === 'Workable'
                            ? 'bg-blue-500/10 text-blue-400'
                            : item.platform === 'Breezy'
                              ? 'bg-teal-500/10 text-teal-400'
                              : item.platform === 'Recruitee'
                                ? 'bg-rose-500/10 text-rose-400'
                                : item.platform === 'BambooHR'
                                  ? 'bg-lime-500/10 text-lime-400'
                                  : 'bg-surface-container-highest text-on-surface-variant'
                  ]"
                >
                  {{ item.company }} • {{ item.platform }}
                </span>
                <span>•</span>
                <span>{{ item.formattedSize }}</span>

                <span
                  v-if="item.applicationStatus"
                  class="ml-auto inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-sans uppercase"
                  :class="[
                    item.applicationStatus === 'applied'
                      ? 'bg-sky-500/10 text-sky-400'
                      : item.applicationStatus === 'interview'
                        ? 'bg-amber-500/15 text-amber-300'
                        : item.applicationStatus === 'offer'
                          ? 'bg-emerald-500/15 text-emerald-400'
                          : item.applicationStatus === 'pending'
                            ? 'bg-amber-500/10 text-amber-400'
                            : 'bg-surface-container text-outline'
                  ]"
                >
                  {{ $t('status.' + item.applicationStatus) }}
                </span>
              </div>
            </div>

            <!-- Quick actions on hover -->
            <div class="absolute right-2 bottom-2 hidden group-hover:flex items-center gap-1 bg-surface-container-highest px-1.5 py-0.5 rounded shadow">
              <button
                class="p-1 hover:text-accent transition-colors text-outline"
                :title="$t('cvs.detail.downloadPdf')"
                type="button"
                @click.stop="downloadPdf(item)"
              >
                <span class="material-symbols-outlined text-[15px]">download</span>
              </button>
              <button
                class="p-1 hover:text-accent transition-colors text-outline"
                :title="$t('cvs.detail.copyLocalPath')"
                type="button"
                @click.stop="copyPath(item)"
              >
                <span class="material-symbols-outlined text-[15px]">content_copy</span>
              </button>
            </div>
          </div>
        </div>

        <!-- List Footer Counter -->
        <div class="pt-2 flex items-center justify-between font-mono text-[11px] text-outline border-t border-border-subtle">
          <span>{{ $t('cvs.list.fileCount', { shown: filteredFiles.length, total: stats.total }) }}</span>
          <span v-if="selectedPlatform !== 'all'" class="text-accent">{{ $t('cvs.list.activeFilter', { filter: selectedPlatform }) }}</span>
        </div>
      </div>

      <!-- RIGHT COLUMN: HIGH-FIDELITY PDF VIEWER CANVAS (xl:col-span-7 2xl:col-span-8) -->
      <div class="xl:col-span-7 2xl:col-span-8 flex flex-col rounded-xl overflow-hidden bg-surface-card border border-border-subtle shadow-lg">
        <!-- VIEWER TOP TOOLBAR -->
        <div class="h-14 px-4 bg-surface-container border-b border-border-subtle flex items-center justify-between gap-3 select-none flex-wrap">
          <!-- Left: Title & ATS Badge -->
          <div class="flex items-center gap-2.5 min-w-0">
            <span class="material-symbols-outlined text-[18px] text-accent">description</span>
            <div class="flex flex-col min-w-0">
              <span class="text-xs font-semibold text-on-surface truncate max-w-xs md:max-w-md">
                {{ selectedCv?.company }} · {{ selectedCv?.role }}
              </span>
              <span class="font-mono text-[10px] text-outline truncate">
                {{ selectedCv?.fileName || $t('cvs.detail.noFileSelected') }}
              </span>
            </div>
            <span
              class="hidden sm:inline-flex items-center px-2 py-0.5 rounded font-mono text-[10px] ml-1"
              :class="[
                selectedCv?.isBase
                  ? 'bg-surface-container-highest text-on-surface-variant'
                  : 'bg-accent/15 text-accent border border-accent/20'
              ]"
            >
              {{ selectedCv?.isBase ? $t('cvs.detail.baseCv') : `${selectedCv?.platform} ATS-Ready` }}
            </span>
          </div>

          <!-- Right: Actions -->
          <div class="flex items-center gap-1.5 flex-wrap">
            <!-- BOTÓN: VER VACANTE ASOCIADA -->
            <button
              v-if="selectedCv?.applicationUrl"
              class="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/30 text-xs font-medium transition-colors shadow-sm"
              :title="$t('cvs.detail.openVacancyTip')"
              type="button"
              @click="openAssociatedVacancy(selectedCv)"
            >
              <span class="material-symbols-outlined text-[15px]">open_in_new</span>
              <span>{{ $t('cvs.detail.openVacancy') }}</span>
            </button>

            <!-- BOTÓN: VER EN POSTULACIONES -->
            <button
              v-if="selectedCv?.applicationId"
              class="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-xs font-medium border border-border-subtle transition-colors"
              :title="$t('cvs.detail.goToAppTip')"
              type="button"
              @click="goToApplications(selectedCv)"
            >
              <span class="material-symbols-outlined text-[15px] text-accent">send</span>
              <span>{{ $t('cvs.detail.goToApp') }}</span>
            </button>

            <!-- Quick icon actions -->
            <button
              class="p-1.5 rounded hover:bg-surface-container-high text-outline hover:text-on-surface transition-colors"
              :title="$t('cvs.detail.copyPathTip')"
              type="button"
              @click="copyPath(selectedCv)"
            >
              <span class="material-symbols-outlined text-[17px]">content_copy</span>
            </button>

            <button
              class="p-1.5 rounded hover:bg-surface-container-high text-outline hover:text-on-surface transition-colors"
              :title="$t('cvs.detail.downloadTip')"
              type="button"
              @click="downloadPdf(selectedCv)"
            >
              <span class="material-symbols-outlined text-[17px]">download</span>
            </button>

            <button
              class="p-1.5 rounded hover:bg-surface-container-high text-outline hover:text-on-surface transition-colors"
              :title="$t('cvs.detail.openNewTabTip')"
              type="button"
              @click="openInNewTab(selectedCv)"
            >
              <span class="material-symbols-outlined text-[17px]">open_in_browser</span>
            </button>
          </div>
        </div>

        <!-- VIEWER DESK / REAL PDF CANVAS -->
        <div class="p-2 sm:p-4 bg-surface-dim/95 flex justify-center items-center viewer-desk">
          <iframe
            v-if="selectedCv?.downloadUrl"
            :key="selectedCv.downloadUrl"
            class="viewer-frame rounded-md border border-border-subtle shadow-2xl"
            :src="selectedCv.downloadUrl"
            :title="$t('cvs.detail.previewFrameTitle')"
          />
          <div
            v-else
            class="flex flex-col items-center justify-center p-12 text-center text-outline gap-2"
          >
            <span class="material-symbols-outlined text-4xl text-outline">description</span>
            <span class="text-xs font-mono">{{ $t('cvs.detail.selectCvPrompt') }}</span>
          </div>
        </div>

        <!-- VIEWER BOTTOM METADATA BAR -->
        <div class="h-10 px-4 bg-surface-container border-t border-border-subtle flex items-center justify-between text-outline font-mono text-[11px] flex-wrap gap-2">
          <div class="flex items-center gap-2.5">
            <span>{{ $t('cvs.detail.fileLabel') }} <code class="text-on-surface-variant">{{ selectedCv?.fileName }}</code></span>
            <span>•</span>
            <span>{{ $t('cvs.detail.sizeLabel') }} <span class="text-on-surface">{{ selectedCv?.formattedSize }}</span></span>
            <span class="hidden md:inline">•</span>
            <span class="hidden md:inline">{{ $t('cvs.detail.modifiedLabel') }} <span class="text-on-surface">{{ selectedCv?.fullDate }}</span></span>
          </div>

          <div class="flex items-center gap-2.5">
            <span
              v-if="selectedCv?.applicationStatus"
              class="inline-flex items-center gap-1 text-sky-400"
            >
              <span class="material-symbols-outlined text-[13px]">verified</span>
              {{ $t('cvs.detail.applicationStatus', { status: $t('status.' + selectedCv.applicationStatus) }) }}
            </span>
            <span v-else class="text-outline">
              {{ selectedCv?.isBase ? $t('cvs.detail.baseTemplate') : $t('cvs.detail.localTailored') }}
            </span>
          </div>
        </div>
      </div>
    </section>

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

<style scoped>
.viewer-desk {
  min-height: 640px;
}
.viewer-frame {
  width: 100%;
  height: calc(100vh - 360px);
  min-height: 620px;
  background-color: #1e1e20;
}
</style>
