<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api.js'

const files = ref([])
const selected = ref(null)
const error = ref('')

const src = computed(() => {
  if (!selected.value?.dir || !selected.value?.name) return ''
  const encodedPath = String(selected.value.name)
    .split('/')
    .map((part) => encodeURIComponent(part))
    .join('/')
  return `/files/${encodeURIComponent(selected.value.dir)}/${encodedPath}`
})

onMounted(async () => {
  try {
    files.value = await api.listFiles()
    selected.value = files.value[0] ?? null
  } catch (e) {
    error.value = e.message
  }
})

const fmt = (iso) => new Date(iso).toLocaleString()
const displayTitle = (f) => {
  const parts = String(f.name).split('/')
  return parts.length > 1 ? parts[0].replace(/^\d{4}-\d{2}_/, '').replace(/_/g, ' ') : f.name
}
const displaySubtitle = (f) => {
  const parts = String(f.name).split('/')
  const fileName = parts[parts.length - 1]
  return `${fileName} · ${fmt(f.modifiedAt)}`
}
</script>

<template>
  <v-container fluid class="pa-6 fill-height align-stretch">
    <v-row class="flex-nowrap fill-height">
      <v-col cols="12" md="4" lg="3" class="d-flex flex-column">
        <h1 class="text-h5 mb-4">CVs ({{ files.length }})</h1>
        <v-alert v-if="error" type="error" variant="tonal" class="mb-3">{{ error }}</v-alert>
        <v-card class="cv-list-card">
          <v-list lines="two">
            <v-list-item
              v-for="f in files"
              :key="f.dir + '/' + f.name"
              :active="selected && selected.dir === f.dir && selected.name === f.name"
              color="primary"
              prepend-icon="mdi-file-pdf-box"
              :title="displayTitle(f)"
              :subtitle="displaySubtitle(f)"
              @click="selected = f"
            />
            <v-list-item v-if="!files.length" title="No hay PDFs todavía" />
          </v-list>
        </v-card>
      </v-col>
      <v-col cols="12" md="8" lg="9">
        <v-card height="calc(100vh - 48px)">
          <iframe v-if="src" :key="src" :src="src" title="Vista previa del CV" class="viewer" />
          <div v-else class="d-flex align-center justify-center fill-height text-medium-emphasis">Selecciona un CV</div>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<style scoped>
.cv-list-card {
  max-height: calc(100vh - 110px);
  overflow-y: auto;
}
.viewer {
  width: 100%;
  height: 100%;
  border: 0;
}
</style>
