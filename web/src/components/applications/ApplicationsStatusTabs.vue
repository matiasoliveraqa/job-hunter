<script setup>
defineProps({
  counts: {
    type: Array,
    required: true,
  },
  filterStatus: {
    type: String,
    default: null,
  },
  totalCount: {
    type: Number,
    default: 0,
  },
  statusStyles: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['update:filterStatus'])

function setStatus(key) {
  emit('update:filterStatus', key)
}
</script>

<template>
  <div class="flex items-center gap-1.5 overflow-x-auto pb-1 border-b border-border-subtle text-xs font-medium">
    <button
      type="button"
      :class="[
        'px-3 py-1.5 rounded-lg flex items-center gap-2 transition-colors whitespace-nowrap',
        filterStatus === null
          ? 'bg-surface-container-highest text-on-surface shadow-sm'
          : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
      ]"
      @click="setStatus(null)"
    >
      <span>{{ $t('applications.filterTabs.all') }}</span>
      <span class="px-1.5 py-0.2 rounded-md bg-surface-dim text-[11px] font-mono text-outline">{{ totalCount }}</span>
    </button>

    <button
      v-for="c in counts"
      :key="c.key"
      type="button"
      :class="[
        'px-3 py-1.5 rounded-lg flex items-center gap-2 transition-colors whitespace-nowrap',
        filterStatus === c.key
          ? 'bg-surface-container-highest text-on-surface shadow-sm'
          : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
      ]"
      @click="setStatus(filterStatus === c.key ? null : c.key)"
    >
      <span :class="['w-2 h-2 rounded-full', statusStyles[c.key]?.dot || 'bg-outline']"></span>
      <span>{{ c.title }}</span>
      <span class="px-1.5 py-0.2 rounded-md bg-surface-container text-[11px] font-mono text-outline">{{ c.count }}</span>
    </button>
  </div>
</template>
