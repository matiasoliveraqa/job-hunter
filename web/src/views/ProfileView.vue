<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api.js'
import { t } from '../i18n/index.js'
import ProfilePersonalTab from '../components/profile/ProfilePersonalTab.vue'
import ProfileQuestionsTab from '../components/profile/ProfileQuestionsTab.vue'
import ProfileAiTab from '../components/profile/ProfileAiTab.vue'

const route = useRoute()

const profile = ref(null)
const original = ref('')
const loading = ref(true)
const saving = ref(false)
const snack = reactive({ show: false, text: '', color: 'success' })

const activeTab = ref('profile') // 'profile' | 'questions' | 'ai'

function notify(text, color = 'success') {
  Object.assign(snack, { show: true, text, color })
}

function adopt(data) {
  data.personal_info ??= {}
  data.personal_info.full_name ??= ''
  data.personal_info.email ??= ''
  data.personal_info.phone ??= ''
  data.personal_info.location ??= ''
  data.personal_info.city ??= ''
  data.personal_info.country ??= ''
  data.personal_info.linkedin_url ??= ''
  data.personal_info.github_url ??= ''
  data.personal_info.portfolio_url ??= ''
  data.personal_info.current_company ??= ''
  data.personal_info.years_of_experience ??= null
  data.personal_info.requires_us_visa_sponsorship ??= 'No'

  const normalizeCanonical = (val, map) => {
    if (!val) return null
    const lower = String(val).trim().toLowerCase()
    return map[lower] || val
  }
  const genderMap = {
    male: 'male', hombre: 'male', masculino: 'male', man: 'male',
    female: 'female', mujer: 'female', femenino: 'female', woman: 'female',
    'non-binary': 'non_binary', 'non binary': 'non_binary', 'no binario': 'non_binary',
    'decline to self-identify': 'decline', 'prefer not to say': 'decline', 'prefiero no responder': 'decline', decline: 'decline'
  }
  const raceMap = {
    'hispanic or latino': 'hispanic_latino', hispanic: 'hispanic_latino', latino: 'hispanic_latino',
    'hispano o latino': 'hispanic_latino', hispano: 'hispanic_latino',
    white: 'white', blanco: 'white', 'white (not hispanic or latino)': 'white',
    'black or african american': 'black', black: 'black', negro: 'black', 'negro o afroamericano': 'black',
    asian: 'asian', 'asiático': 'asian', asiatico: 'asian',
    'two or more races': 'two_or_more', 'dos o más razas': 'two_or_more', 'dos o más etnias': 'two_or_more',
    'decline to self-identify': 'decline', 'prefer not to say': 'decline', 'prefiero no responder': 'decline', decline: 'decline'
  }
  const veteranMap = {
    'i am not a veteran': 'not_veteran', 'not a veteran': 'not_veteran', 'no soy veterano': 'not_veteran', 'no soy un veterano': 'not_veteran', no: 'not_veteran', not_veteran: 'not_veteran',
    'i identify as one or more of the classifications of protected veteran': 'veteran', 'protected veteran': 'veteran', veteran: 'veteran', veterano: 'veteran', 'soy veterano protegido': 'veteran', yes: 'veteran',
    'i decline to self-identify': 'decline', 'decline to self-identify': 'decline', 'prefer not to say': 'decline', 'prefiero no responder': 'decline', decline: 'decline'
  }
  const disabilityMap = {
    'no, i do not have a disability': 'no', no: 'no', 'no tengo discapacidad': 'no', 'no tengo una discapacidad': 'no',
    'yes, i have a disability (or previously had one)': 'yes', 'yes, i have a disability': 'yes', 'sí tengo o tuve una discapacidad': 'yes', 'sí, tengo una discapacidad': 'yes', yes: 'yes',
    'i do not wish to answer': 'decline', 'decline to self-identify': 'decline', 'prefer not to say': 'decline', 'prefiero no responder': 'decline', decline: 'decline'
  }
  data.personal_info.gender = normalizeCanonical(data.personal_info.gender, genderMap) || 'decline'
  data.personal_info.race = normalizeCanonical(data.personal_info.race, raceMap) || 'decline'
  data.personal_info.veteran_status = normalizeCanonical(data.personal_info.veteran_status, veteranMap) || 'not_veteran'
  data.personal_info.disability_status = normalizeCanonical(data.personal_info.disability_status, disabilityMap) || 'no'

  data.search_criteria ??= {}
  data.search_criteria.target_roles ??= []
  data.search_criteria.keywords ??= []
  data.search_criteria.location_keywords ??= []
  data.search_criteria.max_years_of_experience ??= null
  data.search_criteria.min_salary_usd ??= null

  data.preferences ??= {}
  data.preferences.dependent_salary_usd ??= data.preferences.desired_salary_usd ?? null
  data.preferences.contractor_salary_usd ??= null
  data.preferences.salary_period ??= 'monthly'
  data.preferences.notice_period ??= ''
  data.preferences.english_level ??= ''
  data.preferences.native_language ??= ''
  data.preferences.legally_authorized_to_work ??= 'Yes'

  data.ats_settings ??= {}
  data.ats_settings.enabled_platforms ??= ['ashby', 'greenhouse', 'lever', 'workable', 'breezy', 'recruitee', 'bamboohr']
  data.ats_settings.auto_upload_resume ??= true
  data.ats_settings.stealth_mode ??= true

  data.open_questions ??= {}
  data.open_questions.motivation ??= ''
  data.open_questions.experience_summary ??= ''
  data.open_questions.key_project ??= data.open_questions.metrics_and_kpis || ''
  data.open_questions.timezone_overlap ??= ''
  data.open_questions.education_level ??= ''
  data.open_questions.education_institution ??= ''
  data.open_questions.education_start_year ??= null
  data.open_questions.education_end_year ??= null
  data.open_questions.additional_info ??= ''
  data.open_questions.custom_qa ??= {}
  if (data.open_questions.fintech_motivation && !data.open_questions.custom_qa.fintech) {
    data.open_questions.custom_qa.fintech = data.open_questions.fintech_motivation
  }

  profile.value = data
  original.value = JSON.stringify(data)
}

