<script setup>
import { nextTick, onMounted, ref } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { api } from '../api.js'

const SESSION_KEY = 'jobhunter.sessionId'
const suggestions = [
  'Revisa el estado de mis postulaciones y dime qué sigue',
  'Escanea nuevas ofertas remotas para LatAm y propón las mejores',
]

const messages = ref([])
const input = ref('')
const busy = ref(false)
const sessionId = ref(null)
const demoSessionId = ref(null) // in memory only: a demo conversation never replaces the real one
const scroller = ref(null)
let controller = null

try {
  sessionId.value = localStorage.getItem(SESSION_KEY)
} catch {
  // storage unavailable: the conversation simply won't resume after a reload
}

onMounted(scrollDown)

const render = (text) => DOMPurify.sanitize(marked.parse(text ?? '', { breaks: true }))

function scrollDown() {
  nextTick(() => scroller.value?.scrollTo({ top: scroller.value.scrollHeight }))
}

// ---- posting cards: the agent ends a message with ```jobhunter-posting {json} ``` blocks ----
const POSTING_RE = /```jobhunter-posting\s*([\s\S]*?)```/g
const isHttpUrl = (v) => /^https?:\/\//i.test(String(v ?? ''))

function parsePostings(text) {
  const postings = []
  for (const m of text.matchAll(POSTING_RE)) {
    try {
      const p = JSON.parse(m[1])
      if (p.company && p.role && isHttpUrl(p.url)) {
        postings.push({
          company: String(p.company).slice(0, 120),
          role: String(p.role).slice(0, 160),
          url: String(p.url),
          cv: typeof p.cv === 'string' ? p.cv : undefined,
        })
      }
    } catch {
      // incomplete or invalid block: ignored
    }
  }
  return postings
}

