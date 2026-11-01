<script setup>
import { formatCompanyName } from '../../api.js'

defineProps({
  scanning: {
    type: Boolean,
    default: false,
  },
  progress: {
    type: Object,
    required: true,
  },
  progressPercent: {
    type: Number,
    default: 0,
  },
})
</script>

<template>
  <div
    v-if="scanning"
    class="p-4 rounded-xl bg-surface border border-accent/30 flex flex-col gap-3 shadow-sm"
  >
    <div class="flex items-center justify-between flex-wrap gap-2">
      <div class="flex items-center gap-2">
        <span class="w-2.5 h-2.5 rounded-full bg-accent animate-ping"></span>
        <span class="text-xs font-semibold text-on-surface">{{ $t('search.live.scanningRealtime') }}</span>
        <span v-if="progress.company" class="text-xs font-mono text-outline">
          [{{ progress.platform.toUpperCase() }}] {{ formatCompanyName(progress.company) }}
        </span>
      </div>
      <div class="text-xs font-mono text-on-surface-variant">
        {{ $t('search.live.companiesProgress', { checked: progress.checked, total: progress.total, percent: progressPercent }) }}
      </div>
    </div>
    <div class="w-full bg-surface-container h-2 rounded-full overflow-hidden">
      <div
        class="bg-accent h-full rounded-full transition-all duration-300"
        :style="{ width: progressPercent + '%' }"
      ></div>
    </div>
  </div>
</template>
