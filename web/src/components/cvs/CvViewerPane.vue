<script setup>
defineProps({
  selectedCv: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits([
  'open-associated-vacancy',
  'go-to-applications',
  'copy-path',
  'download-pdf',
  'open-in-new-tab',
])
</script>

<template>
  <div class="xl:col-span-7 2xl:col-span-8 flex flex-col rounded-xl overflow-hidden bg-surface-card border border-border-subtle shadow-lg">
    <!-- VIEWER TOP TOOLBAR -->
    <div class="h-14 px-4 bg-surface-container border-b border-border-subtle flex items-center justify-between gap-3 select-none flex-wrap">
      <!-- Left: Title & ATS Badge -->
      <div class="flex items-center gap-2.5 min-w-0">
        <span class="material-symbols-outlined text-[18px] text-accent">description</span>
        <div class="flex flex-col min-w-0">
          <span class="text-xs font-semibold text-on-surface truncate max-w-xs md:max-w-md">
            {{ selectedCv?.company }} · {{ selectedCv?.role }}
          </span>
          <span class="font-mono text-[10px] text-outline truncate">
            {{ selectedCv?.fileName || $t('cvs.detail.noFileSelected') }}
          </span>
        </div>
        <span
          class="hidden sm:inline-flex items-center px-2 py-0.5 rounded font-mono text-[10px] ml-1"
          :class="[
            selectedCv?.isBase
              ? 'bg-surface-container-highest text-on-surface-variant'
              : 'bg-accent/15 text-accent border border-accent/20'
          ]"
        >
          {{ selectedCv?.isBase ? $t('cvs.detail.baseCv') : `${selectedCv?.platform} ATS-Ready` }}
        </span>
      </div>

      <!-- Right: Actions -->
      <div class="flex items-center gap-1.5 flex-wrap">
        <!-- BOTÓN: VER VACANTE ASOCIADA -->
        <button
          v-if="selectedCv?.applicationUrl"
          class="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/30 text-xs font-medium transition-colors shadow-sm"
          :title="$t('cvs.detail.openVacancyTip')"
          type="button"
          @click="$emit('open-associated-vacancy', selectedCv)"
        >
          <span class="material-symbols-outlined text-[15px]">open_in_new</span>
          <span>{{ $t('cvs.detail.openVacancy') }}</span>
        </button>

        <!-- BOTÓN: VER EN POSTULACIONES -->
        <button
          v-if="selectedCv?.applicationId"
          class="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-surface-container-high hover:bg-surface-container-highest text-on-surface text-xs font-medium border border-border-subtle transition-colors"
          :title="$t('cvs.detail.goToAppTip')"
          type="button"
          @click="$emit('go-to-applications', selectedCv)"
        >
          <span class="material-symbols-outlined text-[15px] text-accent">send</span>
          <span>{{ $t('cvs.detail.goToApp') }}</span>
        </button>

        <!-- Quick icon actions -->
        <button
          class="p-1.5 rounded hover:bg-surface-container-high text-outline hover:text-on-surface transition-colors"
          :title="$t('cvs.detail.copyPathTip')"
          type="button"
          @click="$emit('copy-path', selectedCv)"
        >
          <span class="material-symbols-outlined text-[17px]">content_copy</span>
        </button>

        <button
          class="p-1.5 rounded hover:bg-surface-container-high text-outline hover:text-on-surface transition-colors"
          :title="$t('cvs.detail.downloadTip')"
          type="button"
          @click="$emit('download-pdf', selectedCv)"
        >
          <span class="material-symbols-outlined text-[17px]">download</span>
        </button>

        <button
          class="p-1.5 rounded hover:bg-surface-container-high text-outline hover:text-on-surface transition-colors"
          :title="$t('cvs.detail.openNewTabTip')"
          type="button"
          @click="$emit('open-in-new-tab', selectedCv)"
        >
          <span class="material-symbols-outlined text-[17px]">open_in_browser</span>
        </button>
      </div>
    </div>

    <!-- VIEWER DESK / REAL PDF CANVAS -->
    <div class="p-2 sm:p-4 bg-surface-dim/95 flex justify-center items-center viewer-desk">
      <iframe
        v-if="selectedCv?.downloadUrl"
        :key="selectedCv.downloadUrl"
        class="viewer-frame rounded-md border border-border-subtle shadow-2xl"
        :src="selectedCv.downloadUrl"
        :title="$t('cvs.detail.previewFrameTitle')"
      />
      <div
        v-else
        class="flex flex-col items-center justify-center p-12 text-center text-outline gap-2"
      >
        <span class="material-symbols-outlined text-4xl text-outline">description</span>
        <span class="text-xs font-mono">{{ $t('cvs.detail.selectCvPrompt') }}</span>
      </div>
    </div>

    <!-- VIEWER BOTTOM METADATA BAR -->
    <div class="h-10 px-4 bg-surface-container border-t border-border-subtle flex items-center justify-between text-outline font-mono text-[11px] flex-wrap gap-2">
      <div class="flex items-center gap-2.5">
        <span>{{ $t('cvs.detail.fileLabel') }} <code class="text-on-surface-variant">{{ selectedCv?.fileName }}</code></span>
        <span>•</span>
        <span>{{ $t('cvs.detail.sizeLabel') }} <span class="text-on-surface">{{ selectedCv?.formattedSize }}</span></span>
        <span class="hidden md:inline">•</span>
        <span class="hidden md:inline">{{ $t('cvs.detail.modifiedLabel') }} <span class="text-on-surface">{{ selectedCv?.fullDate }}</span></span>
      </div>

      <div class="flex items-center gap-2.5">
        <span
          v-if="selectedCv?.applicationStatus"
          class="inline-flex items-center gap-1 text-sky-400"
        >
          <span class="material-symbols-outlined text-[13px]">verified</span>
          {{ $t('cvs.detail.applicationStatus', { status: $t('status.' + selectedCv.applicationStatus) }) }}
        </span>
        <span v-else class="text-outline">
          {{ selectedCv?.isBase ? $t('cvs.detail.baseTemplate') : $t('cvs.detail.localTailored') }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.viewer-desk {
  min-height: 640px;
}
.viewer-frame {
  width: 100%;
  height: calc(100vh - 360px);
  min-height: 620px;
  background-color: #1e1e20;
}
</style>
