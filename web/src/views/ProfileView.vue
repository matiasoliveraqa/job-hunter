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
  data.personal_info.years_of_experience ??= null
  data.personal_info.gender ??= ''
  data.personal_info.race ??= ''
  data.personal_info.veteran_status ??= ''
  data.personal_info.disability_status ??= ''
  data.search_criteria.max_years_of_experience ??= null
  data.preferences.dependent_salary_usd ??= data.preferences.desired_salary_usd ?? null
  data.preferences.contractor_salary_usd ??= null
  data.preferences.english_level ??= ''
  profile.value = data
  original.value = JSON.stringify(data)
}

const baseCv = ref(null)
const uploadingCv = ref(false)
const fileInputRef = ref(null)

async function loadBaseCv() {
  try {
    baseCv.value = await api.getBaseCv()
  } catch {
    // ignorar
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

onMounted(() => {
  load()
  loadBaseCv()
})

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

      notify('CV cargado con éxito. Se autocompletaron tus datos a partir del documento. Revisa los campos y pulsa Guardar.')
    } else {
      notify('CV guardado en my_cv/ como documento base.')
    }
  } catch (err) {
    notify('Error al procesar el CV: ' + err.message, 'error')
  } finally {
    uploadingCv.value = false
  }
}

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

      <v-card class="mb-4" variant="outlined">
        <v-card-item>
          <template #prepend>
            <v-avatar color="primary" variant="tonal" rounded>
              <v-icon icon="mdi-file-pdf-box" size="26" />
            </v-avatar>
          </template>
          <v-card-title class="text-subtitle-1 font-weight-bold">
            CV Base del Candidato
          </v-card-title>
          <v-card-subtitle>
            Documento maestro guardado en <code>my_cv/</code>. Se utiliza como base para adaptar cada postulación y para autocompletar tu perfil.
          </v-card-subtitle>
        </v-card-item>

        <v-card-text class="pt-0">
          <div v-if="baseCv?.exists" class="d-flex flex-wrap align-center ga-3 mb-3 pa-3 rounded bg-surface-variant">
            <v-icon icon="mdi-file-check" color="success" />
            <div>
              <span class="font-weight-medium">{{ baseCv.filename }}</span>
              <span class="text-caption text-medium-emphasis ml-2">({{ Math.round(baseCv.sizeBytes / 1024) }} KB)</span>
            </div>
            <v-spacer />
            <v-btn
              variant="text"
              size="small"
              prepend-icon="mdi-eye"
              :href="baseCv.url"
              target="_blank"
            >
              Ver CV actual
            </v-btn>
          </div>
          <div v-else class="text-caption text-medium-emphasis mb-3">
            No hay ningún CV base cargado aún en <code>my_cv/</code>.
          </div>

          <div class="d-flex align-center ga-3">
            <input
              ref="fileInputRef"
              type="file"
              accept=".pdf,.html,.md,.txt"
              style="display: none"
              @change="onFileSelected"
            />
            <v-btn
              color="primary"
              variant="flat"
              prepend-icon="mdi-upload"
              :loading="uploadingCv"
              @click="fileInputRef?.click()"
            >
              {{ baseCv?.exists ? 'Cargar nuevo CV y actualizar datos' : 'Cargar CV base' }}
            </v-btn>
            <span class="text-caption text-medium-emphasis">
              Formatos aceptados: PDF, HTML o Markdown. El agente extraerá tu información automáticamente.
            </span>
          </div>
        </v-card-text>
      </v-card>

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
              <v-text-field
                :model-value="profile.personal_info.years_of_experience"
                label="Años de experiencia profesional (opcional)"
                type="number"
                min="0"
                @update:model-value="profile.personal_info.years_of_experience = toNumber($event)"
              />
              <v-select
                v-model="profile.personal_info.requires_us_visa_sponsorship"
                :items="yesNo"
                label="¿Requiere sponsorship de visa de EE. UU.?"
              />
              <v-divider class="my-3" />
              <div class="text-caption text-medium-emphasis mb-2 font-weight-bold">
                DATOS DEMOGRÁFICOS / EEO (OPCIONAL PARA FORMULARIOS ATS)
              </div>
              <v-row density="compact">
                <v-col cols="12" sm="6">
                  <v-text-field v-model="profile.personal_info.gender" label="Género (Gender)" />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-text-field v-model="profile.personal_info.race" label="Etnia / Raza (Race)" />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-text-field v-model="profile.personal_info.veteran_status" label="Estatus de veterano (Veteran status)" />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-text-field v-model="profile.personal_info.disability_status" label="Discapacidad (Disability status)" />
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <v-card title="Preferencias" subtitle="Se usan en las preguntas de salario y disponibilidad de los formularios">
            <v-card-text>
              <v-row>
                <v-col cols="12" sm="4">
                  <v-text-field
                    :model-value="profile.preferences.dependent_salary_usd"
                    label="Salario Dependiente (USD)"
                    type="number"
                    min="0"
                    hint="Por defecto si no aclara modalidad"
                    persistent-hint
                    @update:model-value="profile.preferences.dependent_salary_usd = toNumber($event)"
                  />
                </v-col>
                <v-col cols="12" sm="4">
                  <v-text-field
                    :model-value="profile.preferences.contractor_salary_usd"
                    label="Salario Contractor (USD)"
                    type="number"
                    min="0"
                    hint="Si la oferta dice Contractor / B2B"
                    persistent-hint
                    @update:model-value="profile.preferences.contractor_salary_usd = toNumber($event)"
                  />
                </v-col>
                <v-col cols="12" sm="4">
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
              <v-row class="mt-1">
                <v-col cols="12" sm="6">
                  <v-text-field
                    :model-value="profile.search_criteria.max_years_of_experience"
                    label="Tope máx. años exp. (opcional)"
                    type="number"
                    min="0"
                    hint="Vacío = sin límite de años"
                    persistent-hint
                    @update:model-value="profile.search_criteria.max_years_of_experience = toNumber($event)"
                  />
                </v-col>
                <v-col cols="12" sm="6">
                  <v-text-field
                    :model-value="profile.search_criteria.min_salary_usd"
                    label="Salario mínimo (USD)"
                    type="number"
                    min="0"
                    @update:model-value="profile.search_criteria.min_salary_usd = toNumber($event)"
                  />
                </v-col>
              </v-row>
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
