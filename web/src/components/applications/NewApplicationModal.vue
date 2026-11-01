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
  cvItems: {
    type: Array,
    default: () => [],
  },
  newFormOpened: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['close', 'register', 'launch-form'])
</script>

<template>
  <div
    v-if="show"
    class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
  >
    <div class="bg-surface-card border border-border-muted w-full max-w-lg rounded-xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-150">
      <div class="px-5 py-4 border-b border-border-subtle flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="material-symbols-outlined text-accent text-[20px]">add_circle</span>
          <h3 class="text-sm font-semibold text-on-surface">{{ $t('applications.dialogs.newTitle') }}</h3>
        </div>
        <button class="text-outline hover:text-on-surface p-1 rounded-md hover:bg-surface-container transition-colors" type="button" @click="$emit('close')">
          <span class="material-symbols-outlined text-[18px] block">close</span>
        </button>
      </div>

      <form class="p-5 flex flex-col gap-4 text-xs" @submit.prevent="$emit('register')">
        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-outline mb-1.5">{{ $t('applications.dialogs.companyLabel') }} *</label>
          <input
            v-model="dialog.form.company"
            class="w-full px-3 py-2 rounded-lg bg-surface-container border border-border-subtle text-on-surface text-xs focus:border-accent focus:outline-none"
            :placeholder="$t('applications.dialogs.companyPlaceholder')"
            required
            type="text"
          />
        </div>

        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-outline mb-1.5">{{ $t('applications.dialogs.roleLabel') }} *</label>
          <input
            v-model="dialog.form.role"
            class="w-full px-3 py-2 rounded-lg bg-surface-container border border-border-subtle text-on-surface text-xs focus:border-accent focus:outline-none"
            :placeholder="$t('applications.dialogs.rolePlaceholder')"
            required
            type="text"
          />
        </div>

        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-outline mb-1.5">{{ $t('applications.dialogs.urlLabel') }}</label>
          <input
            v-model="dialog.form.url"
            class="w-full px-3 py-2 rounded-lg bg-surface-container border border-border-subtle text-on-surface text-xs focus:border-accent focus:outline-none"
            :placeholder="$t('applications.dialogs.urlPlaceholder')"
            type="url"
          />
        </div>

        <div>
          <label class="block text-[11px] font-mono uppercase tracking-wider text-outline mb-1.5">{{ $t('applications.dialogs.cvLabel') }}</label>
          <select
            v-model="dialog.form.cv"
            class="w-full px-3 py-2 rounded-lg bg-surface-container border border-border-subtle text-on-surface text-xs focus:border-accent focus:outline-none cursor-pointer"
          >
            <option value="">{{ $t('applications.dialogs.cvNone') }}</option>
            <option v-for="cv in cvItems" :key="cv" :value="cv">{{ cv }}</option>
          </select>
        </div>

        <div class="p-3 rounded-lg bg-surface-container/60 border border-border-subtle flex items-start gap-2.5">
          <span class="material-symbols-outlined text-accent text-[17px] shrink-0 mt-0.5">info</span>
          <span class="text-[11px] text-on-surface-variant leading-relaxed">
            {{ $t('search.subtitle') }}
          </span>
        </div>

        <div class="pt-3 border-t border-border-subtle flex items-center justify-between gap-2">
          <button
            class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-colors"
            :class="[
              newFormOpened
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                : 'bg-surface-container hover:bg-surface-container-high border-border-subtle text-on-surface'
            ]"
            :disabled="!dialog.form.url"
            type="button"
            @click="$emit('launch-form')"
          >
            <span class="material-symbols-outlined text-[15px]">{{ newFormOpened ? 'check' : 'open_in_browser' }}</span>
            <span>{{ newFormOpened ? $t('common.open') : $t('applications.table.openPlaywright') }}</span>
          </button>

          <div class="flex items-center gap-2">
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
              {{ $t('applications.dialogs.saveApp') }}
            </button>
          </div>
        </div>
      </form>
    </div>
  </div>
</template>
