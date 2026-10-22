<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api.js'

const items = ref([])
const loading = ref(false)
const search = ref('')
const snack = reactive({ show: false, text: '', color: 'success' })

const headers = [
  { title: 'Empresa (slug)', key: 'company' },
  { title: 'Motivo', key: 'reason' },
  { title: '', key: 'actions', sortable: false, align: 'end' },
]

const notify = (text, color = 'success') => Object.assign(snack, { show: true, text, color })

async function load() {
  loading.value = true
  try {
    items.value = await api.listExclusions()
  } catch (e) {
    notify(e.message, 'error')
  } finally {
    loading.value = false
  }
}
onMounted(load)

// ---- add ----
const form = reactive({ company: '', reason: '' })
const shortSlug = computed(() => form.company.trim().length > 0 && form.company.trim().length < 4)

async function add() {
  try {
    await api.addExclusion({ company: form.company, reason: form.reason })
    Object.assign(form, { company: '', reason: '' })
    await load()
    notify('Empresa excluida')
  } catch (e) {
    notify(e.message, 'error')
  }
}

// ---- edit ----
const edit = reactive({ show: false, original: '', company: '', reason: '' })

function openEdit(item) {
  Object.assign(edit, { show: true, original: item.company, company: item.company, reason: item.reason })
}

async function saveEdit() {
  try {
    await api.updateExclusion(edit.original, { company: edit.company, reason: edit.reason })
    edit.show = false
    await load()
    notify('Cambios guardados')
  } catch (e) {
    notify(e.message, 'error')
  }
}

async function remove(item) {
  if (!confirm(`¿Quitar "${item.company}" de las exclusiones? Volverá a aparecer en las búsquedas.`)) return
  try {
    await api.removeExclusion(item.company)
    await load()
    notify('Exclusión eliminada')
  } catch (e) {
    notify(e.message, 'error')
  }
}
</script>

<template>
  <v-container fluid class="pa-6">
    <h1 class="text-h5 mb-1">Exclusiones</h1>
    <p class="text-medium-emphasis mb-4">
      Las empresas de esta lista se omiten en los escaneos y el agente no las propone. Se excluye cualquier empresa cuyo
      nombre <strong>contenga</strong> el texto indicado. Se guarda en <code>config/exclusions.py</code>.
    </p>

    <v-card class="mb-4">
      <v-card-text>
        <v-form class="d-flex flex-wrap ga-3 align-start" @submit.prevent="add">
          <v-text-field
            v-model="form.company"
            label="Empresa"
            placeholder="acme"
            density="comfortable"
            hide-details="auto"
            :hint="shortSlug ? 'Texto muy corto: podría excluir empresas que no quieres' : ''"
            persistent-hint
            style="max-width: 280px"
          />
          <v-text-field
            v-model="form.reason"
            label="Motivo"
            placeholder="Ya postulado, agencia, pide 10+ años…"
            density="comfortable"
            hide-details
            style="min-width: 280px; flex: 1"
          />
          <v-btn type="submit" color="primary" prepend-icon="mdi-plus" height="48" :disabled="!form.company.trim()">Agregar</v-btn>
        </v-form>
      </v-card-text>
    </v-card>

    <v-card>
      <v-card-text>
        <v-text-field v-model="search" label="Buscar" prepend-inner-icon="mdi-magnify" density="compact" hide-details clearable class="mb-3" />
        <v-data-table :headers="headers" :items="items" :search="search" :loading="loading" items-per-page="25" item-value="company">
          <template #item.reason="{ item }">
            <span v-if="item.reason">{{ item.reason }}</span>
            <span v-else class="text-medium-emphasis">Sin motivo</span>
          </template>
          <template #item.actions="{ item }">
            <div class="actions">
              <v-btn icon="mdi-pencil-outline" variant="text" size="small" title="Editar" @click="openEdit(item)" />
              <v-btn icon="mdi-delete-outline" variant="text" size="small" title="Quitar de las exclusiones" @click="remove(item)" />
            </div>
          </template>
          <template #no-data>Aún no hay empresas excluidas.</template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <v-dialog v-model="edit.show" max-width="480">
      <v-card title="Editar exclusión">
        <v-card-text>
          <v-text-field v-model="edit.company" label="Empresa" />
          <v-textarea v-model="edit.reason" label="Motivo" rows="2" auto-grow />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="edit.show = false">Cancelar</v-btn>
          <v-btn color="primary" :disabled="!edit.company.trim()" @click="saveEdit">Guardar</v-btn>
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
