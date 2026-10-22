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

async function launchForm() {
  try {
    await api.launchApply({ url: newDialog.form.url, cv: newDialog.form.cv || undefined })
    notify('Se abrió el navegador con el formulario. Envíalo y cierra la ventana.')
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
      <v-btn color="primary" prepend-icon="mdi-plus" @click="newDialog.show = true">Nueva postulación</v-btn>
    </div>

    <div class="d-flex flex-wrap ga-2 mb-4">
      <v-chip v-for="c in counts" :key="c.key" :color="c.color" :prepend-icon="c.icon" variant="tonal">
        {{ c.title }}: {{ c.count }}
      </v-chip>
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
          :items="items"
          :search="search"
          :loading="loading"
          v-model:expanded="expanded"
          show-expand
          item-value="id"
          :sort-by="[{ key: 'updatedAt', order: 'desc' }]"
          items-per-page="25"
        >
          <template #item.company="{ item }">
            {{ item.company }}
            <v-chip v-if="item.demo" size="x-small" color="warning" class="ml-1" prepend-icon="mdi-flask-outline">Demo</v-chip>
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
            <v-btn icon="mdi-open-in-new" variant="text" size="small" :href="item.url" target="_blank" rel="noopener" :disabled="!item.url" title="Abrir publicación" />
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
          <v-btn prepend-icon="mdi-open-in-browser" :disabled="!newDialog.form.url" @click="launchForm">Abrir formulario</v-btn>
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
