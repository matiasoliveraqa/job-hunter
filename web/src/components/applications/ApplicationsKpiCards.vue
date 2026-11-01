<script setup>
defineProps({
  totalCount: {
    type: Number,
    default: 0,
  },
  last7DaysCount: {
    type: Number,
    default: 0,
  },
  totalSparkline: {
    type: Object,
    required: true,
  },
  activeProcesoCount: {
    type: Number,
    default: 0,
  },
  activeEnviadasCount: {
    type: Number,
    default: 0,
  },
  activePendientesCount: {
    type: Number,
    default: 0,
  },
  activeSparkline: {
    type: Object,
    required: true,
  },
  entrevistasCount: {
    type: Number,
    default: 0,
  },
  responseRatio: {
    type: Number,
    default: 0,
  },
  interviewSparkline: {
    type: Object,
    required: true,
  },
  descartadasTotal: {
    type: Number,
    default: 0,
  },
  rechazadasCount: {
    type: Number,
    default: 0,
  },
  retiradasCount: {
    type: Number,
    default: 0,
  },
  discardedSparkline: {
    type: Object,
    required: true,
  },
})
</script>

<template>
  <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <!-- Card 1: Total Postulaciones -->
    <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
      <div class="flex items-start justify-between">
        <div class="flex flex-col">
          <span class="text-[11px] uppercase tracking-wider text-outline font-mono">{{ $t('applications.kpi.totalRegistered') }}</span>
          <span class="text-[26px] font-semibold text-on-surface tracking-tight mt-1 group-hover:text-primary transition-colors">
            {{ totalCount }}
          </span>
        </div>
        <div class="p-2 rounded-lg bg-surface-container text-accent">
          <span class="material-symbols-outlined text-[20px]">send</span>
        </div>
      </div>
      <div class="flex items-end justify-between mt-4">
        <div class="flex items-center gap-1 text-[11px] text-emerald-400 font-mono">
          <span class="material-symbols-outlined text-[14px]">trending_up</span>
          <span>{{ $t('applications.kpi.thisWeek', { count: last7DaysCount }) }}</span>
        </div>
        <svg class="w-24 h-8 text-accent overflow-visible" fill="none" viewBox="0 0 100 32">
          <path :d="totalSparkline.linePath" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
          <path :d="totalSparkline.areaPath" fill="currentColor" fill-opacity="0.08" />
        </svg>
      </div>
    </div>

    <!-- Card 2: En Proceso Activo -->
    <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
      <div class="flex items-start justify-between">
        <div class="flex flex-col">
          <span class="text-[11px] uppercase tracking-wider text-outline font-mono">{{ $t('applications.kpi.activeInProcess') }}</span>
          <span class="text-[26px] font-semibold text-on-surface tracking-tight mt-1">
            {{ activeProcesoCount }}
          </span>
        </div>
        <div class="p-2 rounded-lg bg-surface-container text-sky-400">
          <span class="material-symbols-outlined text-[20px]">hourglass_top</span>
        </div>
      </div>
      <div class="flex items-end justify-between mt-4">
        <div class="flex items-center gap-1 text-[11px] text-on-surface-variant font-mono">
          <span>{{ $t('applications.kpi.activeRatio', { sent: activeEnviadasCount, pending: activePendientesCount }) }}</span>
        </div>
        <svg class="w-24 h-8 text-sky-400 overflow-visible" fill="none" viewBox="0 0 100 32">
          <path :d="activeSparkline.linePath" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
          <path :d="activeSparkline.areaPath" fill="currentColor" fill-opacity="0.08" />
        </svg>
      </div>
    </div>

    <!-- Card 3: Entrevistas / Ofertas -->
    <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
      <div class="flex items-start justify-between">
        <div class="flex flex-col">
          <span class="text-[11px] uppercase tracking-wider text-outline font-mono">{{ $t('applications.kpi.scheduledInterviews') }}</span>
          <span class="text-[26px] font-semibold text-amber-400 tracking-tight mt-1">
            {{ entrevistasCount }}
          </span>
        </div>
        <div class="p-2 rounded-lg bg-surface-container text-amber-400">
          <span class="material-symbols-outlined text-[20px]">calendar_month</span>
        </div>
      </div>
      <div class="flex items-end justify-between mt-4">
        <div class="flex items-center gap-1 text-[11px] text-amber-400 font-mono">
          <span class="material-symbols-outlined text-[14px]">forum</span>
          <span>{{ $t('applications.kpi.responseRate', { rate: responseRatio }) }}</span>
        </div>
        <svg class="w-24 h-8 text-amber-400 overflow-visible" fill="none" viewBox="0 0 100 32">
          <path :d="interviewSparkline.linePath" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
          <path :d="interviewSparkline.areaPath" fill="currentColor" fill-opacity="0.08" />
        </svg>
      </div>
    </div>

    <!-- Card 4: Descartadas / Retiradas -->
    <div class="p-4 rounded-xl bg-surface-card border border-border-subtle flex flex-col justify-between hover:border-border-muted transition-all group">
      <div class="flex items-start justify-between">
        <div class="flex flex-col">
          <span class="text-[11px] uppercase tracking-wider text-outline font-mono">{{ $t('applications.kpi.discardedTotal') }}</span>
          <span class="text-[26px] font-semibold text-on-surface tracking-tight mt-1">
            {{ descartadasTotal }}
          </span>
        </div>
        <div class="p-2 rounded-lg bg-surface-container text-outline">
          <span class="material-symbols-outlined text-[20px]">do_not_disturb_on</span>
        </div>
      </div>
      <div class="flex items-end justify-between mt-4">
        <div class="flex items-center gap-1 text-[11px] text-outline font-mono">
          <span>{{ $t('applications.kpi.discardedRatio', { rejected: rechazadasCount, withdrawn: retiradasCount }) }}</span>
        </div>
        <svg class="w-24 h-8 text-rose-500/60 overflow-visible" fill="none" viewBox="0 0 100 32">
          <path :d="discardedSparkline.linePath" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" />
          <path :d="discardedSparkline.areaPath" fill="currentColor" fill-opacity="0.08" />
        </svg>
      </div>
    </div>
  </section>
</template>
