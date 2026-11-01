<script setup>
import { computed, ref, watch } from 'vue'
import {
  PRESETS,
  getAvailableCountries,
  normalizeCountryCode,
  getCountryName,
  setGeoScope,
} from '../../scanController.js'
import { currentLang, t } from '../../i18n/index.js'

const props = defineProps({
  form: {
    type: Object,
    required: true,
  },
  profile: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['notify'])

function notify(text, color = 'success') {
  emit('notify', { text, color })
}

const activePreset = ref('')
const newRoleInput = ref('')
const countrySearch = ref('')
const isCountryDropdownOpen = ref(false)

const availableScopeCountries = computed(() => {
  return getAvailableCountries(props.form.geoScope, currentLang.value)
})

const filteredCountries = computed(() => {
  const q = countrySearch.value.trim().toLowerCase()
  return availableScopeCountries.value.filter((item) => {
    const isAdded = props.form.countries.some((c) => (normalizeCountryCode(c) || c) === item.code)
    if (isAdded) return false
    if (!q) return true
    return (
      item.name.toLowerCase().includes(q) ||
      item.code.toLowerCase().includes(q) ||
      item.es.toLowerCase().includes(q) ||
      item.en.toLowerCase().includes(q) ||
      item.aliases?.some((a) => a.toLowerCase().includes(q))
    )
  })
})

const currentScopeLabel = computed(() => {
  if (props.form.geoScope === 'latam') return t('search.params.optLatam')
  if (props.form.geoScope === 'latam_na') return t('search.params.optLatamNa')
  return t('search.params.optGlobal')
})

const localizedPresets = computed(() =>
  PRESETS.map((p) => ({
    ...p,
    displayName: p.name === 'Todos' ? t('search.presets.all') : p.name,
  }))
)

function applyPreset(preset) {
  activePreset.value = preset.name
  props.form.roles = [...preset.roles]
  notify(t('search.presets.appliedToast', { name: preset.name === 'Todos' ? t('search.presets.all') : preset.name, count: preset.roles.length }))
}

function resetToProfile() {
  activePreset.value = ''
  if (props.profile?.search_criteria?.target_roles?.length) {
    props.form.roles = [...props.profile.search_criteria.target_roles]
  } else {
    props.form.roles = []
  }
  props.form.maxYears = 0
  props.form.geoScope = 'latam'
  props.form.countries = []
  props.form.workModes = ['remote']
  notify(t('search.presets.resetToast'))
}

function addRoleTag() {
  const val = newRoleInput.value.trim()
  if (!val) return
  if (!props.form.roles.includes(val)) {
    props.form.roles.push(val)
    newRoleInput.value = ''
    activePreset.value = ''
  }
}

function removeRoleTag(idx) {
  props.form.roles.splice(idx, 1)
  activePreset.value = ''
}

function togglePlatform(plat) {
  const idx = props.form.platforms.indexOf(plat)
  if (idx > -1) {
    if (props.form.platforms.length === 1) {
      return notify(t('search.params.mustKeepOne'), 'warning')
    }
    props.form.platforms.splice(idx, 1)
  } else {
    props.form.platforms.push(plat)
  }
}

function toggleWorkMode(mode) {
  const idx = props.form.workModes.indexOf(mode)
  if (idx > -1) {
    if (props.form.workModes.length === 1) {
      return notify(t('search.params.mustKeepOneMode'), 'warning')
    }
    props.form.workModes.splice(idx, 1)
  } else {
    props.form.workModes.push(mode)
  }
}

function handleCountryEnter() {
  const val = countrySearch.value.trim()
  if (!val) {
    if (filteredCountries.value.length > 0) {
      addCountry(filteredCountries.value[0].code)
    }
    return
  }
  const match = filteredCountries.value.find((c) =>
    c.name.toLowerCase() === val.toLowerCase() ||
    c.en.toLowerCase() === val.toLowerCase() ||
    c.es.toLowerCase() === val.toLowerCase() ||
    c.code.toLowerCase() === val.toLowerCase() ||
    c.aliases?.some((a) => a.toLowerCase() === val.toLowerCase())
  ) || filteredCountries.value[0]

  if (match) {
    addCountry(match.code)
  } else {
    notify(t('search.countries.notInScope'), 'warning')
  }
}

function addCountry(countryOrCode) {
  if (!countryOrCode) return
  const code = normalizeCountryCode(countryOrCode) || countryOrCode
  const allowedCodes = availableScopeCountries.value.map((c) => c.code)
  if (!allowedCodes.includes(code)) {
    return notify(t('search.countries.notInScope'), 'warning')
  }
  const isAdded = props.form.countries.some((c) => (normalizeCountryCode(c) || c) === code)
  if (isAdded) {
    return notify(t('search.countries.alreadyAdded'), 'warning')
  }
  props.form.countries.push(code)
  countrySearch.value = ''
  isCountryDropdownOpen.value = false
}

function removeCountry(idx) {
  props.form.countries.splice(idx, 1)
}

function clearCountries() {
  props.form.countries = []
}

function getCountryLabel(codeOrName) {
  return getCountryName(codeOrName, currentLang.value)
}

watch(
  () => props.form.geoScope,
  (newScope) => {
    setGeoScope(newScope)
  }
)
</script>

<template>
  <section class="bg-surface border border-border-subtle rounded-xl flex flex-col gap-3.5 shadow-sm p-5">
    <!-- 1. BLOQUE SUPERIOR: PRESETS DE ROL Y ESTADO GENERAL -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-border-subtle">
      <div class="flex flex-col gap-1.5">
        <div class="flex items-center gap-2">
          <span class="text-[11px] font-mono uppercase tracking-wider text-outline font-semibold">
            {{ $t('search.presets.title') }}
          </span>
          <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-container-high text-accent border border-border-subtle">
            {{ $t('search.presets.syncedBadge') }}
          </span>
        </div>
        <div class="flex items-center gap-1.5 overflow-x-auto py-1">
          <button
            v-for="p in localizedPresets"
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
            {{ p.displayName }}
          </button>
        </div>
      </div>

      <div class="flex items-center gap-3 self-end md:self-auto">
        <div class="flex items-center gap-1.5 text-xs text-outline font-mono bg-surface-container px-2.5 py-1.5 rounded-lg border border-border-subtle">
          <span class="w-1.5 h-1.5 rounded-full bg-accent animate-pulse"></span>
          <span>{{ $t('search.presets.activeMatch', { count: form.roles.length }) }}</span>
        </div>
        <button
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border-subtle bg-surface-container hover:bg-surface-container-high text-on-surface text-xs font-medium transition-colors shadow-sm"
          type="button"
          @click="resetToProfile"
        >
          <span class="material-symbols-outlined text-[15px] text-outline">restart_alt</span>
          <span>{{ $t('search.presets.reset') }}</span>
        </button>
      </div>
    </div>

    <!-- 2. BLOQUE CENTRAL: 5 PARÁMETROS CLAVE & TOGGLES CON TOOLTIPS -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5 py-1">
      <!-- Parámetro 1: Plataformas ATS -->
      <div class="flex flex-col justify-between gap-1.5 p-3 rounded-lg bg-surface-container border border-border-subtle group hover:border-border-muted transition-colors relative">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1">
            <label class="text-[11px] font-medium text-outline uppercase tracking-wider">{{ $t('search.params.atsPlatforms') }}</label>
            <div class="relative group/tip flex items-center cursor-help">
              <span class="material-symbols-outlined text-[14px] text-outline hover:text-on-surface">help</span>
              <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover/tip:flex flex-col w-56 p-2 rounded-lg bg-surface-container-highest border border-border-muted shadow-lg z-50 text-[11px] text-on-surface leading-snug pointer-events-none">
                <div class="font-semibold text-accent mb-0.5 flex items-center gap-1">
                  <span class="material-symbols-outlined text-[13px]">hub</span> {{ $t('search.params.officialApis') }}
                </div>
                {{ $t('search.params.atsTip') }}
              </div>
            </div>
          </div>
          <span class="px-1.5 py-0.2 rounded bg-surface-container-high text-[10px] font-mono text-accent">
            {{ $t('search.params.activeCount', { count: form.platforms.length }) }}
          </span>
        </div>
        <div class="flex items-center gap-1 pt-0.5 flex-wrap">
          <button
            v-for="plat in ['greenhouse', 'ashby', 'lever', 'workable', 'breezy', 'recruitee', 'bamboohr']"
            :key="plat"
            :class="[
              'px-1.5 py-0.5 rounded text-[10.5px] font-mono capitalize border transition-colors',
              form.platforms.includes(plat)
                ? 'bg-accent/10 border-accent/30 text-accent font-medium'
                : 'bg-surface-card border-border-subtle text-outline line-through opacity-60'
            ]"
            type="button"
            @click="togglePlatform(plat)"
          >
            {{ plat === 'bamboohr' ? 'Bamboo' : (plat === 'breezy' ? 'Breezy' : plat) }}
          </button>
        </div>
        <p class="text-[10.5px] leading-tight min-h-[20px] flex items-center">
          <span class="text-on-surface-variant flex items-center gap-1">
            <span class="material-symbols-outlined text-[13px] shrink-0">hub</span>
            <span>{{ $t('search.params.scansPortals', { count: form.platforms.length }) }}</span>
          </span>
        </p>
      </div>

      <!-- Parámetro 2: Experiencia Máxima (Default 0 = Sin límite) -->
      <div class="flex flex-col justify-between gap-1.5 p-3 rounded-lg bg-surface-container border border-border-subtle group hover:border-border-muted transition-colors relative">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1">
            <label class="text-[11px] font-medium text-outline uppercase tracking-wider">{{ $t('search.params.maxExp') }}</label>
            <div class="relative group/tip flex items-center cursor-help">
              <span class="material-symbols-outlined text-[14px] text-outline hover:text-on-surface">help</span>
              <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover/tip:flex flex-col w-56 p-2 rounded-lg bg-surface-container-highest border border-border-muted shadow-lg z-50 text-[11px] text-on-surface leading-snug pointer-events-none">
                <div class="font-semibold text-accent mb-0.5 flex items-center gap-1">
                  <span class="material-symbols-outlined text-[13px]">work_history</span> {{ $t('search.params.yearsLimit') }}
                </div>
                {{ $t('search.params.maxExpTip') }}
              </div>
            </div>
          </div>
          <span class="text-[10px] font-mono text-outline">{{ $t('search.params.rangeExp') }}</span>
        </div>
        <div class="flex items-center justify-between pt-0.5">
          <span class="text-xs text-on-surface-variant font-medium">{{ $t('search.params.upTo') }}</span>
          <div class="flex items-center gap-2">
            <input
              v-model.number="form.maxYears"
              class="w-14 py-1 text-center font-mono font-medium text-xs bg-surface-card border border-border-muted rounded text-on-surface focus:outline-none focus:border-accent transition-colors shadow-sm"
              max="15"
              min="0"
              type="number"
            />
            <span class="text-xs text-outline font-mono">{{ $t('search.params.years') }}</span>
          </div>
        </div>
        <p class="text-[10.5px] leading-tight min-h-[20px] flex items-center">
          <span v-if="!form.maxYears || form.maxYears === 0" class="text-on-surface-variant flex items-center gap-1">
            <span class="material-symbols-outlined text-[13px] shrink-0">all_inclusive</span>
            <span>{{ $t('search.params.discardsNone') }}</span>
          </span>
          <span v-else class="text-on-surface-variant flex items-center gap-1">
            <span class="material-symbols-outlined text-[13px] shrink-0">filter_list</span>
            <span>{{ $t('search.params.discardsOver', { count: form.maxYears }) }}</span>
          </span>
        </p>
      </div>

      <!-- Parámetro 3: Alcance Territorial -->
      <div class="flex flex-col justify-between gap-1.5 p-3 rounded-lg bg-surface-container border border-border-subtle group hover:border-border-muted transition-colors relative">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1">
            <label class="text-[11px] font-medium text-outline uppercase tracking-wider">{{ $t('search.params.territorialScope') }}</label>
            <div class="relative group/tip flex items-center cursor-help">
              <span class="material-symbols-outlined text-[14px] text-outline hover:text-on-surface">help</span>
              <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover/tip:flex flex-col w-72 p-2.5 rounded-lg bg-surface-container-highest border border-border-muted shadow-lg z-50 text-[11px] text-on-surface leading-snug pointer-events-none">
                <div class="font-semibold text-accent mb-1 flex items-center gap-1">
                  <span class="material-symbols-outlined text-[13px]">public</span> {{ $t('search.params.residencyFilter') }}
                </div>
                <div class="space-y-1.5 text-[11px]">
                  <div>{{ $t('search.params.residencyScopeDesc') }}</div>
                </div>
              </div>
            </div>
          </div>
          <span class="text-[10px] font-mono text-outline">{{ $t('search.params.residence') }}</span>
        </div>
        <div class="pt-0.5">
          <select
            v-model="form.geoScope"
            class="w-full py-1 px-2 text-xs font-medium bg-surface-card border border-border-muted rounded text-on-surface focus:outline-none focus:border-accent transition-colors shadow-sm cursor-pointer"
          >
            <option value="latam">{{ $t('search.params.optLatam') }}</option>
            <option value="latam_na">{{ $t('search.params.optLatamNa') }}</option>
            <option value="global">{{ $t('search.params.optGlobal') }}</option>
          </select>
        </div>
        <p class="text-[10.5px] leading-tight min-h-[20px] flex items-center">
          <span v-if="form.geoScope === 'latam'" class="text-on-surface-variant flex items-center gap-1">
            <span class="material-symbols-outlined text-[13px] shrink-0">location_on</span>
            <span>{{ $t('search.params.tipLatam') }}</span>
          </span>
          <span v-else-if="form.geoScope === 'latam_na'" class="text-on-surface-variant flex items-center gap-1">
            <span class="material-symbols-outlined text-[13px] shrink-0">travel_explore</span>
            <span>{{ $t('search.params.tipLatamNa') }}</span>
          </span>
          <span v-else class="text-amber-500/95 dark:text-amber-400 font-medium flex items-center gap-1">
            <span class="material-symbols-outlined text-[13px] shrink-0">public</span>
            <span>{{ $t('search.params.tipGlobal') }}</span>
          </span>
        </p>
      </div>

      <!-- Parámetro 4: Modalidad de Trabajo (Remoto, Híbrido, Presencial) -->
      <div class="flex flex-col justify-between gap-1.5 p-3 rounded-lg bg-surface-container border border-border-subtle group hover:border-border-muted transition-colors relative">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1">
            <label class="text-[11px] font-medium text-outline uppercase tracking-wider">{{ $t('search.params.workModes') }}</label>
            <div class="relative group/tip flex items-center cursor-help">
              <span class="material-symbols-outlined text-[14px] text-outline hover:text-on-surface">help</span>
              <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover/tip:flex flex-col w-56 p-2 rounded-lg bg-surface-container-highest border border-border-muted shadow-lg z-50 text-[11px] text-on-surface leading-snug pointer-events-none">
                <div class="font-semibold text-accent mb-0.5 flex items-center gap-1">
                  <span class="material-symbols-outlined text-[13px]">badge</span> {{ $t('search.params.workModes') }}
                </div>
                {{ $t('search.params.workModesTip') }}
              </div>
            </div>
          </div>
          <span class="px-1.5 py-0.2 rounded bg-surface-container-high text-[10px] font-mono text-accent">
            {{ $t('search.params.modesCount', { count: form.workModes.length }) }}
          </span>
        </div>
        <div class="flex items-center gap-1 pt-0.5 flex-wrap">
          <button
            v-for="m in [
              { key: 'remote', label: $t('search.params.modeRemote') },
              { key: 'hybrid', label: $t('search.params.modeHybrid') },
              { key: 'onsite', label: $t('search.params.modeOnsite') }
            ]"
            :key="m.key"
            :class="[
              'px-1.5 py-0.5 rounded text-[10.5px] font-mono border transition-colors',
              form.workModes.includes(m.key)
                ? 'bg-accent/10 border-accent/30 text-accent font-medium'
                : 'bg-surface-card border-border-subtle text-outline line-through opacity-60'
            ]"
            type="button"
            @click="toggleWorkMode(m.key)"
          >
            {{ m.label }}
          </button>
        </div>
        <p class="text-[10.5px] leading-tight min-h-[20px] flex items-center">
          <span class="text-on-surface-variant flex items-center gap-1">
            <span class="material-symbols-outlined text-[13px] shrink-0">domain</span>
            <span>{{ $t('search.params.modesDesc', { modes: form.workModes.join(', ') }) }}</span>
          </span>
        </p>
      </div>

      <!-- Parámetro 5: Anti-CAPTCHA -->
      <div class="flex flex-col justify-between gap-1.5 p-3 rounded-lg bg-surface-container border border-border-subtle group hover:border-border-muted transition-colors relative">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1">
            <label class="text-[11px] font-medium text-outline uppercase tracking-wider">{{ $t('search.params.antiCaptcha') }}</label>
            <div class="relative group/tip flex items-center cursor-help">
              <span class="material-symbols-outlined text-[14px] text-outline hover:text-on-surface">help</span>
              <div class="absolute bottom-full right-0 mb-2 hidden group-hover/tip:flex flex-col w-64 p-2.5 rounded-lg bg-surface-container-highest border border-border-muted shadow-lg z-50 text-[11px] text-on-surface leading-snug pointer-events-none">
                <div class="font-semibold text-accent mb-0.5 flex items-center gap-1">
                  <span class="material-symbols-outlined text-[13px]">security</span> {{ $t('search.params.cloudflareProtection') }}
                </div>
                {{ $t('search.params.captchaTip') }}
              </div>
            </div>
          </div>
          <span class="text-[10px] font-mono text-outline">{{ $t('search.params.botFilter') }}</span>
        </div>
        <div class="flex items-center justify-between pt-0.5">
          <span class="text-xs text-on-surface-variant font-medium">{{ $t('search.params.hideTurnstile') }}</span>
          <label class="relative inline-flex items-center cursor-pointer">
            <input
              v-model="form.allowCaptcha"
              class="sr-only peer"
              type="checkbox"
            />
            <div class="w-8 h-4 bg-surface-container-highest peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-accent"></div>
          </label>
        </div>
        <p class="text-[10.5px] leading-tight min-h-[20px] flex items-center">
          <span class="text-on-surface-variant flex items-center gap-1">
            <span class="material-symbols-outlined text-[13px] shrink-0">shield</span>
            <span>{{ form.allowCaptcha ? $t('search.params.captchaAllowed') : $t('search.params.captchaDiscarded') }}</span>
          </span>
        </p>
      </div>
    </div>

    <!-- BLOQUE INTERMEDIO: FILTRO POR PAÍSES ESPECÍFICOS (OPCIONAL) -->
    <div class="flex flex-col gap-2.5 pt-3 border-t border-border-subtle">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <span class="text-[12px] font-semibold text-on-surface tracking-tight">
            {{ $t('search.countries.title') }}
          </span>
          <span class="text-[11px] font-mono text-outline">
            ({{ form.countries.length }})
          </span>
          <span v-if="form.countries.length" class="text-[10px] font-mono px-1.5 py-0.2 rounded bg-accent/10 text-accent border border-accent/20">
            {{ $t('search.countries.activeFilter', { count: form.countries.length }) }}
          </span>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-[11px] text-outline font-mono">
            {{ $t('search.countries.subtitle') }}
          </span>
          <button
            v-if="form.countries.length"
            class="text-[11px] text-accent hover:underline font-mono ml-1"
            type="button"
            @click="clearCountries"
          >
            {{ $t('search.countries.clearAll') }}
          </button>
        </div>
      </div>

      <!-- Buscador con autocompletado y botón Agregar -->
      <div class="relative flex items-center gap-2">
        <div class="relative flex-1 flex items-center">
          <span class="material-symbols-outlined absolute left-3 text-[16px] text-outline">travel_explore</span>
          <input
            v-model="countrySearch"
            class="w-full pl-9 pr-8 py-2 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle placeholder:text-outline focus:outline-none focus:border-accent transition-colors shadow-sm"
            :placeholder="$t('search.countries.placeholder')"
            type="text"
            @blur="setTimeout(() => { isCountryDropdownOpen = false }, 200)"
            @focus="isCountryDropdownOpen = true"
            @keydown.enter.prevent="handleCountryEnter"
          />
          <button
            v-if="countrySearch"
            class="absolute right-2.5 text-outline hover:text-on-surface p-0.5 text-xs"
            type="button"
            @click="countrySearch = ''"
          >
            <span class="material-symbols-outlined text-[14px]">close</span>
          </button>
        </div>

        <!-- Botón Agregar país -->
        <button
          class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-surface-container-highest hover:bg-surface-container-high border border-border-muted text-xs font-medium text-on-surface transition-colors shadow-sm shrink-0"
          type="button"
          @click="handleCountryEnter"
        >
          <span class="material-symbols-outlined text-[15px] text-accent">add_location_alt</span>
          <span>{{ $t('search.countries.addBtn') }}</span>
        </button>

        <!-- Dropdown asistido de sugerencias de países disponibles en el scope actual -->
        <div
          v-if="isCountryDropdownOpen && filteredCountries.length"
          class="absolute top-full left-0 right-28 mt-1 max-h-48 overflow-y-auto rounded-lg bg-surface-container-highest border border-border-muted shadow-xl z-50 py-1"
        >
          <button
            v-for="country in filteredCountries.slice(0, 8)"
            :key="country.code"
            class="w-full text-left px-3 py-1.5 text-xs text-on-surface hover:bg-surface-container flex items-center justify-between transition-colors"
            type="button"
            @mousedown.prevent="addCountry(country.code)"
          >
            <span class="flex items-center gap-1.5">
              <span class="material-symbols-outlined text-[14px] text-outline">flag</span>
              <span>{{ country.name }}</span>
            </span>
            <span class="text-[10px] text-outline font-mono">{{ currentScopeLabel }}</span>
          </button>
        </div>
      </div>

      <!-- Chips de países seleccionados o mensaje vacío -->
      <div class="flex items-center flex-wrap gap-2 pt-0.5">
        <span
          v-for="(c, idx) in form.countries"
          :key="c"
          class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-container text-xs text-on-surface border border-accent/30 text-accent font-medium shadow-sm"
        >
          <span class="material-symbols-outlined text-[13px]">location_on</span>
          <span>{{ getCountryLabel(c) }}</span>
          <button
            :aria-label="$t('search.countries.deleteAria')"
            class="text-outline hover:text-on-surface p-0.5 transition-colors ml-0.5"
            type="button"
            @click="removeCountry(idx)"
          >
            <span class="material-symbols-outlined text-[13px] block">close</span>
          </button>
        </span>
        <p v-if="!form.countries.length" class="text-[11px] text-outline italic">
          {{ $t('search.countries.noCountries', { scope: currentScopeLabel }) }}
        </p>
      </div>
    </div>

    <!-- 3. BLOQUE INFERIOR: TÍTULOS Y ROLES ATS -->
    <div class="flex flex-col gap-3 pt-3 border-t border-border-subtle">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <span class="text-[12px] font-semibold text-on-surface tracking-tight">
            {{ $t('search.roles.title') }}
          </span>
          <span class="text-[11px] font-mono text-outline">{{ $t('search.roles.addedCount', { count: form.roles.length }) }}</span>
        </div>
        <span class="text-[11px] text-outline font-mono">{{ $t('search.roles.helpText') }}</span>
      </div>

      <div class="flex items-center gap-2">
        <div class="relative flex-1 flex items-center">
          <span class="material-symbols-outlined absolute left-3 text-[16px] text-outline">label</span>
          <input
            v-model="newRoleInput"
            class="w-full pl-9 pr-4 py-2 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle placeholder:text-outline focus:outline-none focus:border-accent transition-colors shadow-sm"
            :placeholder="$t('search.roles.placeholder')"
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
          <span>{{ $t('search.roles.addBtn') }}</span>
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
            :aria-label="$t('search.roles.deleteAria')"
            class="text-outline hover:text-on-surface p-0.5 transition-colors"
            type="button"
            @click="removeRoleTag(idx)"
          >
            <span class="material-symbols-outlined text-[13px] block">close</span>
          </button>
        </span>
        <span v-if="!form.roles.length" class="text-xs text-outline italic py-0.5">
          {{ $t('search.roles.noRoles') }}
        </span>
      </div>
    </div>
  </section>
</template>
