<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  profile: {
    type: Object,
    required: true,
  },
  baseCv: {
    type: Object,
    default: null,
  },
  uploadingCv: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['file-selected'])

const fileInputRef = ref(null)

const yesNo = ['Yes', 'No']
const platforms = ['ashby', 'greenhouse', 'lever', 'workable', 'breezy', 'recruitee', 'bamboohr']

const newRoleInput = ref('')
const newKeywordInput = ref('')
const newLocationInput = ref('')

const toNumber = (v) => (v === '' || v === null || v === undefined ? null : Number(v))
const formatSalaryNumber = (v) => {
  const n = Number(v)
  if (isNaN(n) || n <= 0) return '0'
  return n.toLocaleString('en-US')
}

function addTargetRole() {
  const val = newRoleInput.value.trim()
  if (!val || !props.profile?.search_criteria?.target_roles) return
  if (!props.profile.search_criteria.target_roles.includes(val)) {
    props.profile.search_criteria.target_roles.push(val)
  }
  newRoleInput.value = ''
}

function removeTargetRole(idx) {
  props.profile?.search_criteria?.target_roles?.splice(idx, 1)
}

function addKeyword() {
  const val = newKeywordInput.value.trim()
  if (!val || !props.profile?.search_criteria?.keywords) return
  if (!props.profile.search_criteria.keywords.includes(val)) {
    props.profile.search_criteria.keywords.push(val)
  }
  newKeywordInput.value = ''
}

function removeKeyword(idx) {
  props.profile?.search_criteria?.keywords?.splice(idx, 1)
}

function addLocation() {
  const val = newLocationInput.value.trim()
  if (!val || !props.profile?.search_criteria?.location_keywords) return
  if (!props.profile.search_criteria.location_keywords.includes(val)) {
    props.profile.search_criteria.location_keywords.push(val)
  }
  newLocationInput.value = ''
}

function removeLocation(idx) {
  props.profile?.search_criteria?.location_keywords?.splice(idx, 1)
}

const LOCATION_SUGGESTIONS = [
  { label: 'Montevideo, Uruguay', city: 'Montevideo', country: 'Uruguay' },
  { label: 'Punta del Este, Uruguay', city: 'Punta del Este', country: 'Uruguay' },
  { label: 'Buenos Aires, Argentina', city: 'Buenos Aires', country: 'Argentina' },
  { label: 'Córdoba, Argentina', city: 'Córdoba', country: 'Argentina' },
  { label: 'Rosario, Argentina', city: 'Rosario', country: 'Argentina' },
  { label: 'Santiago, Chile', city: 'Santiago', country: 'Chile' },
  { label: 'São Paulo, Brasil', city: 'São Paulo', country: 'Brasil' },
  { label: 'Río de Janeiro, Brasil', city: 'Río de Janeiro', country: 'Brasil' },
  { label: 'Bogotá, Colombia', city: 'Bogotá', country: 'Colombia' },
  { label: 'Medellín, Colombia', city: 'Medellín', country: 'Colombia' },
  { label: 'Lima, Perú', city: 'Lima', country: 'Perú' },
  { label: 'Ciudad de México, México', city: 'Ciudad de México', country: 'México' },
  { label: 'Guadalajara, México', city: 'Guadalajara', country: 'México' },
  { label: 'Madrid, España', city: 'Madrid', country: 'España' },
  { label: 'Barcelona, España', city: 'Barcelona', country: 'España' },
  { label: 'Berlín, Alemania', city: 'Berlín', country: 'Alemania' },
  { label: 'Múnich, Alemania', city: 'Múnich', country: 'Alemania' },
  { label: 'Frankfurt, Alemania', city: 'Frankfurt', country: 'Alemania' },
  { label: 'Londres, Reino Unido', city: 'Londres', country: 'Reino Unido' },
  { label: 'París, Francia', city: 'París', country: 'Francia' },
  { label: 'Ámsterdam, Países Bajos', city: 'Ámsterdam', country: 'Países Bajos' },
  { label: 'Lisboa, Portugal', city: 'Lisboa', country: 'Portugal' },
  { label: 'Roma, Italia', city: 'Roma', country: 'Italia' },
  { label: 'Dublín, Irlanda', city: 'Dublín', country: 'Irlanda' },
  { label: 'Varsovia, Polonia', city: 'Varsovia', country: 'Polonia' },
  { label: 'Estocolmo, Suecia', city: 'Estocolmo', country: 'Suecia' },
  { label: 'Zúrich, Suiza', city: 'Zúrich', country: 'Suiza' },
  { label: 'Nueva York, Estados Unidos', city: 'New York', country: 'Estados Unidos' },
  { label: 'San Francisco, Estados Unidos', city: 'San Francisco', country: 'Estados Unidos' },
  { label: 'Miami, Estados Unidos', city: 'Miami', country: 'Estados Unidos' },
  { label: 'Toronto, Canadá', city: 'Toronto', country: 'Canadá' },
  { label: 'Sídney, Australia', city: 'Sydney', country: 'Australia' },
  { label: 'Tokio, Japón', city: 'Tokyo', country: 'Japón' },
]

