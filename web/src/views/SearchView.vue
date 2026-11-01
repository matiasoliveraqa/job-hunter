<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { api } from '../api.js'
import {
  scanning,
  progress,
  matches,
  errorCount,
  logs,
  form,
  progressPercent,
  initScanSync,
} from '../scanController.js'
import { t } from '../i18n/index.js'
import SearchKpis from '../components/search/SearchKpis.vue'
import SearchFiltersCard from '../components/search/SearchFiltersCard.vue'
import SearchLiveProgress from '../components/search/SearchLiveProgress.vue'
import SearchResultsTable from '../components/search/SearchResultsTable.vue'

const profile = ref(null)
const loadingProfile = ref(true)
const snack = reactive({ show: false, text: '', color: 'success' })
const existingApps = ref([])

function notify(text, color = 'success') {
  Object.assign(snack, { show: true, text, color })
}

function onNotify(payload) {
  notify(payload.text, payload.color)
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
    } else {
      form.roles = []
    }
    if (data?.ats_settings?.enabled_platforms?.length) {
      form.platforms = [...data.ats_settings.enabled_platforms]
    }
    form.maxYears = 0
    form.geoScope = 'latam'
    form.countries = []
    form.workModes = ['remote']

    await loadExistingApps()
    await initScanSync(existingApps.value)
  } catch (e) {
    notify(t('search.toasts.profileLoadError') + e.message, 'warning')
  } finally {
    loadingProfile.value = false
  }
}

onMounted(loadProfile)

watch(scanning, (newVal, oldVal) => {
  if (oldVal === true && newVal === false) {
    notify(t('search.toasts.scanFinished', { count: matches.value.length }))
  }
})
</script>

<template>
  <div class="flex flex-col gap-6 w-full">
    <!-- TITULO DE PAGINA Y SUBTITULO -->
    <div class="flex flex-col gap-1">
      <div class="flex items-center justify-between flex-wrap gap-2">
        <h1 class="text-xl font-semibold text-on-surface tracking-tight">
          {{ $t('search.title') }}
        </h1>
        <div class="flex items-center gap-2">
          <span class="inline-flex items-center gap-1.5 text-xs text-outline font-mono">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            {{ $t('search.platformsTag') }}
          </span>
        </div>
      </div>
      <p class="text-xs text-on-surface-variant">
        {{ $t('search.subtitle') }}
      </p>
    </div>

    <!-- 4 TARJETAS KPI CON SPARKLINES DINAMICOS -->
    <SearchKpis
      :progress="progress"
      :scanning="scanning"
      :progress-percent="progressPercent"
      :matches-count="matches.length"
      :error-count="errorCount"
    />

    <!-- PANEL DE FILTROS -->
    <SearchFiltersCard
      :form="form"
      :profile="profile"
      @notify="onNotify"
    />

    <!-- ESTADO DE PROGRESO EN VIVO (DURANTE ESCANEO) -->
    <SearchLiveProgress
      :scanning="scanning"
      :progress="progress"
      :progress-percent="progressPercent"
    />

    <!-- TABLA DE VACANTES DETECTADAS -->
    <SearchResultsTable
      :matches="matches"
      :existing-apps="existingApps"
      :error-count="errorCount"
      :logs="logs"
      :scanning="scanning"
      @notify="onNotify"
      @refresh-apps="loadExistingApps"
    />

    <!-- NOTIFICACIONES TOAST -->
    <v-snackbar v-model="snack.show" :color="snack.color" timeout="3500">
      {{ snack.text }}
    </v-snackbar>
  </div>
</template>
