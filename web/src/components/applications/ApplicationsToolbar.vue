<script setup>
defineProps({
  search: {
    type: String,
    default: '',
  },
  selectedPlatform: {
    type: String,
    default: 'all',
  },
  selectedSort: {
    type: String,
    default: 'recent',
  },
  selectedCount: {
    type: Number,
    default: 0,
  },
})

const emit = defineEmits([
  'update:search',
  'update:selectedPlatform',
  'update:selectedSort',
  'reset-filters',
  'batch-mark-applied',
  'batch-delete',
  'clear-selection',
])
</script>

<template>
  <div class="flex flex-col gap-3">
    <!-- CONTROLS & SEARCH TOOLBAR -->
    <div class="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
      <!-- Search Input -->
      <div class="relative flex-1 max-w-lg">
        <span class="material-symbols-outlined absolute left-3 top-2.5 text-[17px] text-outline pointer-events-none">search</span>
        <input
          :value="search"
          class="w-full pl-9 pr-12 py-2 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:border-accent focus:outline-none placeholder:text-outline transition-colors"
          :placeholder="$t('applications.toolbar.searchPlaceholder')"
          type="text"
          @input="$emit('update:search', $event.target.value)"
        />
        <span
          v-if="search"
          class="absolute right-3 top-2.5 text-outline hover:text-on-surface cursor-pointer text-xs"
          @click="$emit('update:search', '')"
        >✕</span>
      </div>

      <!-- Filters & Actions -->
      <div class="flex items-center gap-2.5 flex-wrap">
        <!-- ATS Selector -->
        <div class="relative">
          <select
            :value="selectedPlatform"
            class="appearance-none pl-3 pr-8 py-2 rounded-lg bg-surface-container text-on-surface-variant text-xs border border-border-subtle hover:border-border-muted focus:border-accent focus:outline-none transition-colors cursor-pointer"
            @change="$emit('update:selectedPlatform', $event.target.value)"
          >
            <option value="all">{{ $t('applications.toolbar.allPlatforms') }}</option>
            <option value="greenhouse">Greenhouse ATS</option>
            <option value="lever">Lever ATS</option>
            <option value="ashby">Ashby ATS</option>
            <option value="workable">Workable ATS</option>
            <option value="breezy">Breezy HR</option>
            <option value="recruitee">Recruitee ATS</option>
            <option value="bamboohr">BambooHR ATS</option>
            <option value="direct">{{ $t('applications.toolbar.directApply') }}</option>
          </select>
          <span class="material-symbols-outlined absolute right-2 top-2.5 text-[16px] text-outline pointer-events-none">arrow_drop_down</span>
        </div>

        <!-- Sorting Selector -->
        <div class="relative">
          <select
            :value="selectedSort"
            class="appearance-none pl-3 pr-8 py-2 rounded-lg bg-surface-container text-on-surface-variant text-xs border border-border-subtle hover:border-border-muted focus:border-accent focus:outline-none transition-colors cursor-pointer"
            @change="$emit('update:selectedSort', $event.target.value)"
          >
            <option value="recent">{{ $t('applications.toolbar.sortRecent') }}</option>
            <option value="oldest">{{ $t('applications.toolbar.sortOldest') }}</option>
            <option value="company">{{ $t('applications.toolbar.sortCompany') }}</option>
            <option value="status">{{ $t('common.status') }}</option>
          </select>
          <span class="material-symbols-outlined absolute right-2 top-2.5 text-[16px] text-outline pointer-events-none">sort</span>
        </div>

        <!-- Reset button -->
        <button
          class="px-2.5 py-2 rounded-lg bg-surface-container text-outline hover:text-on-surface border border-border-subtle text-xs transition-colors"
          :title="$t('search.presets.reset')"
          type="button"
          @click="$emit('reset-filters')"
        >
          <span class="material-symbols-outlined text-[16px] block">filter_alt_off</span>
        </button>
      </div>
    </div>

    <!-- BATCH ACTIONS FLOATING BAR -->
    <div
      v-if="selectedCount > 0"
      class="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-accent/10 border border-accent/30 text-on-surface text-xs animate-in fade-in duration-150"
    >
      <span class="font-mono text-accent font-semibold">{{ $t('applications.toolbar.selectedCount', { count: selectedCount }) }}</span>
      <span class="text-border-muted">•</span>
      <button
        class="hover:text-accent font-medium transition-colors inline-flex items-center gap-1.5"
        type="button"
        @click="$emit('batch-mark-applied')"
      >
        <span class="material-symbols-outlined text-[15px]">done_all</span>
        {{ $t('applications.toolbar.changeStatus') }}
      </button>
      <span class="text-border-muted">•</span>
      <button
        class="hover:text-rose-400 font-medium transition-colors inline-flex items-center gap-1.5"
        type="button"
        @click="$emit('batch-delete')"
      >
        <span class="material-symbols-outlined text-[15px]">delete</span>
        {{ $t('applications.toolbar.deleteSelected', { count: selectedCount }) }}
      </button>
      <button
        class="text-outline hover:text-on-surface ml-auto p-1 rounded hover:bg-surface-container transition-colors"
        :title="$t('applications.toolbar.clearSelection')"
        type="button"
        @click="$emit('clear-selection')"
      >
        <span class="material-symbols-outlined text-[16px] block">close</span>
      </button>
    </div>
  </div>
</template>
