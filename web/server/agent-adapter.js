/**
 * Agent Adapter Facade
 * Re-exports AI providers, configuration, and task executors from the modular ./ai/ subsystem.
 */

export {
  ROOT,
  buildCleanEnv,
  runTextCommand,
  checkCommandAvailable,
  queryAnthropicApi,
  queryOpenAiCompatibleApi,
  queryGeminiApi,
  queryClaude,
  queryAgy,
  queryCodex,
} from './ai/api-clients.js'

export {
  AI_SETTINGS_FILE,
  readAiSettings,
  writeAiSettings,
  checkBaseCv,
  checkAgentStatus,
  queryIsolatedModel,
} from './ai/providers.js'

export {
  SYSTEM_RULES,
  extractHtml,
  tailorCvHtml,
  answerQuestion,
  extractProfileFromCv,
} from './ai/tasks.js'