const isLocationDropdownOpen = ref(false)

const filteredLocationSuggestions = computed(() => {
  const q = (props.profile?.personal_info?.location || '').trim().toLowerCase()
  if (!q) return LOCATION_SUGGESTIONS.slice(0, 8)
  return LOCATION_SUGGESTIONS.filter(
    (item) => item.label.toLowerCase().includes(q) || item.city.toLowerCase().includes(q) || item.country.toLowerCase().includes(q)
  ).slice(0, 8)
})

function selectLocationSuggestion(item) {
  if (!props.profile?.personal_info) return
  props.profile.personal_info.location = item.label
  props.profile.personal_info.city = item.city
  props.profile.personal_info.country = item.country
  isLocationDropdownOpen.value = false
}

function togglePlatform(pl) {
  const list = props.profile?.ats_settings?.enabled_platforms
  if (!list) return
  const idx = list.indexOf(pl)
  if (idx > -1) {
    list.splice(idx, 1)
  } else {
    list.push(pl)
  }
}

function onFileChange(event) {
  emit('file-selected', event)
}
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
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
                {{ baseCv?.filename || 'Master_Resume.pdf' }}
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
              @change="onFileChange"
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
                :placeholder="$t('profile.placeholders.fullName')"
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
                :placeholder="$t('profile.placeholders.email')"
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
                  :placeholder="$t('profile.placeholders.phone')"
                  type="text"
                />
              </div>
            </div>
            <div class="flex flex-col gap-1.5 relative">
              <label class="text-xs text-on-surface-variant font-medium">
                {{ $t('profile.sections.currentLocation') }} <span class="text-accent">*</span>
              </label>
              <div class="relative flex items-center">
                <span class="material-symbols-outlined text-[16px] text-outline absolute left-2.5 pointer-events-none">pin_drop</span>
                <input
                  v-model="profile.personal_info.location"
                  class="h-9 pl-8 pr-3 w-full rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                  :placeholder="$t('profile.sections.locationSearchPlaceholder')"
                  type="text"
                  @blur="setTimeout(() => { isLocationDropdownOpen = false }, 200)"
                  @focus="isLocationDropdownOpen = true"
                />
                <!-- Dropdown asistido de sugerencias de ubicación estilo LinkedIn -->
                <div
                  v-if="isLocationDropdownOpen && filteredLocationSuggestions.length"
                  class="absolute top-full left-0 right-0 mt-1 max-h-48 overflow-y-auto rounded-lg bg-surface-container-highest border border-border-muted shadow-xl z-50 py-1"
                >
                  <button
                    v-for="item in filteredLocationSuggestions"
                    :key="item.label"
                    class="w-full text-left px-3 py-1.5 text-xs text-on-surface hover:bg-surface-container flex items-center justify-between transition-colors"
                    type="button"
                    @mousedown.prevent="selectLocationSuggestion(item)"
                  >
                    <span class="flex items-center gap-1.5">
                      <span class="material-symbols-outlined text-[14px] text-outline">location_city</span>
                      <span>{{ item.label }}</span>
                    </span>
                    <span class="text-[10px] text-outline font-mono">{{ item.country }}</span>
                  </button>
                </div>
              </div>
              <p class="text-[11px] text-outline leading-tight">
                {{ $t('profile.sections.locationHelper') }}
              </p>
            </div>
          </div>

          <!-- Ciudad & País (detectados / manual) -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.city') }}</label>
              <input
                v-model="profile.personal_info.city"
                class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                :placeholder="$t('profile.placeholders.city')"
                type="text"
              />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.country') }}</label>
              <input
                v-model="profile.personal_info.country"
                class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                :placeholder="$t('profile.placeholders.country')"
                type="text"
              />
            </div>
          </div>

          <!-- Redes Sociales y Links -->
          <div class="flex flex-col gap-3 pt-2 border-t border-border-subtle">
            <span class="text-[11px] font-semibold text-outline tracking-wider uppercase">{{ $t('profile.sections.linksSection') }}</span>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div class="flex flex-col gap-1.5">
                <label class="text-xs text-on-surface-variant font-medium">LinkedIn</label>
                <div class="relative flex items-center">
                  <span class="material-symbols-outlined text-[15px] text-outline absolute left-2.5 pointer-events-none">link</span>
                  <input
                    v-model="profile.personal_info.linkedin_url"
                    class="h-9 pl-8 pr-3 w-full rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                    placeholder="https://linkedin.com/in/..."
                    type="url"
                  />
                </div>
              </div>

              <div class="flex flex-col gap-1.5">
                <label class="text-xs text-on-surface-variant font-medium">GitHub</label>
                <div class="relative flex items-center">
                  <span class="material-symbols-outlined text-[15px] text-outline absolute left-2.5 pointer-events-none">terminal</span>
                  <input
                    v-model="profile.personal_info.github_url"
                    class="h-9 pl-8 pr-3 w-full rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                    placeholder="https://github.com/..."
                    type="url"
                  />
                </div>
              </div>

              <div class="flex flex-col gap-1.5">
                <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.portfolio') }}</label>
                <div class="relative flex items-center">
                  <span class="material-symbols-outlined text-[15px] text-outline absolute left-2.5 pointer-events-none">public</span>
                  <input
                    v-model="profile.personal_info.portfolio_url"
                    class="h-9 pl-8 pr-3 w-full rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                    placeholder="https://..."
                    type="url"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Empresa Actual & Años de Experiencia -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-border-subtle">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.currentCompany') }}</label>
              <input
                v-model="profile.personal_info.current_company"
                class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                :placeholder="$t('profile.placeholders.currentCompany')"
                type="text"
              />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.yearsOfExp') }}</label>
              <input
                :value="profile.personal_info.years_of_experience"
                class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                placeholder="7"
                type="number"
                min="0"
                step="1"
                @input="profile.personal_info.years_of_experience = toNumber($event.target.value)"
              />
            </div>
          </div>

          <!-- Permiso de Trabajo / Visa Sponsorship -->
          <div class="flex items-center justify-between p-3 rounded-lg bg-surface-container/40 border border-border-subtle">
            <div class="flex flex-col">
              <span class="text-xs font-medium text-on-surface">{{ $t('profile.sections.visaReq') }}</span>
              <span class="text-[11px] text-outline">{{ $t('profile.sections.visaReqDesc') }}</span>
            </div>
            <div class="flex items-center gap-2">
              <button
                v-for="opt in yesNo"
                :key="opt"
                type="button"
                :class="[
                  'px-3 py-1 rounded text-xs font-mono font-medium transition-colors border',
                  profile.personal_info.requires_us_visa_sponsorship === opt
                    ? 'bg-accent/20 border-accent text-accent'
                    : 'bg-surface-container border-border-subtle text-on-surface-variant hover:text-on-surface'
                ]"
                @click="profile.personal_info.requires_us_visa_sponsorship = opt"
              >
                {{ opt }}
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 3. Card: Información Demográfica y EEO -->
      <section class="bg-surface-card border border-border-subtle rounded-xl p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between pb-1">
          <div class="flex items-center gap-2.5">
            <span class="material-symbols-outlined text-accent text-[20px]">diversity_3</span>
            <div>
              <h2 class="text-sm font-semibold text-on-surface">{{ $t('profile.sections.eeoTitle') }}</h2>
              <p class="font-mono text-[11px] text-outline">{{ $t('profile.sections.eeoDesc') }}</p>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- Género -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.gender') }}</label>
            <select
              v-model="profile.personal_info.gender"
              class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            >
              <option value="male">{{ $t('profile.sections.genderOptions.male') }}</option>
              <option value="female">{{ $t('profile.sections.genderOptions.female') }}</option>
              <option value="non_binary">{{ $t('profile.sections.genderOptions.non_binary') }}</option>
              <option value="decline">{{ $t('profile.sections.genderOptions.decline') }}</option>
            </select>
          </div>

          <!-- Raza / Etnia -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.race') }}</label>
            <select
              v-model="profile.personal_info.race"
              class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            >
              <option value="hispanic_latino">{{ $t('profile.sections.raceOptions.hispanic_latino') }}</option>
              <option value="white">{{ $t('profile.sections.raceOptions.white') }}</option>
              <option value="black">{{ $t('profile.sections.raceOptions.black') }}</option>
              <option value="asian">{{ $t('profile.sections.raceOptions.asian') }}</option>
              <option value="two_or_more">{{ $t('profile.sections.raceOptions.two_or_more') }}</option>
              <option value="decline">{{ $t('profile.sections.raceOptions.decline') }}</option>
            </select>
          </div>

          <!-- Estado de Veterano -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.veteran') }}</label>
            <select
              v-model="profile.personal_info.veteran_status"
              class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            >
              <option value="not_veteran">{{ $t('profile.sections.veteranOptions.not_veteran') }}</option>
              <option value="veteran">{{ $t('profile.sections.veteranOptions.veteran') }}</option>
              <option value="decline">{{ $t('profile.sections.veteranOptions.decline') }}</option>
            </select>
          </div>

          <!-- Estado de Discapacidad -->
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.disability') }}</label>
            <select
              v-model="profile.personal_info.disability_status"
              class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            >
              <option value="no">{{ $t('profile.sections.disabilityOptions.no') }}</option>
              <option value="yes">{{ $t('profile.sections.disabilityOptions.yes') }}</option>
              <option value="decline">{{ $t('profile.sections.disabilityOptions.decline') }}</option>
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
            <span v-if="!profile.search_criteria.target_roles?.length" class="text-xs text-outline italic self-center px-1">
              {{ $t('profile.sections.noRolesConfigured') }}
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
          <div class="flex flex-wrap gap-1 p-2 rounded-lg bg-surface-container border border-border-subtle min-h-[38px] max-h-36 overflow-y-auto">
            <span
              v-for="(kw, idx) in profile.search_criteria.keywords"
              :key="kw"
              class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-container-high text-on-surface text-[11px] font-mono border border-border-subtle"
            >
              {{ kw }}
              <button
                class="text-outline hover:text-rose-400 transition-colors"
                type="button"
                @click="removeKeyword(idx)"
              >
                ✕
              </button>
            </span>
            <span v-if="!profile.search_criteria.keywords?.length" class="text-xs text-outline italic self-center px-1">
              {{ $t('profile.sections.noKeywordsConfigured') }}
            </span>
          </div>
          <div class="flex items-center gap-2 mt-1">
            <input
              v-model="newKeywordInput"
              class="h-8 px-2.5 flex-1 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
              :placeholder="$t('profile.sections.keywordsPlaceholder')"
              type="text"
              @keyup.enter="addKeyword"
            />
            <button
              class="h-8 px-3 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-xs font-medium border border-border-subtle transition-colors"
              type="button"
              @click="addKeyword"
            >
              {{ $t('profile.sections.addKeywordBtn') }}
            </button>
          </div>
        </div>

        <!-- Keywords de Ubicación -->
        <div class="flex flex-col gap-2">
          <div class="flex items-center justify-between">
            <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.locationKeywords') }}</label>
            <span class="font-mono text-[10px] text-outline">{{ profile.search_criteria.location_keywords?.length || 0 }} tags</span>
          </div>
          <div class="flex flex-wrap gap-1 p-2 rounded-lg bg-surface-container border border-border-subtle min-h-[38px]">
            <span
              v-for="(loc, idx) in profile.search_criteria.location_keywords"
              :key="loc"
              class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-container-high text-on-surface text-[11px] font-mono border border-border-subtle"
            >
              {{ loc }}
              <button
                class="text-outline hover:text-rose-400 transition-colors"
                type="button"
                @click="removeLocation(idx)"
              >
                ✕
              </button>
            </span>
            <span v-if="!profile.search_criteria.location_keywords?.length" class="text-xs text-outline italic self-center px-1">
              {{ $t('profile.sections.noLocationKeywords') }}
            </span>
          </div>
          <div class="flex items-center gap-2 mt-1">
            <input
              v-model="newLocationInput"
              class="h-8 px-2.5 flex-1 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
              :placeholder="$t('profile.sections.locationKeywordsPlaceholder')"
              type="text"
              @keyup.enter="addLocation"
            />
            <button
              class="h-8 px-3 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-xs font-medium border border-border-subtle transition-colors"
              type="button"
              @click="addLocation"
            >
              {{ $t('profile.sections.addLocationBtn') }}
            </button>
          </div>
        </div>

        <!-- Experiencia Máxima Requerida para Escaneo -->
        <div class="flex flex-col gap-1.5 pt-2 border-t border-border-subtle">
          <div class="flex items-center justify-between">
            <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.maxExp') }}</label>
            <span class="font-mono text-xs text-accent">
              {{ profile.search_criteria.max_years_of_experience ? `${profile.search_criteria.max_years_of_experience} ${$t('profile.sections.yearsShort')}` : $t('profile.sections.unlimited') }}
            </span>
          </div>
          <input
            :value="profile.search_criteria.max_years_of_experience"
            class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            placeholder="7"
            type="number"
            min="0"
            max="30"
            @input="profile.search_criteria.max_years_of_experience = toNumber($event.target.value)"
          />
          <p class="text-[11px] text-outline">
            {{ $t('profile.sections.maxExpDesc') }}
          </p>
        </div>
      </section>

      <!-- 5. Card: Compensación y Preferencias de Empleo -->
      <section class="bg-surface-card border border-border-subtle rounded-xl p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between pb-1">
          <div class="flex items-center gap-2.5">
            <span class="material-symbols-outlined text-accent text-[20px]">payments</span>
            <div>
              <h2 class="text-sm font-semibold text-on-surface">{{ $t('profile.sections.compensation') }}</h2>
              <p class="font-mono text-[11px] text-outline">{{ $t('profile.sections.compensationDesc') }}</p>
            </div>
          </div>
        </div>

        <div class="flex flex-col gap-4">
          <!-- Salario Dependiente vs Contractor -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">
                {{ $t('profile.sections.salaryDependent') }}
              </label>
              <div class="relative flex items-center">
                <span class="text-outline text-xs absolute left-3 font-mono pointer-events-none">$</span>
                <input
                  :value="profile.preferences.dependent_salary_usd"
                  class="h-9 pl-7 pr-3 w-full rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                  placeholder="3000"
                  type="number"
                  min="0"
                  step="100"
                  @input="profile.preferences.dependent_salary_usd = toNumber($event.target.value)"
                />
              </div>
              <span class="text-[10px] text-outline font-mono">
                ${{ formatSalaryNumber(profile.preferences.dependent_salary_usd) }} USD / {{ profile.preferences.salary_period || 'monthly' }}
              </span>
            </div>

            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">
                {{ $t('profile.sections.salaryContractor') }}
              </label>
              <div class="relative flex items-center">
                <span class="text-outline text-xs absolute left-3 font-mono pointer-events-none">$</span>
                <input
                  :value="profile.preferences.contractor_salary_usd"
                  class="h-9 pl-7 pr-3 w-full rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                  placeholder="4500"
                  type="number"
                  min="0"
                  step="100"
                  @input="profile.preferences.contractor_salary_usd = toNumber($event.target.value)"
                />
              </div>
              <span class="text-[10px] text-outline font-mono">
                ${{ formatSalaryNumber(profile.preferences.contractor_salary_usd) }} USD / {{ profile.preferences.salary_period || 'monthly' }}
              </span>
            </div>
          </div>

          <!-- Período de Salario & Disponibilidad -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.salaryPeriod') }}</label>
              <select
                v-model="profile.preferences.salary_period"
                class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
              >
                <option value="monthly">{{ $t('profile.sections.salaryPeriods.monthly') }}</option>
                <option value="annual">{{ $t('profile.sections.salaryPeriods.annual') }}</option>
                <option value="hourly">{{ $t('profile.sections.salaryPeriods.hourly') }}</option>
              </select>
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.noticePeriod') }}</label>
              <input
                v-model="profile.preferences.notice_period"
                class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                :placeholder="$t('profile.placeholders.noticePeriod')"
                type="text"
              />
            </div>
          </div>

          <!-- Nivel de Inglés & Idioma Nativo -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.englishLevel') }}</label>
              <input
                v-model="profile.preferences.english_level"
                class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                placeholder="Fluent / C1 / Professional"
                type="text"
              />
            </div>
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.nativeLanguage') }}</label>
              <input
                v-model="profile.preferences.native_language"
                class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
                placeholder="Spanish"
                type="text"
              />
            </div>
          </div>
        </div>
      </section>

      <!-- 6. Card: Portales ATS y Preferencias de Automatización -->
      <section class="bg-surface-card border border-border-subtle rounded-xl p-5 flex flex-col gap-4">
        <div class="flex items-center justify-between pb-1">
          <div class="flex items-center gap-2.5">
            <span class="material-symbols-outlined text-accent text-[20px]">hub</span>
            <div>
              <h2 class="text-sm font-semibold text-on-surface">{{ $t('profile.sections.atsPlatforms') }}</h2>
              <p class="font-mono text-[11px] text-outline">{{ $t('profile.sections.atsPlatformsDesc') }}</p>
            </div>
          </div>
        </div>

        <!-- Selector de Portales ATS -->
        <div class="flex flex-wrap gap-2">
          <button
            v-for="pl in platforms"
            :key="pl"
            type="button"
            :class="[
              'px-3 py-1.5 rounded-lg text-xs font-mono font-medium transition-all border flex items-center gap-2',
              profile.ats_settings.enabled_platforms?.includes(pl)
                ? 'bg-accent/15 border-accent text-on-surface'
                : 'bg-surface-container border-border-subtle text-outline hover:text-on-surface-variant'
            ]"
            @click="togglePlatform(pl)"
          >
            <span
              class="w-1.5 h-1.5 rounded-full"
              :class="profile.ats_settings.enabled_platforms?.includes(pl) ? 'bg-accent' : 'bg-outline'"
            ></span>
            <span class="capitalize">{{ pl }}</span>
          </button>
        </div>

        <!-- Toggles de Automatización -->
        <div class="flex flex-col gap-3 pt-3 border-t border-border-subtle">
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
</template>