// Text shown to the user: without complete blocks, and without a block still being streamed.
function visibleText(text) {
  return text.replace(POSTING_RE, '').replace(/```jobhunter-posting[\s\S]*$/, '').trim()
}

function newChat() {
  controller?.abort()
  messages.value = []
  sessionId.value = null
  demoSessionId.value = null
  busy.value = false
  try {
    localStorage.removeItem(SESSION_KEY)
  } catch {
    // ignore
  }
}

const runDemo = () => {
  demoSessionId.value = null
  return send('Busca publicaciones', true)
}

async function send(text = input.value, demo = false, { auto = false } = {}) {
  text = text.trim()
  if (!text || busy.value) return
  input.value = ''
  busy.value = true
  messages.value.push({ role: 'user', text, demo, auto })
  messages.value.push({ role: 'assistant', text: '', tools: [], error: '', demo, cards: [] })
  const live = messages.value[messages.value.length - 1]
  scrollDown()

  controller = new AbortController()
  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, sessionId: demo ? demoSessionId.value : sessionId.value, demo }),
      signal: controller.signal,
    })
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || `Error ${res.status}`)

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let sep
      while ((sep = buffer.indexOf('\n\n')) !== -1) {
        const line = buffer.slice(0, sep).trim()
        buffer = buffer.slice(sep + 2)
        if (line.startsWith('data:')) handle(live, JSON.parse(line.slice(5)), demo)
      }
      scrollDown()
    }
    await loadCards(live)
  } catch (e) {
    if (e.name !== 'AbortError') live.error = e.message
  } finally {
    busy.value = false
    scrollDown()
  }
}

function handle(msg, evt, demo) {
  if (evt.type === 'session' || evt.type === 'done') {
    const id = evt.id ?? evt.sessionId
    if (id) {
      if (demo) {
        demoSessionId.value = id
      } else {
        sessionId.value = id
        try {
          localStorage.setItem(SESSION_KEY, id)
        } catch {
          // ignore
        }
      }
    }
    if (evt.type === 'done' && evt.isError) msg.error = evt.result || 'El agente terminó con error'
  } else if (evt.type === 'text') {
    msg.text += evt.text
  } else if (evt.type === 'tool') {
    msg.tools.push(`${evt.name}${evt.input ? ': ' + evt.input : ''}`)
  } else if (evt.type === 'error') {
    msg.error = evt.message
  }
}

// ---- card lifecycle: loaded -> form opened -> sent / not sent ----
// Postings found by the agent are loaded into the Applications page automatically as "pending".
async function loadCards(msg) {
  for (const posting of parsePostings(msg.text)) {
    const card = { ...posting, state: 'loading', appId: null, error: '' }
    msg.cards.push(card)
    try {
      const item = await api.createApplication({ ...posting, status: 'pending', demo: msg.demo || undefined })
      card.appId = item.id
      // An existing entry may already be past "pending" (same url found again).
      card.state = item.status === 'pending' ? 'ready' : item.status === 'not_sent' ? 'not_sent' : 'sent'
    } catch (e) {
      card.state = 'error'
      card.error = e.message
    }
  }
}

async function openForm(card, msg) {
  card.error = ''
  try {
    await api.launchApply({ url: card.url, cv: card.cv, applicationId: card.appId, demo: msg.demo || undefined })
    card.state = 'launched' // the button is replaced right away by "Enviado" / "No enviado"
  } catch (e) {
    card.error = e.message
  }
}

async function feedback(card, msg, sent) {
  card.error = ''
  try {
    await api.updateApplication(card.appId, sent
      ? { status: 'applied', event: 'Marcada como enviada por el usuario' }
      : { status: 'not_sent', event: 'El usuario decidió no enviarla' })
    card.state = sent ? 'sent' : 'not_sent'
  } catch (e) {
    card.error = e.message
    return
  }
  const what = `${card.company} (${card.role})`
  await send(
    sent
      ? `[Acción en el panel] Envié la postulación a ${what}.`
      : `[Acción en el panel] No envié la postulación a ${what}.`,
    msg.demo,
    { auto: true },
  )
}
</script>

<template>
  <v-container fluid class="pa-6 chat">
    <div class="d-flex align-center mb-3">
      <h1 class="text-h5">Chat con el agente</h1>
      <v-spacer />
      <v-btn
        variant="tonal"
        color="warning"
        prepend-icon="mdi-flask-outline"
        class="mr-2"
        :disabled="busy"
        @click="runDemo"
      >
        Realizar prueba
      </v-btn>
      <v-btn variant="text" prepend-icon="mdi-plus" @click="newChat">Nueva conversación</v-btn>
    </div>

    <v-card class="flex-grow-1 d-flex flex-column overflow-hidden">
      <div ref="scroller" class="messages pa-4">
        <div v-if="!messages.length" class="text-medium-emphasis">
          <p class="mb-3">Usa tu sesión de Claude Code local. "Realizar prueba" trabaja solo con datos ficticios.</p>
          <v-chip v-for="s in suggestions" :key="s" class="mr-2 mb-2" variant="outlined" @click="send(s)">{{ s }}</v-chip>
        </div>

        <div v-for="(m, i) in messages" :key="i" class="mb-4" :class="m.role === 'user' ? 'text-right' : ''">
          <div v-if="m.role === 'user'" class="bubble user">
            <v-chip v-if="m.demo" size="x-small" color="warning" class="mr-2" prepend-icon="mdi-flask-outline">Prueba</v-chip>
            <v-chip v-if="m.auto" size="x-small" class="mr-2" prepend-icon="mdi-cursor-default-click">Acción</v-chip>{{ m.text }}
          </div>
          <div v-else class="bubble assistant">
            <div class="mb-1">
              <v-chip v-for="(t, j) in m.tools" :key="j" size="x-small" class="mr-1 mb-1" prepend-icon="mdi-wrench">{{ t }}</v-chip>
            </div>
            <div v-if="visibleText(m.text)" class="markdown" v-html="render(visibleText(m.text))" />
            <v-progress-circular v-else-if="busy && i === messages.length - 1 && !m.error" indeterminate size="18" width="2" />

            <v-card v-for="c in m.cards" :key="c.url" variant="outlined" class="posting-card mt-3">
              <v-card-item>
                <v-card-title class="text-body-1 font-weight-bold">{{ c.company }} · {{ c.role }}</v-card-title>
                <v-card-subtitle>
                  <a :href="c.url" target="_blank" rel="noopener">{{ c.url }}</a>
                </v-card-subtitle>
                <template #append>
                  <v-chip v-if="m.demo" size="small" color="warning" prepend-icon="mdi-flask-outline">Demo</v-chip>
                </template>
              </v-card-item>
              <v-card-actions class="px-4 pb-3">
                <template v-if="c.state === 'loading'">
                  <v-progress-circular indeterminate size="18" width="2" class="mr-2" />
                  <span class="text-medium-emphasis">Cargando en Postulaciones…</span>
                </template>
                <template v-else-if="c.state === 'ready'">
                  <v-chip size="small" color="secondary" prepend-icon="mdi-clock-outline" class="mr-3">Cargada en Postulaciones</v-chip>
                  <v-btn color="primary" prepend-icon="mdi-open-in-new" @click="openForm(c, m)">Abrir formulario</v-btn>
                </template>
                <template v-else-if="c.state === 'launched'">
                  <span class="text-medium-emphasis mr-3">¿Enviaste la postulación?</span>
                  <v-btn color="success" prepend-icon="mdi-check" :disabled="busy" @click="feedback(c, m, true)">Enviado</v-btn>
                  <v-btn variant="outlined" prepend-icon="mdi-close" :disabled="busy" class="ml-2" @click="feedback(c, m, false)">No enviado</v-btn>
                </template>
                <v-chip v-else-if="c.state === 'sent'" color="success" prepend-icon="mdi-check-circle">Enviada · registrada</v-chip>
                <v-chip v-else-if="c.state === 'not_sent'" prepend-icon="mdi-cancel">No enviada · registrada</v-chip>
              </v-card-actions>
              <v-alert v-if="c.error" type="error" variant="tonal" density="compact" class="mx-4 mb-3">{{ c.error }}</v-alert>
            </v-card>

            <v-alert v-if="m.error" type="error" variant="tonal" density="compact" class="mt-2">{{ m.error }}</v-alert>
          </div>
        </div>
      </div>

      <v-divider />
      <div class="pa-3 d-flex align-end ga-2">
        <v-textarea
          v-model="input"
          placeholder="Escribe un mensaje (Enter envía, Shift+Enter nueva línea)"
          rows="1"
          max-rows="6"
          auto-grow
          hide-details
          variant="outlined"
          density="comfortable"
          :disabled="busy"
          @keydown.enter.exact.prevent="send()"
        />
        <v-btn color="primary" icon="mdi-send" :loading="busy" :disabled="!input.trim()" @click="send()" />
      </div>
    </v-card>
  </v-container>
</template>

<style scoped>
.chat {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.messages {
  flex: 1;
  overflow-y: auto;
}
.bubble {
  display: inline-block;
  max-width: 85%;
  padding: 8px 14px;
  border-radius: 12px;
  text-align: left;
  white-space: pre-wrap;
}
.bubble.user {
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
}
.bubble.assistant {
  background: rgba(var(--v-theme-on-surface), 0.06);
  white-space: normal;
}
.posting-card {
  background: rgb(var(--v-theme-surface));
}
.markdown :deep(p) {
  margin-bottom: 0.6em;
}
.markdown :deep(ul),
.markdown :deep(ol) {
  padding-left: 1.4em;
  margin-bottom: 0.6em;
}
.markdown :deep(table) {
  border-collapse: collapse;
  margin-bottom: 0.6em;
}
.markdown :deep(th),
.markdown :deep(td) {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.2);
  padding: 4px 8px;
}
.markdown :deep(code) {
  background: rgba(var(--v-theme-on-surface), 0.1);
  padding: 0 4px;
  border-radius: 4px;
}
</style>
