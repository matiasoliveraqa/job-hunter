<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api, STATUS_META } from '../api.js'

const items = ref([])
const files = ref([])
const loading = ref(false)
const search = ref('')
const snack = reactive({ show: false, text: '', color: 'success' })

const expanded = ref([])
const headers = [
  { title: 'Empresa', key: 'company' },
  { title: 'Puesto', key: 'role' },
  { title: 'Fecha', key: 'appliedAt' },
  { title: 'Estado', key: 'status' },
  { title: 'Motivo / notas', key: 'reason', sortable: false },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

const counts = computed(() =>
  Object.keys(STATUS_META).map((key) => ({
    key,
    ...STATUS_META[key],
    count: items.value.filter((a) => !a.demo && a.status === key).length,
  })),
)

const filterStatus = ref(null)

function toggleStatusFilter(key) {
  filterStatus.value = filterStatus.value === key ? null : key
}

const totalCount = computed(() => items.value.filter((a) => !a.demo).length)

const filteredItems = computed(() => {
  if (!filterStatus.value) return items.value
  return items.value.filter((a) => a.status === filterStatus.value)
})

const demoCount = computed(() => items.value.filter((a) => a.demo).length)
const statusItems = Object.entries(STATUS_META).map(([value, m]) => ({ value, title: m.title }))
const cvItems = computed(() => files.value.map((f) => ({ value: `${f.dir}/${f.name}`, title: `${f.dir}/${f.name}` })))

function notify(text, color = 'success') {
  Object.assign(snack, { show: true, text, color })
}

async function load() {
  loading.value = true
  try {
    ;[items.value, files.value] = await Promise.all([api.listApplications(), api.listFiles()])
  } catch (e) {
    notify(e.message, 'error')
  } finally {
    loading.value = false
  }
}
onMounted(load)

// ---- change status ----
const statusDialog = reactive({ show: false, item: null, status: 'applied', reason: '', notes: '' })

function openStatus(item) {
  Object.assign(statusDialog, { show: true, item, status: item.status, reason: item.reason, notes: item.notes })
}

async function saveStatus() {
  const needsReason = statusDialog.status === 'rejected' && !statusDialog.reason.trim()
  if (needsReason) return notify('Indica el motivo del rechazo', 'error')
  try {
    const updated = await api.updateApplication(statusDialog.item.id, {
      status: statusDialog.status,
      reason: statusDialog.reason,
      notes: statusDialog.notes,
    })
    Object.assign(statusDialog.item, updated)
    statusDialog.show = false
  } catch (e) {
    notify(e.message, 'error')
  }
}

// ---- new application ----
const emptyForm = () => ({ company: '', role: '', url: '', cv: '' })
const newDialog = reactive({ show: false, form: emptyForm() })
const newFormOpened = ref(false)

async function launchForm() {
  try {
    await api.launchApply({
      url: newDialog.form.url,
      company: newDialog.form.company || undefined,
      role: newDialog.form.role || undefined,
      cv: newDialog.form.cv || undefined,
    })
    newFormOpened.value = true
    notify('Se abrió el navegador con el formulario. Envíalo y cierra la ventana.')
  } catch (e) {
    notify(e.message, 'error')
  }
}

const openedAppsMap = reactive({})

function isAppOpened(item) {
  if (openedAppsMap[item.id]) return true
  return Boolean(
    item.history?.some((h) =>
      h.note?.toLowerCase().includes('formulario abierto') ||
      h.note?.toLowerCase().includes('playwright')
    )
  )
}

async function launchItemForm(item) {
  try {
    await api.launchApply({
      url: item.url,
      company: item.company || undefined,
      role: item.role || undefined,
      cv: item.cv || undefined,
      applicationId: item.id,
      demo: item.demo || undefined,
    })
    openedAppsMap[item.id] = true
    await load()
    notify(`Formulario de ${item.company} abierto y completado en Playwright`)
  } catch (e) {
    notify(e.message, 'error')
  }
}

const tailoringMap = reactive({})

async function tailorAppCv(item) {
  tailoringMap[item.id] = true
  try {
    const res = await api.tailorCv({
      company: item.company,
      role: item.role,
      url: item.url || undefined,
      description: item.role,
    })
    if (res?.cv) {
      item.cv = res.cv
      await api.updateApplication(item.id, { cv: res.cv })
      notify(`CV adaptado generado para ${item.company} (${res.cv})`)
      await load()
    }
  } catch (err) {
    notify('Error al adaptar CV: ' + err.message, 'error')
  } finally {
    tailoringMap[item.id] = false
  }
}

async function confirmSent(item) {
  if (!item.cv) {
    const ok = window.confirm(`Atención: "${item.company}" no tiene un CV adaptado generado.\n¿Deseas registrarla como enviada de todas formas?`)
    if (!ok) return
  }
  const today = new Date().toISOString().slice(0, 10)
  try {
    await api.updateApplication(item.id, {
      status: 'applied',
      appliedAt: today,
      event: 'Postulación confirmada y enviada manualmente por el candidato',
    })
    if (item.company && !item.demo) {
      await api.addExclusion({ company: item.company, reason: `Ya postulado (${today})` }).catch(() => {})
    }
    notify(`Postulación a ${item.company} confirmada como enviada y agregada a exclusiones`)
    await load()
  } catch (e) {
    notify(e.message, 'error')
  }
}

async function register() {
  try {
    items.value.push(await api.createApplication(newDialog.form))
    newDialog.show = false
    newDialog.form = emptyForm()
  } catch (e) {
    notify(e.message, 'error')
  }
}

async function clearDemos() {
  if (!confirm(`¿Eliminar las ${demoCount.value} postulaciones de demostración?`)) return
  await api.clearDemos()
  items.value = items.value.filter((a) => !a.demo)
}

const fmtDate = (iso) => new Date(iso).toLocaleString()

async function remove(item) {
  if (!confirm(`¿Eliminar la postulación a ${item.company}?`)) return
  await api.deleteApplication(item.id)
  items.value = items.value.filter((a) => a.id !== item.id)
}
</script>

<template>
  <v-container fluid class="pa-6">
    <div class="d-flex align-center mb-4">
      <h1 class="text-h5">Postulaciones</h1>
      <v-spacer />
      <v-btn v-if="demoCount" variant="text" color="warning" prepend-icon="mdi-flask-off-outline" class="mr-2" @click="clearDemos">
        Limpiar demos ({{ demoCount }})
      </v-btn>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="newDialog.show = true; newFormOpened = false">Nueva postulación</v-btn>
    </div>

    <div class="d-flex flex-wrap ga-2 mb-4 align-center">
      <v-chip
        :variant="filterStatus === null ? 'flat' : 'tonal'"
        color="primary"
        prepend-icon="mdi-format-list-bulleted"
        class="font-weight-bold"
        style="cursor: pointer"
        @click="filterStatus = null"
      >
        Todas: {{ totalCount }}
      </v-chip>
      <v-chip
        v-for="c in counts"
        :key="c.key"
        :color="c.color"
        :prepend-icon="c.icon"
        :variant="filterStatus === c.key ? 'flat' : 'tonal'"
        :elevation="filterStatus === c.key ? 2 : 0"
        class="font-weight-medium"
        style="cursor: pointer"
        @click="toggleStatusFilter(c.key)"
      >
        {{ c.title }}: {{ c.count }}
        <v-icon v-if="filterStatus === c.key" icon="mdi-check" size="x-small" class="ml-1" />
      </v-chip>
      <v-btn
        v-if="filterStatus !== null"
        size="x-small"
        variant="text"
        color="error"
        prepend-icon="mdi-close"
        class="ml-1"
        @click="filterStatus = null"
      >
        Limpiar filtro
      </v-btn>
    </div>

    <v-card>
      <v-card-text>
        <v-text-field
          v-model="search"
          label="Buscar"
          prepend-inner-icon="mdi-magnify"
          density="compact"
          hide-details
          clearable
          class="mb-3"
        />
        <v-data-table
          :headers="headers"
          :items="filteredItems"
          :search="search"
          :loading="loading"
          v-model:expanded="expanded"
          show-expand
          item-value="id"
          :sort-by="[{ key: 'updatedAt', order: 'desc' }]"
          items-per-page="25"
        >
          <template #item.company="{ item }">
            <div>
              <span class="font-weight-medium">{{ item.company }}</span>
              <v-chip v-if="item.demo" size="x-small" color="warning" class="ml-1" prepend-icon="mdi-flask-outline">Demo</v-chip>
              <div v-if="item.cv" class="text-caption text-success mt-0.5 d-flex align-center">
                <v-icon icon="mdi-file-pdf-box" size="x-small" class="mr-1" />
                <span>{{ item.cv.split('/').pop() }}</span>
              </div>
            </div>
          </template>
          <template #item.appliedAt="{ item }">{{ item.appliedAt || '—' }}</template>
          <template #item.status="{ item }">
            <v-chip
              :color="STATUS_META[item.status].color"
              :prepend-icon="STATUS_META[item.status].icon"
              size="small"
              variant="tonal"
            >
              {{ STATUS_META[item.status].title }}
            </v-chip>
          </template>
          <template #expanded-row="{ columns, item }">
            <tr>
              <td :colspan="columns.length" class="py-3">
                <div class="text-caption text-medium-emphasis mb-2">Historial</div>
                <div v-for="(h, i) in item.history ?? []" :key="i" class="d-flex align-center mb-1">
                  <v-chip :color="STATUS_META[h.status]?.color" size="x-small" variant="tonal" class="mr-2">{{ STATUS_META[h.status]?.title ?? h.status }}</v-chip>
                  <span class="text-caption text-medium-emphasis mr-2">{{ fmtDate(h.at) }}</span>
                  <span class="text-body-2">{{ h.note }}</span>
                </div>
                <div v-if="!(item.history ?? []).length" class="text-body-2 text-medium-emphasis">Sin eventos registrados.</div>
              </td>
            </tr>
          </template>
          <template #item.reason="{ item }">
            <span class="text-medium-emphasis">{{ item.reason || item.notes }}</span>
          </template>
          <template #item.actions="{ item }">
            <div class="actions">
              <v-btn
                v-if="item.status === 'pending'"
                :color="item.cv ? 'success' : 'info'"
                variant="tonal"
                size="small"
                :prepend-icon="tailoringMap[item.id] ? undefined : (item.cv ? 'mdi-check-circle' : 'mdi-file-document-edit')"
                :loading="tailoringMap[item.id]"
                class="mr-1"
                :title="tailoringMap[item.id] ? 'El agente está adaptando el CV para esta vacante...' : (item.cv ? `CV generado: ${item.cv}` : 'Generar CV adaptado a medida para esta vacante')"
                @click="tailorAppCv(item)"
              >
                <template v-if="tailoringMap[item.id]" #loader>
                  <v-progress-circular indeterminate size="14" width="2" class="mr-1.5" />
                  <span>Adaptando CV...</span>
                </template>
                {{ tailoringMap[item.id] ? 'Adaptando CV...' : (item.cv ? 'CV Adaptado' : 'Adaptar CV') }}
              </v-btn>
              <v-btn
                v-if="item.url"
                :color="isAppOpened(item) ? 'success' : 'primary'"
                variant="tonal"
                size="small"
                :prepend-icon="isAppOpened(item) ? 'mdi-check-all' : 'mdi-open-in-app'"
                class="mr-1"
                title="Abrir formulario y completar campos automáticamente con Playwright"
                @click="launchItemForm(item)"
              >
                {{ isAppOpened(item) ? 'Formulario abierto' : 'Abrir form' }}
              </v-btn>
              <v-btn
                v-if="item.status === 'pending'"
                color="success"
                variant="tonal"
                size="small"
                prepend-icon="mdi-send"
                class="mr-1"
                title="Confirmar postulación enviada y registrar exclusión"
                @click="confirmSent(item)"
              >
                Marcar enviada
              </v-btn>
              <v-btn icon="mdi-flag-checkered" variant="text" size="small" title="Cambiar estado" @click="openStatus(item)" />
              <v-btn icon="mdi-delete-outline" variant="text" size="small" title="Eliminar" @click="remove(item)" />
            </div>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <v-dialog v-model="statusDialog.show" max-width="480">
      <v-card v-if="statusDialog.item" :title="statusDialog.item.company" :subtitle="statusDialog.item.role">
        <v-card-text>
          <v-select v-model="statusDialog.status" :items="statusItems" label="Estado" />
          <v-textarea
            v-model="statusDialog.reason"
            :label="statusDialog.status === 'rejected' ? 'Motivo del rechazo (obligatorio)' : 'Motivo'"
            rows="2"
            auto-grow
          />
          <v-textarea v-model="statusDialog.notes" label="Notas" rows="2" auto-grow />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="statusDialog.show = false">Cancelar</v-btn>
          <v-btn color="primary" @click="saveStatus">Guardar</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="newDialog.show" max-width="560">
      <v-card title="Nueva postulación">
        <v-card-text>
          <v-text-field v-model="newDialog.form.company" label="Empresa" />
          <v-text-field v-model="newDialog.form.role" label="Puesto" />
          <v-text-field v-model="newDialog.form.url" label="Enlace de la postulación" placeholder="https://" />
          <v-select v-model="newDialog.form.cv" :items="cvItems" label="CV a adjuntar" clearable />
          <v-alert type="info" variant="tonal" density="compact">
            "Abrir formulario" lanza el navegador con los datos pre-rellenados. Tú revisas y envías; luego registra la postulación.
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-btn
            :color="newFormOpened ? 'success' : undefined"
            :variant="newFormOpened ? 'tonal' : 'text'"
            :prepend-icon="newFormOpened ? 'mdi-check-all' : 'mdi-open-in-browser'"
            :disabled="!newDialog.form.url"
            @click="launchForm"
          >
            {{ newFormOpened ? 'Formulario abierto' : 'Abrir formulario' }}
          </v-btn>
          <v-spacer />
          <v-btn @click="newDialog.show = false">Cancelar</v-btn>
          <v-btn color="primary" :disabled="!newDialog.form.company || !newDialog.form.role" @click="register">Registrar como enviada</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snack.show" :color="snack.color" timeout="4000">{{ snack.text }}</v-snackbar>
  </v-container>
</template>

<style scoped>
.actions {
  display: flex;
  flex-wrap: nowrap;
  justify-content: flex-end;
}
</style>
