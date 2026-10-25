<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { api } from '../api.js'
import { t } from '../i18n/index.js'

const items = ref([])
const loading = ref(false)
const adding = ref(false)
const search = ref('')
const searchInputRef = ref(null)
const fileInputRef = ref(null)

const form = reactive({ company: '', reason: '' })
const edit = reactive({ show: false, original: '', company: '', reason: '', saving: false })
const showClearModal = ref(false)
const clearing = ref(false)
const snack = reactive({ show: false, text: '', color: 'success' })

let snackTimer = null
function notify(text, color = 'success') {
  if (snackTimer) clearTimeout(snackTimer)
  Object.assign(snack, { show: true, text, color })
  snackTimer = setTimeout(() => {
    snack.show = false
  }, 3500)
}

const shortSlug = computed(() => form.company.trim().length > 0 && form.company.trim().length < 4)

const filteredItems = computed(() => {
  const q = search.value.toLowerCase().trim()
  if (!q) return items.value
  return items.value.filter(
    (item) =>
      item.company?.toLowerCase().includes(q) ||
      item.reason?.toLowerCase().includes(q)
  )
})

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

async function add() {
  if (!form.company.trim() || adding.value) return
  adding.value = true
  try {
    await api.addExclusion({ company: form.company, reason: form.reason })
    Object.assign(form, { company: '', reason: '' })
    await load()
    notify(t('exclusions.toasts.added'))
  } catch (e) {
    notify(e.message, 'error')
  } finally {
    adding.value = false
  }
}

function openEdit(item) {
  Object.assign(edit, {
    show: true,
    original: item.company,
    company: item.company,
    reason: item.reason || '',
    saving: false,
  })
}

async function saveEdit() {
  if (!edit.company.trim() || edit.saving) return
  edit.saving = true
  try {
    await api.updateExclusion(edit.original, { company: edit.company, reason: edit.reason })
    edit.show = false
    await load()
    notify(t('exclusions.toasts.updated'))
  } catch (e) {
    notify(e.message, 'error')
  } finally {
    edit.saving = false
  }
}

async function remove(item) {
  if (!confirm(t('exclusions.confirmDelete', { company: item.company }))) return
  try {
    await api.removeExclusion(item.company)
    await load()
    notify(t('exclusions.toasts.deleted'))
  } catch (e) {
    notify(e.message, 'error')
  }
}

function exportJson() {
  try {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(items.value, null, 2))
    const downloadAnchor = document.createElement('a')
    downloadAnchor.setAttribute('href', dataStr)
    downloadAnchor.setAttribute('download', 'exclusions.json')
    document.body.appendChild(downloadAnchor)
    downloadAnchor.click()
    downloadAnchor.remove()
    notify(t('exclusions.toasts.exported'))
  } catch (e) {
    notify(t('exclusions.toasts.exportError') + e.message, 'error')
  }
}

function triggerImport() {
  fileInputRef.value?.click()
}

async function onFileSelected(event) {
  const file = event.target.files?.[0]
  if (!file) return
  try {
    const text = await file.text()
    const parsed = JSON.parse(text)
    const res = await api.importExclusions(parsed)
    await load()
    notify(t('exclusions.toasts.imported', { added: res.added, total: res.total }))
  } catch (e) {
    notify(t('exclusions.toasts.importError') + e.message, 'error')
  } finally {
    event.target.value = ''
  }
}

function clearAll() {
  showClearModal.value = true
}

async function confirmClearAll() {
  clearing.value = true
  try {
    const res = await api.clearExclusions()
    showClearModal.value = false
    await load()
    notify(t('exclusions.toasts.cleared', { cleared: res.cleared }))
  } catch (e) {
    notify(e.message, 'error')
  } finally {
    clearing.value = false
  }
}

function onKeyDown(e) {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'f') {
    e.preventDefault()
    searchInputRef.value?.focus()
    searchInputRef.value?.select()
  }
}

