import { reactive } from 'vue'
import { api } from './api.js'

export const appStats = reactive({
  applications: 0,
  cvs: 0,
  exclusions: 0,
})

export async function refreshAppStats() {
  try {
    const [apps, files, exclusions] = await Promise.all([
      api.listApplications().catch(() => []),
      api.listFiles().catch(() => []),
      api.listExclusions().catch(() => []),
    ])
    appStats.applications = apps.length
    appStats.cvs = files.length
    appStats.exclusions = exclusions.length
  } catch {
    // ignorar errores de conexion en carga inicial
  }
}
