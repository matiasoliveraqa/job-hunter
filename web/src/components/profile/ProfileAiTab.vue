<script setup>
defineProps({
  agentStatus: {
    type: Object,
    default: null,
  },
  agentConfig: {
    type: Object,
    required: true,
  },
  savingAgentConfig: {
    type: Boolean,
    default: false,
  },
  providerOptions: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits(['save-config'])
</script>

<template>
  <div class="flex flex-col gap-6">
    <section class="bg-surface-card border border-border-subtle rounded-xl p-5 flex flex-col gap-4">
      <div class="flex items-center justify-between pb-1">
        <div class="flex items-center gap-2.5">
          <span class="material-symbols-outlined text-tertiary text-[20px]">smart_toy</span>
          <div>
            <h2 class="text-sm font-semibold text-on-surface">{{ $t('profile.sections.aiTitle') }}</h2>
            <p class="font-mono text-[11px] text-outline">{{ $t('profile.sections.aiDesc') }}</p>
          </div>
        </div>
        <span
          class="px-2 py-0.5 rounded text-[10px] font-mono"
          :class="agentStatus?.connected ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'"
        >
          {{ agentStatus?.connected ? $t('profile.sections.aiActiveBadge', { name: agentStatus.activeProviderName }) : $t('profile.sections.aiBaseCvActiveBadge') }}
        </span>
      </div>

      <!-- Status Card -->
      <div
        class="p-4 rounded-lg border flex flex-col gap-2"
        :class="agentStatus?.connected ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-amber-500/5 border-amber-500/20'"
      >
        <div class="flex items-center justify-between flex-wrap gap-2">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-[18px]" :class="agentStatus?.connected ? 'text-emerald-400' : 'text-amber-400'">
              {{ agentStatus?.connected ? 'check_circle' : 'info' }}
            </span>
            <span class="text-xs font-semibold text-on-surface">
              {{ agentStatus?.connected ? $t('profile.sections.aiConnectedTitle', { name: agentStatus.activeProviderName }) : $t('profile.sections.aiDisconnectedTitle') }}
            </span>
          </div>
          <span class="font-mono text-[11px] text-outline">
            {{ agentStatus?.connected ? $t('profile.sections.aiTailorAvailable') : $t('profile.sections.aiBaseCvStandard') }}
          </span>
        </div>
        <p class="text-xs text-on-surface-variant">
          {{ agentStatus?.connected ? $t('profile.sections.aiConnectedDesc') : $t('profile.sections.aiDisconnectedDesc') }}
        </p>
      </div>

      <!-- Provider Select -->
      <div class="flex flex-col gap-1.5 max-w-md">
        <label class="text-xs text-on-surface-variant font-medium">{{ $t('profile.sections.aiPreferredProvider') }}</label>
        <select
          v-model="agentConfig.provider"
          class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs border border-border-subtle focus:outline-none focus:border-accent transition-colors cursor-pointer"
        >
          <option v-for="opt in providerOptions" :key="opt.value" :value="opt.value">{{ opt.title }}</option>
        </select>
      </div>

      <div class="my-2 border-t border-border-subtle"></div>

      <!-- Direct API Keys -->
      <div class="flex flex-col gap-1">
        <h3 class="text-xs font-semibold text-on-surface">{{ $t('profile.sections.apiKeysDirectTitle') }}</h3>
        <p class="text-xs text-outline">{{ $t('profile.sections.apiKeysDirectDesc') }}</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <!-- DeepSeek -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs text-on-surface-variant flex items-center justify-between">
            <span>DeepSeek API Key</span>
            <span class="font-mono text-[10px] text-outline">{{ agentConfig.hasDeepSeekKey ? $t('profile.sections.configured') : 'platform.deepseek.com' }}</span>
          </label>
          <input
            v-model="agentConfig.deepseekApiKey"
            class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            placeholder="sk-..."
            type="password"
          />
        </div>

        <!-- Kimi -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs text-on-surface-variant flex items-center justify-between">
            <span>Kimi / Moonshot AI Key</span>
            <span class="font-mono text-[10px] text-outline">{{ agentConfig.hasKimiKey ? $t('profile.sections.configured') : 'platform.moonshot.cn' }}</span>
          </label>
          <input
            v-model="agentConfig.kimiApiKey"
            class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            placeholder="sk-..."
            type="password"
          />
        </div>

        <!-- Anthropic -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs text-on-surface-variant flex items-center justify-between">
            <span>Anthropic Claude API Key</span>
            <span class="font-mono text-[10px] text-outline">{{ agentConfig.hasAnthropicKey ? $t('profile.sections.configured') : 'sk-ant-...' }}</span>
          </label>
          <input
            v-model="agentConfig.anthropicApiKey"
            class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            placeholder="sk-ant-..."
            type="password"
          />
        </div>

        <!-- OpenAI -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs text-on-surface-variant flex items-center justify-between">
            <span>OpenAI API Key</span>
            <span class="font-mono text-[10px] text-outline">{{ agentConfig.hasOpenAiKey ? $t('profile.sections.configured') : 'sk-...' }}</span>
          </label>
          <input
            v-model="agentConfig.openaiApiKey"
            class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            placeholder="sk-..."
            type="password"
          />
        </div>

        <!-- Gemini -->
        <div class="flex flex-col gap-1.5">
          <label class="text-xs text-on-surface-variant flex items-center justify-between">
            <span>Google Gemini API Key</span>
            <span class="font-mono text-[10px] text-outline">{{ agentConfig.hasGeminiKey ? $t('profile.sections.configured') : 'AI Studio' }}</span>
          </label>
          <input
            v-model="agentConfig.geminiApiKey"
            class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            placeholder="AIza..."
            type="password"
          />
        </div>
      </div>

      <div class="my-2 border-t border-border-subtle"></div>

      <!-- Custom endpoint -->
      <div class="flex flex-col gap-1">
        <h3 class="text-xs font-semibold text-on-surface">{{ $t('profile.sections.customEndpointTitle') }}</h3>
        <p class="text-xs text-outline">{{ $t('profile.sections.customEndpointDesc') }}</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-12 gap-4">
        <div class="md:col-span-5 flex flex-col gap-1.5">
          <label class="text-xs text-on-surface-variant">{{ $t('profile.sections.apiBaseUrlLabel') }}</label>
          <input
            v-model="agentConfig.customOpenAiBaseUrl"
            class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            placeholder="https://api.deepseek.com/v1 o http://localhost:11434/v1"
            type="text"
          />
        </div>

        <div class="md:col-span-3 flex flex-col gap-1.5">
          <label class="text-xs text-on-surface-variant">{{ $t('profile.sections.modelNameLabel') }}</label>
          <input
            v-model="agentConfig.customOpenAiModel"
            class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            placeholder="deepseek-chat, llama3, etc."
            type="text"
          />
        </div>

        <div class="md:col-span-4 flex flex-col gap-1.5">
          <label class="text-xs text-on-surface-variant flex items-center justify-between">
            <span>{{ $t('profile.sections.customApiKeyLabel') }}</span>
            <span class="font-mono text-[10px] text-outline">{{ $t('profile.sections.optionalOllama') }}</span>
          </label>
          <input
            v-model="agentConfig.customOpenAiApiKey"
            class="h-9 px-3 rounded-lg bg-surface-container text-on-surface text-xs font-mono border border-border-subtle focus:outline-none focus:border-accent transition-colors"
            placeholder="Opcional"
            type="password"
          />
        </div>
      </div>

      <div class="flex justify-end pt-3">
        <button
          class="px-4 py-2 rounded-lg bg-accent hover:bg-accent-hover text-white text-xs font-medium shadow-sm transition-all active:scale-[0.98] flex items-center gap-1.5 disabled:opacity-50"
          :disabled="savingAgentConfig"
          type="button"
          @click="emit('save-config')"
        >
          <span :class="['material-symbols-outlined text-[16px]', savingAgentConfig ? 'animate-spin' : '']">
            {{ savingAgentConfig ? 'sync' : 'check_circle' }}
          </span>
          <span>{{ savingAgentConfig ? $t('profile.sections.testingConnection') : $t('profile.sections.saveAndTestConnection') }}</span>
        </button>
      </div>
    </section>
  </div>
</template>