onMounted(() => {
  load()
  window.addEventListener('keydown', onKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
  if (snackTimer) clearTimeout(snackTimer)
})
</script>

<template>
  <div class="p-6 flex flex-col gap-6 max-w-[1580px] w-full mx-auto font-sans text-on-surface">
    <!-- SECCIÓN SUPERIOR: Título, contextualización de archivo de configuración y descripción -->
    <section class="flex flex-col gap-3 pb-2 border-b border-border-subtle">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <h1 class="text-2xl font-semibold text-on-surface tracking-tight">{{ $t('exclusions.title') }}</h1>
        <div class="flex items-center gap-2 px-2.5 py-1 rounded-md bg-surface-container text-outline font-mono text-[11px] border border-border-subtle">
          <span class="inline-block w-2 h-2 rounded-full bg-emerald-400"></span>
          <span>{{ $t('exclusions.activeFilterBadge') }}</span>
        </div>
      </div>
      <p class="text-xs text-on-surface-variant max-w-4xl leading-relaxed">
        {{ $t('exclusions.description') }}
      </p>
    </section>

    <!-- FORMULARIO RÁPIDO DE ADICIÓN (Fila limpia horizontal) -->
    <section class="p-3.5 rounded-xl bg-surface-card border border-border-subtle shadow-sm">
      <form class="flex flex-col md:flex-row items-stretch md:items-center gap-3" @submit.prevent="add">
        <div class="flex-1 relative">
          <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[18px]">business</span>
          <input
            v-model="form.company"
            class="w-full pl-9 pr-3 py-2 bg-surface-container text-on-surface placeholder:text-outline font-mono text-xs rounded-lg border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            :placeholder="$t('exclusions.companyPlaceholder')"
            required
            type="text"
          />
        </div>
        <div class="flex-[1.4] relative">
          <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[18px]">sticky_note_2</span>
          <input
            v-model="form.reason"
            class="w-full pl-9 pr-3 py-2 bg-surface-container text-on-surface placeholder:text-outline text-xs rounded-lg border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            :placeholder="$t('exclusions.reasonPlaceholder')"
            type="text"
          />
        </div>
        <button
          class="inline-flex items-center justify-center gap-2 px-4 py-2 bg-accent hover:bg-accent-hover text-white text-xs rounded-lg font-medium shadow-sm transition-all active:scale-[0.98] disabled:opacity-50 whitespace-nowrap cursor-pointer"
          :disabled="!form.company.trim() || adding"
          type="submit"
        >
          <span class="material-symbols-outlined text-[17px]">add_circle</span>
          <span>{{ $t('exclusions.addBtn') }}</span>
        </button>
      </form>
      <p v-if="shortSlug" class="text-[11px] font-mono text-amber-400 mt-2 ml-1">
        {{ $t('exclusions.shortSlugWarning') }}
      </p>
    </section>

    <!-- BARRA DE HERRAMIENTAS Y CONTROL DE LISTA -->
    <section class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
      <!-- Buscador y contador -->
      <div class="flex items-center gap-3 flex-1 max-w-lg">
        <div class="relative w-full">
          <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[16px]">search</span>
          <input
            ref="searchInputRef"
            v-model="search"
            class="w-full pl-9 pr-12 py-1.5 bg-surface-container text-on-surface placeholder:text-outline text-xs rounded-lg border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            :placeholder="$t('exclusions.searchPlaceholder')"
            type="text"
          />
          <kbd
            class="absolute right-2.5 top-1/2 -translate-y-1/2 px-1.5 py-0.5 rounded bg-surface-container-high text-outline font-mono text-[10px] border border-border-subtle cursor-pointer hover:text-on-surface"
            title="Ctrl+F / ⌘F"
            @click="searchInputRef?.focus()"
          >
            ⌘F
          </kbd>
        </div>
        <div class="whitespace-nowrap font-mono text-xs text-outline px-2.5 py-1 rounded bg-surface-container border border-border-subtle">
          {{ $t('exclusions.activeCount', { count: filteredItems.length }) }}
        </div>
      </div>

      <!-- Botones de archivo / exportación -->
      <div class="flex items-center gap-2">
        <input
          ref="fileInputRef"
          type="file"
          accept=".json"
          class="hidden"
          @change="onFileSelected"
        />
        <button
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface text-xs font-medium border border-border-subtle transition-colors cursor-pointer"
          type="button"
          :title="$t('exclusions.exportBtn')"
          @click="exportJson"
        >
          <span class="material-symbols-outlined text-[16px]">download</span>
          <span>{{ $t('exclusions.exportBtn') }}</span>
        </button>
        <button
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface text-xs font-medium border border-border-subtle transition-colors cursor-pointer"
          type="button"
          :title="$t('exclusions.importBtn')"
          @click="triggerImport"
        >
          <span class="material-symbols-outlined text-[16px]">file_upload</span>
          <span>{{ $t('exclusions.importBtn') }}</span>
        </button>
        <button
          class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container hover:bg-rose-950/40 text-outline hover:text-rose-400 text-xs font-medium border border-border-subtle hover:border-rose-900/50 transition-colors cursor-pointer"
          type="button"
          :title="$t('exclusions.clearBtn')"
          @click="clearAll"
        >
          <span class="material-symbols-outlined text-[16px]">delete_sweep</span>
          <span>{{ $t('exclusions.clearBtn') }}</span>
        </button>
      </div>
    </section>

    <!-- TABLA DE EXCLUSIONES -->
    <section class="rounded-xl bg-surface-card border border-border-subtle shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-surface-container border-b border-border-subtle text-outline font-mono text-[11px] uppercase tracking-wider">
              <th class="py-3 px-4 w-[32%] font-medium">{{ $t('exclusions.colCompany') }}</th>
              <th class="py-3 px-4 w-[54%] font-medium">{{ $t('exclusions.colReason') }}</th>
              <th class="py-3 px-4 w-[14%] text-right font-medium">{{ $t('exclusions.colActions') }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-border-subtle text-on-surface text-xs font-sans">
            <tr v-if="loading">
              <td colspan="3" class="py-8 text-center text-outline font-mono text-xs">
                {{ $t('exclusions.loading') }}
              </td>
            </tr>
            <tr v-else-if="filteredItems.length === 0">
              <td colspan="3" class="py-8 text-center text-outline text-xs">
                {{ search ? $t('exclusions.emptySearch') : $t('exclusions.emptyList') }}
              </td>
            </tr>
            <tr
              v-for="item in filteredItems"
              :key="item.company"
              class="hover:bg-surface-container/50 transition-colors group"
            >
              <td class="py-2.5 px-4">
                <span class="inline-flex items-center gap-2 px-2 py-0.5 rounded bg-surface-container-high text-accent font-mono text-xs font-semibold tracking-wide border border-border-subtle">
                  <span class="w-1.5 h-1.5 rounded-full bg-outline"></span>
                  {{ item.company }}
                </span>
              </td>
              <td class="py-2.5 px-4 text-on-surface-variant">
                {{ item.reason || $t('exclusions.noReason') }}
              </td>
              <td class="py-2.5 px-4 text-right">
                <div class="inline-flex items-center justify-end gap-1">
                  <button
                    class="p-1 rounded text-outline hover:text-on-surface hover:bg-surface-container-high transition-colors cursor-pointer"
                    type="button"
                    :title="$t('common.edit')"
                    @click="openEdit(item)"
                  >
                    <span class="material-symbols-outlined text-[16px]">edit</span>
                  </button>
                  <button
                    class="p-1 rounded text-outline hover:text-rose-400 hover:bg-surface-container-high transition-colors cursor-pointer"
                    type="button"
                    :title="$t('common.delete')"
                    @click="remove(item)"
                  >
                    <span class="material-symbols-outlined text-[16px]">delete</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pie de tabla / resumen -->
      <div class="p-3 bg-surface-container border-t border-border-subtle flex items-center justify-between text-outline text-xs font-sans">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-[16px]">database</span>
          <span>{{ $t('exclusions.showingStats', { shown: filteredItems.length, total: items.length }) }}</span>
        </div>
        <div class="flex items-center gap-1.5 font-mono text-[11px] text-outline">
          <span class="w-2 h-2 rounded-full bg-emerald-400"></span>
          <span>{{ $t('exclusions.syncedWithDisk') }}</span>
        </div>
      </div>
    </section>

    <!-- MODAL DE EDICIÓN -->
    <div
      v-if="edit.show"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      @click.self="edit.show = false"
    >
      <div class="bg-surface-card border border-border-subtle rounded-xl max-w-md w-full p-5 flex flex-col gap-4 shadow-2xl">
        <div class="flex items-center justify-between border-b border-border-subtle pb-3">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-accent text-[20px]">edit</span>
            <h2 class="text-sm font-semibold text-on-surface">{{ $t('exclusions.editTitle') }}</h2>
          </div>
          <button
            class="text-outline hover:text-on-surface p-1 transition-colors cursor-pointer"
            type="button"
            @click="edit.show = false"
          >
            <span class="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>

        <div class="flex flex-col gap-3">
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-on-surface-variant font-medium">{{ $t('exclusions.editCompanyLabel') }}</label>
            <input
              v-model="edit.company"
              class="h-9 px-3 rounded-lg bg-surface-container text-on-surface font-mono text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors"
              type="text"
            />
          </div>

          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-on-surface-variant font-medium">{{ $t('exclusions.editReasonLabel') }}</label>
            <textarea
              v-model="edit.reason"
              rows="3"
              class="p-2.5 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors resize-none font-sans"
              :placeholder="$t('exclusions.editReasonPlaceholder')"
            ></textarea>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 pt-2 border-t border-border-subtle">
          <button
            class="px-3.5 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface text-xs font-medium border border-border-subtle transition-colors cursor-pointer"
            type="button"
            @click="edit.show = false"
          >
            {{ $t('common.cancel') }}
          </button>
          <button
            class="px-4 py-1.5 rounded-lg bg-accent hover:bg-accent-hover text-white text-xs font-medium shadow-sm transition-all disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
            :disabled="!edit.company.trim() || edit.saving"
            type="button"
            @click="saveEdit"
          >
            <span v-if="edit.saving" class="material-symbols-outlined text-[16px] animate-spin">sync</span>
            <span>{{ edit.saving ? $t('exclusions.savingEditBtn') : $t('exclusions.saveEditBtn') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL DE CONFIRMACIÓN: VACIAR LISTA -->
    <div
      v-if="showClearModal"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm"
      @click.self="showClearModal = false"
    >
      <div class="bg-surface-card border border-rose-900/40 rounded-xl max-w-md w-full p-5 flex flex-col gap-4 shadow-2xl">
        <div class="flex items-start gap-3">
          <div class="p-2.5 rounded-lg bg-rose-950/60 text-rose-400 border border-rose-900/50 shrink-0">
            <span class="material-symbols-outlined text-[22px]">warning</span>
          </div>
          <div class="flex flex-col gap-1">
            <h2 class="text-sm font-semibold text-on-surface">{{ $t('exclusions.clearModalTitle') }}</h2>
            <p class="text-xs text-on-surface-variant leading-relaxed">
              {{ $t('exclusions.clearModalDesc', { count: items.length }) }}
            </p>
          </div>
        </div>

        <div class="flex items-center justify-end gap-2 pt-2 border-t border-border-subtle mt-1">
          <button
            class="px-3.5 py-1.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface text-xs font-medium border border-border-subtle transition-colors cursor-pointer"
            type="button"
            :disabled="clearing"
            @click="showClearModal = false"
          >
            {{ $t('common.cancel') }}
          </button>
          <button
            class="px-4 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium shadow-sm transition-all disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
            :disabled="clearing"
            type="button"
            @click="confirmClearAll"
          >
            <span v-if="clearing" class="material-symbols-outlined text-[16px] animate-spin">sync</span>
            <span>{{ clearing ? $t('exclusions.clearingBtn') : $t('exclusions.confirmClearBtn') }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- NOTIFICACIÓN TOAST / SNACKBAR -->
    <div
      v-if="snack.show"
      class="fixed bottom-5 right-5 z-50 flex items-center gap-2 px-4 py-2.5 rounded-lg border text-xs shadow-lg transition-all"
      :class="snack.color === 'error' ? 'bg-rose-950/90 text-rose-200 border-rose-800' : 'bg-surface-card text-on-surface border-border-subtle'"
    >
      <span class="material-symbols-outlined text-[18px]" :class="snack.color === 'error' ? 'text-rose-400' : 'text-emerald-400'">
        {{ snack.color === 'error' ? 'error' : 'check_circle' }}
      </span>
      <span>{{ snack.text }}</span>
      <button class="ml-2 text-outline hover:text-on-surface cursor-pointer" type="button" @click="snack.show = false">
        ✕
      </button>
    </div>
  </div>
</template>
