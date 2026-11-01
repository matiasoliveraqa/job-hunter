<script setup>
defineProps({
  show: {
    type: Boolean,
    default: false,
  },
  dialog: {
    type: Object,
    required: true,
  },
  statusStyles: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['close', 'save'])
</script>

<template>
  <div
    v-if="show"
    class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
  >
    <div class="bg-surface-card border border-border-muted w-full max-w-md rounded-xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
      <div class="px-5 py-4 border-b border-border-subtle flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-accent text-[20px]">flag</span>
          <div class="flex flex-col leading-tight">
            <h3 class="text-sm font-semibold text-on-surface">{{ dialog.item?.company }}</h3>
            <span class="text-[11px] text-outline">{{ dialog.item?.role }}</span>
          </div>
        </div>
        <button class="text-outline hover:text-on-surface p-1 rounded-md hover:bg-surface-container transition-colors" type="button" @click="$emit('close')">
          <span class="material-symbols-outlined text-[18px] block">close</span>
        </button>
      </div>

      <form class="p-5 flex flex-col gap-4 text-xs" @submit.prevent="$emit('save')">
        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-outline mb-1.5">{{ $t('common.status') }}</label>
          <select
            v-model="dialog.status"
            class="w-full px-3 py-2 rounded-lg bg-surface-container border border-border-subtle text-on-surface text-xs focus:border-accent focus:outline-none cursor-pointer"
          >
            <option value="pending">{{ statusStyles.pending?.label }}</option>
            <option value="applied">{{ statusStyles.applied?.label }}</option>
            <option value="interview">{{ statusStyles.interview?.label }}</option>
            <option value="offer">{{ statusStyles.offer?.label }}</option>
            <option value="rejected">{{ statusStyles.rejected?.label }}</option>
            <option value="withdrawn">{{ statusStyles.withdrawn?.label }}</option>
            <option value="not_sent">{{ statusStyles.not_sent?.label }}</option>
          </select>
        </div>

        <div v-if="dialog.status === 'rejected'">
          <label class="block text-[11px] font-mono uppercase tracking-wider text-rose-400 mb-1.5">
            {{ $t('status.rejected') }} ({{ $t('common.confirm') }})
          </label>
          <textarea
            v-model="dialog.reason"
            class="w-full px-3 py-2 rounded-lg bg-surface-container border border-rose-500/30 text-on-surface text-xs focus:border-rose-400 focus:outline-none"
            placeholder="Ej: Requisito de residencia US no cumplido, nivel de inglés..."
            rows="2"
          ></textarea>
        </div>

        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-outline mb-1.5">{{ $t('common.notes') }}</label>
          <textarea
            v-model="dialog.notes"
            class="w-full px-3 py-2 rounded-lg bg-surface-container border border-border-subtle text-on-surface text-xs focus:border-accent focus:outline-none"
            placeholder="Detalles de entrevistas, contacto con recruiter, seguimiento..."
            rows="3"
          ></textarea>
        </div>

        <div class="pt-3 border-t border-border-subtle flex items-center justify-end gap-2">
          <button
            class="px-3 py-1.5 rounded-lg text-outline hover:text-on-surface hover:bg-surface-container transition-colors"
            type="button"
            @click="$emit('close')"
          >
            {{ $t('common.cancel') }}
          </button>
          <button
            class="px-4 py-1.5 rounded-lg bg-accent hover:bg-accent-hover text-white font-medium shadow-sm transition-colors"
            type="submit"
          >
            {{ $t('common.save') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