const dirty = computed(() => {
  if (!profile.value || !original.value) return false
  return JSON.stringify(profile.value) !== original.value
})

const baseCv = ref(null)
const uploadingCv = ref(false)

async function loadBaseCv() {
  try {
    baseCv.value = await api.getBaseCv()
  } catch {
    // ignora
  }
}

async function load() {
  loading.value = true
  try {
    adopt(await api.getProfile())
  } catch (e) {
    notify(e.message, 'error')
  } finally {
    loading.value = false
  }
}

const agentStatus = ref(null)
const agentConfig = reactive({
  provider: 'auto',
  anthropicApiKey: '',
  openaiApiKey: '',
  geminiApiKey: '',
  deepseekApiKey: '',
  kimiApiKey: '',
  customOpenAiApiKey: '',
  customOpenAiBaseUrl: '',
  customOpenAiModel: '',
  hasAnthropicKey: false,
  hasOpenAiKey: false,
  hasGeminiKey: false,
  hasDeepSeekKey: false,
  hasKimiKey: false,
  hasCustomKey: false,
})
const savingAgentConfig = ref(false)

const providerOptions = computed(() => [
  { value: 'auto', title: t('profile.providers.auto') },
  { value: 'deepseek_api', title: t('profile.providers.deepseek') },
  { value: 'kimi_api', title: t('profile.providers.kimi') },
  { value: 'custom_openai_api', title: t('profile.providers.custom') },
  { value: 'anthropic_api', title: t('profile.providers.anthropic') },
  { value: 'openai_api', title: t('profile.providers.openai') },
  { value: 'gemini_api', title: t('profile.providers.gemini') },
  { value: 'claude', title: t('profile.providers.claude') },
  { value: 'agy', title: t('profile.providers.agy') },
  { value: 'codex', title: t('profile.providers.codex') },
])

async function loadAgentConfig() {
  try {
    const [status, cfg] = await Promise.all([api.getAgentStatus(), api.getAgentConfig()])
    agentStatus.value = status
    Object.assign(agentConfig, cfg)
  } catch (e) {
    console.warn('[ProfileView] No se pudo cargar config de IA:', e.message)
  }
}

async function saveAgentConfigAction() {
  savingAgentConfig.value = true
  try {
    const res = await api.saveAgentConfig({
      provider: agentConfig.provider,
      anthropicApiKey: agentConfig.anthropicApiKey,
      openaiApiKey: agentConfig.openaiApiKey,
      geminiApiKey: agentConfig.geminiApiKey,
      deepseekApiKey: agentConfig.deepseekApiKey,
      kimiApiKey: agentConfig.kimiApiKey,
      customOpenAiApiKey: agentConfig.customOpenAiApiKey,
      customOpenAiBaseUrl: agentConfig.customOpenAiBaseUrl,
      customOpenAiModel: agentConfig.customOpenAiModel,
    })
    if (res?.status) {
      agentStatus.value = res.status
    }
    notify(
      agentStatus.value?.connected
        ? t('profile.toasts.agentTestedSuccess', { name: agentStatus.value.activeProviderName })
        : t('profile.toasts.agentNoAiWarn'),
      agentStatus.value?.connected ? 'success' : 'warning',
    )
    await loadAgentConfig()
  } catch (err) {
    notify(t('profile.toasts.agentTestedError') + err.message, 'error')
  } finally {
    savingAgentConfig.value = false
  }
}

