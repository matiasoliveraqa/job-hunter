<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api.js'
import { t } from '../i18n/index.js'
import CvsKpis from '../components/cvs/CvsKpis.vue'
import CvsSidebarList from '../components/cvs/CvsSidebarList.vue'
import CvViewerPane from '../components/cvs/CvViewerPane.vue'

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
    } else if (f.dir === 'my_cv' || fileName.toLowerCase().includes('_cv') || fileName.toLowerCase().includes('resume')) {
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
  } else if (appUrl.includes('bamboohr.com') || appUrl.includes('bamboohr.co.uk')) {
    platform = 'BambooHR'
  } else if (f.dir === 'my_cv' || fileName.toLowerCase().includes('_cv') || fileName.toLowerCase().includes('resume')) {
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

      <!-- Quick action buttons -->
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

    <!-- METRICS / KPIS ROW -->
    <CvsKpis
      :stats="stats"
      :total-sparkline="totalSparkline"
      :tailored-sparkline="tailoredSparkline"
      :active-sparkline="activeSparkline"
    />

    <!-- MASTER-DETAIL MAIN SECTION: SPLIT PANE -->
    <section class="grid grid-cols-1 xl:grid-cols-12 gap-5 items-start">
      <!-- LEFT COLUMN: CV LIST -->
      <CvsSidebarList
        v-model:search="search"
        v-model:selected-platform="selectedPlatform"
        :stats="stats"
        :filtered-files="filteredFiles"
        :selected-cv="selectedCv"
        :loading="loading"
        @select-item="selectItem"
        @download-pdf="downloadPdf"
        @copy-path="copyPath"
      />

      <!-- RIGHT COLUMN: HIGH-FIDELITY PDF VIEWER CANVAS -->
      <CvViewerPane
        :selected-cv="selectedCv"
        @open-associated-vacancy="openAssociatedVacancy"
        @go-to-applications="goToApplications"
        @copy-path="copyPath"
        @download-pdf="downloadPdf"
        @open-in-new-tab="openInNewTab"
      />
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
