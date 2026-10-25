<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from './api.js'
import { initTheme, isDark, toggleTheme } from './theme.js'
import { appStats, refreshAppStats } from './stats.js'
import { scanning, startScan, stopScan, lastScanTime, initScanSync } from './scanController.js'
import { currentLang, toggleLanguage, t } from './i18n/index.js'

const route = useRoute()
const router = useRouter()

const collapsed = ref(false)
const profile = ref(null)

const candidateName = computed(() => profile.value?.personal_info?.full_name || t('nav.candidateDefault'))
const candidateRole = computed(() => profile.value?.search_criteria?.target_roles?.[0] || t('nav.profileDefault'))
const candidateInitials = computed(() => {
  const name = candidateName.value
  if (!name || name === t('nav.candidateDefault') || name === 'Candidato' || name === 'Candidate') return 'C'
  const parts = name.trim().split(/\s+/)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
})

const navLinks = computed(() => [
  { to: '/search', label: t('nav.search'), icon: 'travel_explore' },
  { to: '/applications', label: t('nav.applications'), icon: 'send', countKey: 'applications' },
  { to: '/cvs', label: t('nav.cvs'), icon: 'description', countKey: 'cvs' },
  { to: '/profile', label: t('nav.profile'), icon: 'badge' },
  { to: '/exclusions', label: t('nav.exclusions'), icon: 'do_not_disturb_on', countKey: 'exclusions' },
])

const pageTitle = computed(() => {
  const match = navLinks.value.find((l) => l.to === route.path)
  return match ? match.label : t('nav.dashboard')
})

const isSearchRoute = computed(() => route.path === '/search')

async function handleScanAction() {
  if (scanning.value) {
    await stopScan()
  } else {
    try {
      await startScan()
    } catch (e) {
      // error reportado en SearchView
    }
  }
}


async function loadProfileData() {
  try {
    profile.value = await api.getProfile()
  } catch {}
}

const agentStatus = ref({
  connected: false,
  activeProviderName: 'Comprobando...',
  activeProvider: 'none',
})

async function checkAgent() {
  try {
    agentStatus.value = await api.getAgentStatus()
  } catch {
    agentStatus.value = {
      connected: false,
      activeProviderName: 'Sin motor de IA',
      activeProvider: 'none',
    }
  }
}

onMounted(() => {
  initTheme()
  refreshAppStats()
  loadProfileData()
  checkAgent()
  initScanSync()
})
</script>