async function onFileSelected(event) {
  const file = event.target?.files?.[0]
  if (!file) return
  await handleCvUpload(file)
  if (event.target) event.target.value = ''
}

async function handleCvUpload(file) {
  uploadingCv.value = true
  try {
    const reader = new FileReader()
    const base64Promise = new Promise((resolve, reject) => {
      reader.onload = () => {
        const result = reader.result || ''
        const b64 = result.includes(',') ? result.split(',')[1] : result
        resolve(b64)
      }
      reader.onerror = reject
    })
    reader.readAsDataURL(file)
    const base64 = await base64Promise

    const res = await api.uploadBaseCv({
      filename: file.name,
      base64,
    })

    await loadBaseCv()

    if (res?.extracted) {
      const ext = res.extracted
      if (ext.personal_info && profile.value?.personal_info) {
        const pi = profile.value.personal_info
        for (const [k, v] of Object.entries(ext.personal_info)) {
          if (v !== undefined && v !== null && v !== '') {
            pi[k] = v
          }
        }
      }
      if (Array.isArray(ext.keywords) && profile.value?.search_criteria) {
        const curKw = new Set(profile.value.search_criteria.keywords || [])
        for (const kw of ext.keywords) {
          curKw.add(kw)
        }
        profile.value.search_criteria.keywords = Array.from(curKw)
      }
      if (Array.isArray(ext.target_roles) && ext.target_roles.length && profile.value?.search_criteria) {
        const curRoles = new Set(profile.value.search_criteria.target_roles || [])
        for (const r of ext.target_roles) {
          curRoles.add(r)
        }
        profile.value.search_criteria.target_roles = Array.from(curRoles)
      }

      notify(t('profile.toasts.cvUploadedParsed'))
    } else {
      notify(t('profile.toasts.cvUploaded'))
    }
  } catch (err) {
    notify(t('profile.toasts.cvUploadError') + err.message, 'error')
  } finally {
    uploadingCv.value = false
  }
}

async function save() {
  saving.value = true
  try {
    adopt(await api.saveProfile(profile.value))
    notify(t('profile.toasts.saved'))
  } catch (e) {
    notify(t('profile.toasts.saveError') + e.message, 'error')
  } finally {
    saving.value = false
  }
}

const reset = () => adopt(JSON.parse(original.value))

onMounted(async () => {
  load()
  loadBaseCv()
  await loadAgentConfig()
  if (route.query.tab === 'ai') {
    activeTab.value = 'ai'
  } else if (route.query.tab === 'questions') {
    activeTab.value = 'questions'
  }
})
</script>

