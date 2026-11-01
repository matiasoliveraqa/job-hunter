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
  stats: {
    type: Object,
    required: true,
  },
  filteredFiles: {
    type: Array,
    required: true,
  },
  selectedCv: {
    type: Object,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits([
  'update:search',
  'update:selectedPlatform',
  'select-item',
  'download-pdf',
  'copy-path',
])
</script>

<template>
  <div class="xl:col-span-5 2xl:col-span-4 flex flex-col gap-3 bg-surface-card border border-border-subtle p-3.5 rounded-xl">
    <!-- Search and filter box -->
    <div class="flex flex-col gap-2">
      <div class="relative flex items-center">
        <span class="material-symbols-outlined absolute left-3 text-[17px] text-outline">search</span>
        <input
          :value="search"
          class="w-full pl-9 pr-8 py-1.5 rounded-lg bg-surface-container text-on-surface text-xs placeholder:text-outline border border-border-subtle focus:outline-none focus:border-accent transition-colors"
          :placeholder="$t('cvs.list.searchPlaceholder')"
          type="text"
          @input="$emit('update:search', $event.target.value)"
        />
        <button
          v-if="search"
          class="absolute right-2 text-outline hover:text-on-surface text-xs"
          type="button"
          @click="$emit('update:search', '')"
        >
          ✕
        </button>
      </div>

      <!-- Filter Tabs / Pills -->
      <div class="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
        <button
          class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
          :class="[
            selectedPlatform === 'all'
              ? 'bg-surface-container-high text-on-surface border border-border-muted font-semibold'
              : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
          ]"
          type="button"
          @click="$emit('update:selectedPlatform', 'all')"
        >
          {{ $t('common.all') }} ({{ stats.total }})
        </button>

        <button
          class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
          :class="[
            selectedPlatform === 'Greenhouse'
              ? 'bg-surface-container-high text-sky-400 border border-sky-500/30 font-semibold'
              : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
          ]"
          type="button"
          @click="$emit('update:selectedPlatform', 'Greenhouse')"
        >
          Greenhouse ({{ stats.greenhouse }})
        </button>

        <button
          class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
          :class="[
            selectedPlatform === 'Lever'
              ? 'bg-surface-container-high text-amber-400 border border-amber-500/30 font-semibold'
              : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
          ]"
          type="button"
          @click="$emit('update:selectedPlatform', 'Lever')"
        >
          Lever ({{ stats.lever }})
        </button>

        <button
          class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
          :class="[
            selectedPlatform === 'Ashby'
              ? 'bg-surface-container-high text-emerald-400 border border-emerald-500/30 font-semibold'
              : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
          ]"
          type="button"
          @click="$emit('update:selectedPlatform', 'Ashby')"
        >
          Ashby ({{ stats.ashby }})
        </button>

        <button
          class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
          :class="[
            selectedPlatform === 'Workable'
              ? 'bg-surface-container-high text-blue-400 border border-blue-500/30 font-semibold'
              : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
          ]"
          type="button"
          @click="$emit('update:selectedPlatform', 'Workable')"
        >
          Workable ({{ stats.workable }})
        </button>

        <button
          class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
          :class="[
            selectedPlatform === 'Breezy'
              ? 'bg-surface-container-high text-teal-400 border border-teal-500/30 font-semibold'
              : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
          ]"
          type="button"
          @click="$emit('update:selectedPlatform', 'Breezy')"
        >
          Breezy ({{ stats.breezy }})
        </button>

        <button
          class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
          :class="[
            selectedPlatform === 'Recruitee'
              ? 'bg-surface-container-high text-rose-400 border border-rose-500/30 font-semibold'
              : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
          ]"
          type="button"
          @click="$emit('update:selectedPlatform', 'Recruitee')"
        >
          Recruitee ({{ stats.recruitee }})
        </button>

        <button
          class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
          :class="[
            selectedPlatform === 'BambooHR'
              ? 'bg-surface-container-high text-lime-400 border border-lime-500/30 font-semibold'
              : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
          ]"
          type="button"
          @click="$emit('update:selectedPlatform', 'BambooHR')"
        >
          BambooHR ({{ stats.bamboohr }})
        </button>

        <button
          class="px-2.5 py-1 rounded-md text-xs font-medium transition-colors"
          :class="[
            selectedPlatform === 'Base'
              ? 'bg-surface-container-high text-primary border border-primary/30 font-semibold'
              : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
          ]"
          type="button"
          @click="$emit('update:selectedPlatform', 'Base')"
        >
          Base ({{ stats.base }})
        </button>
      </div>
    </div>

    <!-- Scrollable List of CV Cards -->
    <div class="flex flex-col gap-1.5 max-h-[calc(100vh-340px)] min-h-[520px] overflow-y-auto pr-1">
      <div
        v-if="!filteredFiles.length && !loading"
        class="p-6 text-center text-xs text-outline font-mono bg-surface-container/30 rounded-lg border border-border-subtle"
      >
        {{ $t('cvs.list.emptySearch') }}
      </div>

      <div
        v-for="item in filteredFiles"
        :key="item.key"
        class="p-3 rounded-lg border transition-all flex items-start gap-3 relative group cursor-pointer"
        :class="[
          selectedCv && selectedCv.key === item.key
            ? 'bg-surface-container-high border-accent shadow-sm'
            : 'bg-surface-container/50 border-border-subtle hover:bg-surface-container hover:border-border-muted'
        ]"
        @click="$emit('select-item', item)"
      >
        <!-- PDF Icon Box -->
        <div
          class="w-7 h-8 rounded flex flex-col items-center justify-center shrink-0 transition-colors"
          :class="[
            selectedCv && selectedCv.key === item.key
              ? 'bg-accent/20 text-accent'
              : 'bg-surface-container-highest text-outline group-hover:text-on-surface'
          ]"
        >
          <span class="material-symbols-outlined text-[17px]">picture_as_pdf</span>
        </div>

        <!-- Card Content -->
        <div class="flex flex-col min-w-0 flex-1">
          <div class="flex items-center justify-between gap-2">
            <span
              class="text-xs font-medium truncate"
              :class="[selectedCv && selectedCv.key === item.key ? 'text-accent font-semibold' : 'text-on-surface']"
            >
              {{ item.company }} · {{ item.role }}
            </span>
            <span class="font-mono text-[11px] text-outline shrink-0">{{ item.formattedDate }}</span>
          </div>

          <p class="font-mono text-[11px] text-on-surface-variant truncate mt-0.5">
            {{ item.fileName }}
          </p>

          <div class="flex items-center gap-2 mt-2 font-mono text-[11px] text-outline flex-wrap">
            <span
              class="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-sans"
              :class="[
                item.platform === 'Greenhouse'
                  ? 'bg-sky-500/10 text-sky-400'
                  : item.platform === 'Lever'
                    ? 'bg-amber-500/10 text-amber-400'
                    : item.platform === 'Ashby'
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : item.platform === 'Workable'
                        ? 'bg-blue-500/10 text-blue-400'
                        : item.platform === 'Breezy'
                          ? 'bg-teal-500/10 text-teal-400'
                          : item.platform === 'Recruitee'
                            ? 'bg-rose-500/10 text-rose-400'
                            : item.platform === 'BambooHR'
                              ? 'bg-lime-500/10 text-lime-400'
                              : 'bg-surface-container-highest text-on-surface-variant'
              ]"
            >
              {{ item.company }} • {{ item.platform }}
            </span>
            <span>•</span>
            <span>{{ item.formattedSize }}</span>

            <span
              v-if="item.applicationStatus"
              class="ml-auto inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-sans uppercase"
              :class="[
                item.applicationStatus === 'applied'
                  ? 'bg-sky-500/10 text-sky-400'
                  : item.applicationStatus === 'interview'
                    ? 'bg-amber-500/15 text-amber-300'
                    : item.applicationStatus === 'offer'
                      ? 'bg-emerald-500/15 text-emerald-400'
                      : item.applicationStatus === 'pending'
                        ? 'bg-amber-500/10 text-amber-400'
                        : 'bg-surface-container text-outline'
              ]"
            >
              {{ $t('status.' + item.applicationStatus) }}
            </span>
          </div>
        </div>

        <!-- Quick actions on hover -->
        <div class="absolute right-2 bottom-2 hidden group-hover:flex items-center gap-1 bg-surface-container-highest px-1.5 py-0.5 rounded shadow">
          <button
            class="p-1 hover:text-accent transition-colors text-outline"
            :title="$t('cvs.detail.downloadPdf')"
            type="button"
            @click.stop="$emit('download-pdf', item)"
          >
            <span class="material-symbols-outlined text-[15px]">download</span>
          </button>
          <button
            class="p-1 hover:text-accent transition-colors text-outline"
            :title="$t('cvs.detail.copyLocalPath')"
            type="button"
            @click.stop="$emit('copy-path', item)"
          >
            <span class="material-symbols-outlined text-[15px]">content_copy</span>
          </button>
        </div>
      </div>
    </div>

    <!-- List Footer Counter -->
    <div class="pt-2 flex items-center justify-between font-mono text-[11px] text-outline border-t border-border-subtle">
      <span>{{ $t('cvs.list.fileCount', { shown: filteredFiles.length, total: stats.total }) }}</span>
      <span v-if="selectedPlatform !== 'all'" class="text-accent">{{ $t('cvs.list.activeFilter', { filter: selectedPlatform }) }}</span>
    </div>
  </div>
</template>
