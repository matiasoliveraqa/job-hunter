import { ref } from 'vue'

export const isDark = ref(true)

export function initTheme() {
  const saved = localStorage.getItem('job-hunter-theme')
  if (saved === 'light') {
    isDark.value = false
    document.documentElement.classList.remove('dark')
  } else {
    isDark.value = true
    document.documentElement.classList.add('dark')
  }
}

export function toggleTheme() {
  isDark.value = !isDark.value
  if (isDark.value) {
    document.documentElement.classList.add('dark')
    localStorage.setItem('job-hunter-theme', 'dark')
  } else {
    document.documentElement.classList.remove('dark')
    localStorage.setItem('job-hunter-theme', 'light')
  }
}