<template>
  <v-app class="!bg-surface-dim font-sans antialiased text-[13px] selection:bg-accent selection:text-white">
    <!-- SIDEBAR (Nexora / Obsidian Style) -->
    <aside
      :class="[
        'fixed left-0 top-0 h-screen bg-surface border-r border-border-subtle flex flex-col justify-between z-50 transition-all duration-200',
        collapsed ? 'w-16' : 'w-60'
      ]"
    >
      <div class="flex flex-col min-h-0 overflow-y-auto">
        <!-- Workspace Brand -->
        <div
          :class="[
            'h-14 border-b border-border-subtle flex items-center shrink-0 transition-all',
            collapsed ? 'justify-center px-2' : 'justify-between px-4'
          ]"
        >
          <!-- Expanded: Logo Lockup (Isotype + Text) -->
          <router-link
            v-if="!collapsed"
            to="/search"
            class="flex items-center gap-2.5 overflow-hidden group cursor-pointer no-underline min-w-0"
            title="Job Hunter"
          >
            <img
              src="/isotype.png"
              alt="Job Hunter"
              class="w-7 h-7 object-contain shrink-0 select-none drop-shadow-sm transition-transform duration-200 group-hover:scale-105"
            />
            <div class="flex flex-col leading-tight truncate">
              <span class="font-semibold text-on-surface text-[14px] tracking-tight group-hover:text-accent transition-colors">
                Job Hunter
              </span>
            </div>
          </router-link>

          <!-- Collapsed: Centered Isotype Icon with toggle -->
          <button
            v-else
            class="p-1 rounded-lg hover:bg-surface-container transition-all group flex items-center justify-center"
            :title="$t('nav.expandMenu')"
            @click="collapsed = false"
          >
            <img
              src="/isotype.png"
              alt="Job Hunter"
              class="w-8 h-8 object-contain select-none drop-shadow-sm transition-transform duration-200 group-hover:scale-110"
            />
          </button>

          <!-- Collapse button (expanded only) -->
          <button
            v-if="!collapsed"
            class="text-outline hover:text-on-surface transition-colors p-1 rounded hover:bg-surface-container shrink-0"
            :title="$t('nav.collapseMenu')"
            @click="collapsed = true"
          >
            <span class="material-symbols-outlined text-[18px]">
              left_panel_close
            </span>
          </button>
        </div>


        <!-- Navigation links -->
        <nav class="px-3 py-1 flex flex-col gap-0.5">
          <div v-if="!collapsed" class="px-2 pt-2 pb-1 text-[10px] font-semibold tracking-wider text-outline uppercase font-mono">
            {{ $t('nav.title') }}
          </div>
          <router-link
            v-for="link in navLinks"
            :key="link.to"
            :to="link.to"
            :class="[
              'flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs transition-colors',
              route.path === link.to
                ? 'bg-surface-container-high text-on-surface font-medium shadow-sm'
                : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
            ]"
            :title="collapsed ? link.label : undefined"
          >
            <div class="flex items-center gap-2.5 truncate">
              <span
                class="material-symbols-outlined text-[18px]"
                :class="route.path === link.to ? 'text-accent' : 'text-outline'"
              >
                {{ link.icon }}
              </span>
              <span v-if="!collapsed" class="truncate">{{ link.label }}</span>
            </div>
            <div v-if="!collapsed" class="flex items-center gap-1">
              <span
                v-if="link.countKey && appStats[link.countKey] !== undefined"
                class="px-1.5 py-0.2 rounded text-[10px] font-mono text-outline bg-surface-container"
              >
                {{ appStats[link.countKey] }}
              </span>
              <span
                v-else-if="route.path === link.to"
                class="w-1.5 h-1.5 rounded-full bg-accent"
              ></span>
            </div>
          </router-link>
        </nav>
      </div>

      <!-- Sidebar Footer / Candidate info -->
      <div class="p-3 border-t border-border-subtle bg-surface flex flex-col gap-2 shrink-0">
        <div
          v-if="!collapsed"
          class="flex items-center justify-between px-1 cursor-pointer hover:opacity-85 transition-opacity py-0.5"
          :title="agentStatus.connected ? $t('topbar.agentActive', { name: agentStatus.activeProviderName }) : $t('topbar.agentNone')"
          @click="router.push('/profile?tab=ai')"
        >
          <div class="flex items-center gap-1.5 min-w-0">
            <span
              class="w-2 h-2 rounded-full shrink-0"
              :class="agentStatus.connected ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'"
            ></span>
            <span class="text-[11px] font-mono text-outline truncate">
              {{ agentStatus.connected ? agentStatus.activeProviderName : $t('topbar.agentNoAi') }}
            </span>
          </div>
          <span
            class="text-[10px] font-mono px-1 py-0.5 rounded shrink-0 ml-1"
            :class="agentStatus.connected ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'"
          >
            {{ agentStatus.connected ? $t('topbar.statusReady') : $t('topbar.statusBaseCv') }}
          </span>
        </div>
        <div
          class="flex items-center gap-2.5 p-1.5 rounded-lg bg-surface-container border border-border-subtle hover:border-border-muted transition-colors cursor-pointer"
          :title="collapsed ? `${candidateName} (${candidateRole})` : undefined"
          @click="router.push('/profile')"
        >
          <div class="w-7 h-7 rounded-full bg-gradient-to-tr from-slate-700 to-indigo-900 border border-border-subtle flex items-center justify-center text-white text-xs font-semibold shrink-0">
            {{ candidateInitials }}
          </div>
          <div v-if="!collapsed" class="flex flex-col min-w-0 flex-1">
            <span class="font-medium text-[12px] text-on-surface truncate leading-snug">{{ candidateName }}</span>
            <span class="text-[10px] text-outline truncate leading-none">{{ candidateRole }}</span>
          </div>
        </div>
      </div>
    </aside>

    <!-- MAIN WRAPPER -->
    <div
      :class="[
        'flex-1 flex flex-col min-w-0 min-h-screen bg-surface-dim transition-all duration-200',
        collapsed ? 'pl-16' : 'pl-60'
      ]"
    >
      <!-- TOPBAR (Breadcrumbs + Date / Status + Theme Switcher + Language Selector + Scan CTA) -->
      <header class="h-14 border-b border-border-subtle bg-surface sticky top-0 z-40 px-6 flex items-center justify-between">
        <!-- Breadcrumbs -->
        <div class="flex items-center gap-2 text-on-surface-variant text-[13px]">
          <span class="text-outline hover:text-on-surface cursor-pointer" @click="router.push('/search')">
            Job Hunter
          </span>
          <span class="text-outline text-xs">/</span>
          <span class="font-medium text-on-surface">{{ pageTitle }}</span>
        </div>

        <!-- Right Actions -->
        <div class="flex items-center gap-3">
          <!-- Scan status badge -->
          <div class="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-md bg-surface-container border border-border-subtle text-[11px] font-mono text-on-surface-variant">
            <span class="material-symbols-outlined text-[14px] text-outline">calendar_today</span>
            <span>{{ lastScanTime ? $t('topbar.lastScan', { time: lastScanTime }) : $t('topbar.readyToScan') }}</span>
          </div>

          <!-- Language Selector / Toggle Button -->
          <button
            class="p-1.5 px-2 rounded-md border border-border-subtle bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors flex items-center gap-1.5 font-mono text-xs font-semibold cursor-pointer"
            :title="currentLang === 'es' ? 'Switch to English' : 'Cambiar a Español'"
            type="button"
            @click="toggleLanguage"
          >
            <span class="material-symbols-outlined text-[16px] text-accent">language</span>
            <span class="text-[11px] uppercase tracking-wider text-on-surface">{{ currentLang }}</span>
          </button>

          <!-- Light / Dark Mode Toggle Button -->
          <button
            class="p-1.5 rounded-md border border-border-subtle bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high transition-colors"
            :title="$t('topbar.toggleTheme')"
            type="button"
            @click="toggleTheme"
          >
            <span class="material-symbols-outlined text-[17px] block">
              {{ isDark ? 'light_mode' : 'dark_mode' }}
            </span>
          </button>

          <!-- Primary Scan CTA (visible when in Search view) -->
          <button
            v-if="isSearchRoute"
            :class="[
              'inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-white font-medium text-[12px] shadow-sm transition-colors active:scale-[0.98]',
              scanning
                ? 'bg-amber-600 hover:bg-amber-700'
                : 'bg-accent hover:bg-accent-hover'
            ]"
            type="button"
            @click="handleScanAction"
          >
            <span class="material-symbols-outlined text-[16px]">
              {{ scanning ? 'pause' : 'play_arrow' }}
            </span>
            <span>{{ scanning ? $t('topbar.stopScan') : $t('topbar.startScan') }}</span>
          </button>
        </div>
      </header>

      <!-- VIEW BODY -->
      <main class="p-6 flex-1 max-w-[1600px] w-full mx-auto">
        <router-view v-slot="{ Component }">
          <keep-alive>
            <component :is="Component" />
          </keep-alive>
        </router-view>
      </main>
    </div>
  </v-app>
</template>

<style scoped>
/* Scoped adjustments for smooth dark mode appearance */
:deep(.v-application__wrap) {
  min-height: 100vh;
  display: flex;
  flex-direction: row;
}
</style>