<template>
  <div class="p-6 flex flex-col gap-6 max-w-[1680px] w-full mx-auto font-sans">
    <!-- TOP ACTION & TITLE HEADER -->
    <div class="flex flex-col md:flex-row md:items-end justify-between gap-4 pb-2 border-b border-border-subtle">
      <div class="flex flex-col gap-1">
        <h1 class="text-2xl font-semibold text-on-surface tracking-tight">{{ $t('profile.title') }}</h1>
      </div>

      <!-- Action Cluster -->
      <div class="flex items-center gap-3 self-start md:self-auto flex-wrap">
        <button
          class="px-3.5 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface text-xs font-medium border border-border-subtle transition-colors flex items-center gap-1.5 disabled:opacity-50"
          :disabled="!dirty || saving"
          type="button"
          @click="reset"
        >
          <span class="material-symbols-outlined text-[16px]">restart_alt</span>
          <span>{{ $t('profile.discardChanges') }}</span>
        </button>

        <button
          class="px-4 py-1.5 rounded-lg bg-accent hover:bg-accent-hover text-white text-xs font-medium shadow-sm transition-all active:scale-[0.98] flex items-center gap-1.5 disabled:opacity-50"
          :disabled="!dirty || saving"
          type="button"
          @click="save"
        >
          <span :class="['material-symbols-outlined text-[16px]', saving ? 'animate-spin' : '']">
            {{ saving ? 'sync' : 'save' }}
          </span>
          <span>{{ saving ? $t('profile.savingProfile') : $t('profile.saveProfile') }}</span>
        </button>
      </div>
    </div>

    <!-- TABS DE NAVEGACIÓN EN CABECERA -->
    <div class="flex items-center gap-2 border-b border-border-subtle pb-px flex-wrap">
      <button
        class="flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition-colors rounded-t-lg"
        :class="[
          activeTab === 'profile'
            ? 'border-accent text-on-surface font-semibold bg-surface-container/50'
            : 'border-transparent text-on-surface-variant hover:text-on-surface hover:bg-surface-container/20'
        ]"
        type="button"
        @click="activeTab = 'profile'"
      >
        <span class="material-symbols-outlined text-[17px] text-accent">badge</span>
        <span>{{ $t('profile.tabs.profile') }}</span>
      </button>

      <button
        class="flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition-colors rounded-t-lg"
        :class="[
          activeTab === 'questions'
            ? 'border-accent text-on-surface font-semibold bg-surface-container/50'
            : 'border-transparent text-on-surface-variant hover:text-on-surface hover:bg-surface-container/20'
        ]"
        type="button"
        @click="activeTab = 'questions'"
      >
        <span class="material-symbols-outlined text-[17px] text-sky-400">forum</span>
        <span>{{ $t('profile.tabs.questions') }}</span>
        <span class="px-1.5 py-0.2 rounded text-[10px] font-mono bg-surface-container-high text-outline">6</span>
      </button>

      <button
        class="flex items-center gap-2 px-3.5 py-2 text-xs font-medium border-b-2 transition-colors rounded-t-lg"
        :class="[
          activeTab === 'ai'
            ? 'border-accent text-on-surface font-semibold bg-surface-container/50'
            : 'border-transparent text-on-surface-variant hover:text-on-surface hover:bg-surface-container/20'
        ]"
        type="button"
        @click="activeTab = 'ai'"
      >
        <span class="material-symbols-outlined text-[17px] text-tertiary">smart_toy</span>
        <span>{{ $t('profile.tabs.ai') }}</span>
        <span
          class="w-2 h-2 rounded-full"
          :class="agentStatus?.connected ? 'bg-emerald-400' : 'bg-amber-400'"
          :title="agentStatus?.connected ? `Conectado: ${agentStatus.activeProviderName}` : 'Modo CV base estándar'"
        ></span>
      </button>
    </div>

    <!-- Security & Purpose Info Banner -->
    <div class="flex items-start gap-3 p-3.5 rounded-lg bg-surface-card border border-border-subtle border-l-4 border-l-accent text-on-surface-variant">
      <span class="material-symbols-outlined text-accent text-[20px] shrink-0 mt-0.5">verified_user</span>
      <div class="flex-1 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <p class="text-xs text-on-surface-variant">
          {{ $t('profile.banner.text') }}
          <code class="font-mono text-outline px-1.5 py-0.5 bg-surface-container rounded text-[11px]">config/profile.json</code> (ignorado por git), {{ $t('profile.banner.backupText') }}
          <code class="font-mono text-outline px-1.5 py-0.5 bg-surface-container rounded text-[11px]">output/backups/</code>.
        </p>
        <span class="shrink-0 font-mono text-outline text-[11px] self-end sm:self-auto">{{ $t('profile.banner.localStorageBadge') }}</span>
      </div>
    </div>

    <!-- LOADING STATE -->
    <div v-if="loading" class="p-12 text-center text-xs font-mono text-outline">
      {{ $t('common.loading') }}
    </div>

    <!-- TAB 1: PERFIL Y CRITERIOS -->
    <ProfilePersonalTab
      v-else-if="activeTab === 'profile' && profile"
      :profile="profile"
      :base-cv="baseCv"
      :uploading-cv="uploadingCv"
      @file-selected="onFileSelected"
    />

    <!-- TAB 2: PREGUNTAS ABIERTAS ATS -->
    <ProfileQuestionsTab
      v-else-if="activeTab === 'questions' && profile"
      :profile="profile"
    />

    <!-- TAB 3: AGENTE IA Y CONFIGURACIÓN -->
    <ProfileAiTab
      v-else-if="activeTab === 'ai'"
      :agent-config="agentConfig"
      :agent-status="agentStatus"
      :saving-agent-config="savingAgentConfig"
      :provider-options="providerOptions"
      @save-config="saveAgentConfigAction"
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
