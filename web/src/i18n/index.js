import { ref } from 'vue'
import es from './es.js'
import en from './en.js'

const STORAGE_KEY = 'job-hunter-lang'

const savedLang = typeof localStorage !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null
export const currentLang = ref(savedLang === 'en' ? 'en' : 'es')

if (typeof document !== 'undefined') {
  document.documentElement.setAttribute('lang', currentLang.value)
}

const dictionaries = { es, en }

const FORBIDDEN_PROPS = new Set(['__proto__', 'constructor', 'prototype'])

function getNested(obj, path) {
  if (!obj || !path) return undefined
  const segments = path.split('.')
  let current = obj
  for (const seg of segments) {
    if (FORBIDDEN_PROPS.has(seg)) return undefined
    if (current && typeof current === 'object' && Object.prototype.hasOwnProperty.call(current, seg)) {
      // nosemgrep: javascript.lang.security.audit.prototype-pollution.prototype-pollution-loop.prototype-pollution-loop
      current = current[seg]
    } else {
      return undefined
    }
  }
  return current
}

export function t(key, vars = {}) {
  // Access currentLang.value so Vue reactivity tracks currentLang in computeds and template renders
  const lang = currentLang.value
  const activeDict = dictionaries[lang] || dictionaries.es

  let val = getNested(activeDict, key)
  if (val === undefined) {
    val = getNested(dictionaries.es, key)
  }
  if (val === undefined) {
    return key
  }
  if (typeof val !== 'string') {
    return val
  }

  // Interpolate {var}
  return val.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? String(vars[k]) : `{${k}}`))
}

export function setLanguage(lang) {
  const target = lang === 'en' ? 'en' : 'es'
  currentLang.value = target
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, target)
  }
  if (typeof document !== 'undefined') {
    document.documentElement.setAttribute('lang', target)
  }
}

export function toggleLanguage() {
  setLanguage(currentLang.value === 'es' ? 'en' : 'es')
}

export const i18nPlugin = {
  install(app) {
    app.config.globalProperties.$t = (key, vars) => t(key, vars)
    app.config.globalProperties.$lang = currentLang
    app.provide('t', t)
    app.provide('currentLang', currentLang)
  },
}
