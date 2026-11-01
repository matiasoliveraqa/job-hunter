<script setup>
import { formatCompanyName } from '../../api.js'

const props = defineProps({
  paginatedItems: {
    type: Array,
    required: true,
  },
  filteredItemsCount: {
    type: Number,
    required: true,
  },
  selectedIds: {
    type: Object, // Set
    required: true,
  },
  isAllSelected: {
    type: Boolean,
    default: false,
  },
  expandedRows: {
    type: Object, // Set
    required: true,
  },
  currentPage: {
    type: Number,
    required: true,
  },
  pageSize: {
    type: Number,
    required: true,
  },
  totalPages: {
    type: Number,
    required: true,
  },
  statusStyles: {
    type: Object,
    required: true,
  },
  tailoringMap: {
    type: Object,
    required: true,
  },
  openedAppsMap: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits([
  'toggle-select-all',
  'toggle-select',
  'toggle-expand-row',
  'tailor-cv',
  'assign-base-cv',
  'launch-form',
  'confirm-sent',
  'open-folder',
  'open-status',
  'remove',
  'prev-page',
  'next-page',
  'reset-filters',
])

function fmtDate(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return iso
    return d.toLocaleDateString([], {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function getAppAts(item) {
  const u = (item.url || '').toLowerCase()
  if (u.includes('greenhouse.io') || u.includes('gh_jid')) return { key: 'greenhouse', label: 'Greenhouse ATS' }
  if (u.includes('lever.co')) return { key: 'lever', label: 'Lever ATS' }
  if (u.includes('ashbyhq.com')) return { key: 'ashby', label: 'Ashby ATS' }
  if (u.includes('workable.com')) return { key: 'workable', label: 'Workable ATS' }
  if (u.includes('breezy.hr')) return { key: 'breezy', label: 'Breezy HR' }
  if (u.includes('recruitee.com')) return { key: 'recruitee', label: 'Recruitee ATS' }
  if (u.includes('bamboohr.com') || u.includes('bamboohr.co.uk')) return { key: 'bamboohr', label: 'BambooHR ATS' }
  return { key: 'direct', label: 'Postulación Directa' }
}

function isAppOpened(item) {
  if (props.openedAppsMap[item.id]) return true
  return Boolean(
    item.history?.some((h) =>
      h.note?.toLowerCase().includes('formulario abierto') ||
      h.note?.toLowerCase().includes('playwright')
    )
  )
}
</script>

<template>
  <div class="w-full bg-surface-card rounded-xl border border-border-subtle overflow-hidden shadow-sm">
    <div class="overflow-x-auto">
      <table class="w-full text-left border-collapse table-auto">
        <thead>
          <tr class="border-b border-border-subtle bg-surface-container/60 text-outline text-[11px] uppercase tracking-wider font-mono">
            <th class="w-10 px-3.5 py-3 text-center">
              <input
                class="rounded bg-surface-container border border-border-muted text-accent focus:ring-0 focus:ring-offset-0 w-3.5 h-3.5 cursor-pointer"
                :checked="isAllSelected"
                type="checkbox"
                @change="$emit('toggle-select-all')"
              />
            </th>
            <th class="px-4 py-3 w-[22%]">{{ $t('common.company') }}</th>
            <th class="px-4 py-3 w-[36%]">{{ $t('applications.table.colCompanyRole') }}</th>
            <th class="px-3 py-3 w-[11%] whitespace-nowrap">{{ $t('applications.table.colDate') }}</th>
            <th class="px-3 py-3 w-[13%] whitespace-nowrap">{{ $t('common.status') }}</th>
            <th class="px-4 py-3 text-right w-[18%] whitespace-nowrap">{{ $t('common.actions') }}</th>
          </tr>
        </thead>

        <tbody class="divide-y divide-border-subtle text-xs text-on-surface">
          <template v-for="item in paginatedItems" :key="item.id">
            <tr
              class="hover:bg-surface-container/50 transition-colors group"
              :class="{ 'bg-surface-container/20': selectedIds.has(item.id) }"
            >
              <!-- Checkbox -->
              <td class="px-3.5 py-3 text-center">
                <input
                  class="rounded bg-surface-container border border-border-muted text-accent focus:ring-0 focus:ring-offset-0 w-3.5 h-3.5 cursor-pointer"
                  :checked="selectedIds.has(item.id)"
                  type="checkbox"
                  @change="$emit('toggle-select', item.id)"
                />
              </td>

              <!-- Empresa -->
              <td class="px-4 py-3">
                <div class="flex flex-col min-w-0">
                  <span class="font-medium text-on-surface truncate" :title="formatCompanyName(item.company)">
                    {{ formatCompanyName(item.company) }}
                  </span>
                  <span class="text-[11px] font-mono text-outline">{{ getAppAts(item).label }}</span>
                </div>
              </td>

              <!-- Puesto & CV Adaptado -->
              <td class="px-4 py-3">
                <div class="flex flex-col min-w-0">
                  <span class="font-medium text-on-surface truncate" :title="item.role">{{ item.role }}</span>
                  <div v-if="item.cv" class="flex items-center gap-1.5 font-mono text-[11px] text-emerald-400 mt-0.5 min-w-0">
                    <span class="material-symbols-outlined text-[14px] shrink-0">picture_as_pdf</span>
                    <a
                      class="hover:underline truncate"
                      :href="'/files/' + item.cv"
                      rel="noopener noreferrer"
                      target="_blank"
                      :title="'Abrir ' + item.cv"
                    >
                      {{ item.cv.split('/').pop() }}
                    </a>
                    <button
                      type="button"
                      class="text-outline hover:text-amber-400 p-0.5 rounded transition-colors shrink-0"
                      :title="$t('applications.table.openFolder')"
                      @click="$emit('open-folder', item)"
                    >
                      <span class="material-symbols-outlined text-[13px] block">folder_open</span>
                    </button>
                  </div>
                  <span v-else-if="item.notes" class="text-[11px] text-on-surface-variant truncate mt-0.5" :title="item.notes">
                    {{ item.notes }}
                  </span>
                  <span v-else class="text-[11px] text-outline font-mono mt-0.5">
                    {{ $t('applications.table.noCv') }}
                  </span>
                </div>
              </td>

              <!-- Fecha Envío -->
              <td class="px-3 py-3 font-mono text-on-surface-variant text-[11px] whitespace-nowrap">
                {{ item.appliedAt || '—' }}
              </td>

              <!-- Estado -->
              <td class="px-3 py-3 whitespace-nowrap">
                <span
                  :class="[
                    'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium border',
                    statusStyles[item.status]?.bg || 'bg-surface-container text-outline border-border-subtle'
                  ]"
                >
                  <span :class="['w-1.5 h-1.5 rounded-full', statusStyles[item.status]?.dot || 'bg-outline']"></span>
                  <span>{{ statusStyles[item.status]?.label || item.status }}</span>
                </span>
              </td>

              <!-- Acciones -->
              <td class="px-4 py-3 text-right whitespace-nowrap">
                <div class="inline-flex items-center justify-end gap-1.5">
                  <!-- Adaptar CV con IA (solo cuando está pendiente y aún no tiene CV) -->
                  <button
                    v-if="item.status === 'pending' && !item.cv"
                    :class="[
                      'inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium transition-all duration-200 border',
                      tailoringMap[item.id]
                        ? 'bg-accent/20 text-accent border-accent/40 cursor-wait'
                        : 'bg-accent-subtle hover:bg-accent/20 text-accent border-transparent'
                    ]"
                    :disabled="tailoringMap[item.id]"
                    :title="$t('search.table.btnTailor')"
                    type="button"
                    @click="$emit('tailor-cv', item)"
                  >
                    <svg
                      v-if="tailoringMap[item.id]"
                      class="animate-spin h-3 w-3 text-accent shrink-0"
                      fill="none"
                      viewBox="0 0 24 24"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" fill="currentColor"></path>
                    </svg>
                    <span v-else class="material-symbols-outlined text-[13px] leading-none text-accent">auto_fix_high</span>
                    <span>{{ tailoringMap[item.id] ? $t('search.table.btnTailoring') : $t('search.table.btnTailor') }}</span>
                  </button>

                  <!-- Usar CV base directamente sin IA (solo cuando está pendiente y aún no tiene CV) -->
                  <button
                    v-if="item.status === 'pending' && !item.cv"
                    class="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-medium bg-surface-container hover:bg-surface-container-high text-on-surface border border-border-subtle transition-colors"
                    :title="$t('topbar.statusBaseCv')"
                    type="button"
                    @click="$emit('assign-base-cv', item)"
                  >
                    <span class="material-symbols-outlined text-[13px] leading-none text-outline">description</span>
                    <span>{{ $t('topbar.statusBaseCv') }}</span>
                  </button>

                  <!-- Abrir Formulario Playwright -->
                  <button
                    v-if="item.url"
                    :class="[
                      'inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium transition-colors border',
                      isAppOpened(item)
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-surface-container hover:bg-surface-container-high border-border-subtle text-on-surface'
                    ]"
                    :title="$t('search.table.openPlaywright')"
                    type="button"
                    @click="$emit('launch-form', item)"
                  >
                    <span class="material-symbols-outlined text-[13px]">{{ isAppOpened(item) ? 'check' : 'open_in_new' }}</span>
                    <span>{{ isAppOpened(item) ? $t('common.open') : $t('applications.table.openPlaywright') }}</span>
                  </button>

                  <!-- Confirmar postulación enviada -->
                  <button
                    v-if="item.status === 'pending'"
                    class="inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-medium bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 transition-colors"
                    :title="$t('common.confirm')"
                    type="button"
                    @click="$emit('confirm-sent', item)"
                  >
                    <span class="material-symbols-outlined text-[13px]">done_all</span>
                    <span>{{ $t('common.confirm') }}</span>
                  </button>

                  <!-- Abrir carpeta local con información enviada -->
                  <button
                    v-if="item.status !== 'pending' || item.cv"
                    class="p-1 rounded text-outline hover:text-amber-400 hover:bg-amber-500/10 transition-colors"
                    :title="$t('applications.table.openFolder')"
                    type="button"
                    @click="$emit('open-folder', item)"
                  >
                    <span class="material-symbols-outlined text-[16px] block">folder_open</span>
                  </button>

                  <!-- Cambiar estado / notas -->
                  <button
                    class="p-1 rounded text-outline hover:text-on-surface hover:bg-surface-container transition-colors"
                    :title="$t('applications.table.editNotes')"
                    type="button"
                    @click="$emit('open-status', item)"
                  >
                    <span class="material-symbols-outlined text-[15px] block">flag</span>
                  </button>

                  <!-- Desplegar historial -->
                  <button
                    :class="[
                      'p-1 rounded text-outline hover:text-on-surface hover:bg-surface-container transition-colors',
                      expandedRows.has(item.id) ? 'text-accent bg-surface-container' : ''
                    ]"
                    :title="$t('applications.table.colNotes')"
                    type="button"
                    @click="$emit('toggle-expand-row', item.id)"
                  >
                    <span class="material-symbols-outlined text-[16px] block transition-transform duration-150" :class="{ 'rotate-180': expandedRows.has(item.id) }">
                      expand_more
                    </span>
                  </button>

                  <!-- Eliminar -->
                  <button
                    class="p-1 rounded text-outline hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                    :title="$t('applications.table.deleteApp')"
                    type="button"
                    @click="$emit('remove', item)"
                  >
                    <span class="material-symbols-outlined text-[15px] block">delete</span>
                  </button>
                </div>
              </td>
            </tr>

            <!-- EXPANDED ROW (Historial de eventos y notas) -->
            <tr v-if="expandedRows.has(item.id)" class="bg-surface-container/20 border-b border-border-subtle">
              <td class="px-6 py-4" colspan="6">
                <div class="flex flex-col gap-3">
                  <div class="flex items-center justify-between border-b border-border-subtle pb-2">
                    <span class="font-mono text-[11px] uppercase tracking-wider text-outline flex items-center gap-1.5">
                      <span class="material-symbols-outlined text-[14px]">history</span>
                      {{ $t('applications.table.colNotes') }}
                    </span>
                    <button
                      class="text-[11px] text-accent hover:underline flex items-center gap-1"
                      type="button"
                      @click="$emit('open-status', item)"
                    >
                      <span class="material-symbols-outlined text-[13px]">edit</span>
                      {{ $t('applications.table.editNotes') }}
                    </button>
                  </div>

                  <!-- Motivo de rechazo -->
                  <div v-if="item.reason" class="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
                    <span class="material-symbols-outlined text-[16px] text-rose-400 shrink-0 mt-0.5">priority_high</span>
                    <div>
                      <span class="font-semibold">{{ $t('status.rejected') }}:</span> {{ item.reason }}
                    </div>
                  </div>

                  <!-- Notas -->
                  <div v-if="item.notes" class="text-xs text-on-surface-variant flex items-start gap-2">
                    <span class="material-symbols-outlined text-[15px] text-outline shrink-0 mt-0.5">notes</span>
                    <span><strong class="text-on-surface">{{ $t('common.notes') }}:</strong> {{ item.notes }}</span>
                  </div>

                  <!-- Eventos cronológicos -->
                  <div v-if="item.history?.length" class="flex flex-col gap-1.5 pt-1">
                    <div
                      v-for="(h, idx) in item.history"
                      :key="idx"
                      class="flex items-center gap-2 text-xs text-on-surface-variant font-mono"
                    >
                      <span class="w-1.5 h-1.5 rounded-full bg-accent shrink-0"></span>
                      <span class="px-1.5 py-0.5 rounded text-[10px] bg-surface-container border border-border-subtle text-outline">
                        {{ fmtDate(h.at) }}
                      </span>
                      <span class="text-on-surface">{{ h.note }}</span>
                    </div>
                  </div>
                  <div v-else class="text-xs text-outline italic">
                    {{ $t('applications.table.noNotes') }}
                  </div>
                </div>
              </td>
            </tr>
          </template>

          <!-- Estado vacío -->
          <tr v-if="paginatedItems.length === 0">
            <td class="py-12 text-center text-outline" colspan="6">
              <div class="flex flex-col items-center justify-center gap-2">
                <span class="material-symbols-outlined text-[36px] text-outline/50">inbox</span>
                <span class="text-xs">{{ $t('applications.table.emptyTitle') }}</span>
                <button
                  class="mt-2 text-xs text-accent hover:underline font-medium"
                  type="button"
                  @click="$emit('reset-filters')"
                >
                  {{ $t('search.presets.reset') }}
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- TABLE FOOTER / PAGINATION -->
    <div class="px-4 py-3 border-t border-border-subtle bg-surface-container/30 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-outline font-mono">
      <div class="flex items-center gap-1.5">
        <span>{{ $t('applications.table.paginationShowing', { from: filteredItemsCount ? (currentPage - 1) * pageSize + 1 : 0, to: Math.min(currentPage * pageSize, filteredItemsCount), total: filteredItemsCount }) }}</span>
      </div>

      <div class="flex items-center gap-1.5">
        <button
          class="px-2.5 py-1 rounded-md bg-surface-container border border-border-subtle text-outline hover:text-on-surface hover:bg-surface-container-high transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="currentPage <= 1"
          type="button"
          @click="$emit('prev-page')"
        >
          {{ $t('applications.table.prevPage') }}
        </button>
        <span class="px-2 text-on-surface font-medium">{{ $t('applications.table.page', { current: currentPage, total: totalPages }) }}</span>
        <button
          class="px-2.5 py-1 rounded-md bg-surface-container border border-border-subtle text-on-surface hover:bg-surface-container-high transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          :disabled="currentPage >= totalPages"
          type="button"
          @click="$emit('next-page')"
        >
          {{ $t('applications.table.nextPage') }}
        </button>
      </div>
    </div>
  </div>
</template>
