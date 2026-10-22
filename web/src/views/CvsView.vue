<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api.js'

const files = ref([])
const selected = ref(null)
const error = ref('')

const src = computed(() => (selected.value ? `/files/${selected.value.dir}/${encodeURIComponent(selected.value.name)}` : ''))

onMounted(async () => {
  try {
    files.value = await api.listFiles()
    selected.value = files.value[0] ?? null
  } catch (e) {
    error.value = e.message
  }
})

const fmt = (iso) => new Date(iso).toLocaleString()
</script>

<template>
  <v-container fluid class="pa-6 fill-height align-stretch">
    <v-row class="flex-nowrap">
      <v-col cols="12" md="4" lg="3">
        <h1 class="text-h5 mb-4">CVs</h1>
        <v-alert v-if="error" type="error" variant="tonal" class="mb-3">{{ error }}</v-alert>
        <v-card>
          <v-list v-model:selected="selected" select-strategy="single-leaf" lines="two">
            <v-list-item
              v-for="f in files"
              :key="f.dir + f.name"
              :value="f"
              :active="selected === f"
              prepend-icon="mdi-file-pdf-box"
              :title="f.name"
              :subtitle="`${f.dir} · ${fmt(f.modifiedAt)}`"
              @click="selected = f"
            />
            <v-list-item v-if="!files.length" title="No hay PDFs todavía" />
          </v-list>
        </v-card>
      </v-col>
      <v-col cols="12" md="8" lg="9">
        <v-card height="calc(100vh - 48px)">
          <iframe v-if="src" :src="src" title="Vista previa del CV" class="viewer" />
          <div v-else class="d-flex align-center justify-center fill-height text-medium-emphasis">Selecciona un CV</div>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<style scoped>
.viewer {
  width: 100%;
  height: 100%;
  border: 0;
}
</style>
