<script setup>
import { ref } from 'vue'

const props = defineProps({
  profile: {
    type: Object,
    required: true,
  },
})

const newCustomKey = ref('')
const newCustomVal = ref('')

function addCustomQa() {
  const k = newCustomKey.value.trim().toLowerCase()
  const v = newCustomVal.value.trim()
  if (!k || !v || !props.profile.open_questions) return
  props.profile.open_questions.custom_qa ??= {}
  props.profile.open_questions.custom_qa[k] = v
  newCustomKey.value = ''
  newCustomVal.value = ''
}

function removeCustomQa(key) {
  if (props.profile?.open_questions?.custom_qa) {
    delete props.profile.open_questions.custom_qa[key]
  }
}
</script>

<template>
  <div v-if="profile" class="flex flex-col gap-6">
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
          :placeholder="$t('profile.placeholders.motivation')"
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
          :placeholder="$t('profile.placeholders.experienceSummary')"
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
          :placeholder="$t('profile.placeholders.keyProject')"
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
          :placeholder="$t('profile.placeholders.additionalInfo')"
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
          :placeholder="$t('profile.placeholders.educationLevel')"
        />

        <label class="text-xs font-semibold text-on-surface pt-2">{{ $t('profile.sections.educationInstitution') }}</label>
        <span class="text-[11px] text-outline">{{ $t('profile.sections.educationInstitutionDesc') }}</span>
        <input
          v-model="profile.open_questions.education_institution"
          type="text"
          class="h-9 px-3 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle focus:outline-none focus:border-accent transition-colors font-sans"
          :placeholder="$t('profile.placeholders.educationInstitution')"
        />

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
          <div class="flex flex-col gap-1">
            <label class="text-xs font-semibold text-on-surface">{{ $t('profile.sections.educationStartYear') }}</label>
            <span class="text-[11px] text-outline">{{ $t('profile.sections.educationStartYearDesc') }}</span>
            <input
              v-model.number="profile.open_questions.education_start_year"
              type="number"
              :placeholder="$t('profile.placeholders.educationStartYear')"
              class="h-9 px-3 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle focus:outline-none focus:border-accent transition-colors font-sans"
            />
          </div>
          <div class="flex flex-col gap-1">
            <label class="text-xs font-semibold text-on-surface">{{ $t('profile.sections.educationEndYear') }}</label>
            <span class="text-[11px] text-outline">{{ $t('profile.sections.educationEndYearDesc') }}</span>
            <input
              v-model.number="profile.open_questions.education_end_year"
              type="number"
              :placeholder="$t('profile.placeholders.educationEndYear')"
              class="h-9 px-3 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle focus:outline-none focus:border-accent transition-colors font-sans"
            />
          </div>
        </div>
      </div>

      <!-- 6. Disponibilidad horaria y huso horario -->
      <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col gap-2">
        <label class="text-xs font-semibold text-on-surface">{{ $t('profile.sections.timezoneOverlap') }}</label>
        <span class="text-[11px] text-outline">{{ $t('profile.sections.timezoneOverlapDesc') }}</span>
        <input
          v-model="profile.open_questions.timezone_overlap"
          type="text"
          class="h-9 px-3 rounded-lg bg-surface-container text-xs text-on-surface border border-border-subtle focus:outline-none focus:border-accent transition-colors font-sans"
          :placeholder="$t('profile.placeholders.timezoneOverlap')"
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
      <div v-if="profile.open_questions?.custom_qa && Object.keys(profile.open_questions.custom_qa).length" class="flex flex-col gap-2.5">
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
</template>
