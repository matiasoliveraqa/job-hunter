<script setup>
defineProps({
  progress: {
    type: Object,
    required: true,
  },
  scanning: {
    type: Boolean,
    default: false,
  },
  progressPercent: {
    type: Number,
    default: 0,
  },
  matchesCount: {
    type: Number,
    default: 0,
  },
  errorCount: {
    type: Number,
    default: 0,
  },
})
</script>

<template>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
    <!-- KPI 1: Total analizadas -->
    <div class="p-4 rounded-xl bg-surface border border-border-subtle flex flex-col justify-between relative overflow-hidden shadow-sm">
      <div class="flex items-center justify-between text-on-surface-variant mb-2">
        <span class="text-xs font-medium">{{ $t('search.kpi.totalAnalyzed') }}</span>
        <span class="material-symbols-outlined text-[15px] text-outline">analytics</span>
      </div>
      <div class="flex items-end justify-between">
        <div class="flex flex-col">
          <span class="text-2xl font-bold font-mono tracking-tight text-on-surface">
            {{ progress.total || (scanning ? progress.checked : 0) }}
          </span>
          <div class="flex items-center gap-1 text-[11px] font-mono text-emerald-400 mt-0.5">
            <span class="material-symbols-outlined text-[13px]">
              {{ scanning ? 'sync' : 'arrow_upward' }}
            </span>
            <span>{{ progressPercent }}% {{ $t('search.kpi.completed') }}</span>
          </div>
        </div>
        <!-- Sparkline SVG -->
        <div class="w-24 h-10">
          <svg class="w-full h-full stroke-emerald-500 fill-none" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" viewBox="0 0 100 35">
            <path d="M 0 30 Q 15 28, 25 20 T 50 15 T 75 8 T 100 2"></path>
          </svg>
        </div>
      </div>
    </div>

    <!-- KPI 2: Vacantes encontradas -->
    <div class="p-4 rounded-xl bg-surface border border-border-subtle flex flex-col justify-between relative overflow-hidden shadow-sm">
      <div class="flex items-center justify-between text-on-surface-variant mb-2">
        <span class="text-xs font-medium">{{ $t('search.kpi.openingsFound') }}</span>
        <span class="material-symbols-outlined text-[15px] text-outline">travel_explore</span>
      </div>
      <div class="flex items-end justify-between">
        <div class="flex flex-col">
          <span class="text-2xl font-bold font-mono tracking-tight text-accent">
            {{ matchesCount }}
          </span>
          <div class="flex items-center gap-1 text-[11px] font-mono text-accent mt-0.5">
            <span class="material-symbols-outlined text-[13px]">add</span>
            <span>{{ matchesCount }} {{ $t('search.kpi.qualified') }}</span>
          </div>
        </div>
        <!-- Sparkline SVG -->
        <div class="w-24 h-10">
          <svg class="w-full h-full stroke-blue-500 fill-none" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" viewBox="0 0 100 35">
            <path d="M 0 25 L 20 28 L 40 16 L 60 22 L 80 8 L 100 4"></path>
          </svg>
        </div>
      </div>
    </div>

    <!-- KPI 3: Empresas activas / analizadas -->
    <div class="p-4 rounded-xl bg-surface border border-border-subtle flex flex-col justify-between relative overflow-hidden shadow-sm">
      <div class="flex items-center justify-between text-on-surface-variant mb-2">
        <span class="text-xs font-medium">{{ $t('search.kpi.companiesAnalyzed') }}</span>
        <span class="material-symbols-outlined text-[15px] text-outline">domain</span>
      </div>
      <div class="flex items-end justify-between">
        <div class="flex flex-col">
          <span class="text-2xl font-bold font-mono tracking-tight text-on-surface">
            {{ progress.checked }}
          </span>
          <div class="flex items-center gap-1 text-[11px] font-mono text-amber-400 mt-0.5">
            <span class="material-symbols-outlined text-[13px]">trending_up</span>
            <span>{{ progress.platform ? progress.platform.toUpperCase() : $t('search.kpi.atsBoards') }}</span>
          </div>
        </div>
        <!-- Sparkline SVG -->
        <div class="w-24 h-10">
          <svg class="w-full h-full stroke-amber-500 fill-none" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" viewBox="0 0 100 35">
            <path d="M 0 32 Q 25 10, 45 22 T 80 18 T 100 12"></path>
          </svg>
        </div>
      </div>
    </div>

    <!-- KPI 4: Errores / descartadas -->
    <div class="p-4 rounded-xl bg-surface border border-border-subtle flex flex-col justify-between relative overflow-hidden shadow-sm">
      <div class="flex items-center justify-between text-on-surface-variant mb-2">
        <span class="text-xs font-medium">{{ $t('search.kpi.errors') }}</span>
        <span class="material-symbols-outlined text-[15px] text-outline">error_outline</span>
      </div>
      <div class="flex items-end justify-between">
        <div class="flex flex-col">
          <span class="text-2xl font-bold font-mono tracking-tight text-on-surface">
            {{ errorCount }}
          </span>
          <div class="flex items-center gap-1 text-[11px] font-mono text-outline mt-0.5">
            <span class="material-symbols-outlined text-[13px]">
              {{ errorCount === 0 ? 'check_circle' : 'warning' }}
            </span>
            <span>{{ errorCount === 0 ? $t('search.kpi.zeroErrors') : $t('search.kpi.incidents', { count: errorCount }) }}</span>
          </div>
        </div>
        <!-- Sparkline SVG -->
        <div class="w-24 h-10">
          <svg class="w-full h-full stroke-zinc-600 fill-none" stroke-linecap="round" stroke-width="2" viewBox="0 0 100 35">
            <path d="M 0 30 L 30 30 L 50 30 L 70 30 L 100 30"></path>
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>
