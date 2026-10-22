<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api.js'

const profile = ref(null)
const original = ref('')
const loading = ref(true)
const saving = ref(false)
const snack = reactive({ show: false, text: '', color: 'success' })

const yesNo = ['Yes', 'No']
const periods = [
  { value: 'monthly', title: 'Mensual' },
  { value: 'annual', title: 'Anual' },
]
const platforms = ['ashby', 'greenhouse', 'lever']

const dirty = computed(() => profile.value && JSON.stringify(profile.value) !== original.value)

function notify(text, color = 'success') {
  Object.assign(snack, { show: true, text, color })
}

function adopt(data) {
  // text fields that may be null in the file are edited as empty strings
  data.personal_info.github_url ??= ''
  data.personal_info.portfolio_url ??= ''
  data.personal_info.current_company ??= ''
  data.preferences.english_level ??= ''
  profile.value = data
  original.value = JSON.stringify(data)
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
onMounted(load)

async function save() {
  saving.value = true
  try {
    adopt(await api.saveProfile(profile.value))
    notify('Perfil guardado en config/profile.json')
  } catch (e) {
    notify(e.message, 'error')
  } finally {
    saving.value = false
  }
}

const reset = () => adopt(JSON.parse(original.value))
const toNumber = (v) => (v === '' || v === null || v === undefined ? null : Number(v))
</script>

<template>
  <v-container fluid class="pa-6">
    <div class="d-flex align-center mb-4">
      <h1 class="text-h5">Mi perfil</h1>
      <v-spacer />
      <v-btn variant="text" :disabled="!dirty || saving" @click="reset">Descartar cambios</v-btn>
      <v-btn color="primary" prepend-icon="mdi-content-save" :disabled="!dirty" :loading="saving" class="ml-2" @click="save">
        Guardar
      </v-btn>
    </div>

    <v-progress-linear v-if="loading" indeterminate />

    <v-form v-if="profile" @submit.prevent="save">
      <v-alert type="info" variant="tonal" density="compact" class="mb-4">
        Estos datos son los que el aplicador usa para rellenar formularios y los que el agente usa para filtrar ofertas.
        Se guardan en <code>config/profile.json</code> (fuera de git), con copia de seguridad en <code>output/backups/</code>.
      </v-alert>

      <v-row>
        <v-col cols="12" lg="6">
          <v-card title="Datos personales" class="mb-4">
            <v-card-text>
              <v-text-field v-model="profile.personal_info.full_name" label="Nombre completo *" />
              <v-text-field v-model="profile.personal_info.email" label="Email *" type="email" />
              <v-text-field v-model="profile.personal_info.phone" label="Teléfono (con código de país) *" />
              <v-text-field v-model="profile.personal_info.location" label="Ubicación *" />
              <v-text-field v-model="profile.personal_info.linkedin_url" label="LinkedIn *" />
              <v-text-field v-model="profile.personal_info.github_url" label="GitHub" />
              <v-text-field v-model="profile.personal_info.portfolio_url" label="Portfolio / sitio web" />
              <v-text-field v-model="profile.personal_info.current_company" label="Empresa actual" />
              <v-select
                v-model="profile.personal_info.requires_us_visa_sponsorship"
                :items="yesNo"
                label="¿Requiere sponsorship de visa de EE. UU.?"
              />
            </v-card-text>
          </v-card>

          <v-card title="Preferencias" subtitle="Se usan en las preguntas de salario y disponibilidad de los formularios">
            <v-card-text>
              <v-row>
                <v-col cols="12" sm="6">
                  <v-text-field
                    :model-value="profile.preferences.desired_salary_usd"
                    label="Salario deseado (USD)"
                    type="number"
                    min="0"
                    @update:model-value="profile.preferences.desired_salary_usd = toNumber($event)"
                  />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-select v-model="profile.preferences.salary_period" :items="periods" label="Período" />
                </v-col>
              </v-row>
              <v-text-field
                v-model="profile.preferences.notice_period"
                label="Disponibilidad / preaviso *"
                hint="Ej.: Immediately, 2 weeks, 1 month"
                persistent-hint
              />
              <v-text-field v-model="profile.preferences.english_level" label="Nivel de inglés" class="mt-3" />
              <v-select
                v-model="profile.preferences.legally_authorized_to_work"
                :items="yesNo"
                label="¿Autorizado a trabajar legalmente?"
              />
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" lg="6">
          <v-card title="Criterios de búsqueda" class="mb-4">
            <v-card-text>
              <v-combobox
                v-model="profile.search_criteria.target_roles"
                label="Roles objetivo"
                multiple
                chips
                closable-chips
                hint="Escribe un rol y pulsa Enter"
                persistent-hint
              />
              <v-combobox
                v-model="profile.search_criteria.keywords"
                label="Keywords técnicas"
                multiple
                chips
                closable-chips
                class="mt-3"
                hint="Solo tecnologías que figuran en tu CV"
                persistent-hint
              />
              <v-combobox
                v-model="profile.search_criteria.location_keywords"
                label="Ubicaciones aceptadas"
                multiple
                chips
                closable-chips
                class="mt-3"
              />
              <v-text-field
                :model-value="profile.search_criteria.min_salary_usd"
                label="Salario mínimo (USD)"
                type="number"
                min="0"
                class="mt-3"
                @update:model-value="profile.search_criteria.min_salary_usd = toNumber($event)"
              />
            </v-card-text>
          </v-card>

          <v-card title="Plataformas y navegador">
            <v-card-text>
              <div class="text-subtitle-2 mb-1">Plataformas ATS a escanear</div>
              <div class="d-flex flex-wrap">
                <v-checkbox
                  v-for="pl in platforms"
                  :key="pl"
                  v-model="profile.ats_settings.enabled_platforms"
                  :label="pl"
                  :value="pl"
                  density="compact"
                  hide-details
                  class="mr-4"
                />
              </div>
              <v-switch
                v-model="profile.ats_settings.auto_upload_resume"
                label="Adjuntar el CV automáticamente"
                color="primary"
                hide-details
                density="compact"
                class="mt-2"
              />
              <v-switch v-model="profile.ats_settings.stealth_mode" label="Modo sigiloso del navegador" color="primary" hide-details density="compact" />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </v-form>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="4000">{{ snack.text }}</v-snackbar>
  </v-container>
</template>
