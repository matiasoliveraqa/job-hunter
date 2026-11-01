<script setup>
defineProps({
  stats: {
    type: Object,
    required: true,
  },
  totalSparkline: {
    type: Object,
    required: true,
  },
  tailoredSparkline: {
    type: Object,
    required: true,
  },
  activeSparkline: {
    type: Object,
    required: true,
  },
})
</script>

<template>
  <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <!-- KPI 1: TOTAL CVS GENERADOS -->
    <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
      <div class="flex items-center justify-between">
        <span class="text-[11px] font-mono uppercase tracking-wider text-outline">{{ $t('cvs.kpi.totalGenerated') }}</span>
        <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-container-high text-accent font-mono text-[11px]">
          {{ $t('cvs.kpi.thisWeek', { count: stats.recentWeek }) }}
        </span>
      </div>
      <div class="flex items-baseline justify-between mt-3 mb-1">
        <span class="text-2xl font-semibold text-on-surface tracking-tight">{{ stats.total }}</span>
        <span class="font-mono text-xs text-outline">output/applications/*</span>
      </div>
      <div class="h-7 w-full mt-1">
        <svg class="w-full h-full text-accent overflow-visible" fill="none" preserveAspectRatio="none" viewBox="0 0 100 28">
          <path :d="totalSparkline.linePath" stroke="currentColor" stroke-linecap="round" stroke-width="1.75" />
          <path :d="totalSparkline.areaPath" fill="currentColor" fill-opacity="0.08" />
        </svg>
      </div>
    </div>

    <!-- KPI 2: ADAPTACIONES ATS -->
    <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
      <div class="flex items-center justify-between">
        <span class="text-[11px] font-mono uppercase tracking-wider text-outline">{{ $t('cvs.kpi.atsTailored') }}</span>
        <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-container-high text-sky-400 font-mono text-[11px]">
          {{ $t('cvs.kpi.atsPlatforms') }}
        </span>
      </div>
      <div class="flex items-baseline justify-between mt-3 mb-1">
        <span class="text-2xl font-semibold text-on-surface tracking-tight">
          {{ stats.tailored }} <span class="text-xs text-outline font-normal">/ {{ stats.total }}</span>
        </span>
        <span class="font-mono text-xs text-sky-400">{{ $t('cvs.kpi.tailoredRatio', { ratio: stats.tailoredRatio }) }}</span>
      </div>
      <div class="h-7 w-full mt-1">
        <svg class="w-full h-full text-sky-400 overflow-visible" fill="none" preserveAspectRatio="none" viewBox="0 0 100 28">
          <path :d="tailoredSparkline.linePath" stroke="currentColor" stroke-linecap="round" stroke-width="1.75" />
          <path :d="tailoredSparkline.areaPath" fill="currentColor" fill-opacity="0.08" />
        </svg>
      </div>
    </div>

    <!-- KPI 3: POSTULACIONES ACTIVAS -->
    <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
      <div class="flex items-center justify-between">
        <span class="text-[11px] font-mono uppercase tracking-wider text-outline">{{ $t('cvs.kpi.activeApps') }}</span>
        <span class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-surface-container-high text-amber-400 font-mono text-[11px]">
          {{ $t('cvs.kpi.inTracking') }}
        </span>
      </div>
      <div class="flex items-baseline justify-between mt-3 mb-1">
        <span class="text-2xl font-semibold text-amber-400 tracking-tight">{{ stats.activeCount }}</span>
        <span class="font-mono text-xs text-outline">{{ $t('cvs.kpi.inProcessRatio', { ratio: stats.activeRatio }) }}</span>
      </div>
      <div class="h-7 w-full mt-1">
        <svg class="w-full h-full text-amber-400 overflow-visible" fill="none" preserveAspectRatio="none" viewBox="0 0 100 28">
          <path :d="activeSparkline.linePath" stroke="currentColor" stroke-linecap="round" stroke-width="1.75" />
          <path :d="activeSparkline.areaPath" fill="currentColor" fill-opacity="0.08" />
        </svg>
      </div>
    </div>

    <!-- KPI 4: ALMACENAMIENTO LOCAL -->
    <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
      <div class="flex items-center justify-between">
        <span class="text-[11px] font-mono uppercase tracking-wider text-outline">{{ $t('cvs.kpi.localStorage') }}</span>
        <span class="inline-flex items-center gap-1.5 text-emerald-400 font-mono text-[11px]">
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          {{ $t('cvs.kpi.synced') }}
        </span>
      </div>
      <div class="flex items-baseline justify-between mt-3 mb-1">
        <span class="text-2xl font-semibold text-on-surface tracking-tight">
          {{ stats.totalMb }} <span class="text-xs text-outline font-normal">MB</span>
        </span>
        <span class="font-mono text-xs text-outline">{{ $t('cvs.kpi.avgPerPdf', { avg: stats.avgKb }) }}</span>
      </div>
      <div class="w-full bg-surface-container-high h-1.5 rounded-full overflow-hidden mt-3">
        <div class="bg-accent h-full rounded-full transition-all" style="width: 28%;"></div>
      </div>
    </div>
  </section>
</template>
