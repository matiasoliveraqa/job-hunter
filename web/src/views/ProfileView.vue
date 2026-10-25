<script setup>
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api.js'
import { t } from '../i18n/index.js'

const route = useRoute()

const profile = ref(null)
const original = ref('')
const loading = ref(true)
const saving = ref(false)
const snack = reactive({ show: false, text: '', color: 'success' })

const activeTab = ref('profile') // 'profile' | 'questions' | 'ai'

const yesNo = ['Yes', 'No']
const platforms = ['ashby', 'greenhouse', 'lever']

const newRoleInput = ref('')
const newKeywordInput = ref('')
const newLocationInput = ref('')

function notify(text, color = 'success') {
  Object.assign(snack, { show: true, text, color })
}

function adopt(data) {
  data.personal_info ??= {}
  data.personal_info.github_url ??= ''
  data.personal_info.portfolio_url ??= ''
  data.personal_info.current_company ??= ''
  data.personal_info.years_of_experience ??= 7
  data.personal_info.requires_us_visa_sponsorship ??= 'No'
  data.personal_info.gender ??= 'Male'
  data.personal_info.race ??= 'Hispanic or Latino'
  data.personal_info.veteran_status ??= 'I am not a veteran'
  data.personal_info.disability_status ??= 'No, I do not have a disability'

  data.search_criteria ??= {}
  data.search_criteria.target_roles ??= []
  data.search_criteria.keywords ??= []
  data.search_criteria.location_keywords ??= []
  data.search_criteria.max_years_of_experience ??= 7
  data.search_criteria.min_salary_usd ??= 3000

  data.preferences ??= {}
  data.preferences.dependent_salary_usd ??= data.preferences.desired_salary_usd ?? 3500
  data.preferences.contractor_salary_usd ??= 4500
  data.preferences.salary_period ??= 'monthly'
  data.preferences.notice_period ??= '2 weeks'
  data.preferences.english_level ??= 'B2 Upper Intermediate (EF SET Certified)'
  data.preferences.legally_authorized_to_work ??= 'Yes'

  data.ats_settings ??= {}
  data.ats_settings.enabled_platforms ??= ['ashby', 'greenhouse', 'lever']
  data.ats_settings.auto_upload_resume ??= true
  data.ats_settings.stealth_mode ??= true

  data.open_questions ??= {}
  data.open_questions.motivation ??= ''
  data.open_questions.experience_summary ??= ''
  data.open_questions.key_project ??= data.open_questions.metrics_and_kpis || ''
  data.open_questions.timezone_overlap ??= ''
  data.open_questions.education_level ??= ''
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
const fileInputRef = ref(null)

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
const toNumber = (v) => (v === '' || v === null || v === undefined ? null : Number(v))
const formatSalaryNumber = (v) => {
  const n = Number(v)
  if (isNaN(n) || n <= 0) return '0'
  return n.toLocaleString('en-US')
}

function addTargetRole() {
  const val = newRoleInput.value.trim()
  if (!val || !profile.value?.search_criteria?.target_roles) return
  if (!profile.value.search_criteria.target_roles.includes(val)) {
    profile.value.search_criteria.target_roles.push(val)
  }
  newRoleInput.value = ''
}

function removeTargetRole(idx) {
  profile.value?.search_criteria?.target_roles?.splice(idx, 1)
}

function addKeyword() {
  const val = newKeywordInput.value.trim()
  if (!val || !profile.value?.search_criteria?.keywords) return
  if (!profile.value.search_criteria.keywords.includes(val)) {
    profile.value.search_criteria.keywords.push(val)
  }
  newKeywordInput.value = ''
}

function removeKeyword(idx) {
  profile.value?.search_criteria?.keywords?.splice(idx, 1)
}

function addLocation() {
  const val = newLocationInput.value.trim()
  if (!val || !profile.value?.search_criteria?.location_keywords) return
  if (!profile.value.search_criteria.location_keywords.includes(val)) {
    profile.value.search_criteria.location_keywords.push(val)
  }
  newLocationInput.value = ''
}

function removeLocation(idx) {
  profile.value?.search_criteria?.location_keywords?.splice(idx, 1)
}

function togglePlatform(pl) {
  const list = profile.value?.ats_settings?.enabled_platforms
  if (!list) return
  const idx = list.indexOf(pl)
  if (idx > -1) {
    list.splice(idx, 1)
  } else {
    list.push(pl)
  }
}

const newCustomKey = ref('')
const newCustomVal = ref('')

function addCustomQa() {
  const k = newCustomKey.value.trim().toLowerCase()
  const v = newCustomVal.value.trim()
  if (!k || !v) return
  profile.value.open_questions.custom_qa ??= {}
  profile.value.open_questions.custom_qa[k] = v
  newCustomKey.value = ''
  newCustomVal.value = ''
}

function removeCustomQa(key) {
  if (profile.value?.open_questions?.custom_qa) {
    delete profile.value.open_questions.custom_qa[key]
  }
}

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
    <div v-else-if="activeTab === 'profile' && profile" class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      <!-- LEFT COLUMN: CV BASE, PERSONAL DATA & DEMOGRAPHICS (7 cols) -->
      <div class="lg:col-span-7 flex flex-col gap-6">
        <!-- 1. Card: CV Base del Candidato -->
        <section class="bg-surface-card border border-border-subtle rounded-xl p-5 flex flex-col gap-4">
          <div class="flex items-center justify-between pb-1">
            <div class="flex items-center gap-2.5">
              <span class="material-symbols-outlined text-accent text-[20px]">picture_as_pdf</span>
              <div>
                <h2 class="text-sm font-semibold text-on-surface">{{ $t('profile.sections.baseCv') }}</h2>
                <p class="font-mono text-[11px] text-outline">{{ $t('profile.sections.baseCvDesc') }}</p>
              </div>
            </div>
            <span class="px-2 py-0.5 rounded bg-surface-container-high text-on-surface-variant font-mono text-[11px]">{{ $t('profile.sections.masterDocBadge') }}</span>
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-lg bg-surface-container/60 border border-border-subtle">
            <div class="flex items-center gap-2.5 min-w-0">
              <span class="material-symbols-outlined text-emerald-400 text-[18px]">verified</span>
              <div class="flex flex-col min-w-0">
                <span class="text-xs font-medium text-on-surface truncate">
                  {{ baseCv?.filename || 'Matias_Olivera_QA_CV.pdf' }}
                </span>
                <span class="font-mono text-[10px] text-outline">
                  {{ baseCv?.exists ? `${Math.round((baseCv.sizeBytes || 0) / 1024)} KB` : $t('profile.sections.notUploadedYet') }} • my_cv/
                </span>
              </div>
            </div>

            <div class="flex items-center gap-2 shrink-0">
              <a
                v-if="baseCv?.exists"
                :href="baseCv.url"
                target="_blank"
                class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface text-xs font-medium border border-border-subtle transition-colors"
              >
                <span class="material-symbols-outlined text-[15px]">visibility</span>
                <span>{{ $t('profile.sections.viewCvBtn') }}</span>
              </a>

              <input
                ref="fileInputRef"
                type="file"
                accept=".pdf,.html,.md,.txt"
                class="hidden"
                @change="onFileSelected"
              />

              <button
                type="button"
                class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent hover:bg-accent-hover text-white text-xs font-medium shadow-sm transition-all active:scale-[0.98]"
                :disabled="uploadingCv"
                @click="fileInputRef?.click()"
              >
                <span :class="['material-symbols-outlined text-[15px]', uploadingCv ? 'animate-spin' : '']">
                  {{ uploadingCv ? 'sync' : 'upload' }}
                </span>
                <span>{{ uploadingCv ? $t('profile.sections.analyzingCv') : $t('profile.sections.loadNewCv') }}</span>
              </button>
            </div>
          </div>
        </section>

        <!-- 2. Card: Datos Personales -->
        <section class="bg-surface-card border border-border-subtle rounded-xl p-5 flex flex-col gap-4">
          <div class="flex items-center justify-between pb-1">
            <div class="flex items-center gap-2.5">
              <span class="material-symbols-outlined text-accent text-[20px]">badge</span>
              <div>
                <h2 class="text-sm font-semibold text-on-surface">{{ $t('profile.sections.personalInfo') }}</h2>
                <p class="font-mono text-[11px] text-outline">{{ $t('profile.sections.personalInfoDesc') }}</p>
              </div>
            </div>
          </div>

          <div class="flex flex-col gap-4">
            <!-- Nombre & Email -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="text-xs text-on-surface-variant font-medium">
                  {{ $t('profile.sections.fullName') }} <span class="text-accent">*</span>
                </label>
                <input
                  v-model="profile.personal_info.full_name"
                  class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                  type="text"
                />
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="text-xs text-on-surface-variant font-medium">
                  {{ $t('profile.sections.email') }} <span class="text-accent">*</span>
                </label>
                <input
                  v-model="profile.personal_info.email"
                  class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                  type="email"
                />
              </div>
            </div>

            <!-- Teléfono & Ubicación -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="text-xs text-on-surface-variant font-medium">
                  {{ $t('profile.sections.phone') }} <span class="text-accent">*</span>
                </label>
                <div class="relative flex items-center">
                  <span class="material-symbols-outlined text-[16px] text-outline absolute left-2.5 pointer-events-none">call</span>
                  <input
                    v-model="profile.personal_info.phone"
                    class="h-9 pl-8 pr-3 w-full rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                    type="text"
                  />
                </div>
              </div>
              <div class="flex flex-col gap-1.5">
                <label class="text-xs text-on-surface-variant font-medium">
                  {{ $t('profile.sections.currentLocation') }} <span class="text-accent">*</span>
                </label>
                <div class="relative flex items-center">
                  <span class="material-symbols-outlined text-[16px] text-outline absolute left-2.5 pointer-events-none">pin_drop</span>
                  <input
                    v-model="profile.personal_info.location"
                    class="h-9 pl-8 pr-3 w-full rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                    type="text"
                  />
                </div>
              </div>
            </div>

            <!-- LinkedIn -->
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">
                {{ $t('profile.sections.linkedin') }} <span class="text-accent">*</span>
              </label>
              <div class="relative flex items-center">
                <input
                  v-model="profile.personal_info.linkedin_url"
                  class="h-9 px-3 pr-9 w-full rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                  type="text"
                />
                <a
                  v-if="profile.personal_info.linkedin_url"
                  :href="profile.personal_info.linkedin_url"
                  target="_blank"
                  class="absolute right-2 text-outline hover:text-on-surface p-1"
                >
                  <span class="material-symbols-outlined text-[16px]">open_in_new</span>
                </a>
              </div>
            </div>

            <!-- GitHub & Portfolio -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div class="flex flex-col gap-1.5">
                <label class="text-xs text-on-surface-variant font-medium">
                  {{ $t('profile.sections.github') }}
                </label>
                <div class="relative flex items-center">
                  <span class="material-symbols-outlined text-[16px] text-outline absolute left-2.5 pointer-events-none">code</span>
                  <input
                    v-model="profile.personal_info.github_url"
                    class="h-9 pl-8 pr-8 w-full rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                    type="text"
                  />
                  <a
                    v-if="profile.personal_info.github_url"
                    :href="profile.personal_info.github_url"
                    target="_blank"
                    class="absolute right-2 text-outline hover:text-on-surface p-1"
                  >
                    <span class="material-symbols-outlined text-[14px]">open_in_new</span>
                  </a>
                </div>
              </div>

              <div class="flex flex-col gap-1.5">
                <label class="text-xs text-on-surface-variant font-medium">
                  {{ $t('profile.sections.portfolio') }}
                </label>
                <div class="relative flex items-center">
                  <span class="material-symbols-outlined text-[16px] text-outline absolute left-2.5 pointer-events-none">language</span>
                  <input
                    v-model="profile.personal_info.portfolio_url"
                    class="h-9 pl-8 pr-8 w-full rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                    type="text"
                  />
                  <a
                    v-if="profile.personal_info.portfolio_url"
                    :href="profile.personal_info.portfolio_url"
                    target="_blank"
                    class="absolute right-2 text-outline hover:text-on-surface p-1"
                  >
                    <span class="material-symbols-outlined text-[14px]">open_in_new</span>
                  </a>
                </div>
              </div>
            </div>

            <!-- Empresa actual, Años Exp & Sponsorship -->
            <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
              <div class="md:col-span-6 flex flex-col gap-1.5">
                <label class="text-xs text-on-surface-variant font-medium">
                  {{ $t('profile.sections.currentCompany') }}
                </label>
                <input
                  v-model="profile.personal_info.current_company"
                  class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                  type="text"
                />
              </div>

              <div class="md:col-span-3 flex flex-col gap-1.5">
                <label class="text-xs text-on-surface-variant font-medium">
                  {{ $t('profile.sections.yearsOfExperience') }}
                </label>
                <div class="flex items-center gap-2">
                  <input
                    :value="profile.personal_info.years_of_experience"
                    class="h-9 px-3 w-full rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                    type="number"
                    min="0"
                    @input="profile.personal_info.years_of_experience = toNumber($event.target.value)"
                  />
                  <span class="px-2 py-1 rounded bg-surface-container-highest text-accent font-mono text-[10px] uppercase font-semibold">
                    {{ (profile.personal_info.years_of_experience || 0) >= 5 ? 'Senior' : 'Mid' }}
                  </span>
                </div>
              </div>

              <div class="md:col-span-3 flex flex-col gap-1.5">
                <label class="text-xs text-on-surface-variant font-medium truncate">
                  {{ $t('profile.sections.visaSponsorship') }}
                </label>
                <select
                  v-model="profile.personal_info.requires_us_visa_sponsorship"
                  class="h-9 px-2 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors cursor-pointer"
                >
                  <option value="No">{{ $t('common.no') }}</option>
                  <option value="Yes">{{ $t('common.yes') }}</option>
                </select>
              </div>
            </div>
          </div>
        </section>

        <!-- 3. Card: Datos Demográficos / EEO -->
        <section class="bg-surface-card border border-border-subtle rounded-xl p-5 flex flex-col gap-4">
          <div class="flex items-start justify-between">
            <div class="flex items-center gap-2.5">
              <span class="material-symbols-outlined text-outline text-[20px]">public</span>
              <div>
                <h2 class="text-sm font-semibold text-on-surface">{{ $t('profile.sections.demographics') }}</h2>
                <p class="text-xs text-outline">{{ $t('profile.sections.eeoSubtitle') }}</p>
              </div>
            </div>
            <span class="px-2 py-0.5 rounded bg-surface-container-high text-outline font-mono text-[10px]">{{ $t('profile.sections.optionalBadge') }}</span>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">
                {{ $t('profile.sections.gender') }}
              </label>
              <select
                v-model="profile.personal_info.gender"
                class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors cursor-pointer"
              >
                <option value="Male">{{ $lang === 'es' ? 'Masculino / Male' : 'Male' }}</option>
                <option value="Female">{{ $lang === 'es' ? 'Femenino / Female' : 'Female' }}</option>
                <option value="Non-binary">{{ $lang === 'es' ? 'No binario / Non-binary' : 'Non-binary' }}</option>
                <option value="Decline to Self-Identify">{{ $lang === 'es' ? 'Prefiero no responder' : 'Decline to Self-Identify' }}</option>
              </select>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">
                {{ $t('profile.sections.race') }}
              </label>
              <select
                v-model="profile.personal_info.race"
                class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors cursor-pointer"
              >
                <option value="Hispanic or Latino">{{ $lang === 'es' ? 'Hispano o Latino' : 'Hispanic or Latino' }}</option>
                <option value="White">{{ $lang === 'es' ? 'Blanco (no hispano o latino)' : 'White (Not Hispanic or Latino)' }}</option>
                <option value="Black or African American">{{ $lang === 'es' ? 'Negro o afroamericano' : 'Black or African American' }}</option>
                <option value="Asian">{{ $lang === 'es' ? 'Asiático' : 'Asian' }}</option>
                <option value="Two or More Races">{{ $lang === 'es' ? 'Dos o más etnias' : 'Two or More Races' }}</option>
                <option value="Decline to Self-Identify">{{ $lang === 'es' ? 'Prefiero no responder' : 'Decline to Self-Identify' }}</option>
              </select>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">
                {{ $t('profile.sections.veteran') }}
              </label>
              <select
                v-model="profile.personal_info.veteran_status"
                class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors cursor-pointer"
              >
                <option value="I am not a veteran">{{ $lang === 'es' ? 'No soy veterano' : 'I am not a veteran' }}</option>
                <option value="I identify as one or more of the classifications of protected veteran">{{ $lang === 'es' ? 'Soy veterano protegido' : 'Protected veteran' }}</option>
                <option value="I decline to self-identify">{{ $lang === 'es' ? 'Prefiero no responder' : 'I decline to self-identify' }}</option>
              </select>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">
                {{ $t('profile.sections.disability') }}
              </label>
              <select
                v-model="profile.personal_info.disability_status"
                class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors cursor-pointer"
              >
                <option value="No, I do not have a disability">{{ $lang === 'es' ? 'No tengo discapacidad' : 'No, I do not have a disability' }}</option>
                <option value="Yes, I have a disability (or previously had one)">{{ $lang === 'es' ? 'Sí tengo o tuve una discapacidad' : 'Yes, I have a disability (or previously had one)' }}</option>
                <option value="I do not wish to answer">{{ $lang === 'es' ? 'Prefiero no responder' : 'I do not wish to answer' }}</option>
              </select>
            </div>
          </div>
        </section>
      </div>

      <!-- RIGHT COLUMN: SEARCH CRITERIA, PREFERENCES & AUTOMATION (5 cols) -->
      <div class="lg:col-span-5 flex flex-col gap-6">
        <!-- 4. Card: Criterios de Búsqueda -->
        <section class="bg-surface-card border border-border-subtle rounded-xl p-5 flex flex-col gap-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2.5">
              <span class="material-symbols-outlined text-accent text-[20px]">filter_alt</span>
              <h2 class="text-sm font-semibold text-on-surface">{{ $t('profile.sections.searchCriteria') }}</h2>
            </div>
          </div>

          <!-- Roles Objetivo -->
          <div class="flex flex-col gap-2">
            <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.targetRoles') }}</label>
            <div class="flex flex-wrap gap-1.5 p-2 rounded-lg bg-surface-container border border-border-subtle min-h-[44px]">
              <span
                v-for="(role, idx) in profile.search_criteria.target_roles"
                :key="role"
                class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-container-high text-on-surface text-xs font-mono border border-border-subtle"
              >
                {{ role }}
                <button
                  class="text-outline hover:text-rose-400 transition-colors"
                  type="button"
                  @click="removeTargetRole(idx)"
                >
                  ✕
                </button>
              </span>
            </div>
            <div class="flex items-center gap-2 mt-1">
              <input
                v-model="newRoleInput"
                class="h-8 px-2.5 flex-1 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                :placeholder="$t('profile.sections.targetRolesPlaceholder')"
                type="text"
                @keyup.enter="addTargetRole"
              />
              <button
                class="h-8 px-3 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-xs font-medium border border-border-subtle transition-colors"
                type="button"
                @click="addTargetRole"
              >
                {{ $t('profile.sections.addRoleBtn') }}
              </button>
            </div>
          </div>

          <!-- Keywords Técnicas -->
          <div class="flex flex-col gap-2">
            <div class="flex items-center justify-between">
              <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.keywords') }}</label>
              <span class="font-mono text-[10px] text-outline">{{ profile.search_criteria.keywords?.length || 0 }} tags</span>
            </div>
            <div class="flex flex-wrap gap-1 p-2 rounded-lg bg-surface-container border border-border-subtle max-h-36 overflow-y-auto">
              <span
                v-for="(kw, idx) in profile.search_criteria.keywords"
                :key="kw"
                class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-container-high text-on-surface-variant text-[11px] font-mono border border-border-subtle"
              >
                {{ kw }}
                <button
                  class="text-outline hover:text-rose-400 text-[10px]"
                  type="button"
                  @click="removeKeyword(idx)"
                >
                  ✕
                </button>
              </span>
            </div>
            <div class="flex items-center gap-2 mt-1">
              <input
                v-model="newKeywordInput"
                class="h-8 px-2.5 flex-1 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors font-mono"
                :placeholder="$t('profile.sections.keywordsPlaceholder')"
                type="text"
                @keyup.enter="addKeyword"
              />
              <button
                class="h-8 px-3 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-xs font-medium border border-border-subtle transition-colors"
                type="button"
                @click="addKeyword"
              >
                {{ $t('profile.sections.addRoleBtn') }}
              </button>
            </div>
          </div>

          <!-- Ubicaciones Aceptadas -->
          <div class="flex flex-col gap-2">
            <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.locationKeywords') }}</label>
            <div class="flex flex-wrap gap-1.5 p-2 rounded-lg bg-surface-container border border-border-subtle">
              <span
                v-for="(loc, idx) in profile.search_criteria.location_keywords"
                :key="loc"
                class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-container-high text-on-surface text-[10px] font-mono border border-border-subtle"
              >
                {{ loc }}
                <button
                  class="text-outline hover:text-rose-400"
                  type="button"
                  @click="removeLocation(idx)"
                >
                  ✕
                </button>
              </span>
            </div>
            <div class="flex items-center gap-2 mt-1">
              <input
                v-model="newLocationInput"
                class="h-8 px-2.5 flex-1 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors font-mono"
                :placeholder="$t('profile.sections.locationKeywordsPlaceholder')"
                type="text"
                @keyup.enter="addLocation"
              />
              <button
                class="h-8 px-3 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-xs font-medium border border-border-subtle transition-colors"
                type="button"
                @click="addLocation"
              >
                {{ $t('profile.sections.addRoleBtn') }}
              </button>
            </div>
          </div>

          <!-- Filtros Numéricos -->
          <div class="grid grid-cols-2 gap-3 pt-1">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant truncate">{{ $t('profile.sections.maxYears') }}</label>
              <input
                :value="profile.search_criteria.max_years_of_experience"
                class="h-9 px-3 rounded-lg bg-surface-container text-on-surface font-mono text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                :placeholder="$t('profile.sections.noLimitPlaceholder')"
                type="number"
                min="0"
                @input="profile.search_criteria.max_years_of_experience = toNumber($event.target.value)"
              />
              <span class="font-mono text-[10px] text-outline">{{ $t('profile.sections.emptyNoLimit') }}</span>
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant truncate">{{ $t('profile.sections.minSalary') }}</label>
              <div class="relative flex items-center">
                <span class="font-mono text-xs text-outline absolute left-2.5">$</span>
                <input
                  :value="profile.search_criteria.min_salary_usd"
                  class="h-9 pl-6 pr-3 w-full rounded-lg bg-surface-container text-on-surface font-mono text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                  type="number"
                  min="0"
                  @input="profile.search_criteria.min_salary_usd = toNumber($event.target.value)"
                />
              </div>
              <span class="font-mono text-[10px] text-outline">{{ $t('profile.sections.strictFilterNote') }}</span>
            </div>
          </div>
        </section>

        <!-- 5. Card: Preferencias & Disponibilidad -->
        <section class="bg-surface-card border border-border-subtle rounded-xl p-5 flex flex-col gap-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2.5">
              <span class="material-symbols-outlined text-accent text-[20px]">payments</span>
              <h2 class="text-sm font-semibold text-on-surface">{{ $t('profile.sections.compensation') }}</h2>
            </div>
          </div>

          <!-- Salarios en USD / mes con cálculo anual en tiempo real (Opción A) -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.dependentSalary') }}</label>
              <div class="relative flex items-center">
                <span class="font-mono text-xs text-outline absolute left-2.5">$</span>
                <input
                  :value="profile.preferences.dependent_salary_usd"
                  class="h-9 pl-6 pr-3 w-full rounded-lg bg-surface-container text-on-surface font-mono text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                  type="number"
                  min="0"
                  @input="profile.preferences.dependent_salary_usd = toNumber($event.target.value)"
                />
              </div>
              <span class="font-mono text-[10px] text-outline">
                {{ $t('profile.sections.payrollDirectAnnual', { amount: formatSalaryNumber((profile.preferences.dependent_salary_usd || 0) * 12) }) }}
              </span>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.contractorSalary') }}</label>
              <div class="relative flex items-center">
                <span class="font-mono text-xs text-outline absolute left-2.5">$</span>
                <input
                  :value="profile.preferences.contractor_salary_usd"
                  class="h-9 pl-6 pr-3 w-full rounded-lg bg-surface-container text-on-surface font-mono text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                  type="number"
                  min="0"
                  @input="profile.preferences.contractor_salary_usd = toNumber($event.target.value)"
                />
              </div>
              <span class="font-mono text-[10px] text-outline">
                {{ $t('profile.sections.contractorAnnual', { amount: formatSalaryNumber((profile.preferences.contractor_salary_usd || 0) * 12) }) }}
              </span>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.noticePeriod') }} <span class="text-accent">*</span></label>
              <input
                v-model="profile.preferences.notice_period"
                class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                type="text"
              />
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.legallyAuthorized') }}</label>
              <select
                v-model="profile.preferences.legally_authorized_to_work"
                class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors cursor-pointer"
              >
                <option value="Yes">{{ $t('common.yes') }}</option>
                <option value="No">{{ $t('common.no') }}</option>
              </select>
            </div>
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.englishLevel') }}</label>
            <div class="flex items-center gap-2">
              <input
                v-model="profile.preferences.english_level"
                class="h-9 px-3 w-full rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                type="text"
              />
              <span class="px-2 py-1 rounded bg-surface-container-highest text-accent font-mono text-[11px] whitespace-nowrap">
                Fluent
              </span>
            </div>
          </div>
        </section>

        <!-- 6. Card: Automatización & ATS -->
        <section class="bg-surface-card border border-border-subtle rounded-xl p-5 flex flex-col gap-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2.5">
              <span class="material-symbols-outlined text-accent text-[20px]">smart_toy</span>
              <h2 class="text-sm font-semibold text-on-surface">{{ $t('profile.sections.atsSettings') }}</h2>
            </div>
            <span class="px-2 py-0.5 rounded bg-surface-container-high text-accent font-mono text-[10px]">Headless Ready</span>
          </div>

          <!-- ATS Engine Checklist -->
          <div class="flex flex-col gap-2">
            <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.enabledPlatforms') }}</label>
            <div class="grid grid-cols-3 gap-2">
              <label
                v-for="pl in platforms"
                :key="pl"
                class="flex items-center gap-2 p-2 rounded-lg bg-surface-container hover:bg-surface-container-high border border-border-subtle cursor-pointer transition-colors"
              >
                <input
                  :checked="profile.ats_settings.enabled_platforms.includes(pl)"
                  class="rounded text-accent focus:ring-0 bg-surface-container-highest"
                  type="checkbox"
                  @change="togglePlatform(pl)"
                />
                <span class="font-mono text-xs text-on-surface capitalize">{{ pl }}</span>
              </label>
            </div>
          </div>

          <!-- Toggles -->
          <div class="flex flex-col gap-3 pt-2">
            <div class="flex items-center justify-between py-1">
              <div class="flex flex-col">
                <span class="text-xs font-medium text-on-surface">{{ $t('profile.sections.autoUploadResume') }}</span>
                <span class="text-[11px] text-outline">{{ $t('profile.sections.autoUploadResumeDesc') }}</span>
              </div>
              <input
                v-model="profile.ats_settings.auto_upload_resume"
                class="w-4 h-4 rounded text-accent focus:ring-0 bg-surface-container-highest cursor-pointer"
                type="checkbox"
              />
            </div>

            <div class="flex items-center justify-between py-1">
              <div class="flex flex-col">
                <span class="text-xs font-medium text-on-surface">{{ $t('profile.sections.stealthMode') }}</span>
                <span class="text-[11px] text-outline">{{ $t('profile.sections.stealthModeDesc') }}</span>
              </div>
              <input
                v-model="profile.ats_settings.stealth_mode"
                class="w-4 h-4 rounded text-accent focus:ring-0 bg-surface-container-highest cursor-pointer"
                type="checkbox"
              />
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- TAB 2: PREGUNTAS ABIERTAS ATS (Punto 3 implementado) -->
    <div v-else-if="activeTab === 'questions' && profile" class="flex flex-col gap-6">
      <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col gap-1">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-sky-400 text-[20px]">forum</span>
          <h2 class="text-sm font-semibold text-on-surface">{{ $t('profile.sections.questionsTabTitle') }}</h2>
        </div>
        <p class="text-xs text-on-surface-variant">
          {{ $t('profile.sections.questionsTabDesc') }}
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- 1. Motivación e interés por la empresa -->
        <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col gap-2">
          <label class="text-xs font-semibold text-on-surface">{{ $t('profile.sections.motivation') }}</label>
          <span class="text-[11px] text-outline">{{ $t('profile.sections.motivationDesc') }}</span>
          <textarea
            v-model="profile.open_questions.motivation"
            rows="5"
            class="w-full p-2.5 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle focus:outline-none focus:border-accent transition-colors font-sans leading-relaxed"
          ></textarea>
        </div>

        <!-- 2. Resumen de trayectoria y experiencia relevante -->
        <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col gap-2">
          <label class="text-xs font-semibold text-on-surface">{{ $t('profile.sections.experienceSummary') }}</label>
          <span class="text-[11px] text-outline">{{ $t('profile.sections.experienceSummaryDesc') }}</span>
          <textarea
            v-model="profile.open_questions.experience_summary"
            rows="5"
            class="w-full p-2.5 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle focus:outline-none focus:border-accent transition-colors font-sans leading-relaxed"
          ></textarea>
        </div>

        <!-- 3. Proyecto destacado o mayor desafío resuelto -->
        <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col gap-2">
          <label class="text-xs font-semibold text-on-surface">{{ $t('profile.sections.keyProject') }}</label>
          <span class="text-[11px] text-outline">{{ $t('profile.sections.keyProjectDesc') }}</span>
          <textarea
            v-model="profile.open_questions.key_project"
            rows="5"
            class="w-full p-2.5 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle focus:outline-none focus:border-accent transition-colors font-sans leading-relaxed"
          ></textarea>
        </div>

        <!-- 4. Información adicional o notas para la postulación -->
        <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col gap-2">
          <label class="text-xs font-semibold text-on-surface">{{ $t('profile.sections.additionalInfo') }}</label>
          <span class="text-[11px] text-outline">{{ $t('profile.sections.additionalInfoDesc') }}</span>
          <textarea
            v-model="profile.open_questions.additional_info"
            rows="5"
            class="w-full p-2.5 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle focus:outline-none focus:border-accent transition-colors font-sans leading-relaxed"
          ></textarea>
        </div>

        <!-- 5. Nivel de formación académica o certificaciones -->
        <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col gap-2">
          <label class="text-xs font-semibold text-on-surface">{{ $t('profile.sections.educationLevel') }}</label>
          <span class="text-[11px] text-outline">{{ $t('profile.sections.educationLevelDesc') }}</span>
          <input
            v-model="profile.open_questions.education_level"
            type="text"
            class="h-9 px-3 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle focus:outline-none focus:border-accent transition-colors font-sans"
          />
        </div>

        <!-- 6. Disponibilidad horaria y huso horario -->
        <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col gap-2">
          <label class="text-xs font-semibold text-on-surface">{{ $t('profile.sections.timezoneOverlap') }}</label>
          <span class="text-[11px] text-outline">{{ $t('profile.sections.timezoneOverlapDesc') }}</span>
          <input
            v-model="profile.open_questions.timezone_overlap"
            type="text"
            class="h-9 px-3 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle focus:outline-none focus:border-accent transition-colors font-sans"
          />
        </div>
      </div>

      <!-- SECCIÓN: PREGUNTAS PERSONALIZADAS POR PALABRA CLAVE (CUSTOM Q&A) -->
      <div class="p-5 rounded-xl bg-surface-card border border-border-subtle flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-amber-400 text-[18px]">tune</span>
            <h3 class="text-xs font-semibold text-on-surface">{{ $t('profile.sections.customQa') }}</h3>
          </div>
          <p class="text-[11px] text-on-surface-variant">
            {{ $t('profile.sections.customQaDesc') }}
          </p>
        </div>

        <!-- Lista de preguntas existentes -->
        <div v-if="profile.open_questions.custom_qa && Object.keys(profile.open_questions.custom_qa).length" class="flex flex-col gap-2.5">
          <div
            v-for="(val, key) in profile.open_questions.custom_qa"
            :key="key"
            class="p-3 rounded-lg bg-surface-container border border-border-subtle flex flex-col sm:flex-row sm:items-start justify-between gap-3"
          >
            <div class="flex flex-col gap-1 min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-container-highest text-accent border border-border-subtle font-semibold">
                  {{ key }}
                </span>
                <span class="text-[11px] text-outline">{{ $t('profile.sections.customKeywordBadge') }}</span>
              </div>
              <p class="text-xs text-on-surface font-sans leading-relaxed pt-0.5">
                {{ val }}
              </p>
            </div>
            <button
              class="self-end sm:self-start p-1.5 rounded-lg text-outline hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
              :title="$t('profile.sections.customQa')"
              type="button"
              @click="removeCustomQa(key)"
            >
              <span class="material-symbols-outlined text-[16px] block">delete</span>
            </button>
          </div>
        </div>
        <div v-else class="text-xs text-outline italic py-2">
          {{ $t('profile.sections.noCustomQuestions') }}
        </div>

        <!-- Formulario para agregar nueva clave/valor -->
        <div class="pt-3 border-t border-border-subtle flex flex-col gap-2.5">
          <span class="text-xs font-medium text-on-surface">{{ $t('profile.sections.addNewCustomResponse') }}</span>
          <div class="flex flex-col sm:flex-row items-stretch sm:items-start gap-2.5">
            <input
              v-model="newCustomKey"
              class="h-9 px-3 w-full sm:w-48 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle focus:outline-none focus:border-accent transition-colors"
              :placeholder="$t('profile.sections.customKeywordPlaceholder')"
              type="text"
            />
            <input
              v-model="newCustomVal"
              class="h-9 px-3 flex-1 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle focus:outline-none focus:border-accent transition-colors"
              :placeholder="$t('profile.sections.customResponsePlaceholder')"
              type="text"
              @keydown.enter.prevent="addCustomQa"
            />
            <button
              class="px-3.5 h-9 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface text-xs font-medium border border-border-subtle transition-colors flex items-center justify-center gap-1.5 shrink-0 disabled:opacity-50"
              :disabled="!newCustomKey.trim() || !newCustomVal.trim()"
              type="button"
              @click="addCustomQa"
            >
              <span class="material-symbols-outlined text-[16px]">add</span>
              <span>{{ $t('profile.sections.addBtn') }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- TAB 3: MOTOR DE IA Y LLM (Punto 2 implementado con Opción A) -->
    <div v-else-if="activeTab === 'ai'" class="flex flex-col gap-6">
      <section class="bg-surface-card border border-border-subtle rounded-xl p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between pb-1">
          <div class="flex items-center gap-2.5">
            <span class="material-symbols-outlined text-tertiary text-[20px]">smart_toy</span>
            <div>
              <h2 class="text-sm font-semibold text-on-surface">{{ $t('profile.sections.aiTitle') }}</h2>
              <p class="font-mono text-[11px] text-outline">{{ $t('profile.sections.aiDesc') }}</p>
            </div>
          </div>
          <span
            class="px-2 py-0.5 rounded text-[10px] font-mono"
            :class="agentStatus?.connected ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'"
          >
            {{ agentStatus?.connected ? $t('profile.sections.aiActiveBadge', { name: agentStatus.activeProviderName }) : $t('profile.sections.aiBaseCvActiveBadge') }}
          </span>
        </div>

        <!-- Status Card -->
        <div
          class="p-4 rounded-lg border flex flex-col gap-2"
          :class="agentStatus?.connected ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-amber-500/5 border-amber-500/20'"
        >
          <div class="flex items-center justify-between flex-wrap gap-2">
            <div class="flex items-center gap-2">
              <span class="material-symbols-outlined text-[18px]" :class="agentStatus?.connected ? 'text-emerald-400' : 'text-amber-400'">
                {{ agentStatus?.connected ? 'check_circle' : 'info' }}
              </span>
              <span class="text-xs font-semibold text-on-surface">
                {{ agentStatus?.connected ? $t('profile.sections.aiConnectedTitle', { name: agentStatus.activeProviderName }) : $t('profile.sections.aiDisconnectedTitle') }}
              </span>
            </div>
            <span class="font-mono text-[11px] text-outline">
              {{ agentStatus?.connected ? $t('profile.sections.aiTailorAvailable') : $t('profile.sections.aiBaseCvStandard') }}
            </span>
          </div>
          <p class="text-xs text-on-surface-variant">
            {{ agentStatus?.connected ? $t('profile.sections.aiConnectedDesc') : $t('profile.sections.aiDisconnectedDesc') }}
          </p>
        </div>

        <!-- Provider Select -->
        <div class="flex flex-col gap-1.5 max-w-md">
          <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.aiPreferredProvider') }}</label>
          <select
            v-model="agentConfig.provider"
            class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors cursor-pointer"
          >
            <option v-for="opt in providerOptions" :key="opt.value" :value="opt.value">{{ opt.title }}</option>
          </select>
        </div>

        <div class="my-2 border-t border-border-subtle"></div>

        <!-- Direct API Keys -->
        <div class="flex flex-col gap-1">
          <h3 class="text-xs font-semibold text-on-surface">{{ $t('profile.sections.apiKeysDirectTitle') }}</h3>
          <p class="text-xs text-outline">{{ $t('profile.sections.apiKeysDirectDesc') }}</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <!-- DeepSeek -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-on-surface-variant flex items-center justify-between">
              <span>DeepSeek API Key</span>
              <span class="font-mono text-[10px] text-outline">{{ agentConfig.hasDeepSeekKey ? $t('profile.sections.configured') : 'platform.deepseek.com' }}</span>
            </label>
            <input
              v-model="agentConfig.deepseekApiKey"
              class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
              placeholder="sk-..."
              type="password"
            />
          </div>

          <!-- Kimi -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-on-surface-variant flex items-center justify-between">
              <span>Kimi / Moonshot AI Key</span>
              <span class="font-mono text-[10px] text-outline">{{ agentConfig.hasKimiKey ? $t('profile.sections.configured') : 'platform.moonshot.cn' }}</span>
            </label>
            <input
              v-model="agentConfig.kimiApiKey"
              class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
              placeholder="sk-..."
              type="password"
            />
          </div>

          <!-- Anthropic -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-on-surface-variant flex items-center justify-between">
              <span>Anthropic Claude API Key</span>
              <span class="font-mono text-[10px] text-outline">{{ agentConfig.hasAnthropicKey ? $t('profile.sections.configured') : 'sk-ant-...' }}</span>
            </label>
            <input
              v-model="agentConfig.anthropicApiKey"
              class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
              placeholder="sk-ant-..."
              type="password"
            />
          </div>

          <!-- OpenAI -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-on-surface-variant flex items-center justify-between">
              <span>OpenAI API Key</span>
              <span class="font-mono text-[10px] text-outline">{{ agentConfig.hasOpenAiKey ? $t('profile.sections.configured') : 'sk-...' }}</span>
            </label>
            <input
              v-model="agentConfig.openaiApiKey"
              class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
              placeholder="sk-..."
              type="password"
            />
          </div>

          <!-- Gemini -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-on-surface-variant flex items-center justify-between">
              <span>Google Gemini API Key</span>
              <span class="font-mono text-[10px] text-outline">{{ agentConfig.hasGeminiKey ? $t('profile.sections.configured') : 'AI Studio' }}</span>
            </label>
            <input
              v-model="agentConfig.geminiApiKey"
              class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
              placeholder="AIza..."
              type="password"
            />
          </div>
        </div>

        <div class="my-2 border-t border-border-subtle"></div>

        <!-- Custom endpoint -->
        <div class="flex flex-col gap-1">
          <h3 class="text-xs font-semibold text-on-surface">{{ $t('profile.sections.customEndpointTitle') }}</h3>
          <p class="text-xs text-outline">{{ $t('profile.sections.customEndpointDesc') }}</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
          <div class="md:col-span-5 flex flex-col gap-1.5">
            <label class="text-xs text-on-surface-variant">{{ $t('profile.sections.apiBaseUrlLabel') }}</label>
            <input
              v-model="agentConfig.customOpenAiBaseUrl"
              class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
              placeholder="https://api.deepseek.com/v1 o http://localhost:11434/v1"
              type="text"
            />
          </div>

          <div class="md:col-span-3 flex flex-col gap-1.5">
            <label class="text-xs text-on-surface-variant">{{ $t('profile.sections.modelNameLabel') }}</label>
            <input
              v-model="agentConfig.customOpenAiModel"
              class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
              placeholder="deepseek-chat, llama3, etc."
              type="text"
            />
          </div>

          <div class="md:col-span-4 flex flex-col gap-1.5">
            <label class="text-xs text-on-surface-variant flex items-center justify-between">
              <span>{{ $t('profile.sections.customApiKeyLabel') }}</span>
              <span class="font-mono text-[10px] text-outline">{{ $t('profile.sections.optionalOllama') }}</span>
            </label>
            <input
              v-model="agentConfig.customOpenAiApiKey"
              class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
              placeholder="Opcional"
              type="password"
            />
          </div>
        </div>

        <div class="flex justify-end pt-3">
          <button
            class="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-xs font-medium shadow-sm transition-all active:scale-[0.98] flex items-center gap-1.5 disabled:opacity-50"
            :disabled="savingAgentConfig"
            type="button"
            @click="saveAgentConfigAction"
          >
            <span :class="['material-symbols-outlined text-[16px]', savingAgentConfig ? 'animate-spin' : '']">
              {{ savingAgentConfig ? 'sync' : 'check_circle' }}
            </span>
            <span>{{ savingAgentConfig ? $t('profile.sections.testingConnection') : $t('profile.sections.saveAndTestConnection') }}</span>
          </button>
        </div>
      </section>
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
