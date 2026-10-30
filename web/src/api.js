async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data.error || `Error ${res.status}`)
  }
  return res.status === 204 ? null : res.json()
}

export const api = {
  listApplications: () => request('/api/applications'),
  createApplication: (body) => request('/api/applications', { method: 'POST', body }),
  updateApplication: (id, body) => request(`/api/applications/${id}`, { method: 'PATCH', body }),
  deleteApplication: (id) => request(`/api/applications/${id}`, { method: 'DELETE' }),
  clearDemos: () => request('/api/applications/clear-demos', { method: 'POST', body: {} }),
  getProfile: () => request('/api/profile'),
  saveProfile: (body) => request('/api/profile', { method: 'PUT', body }),
  getBaseCv: () => request('/api/profile/cv'),
  uploadBaseCv: (body) => request('/api/profile/upload-cv', { method: 'POST', body }),
  listExclusions: () => request('/api/exclusions'),
  addExclusion: (body) => request('/api/exclusions', { method: 'POST', body }),
  updateExclusion: (company, body) => request(`/api/exclusions/${encodeURIComponent(company)}`, { method: 'PUT', body }),
  removeExclusion: (company) => request(`/api/exclusions/${encodeURIComponent(company)}`, { method: 'DELETE' }),
  importExclusions: (items) => request('/api/exclusions/import', { method: 'POST', body: items }),
  clearExclusions: () => request('/api/exclusions/clear', { method: 'POST', body: {} }),
  listFiles: () => request('/api/files'),
  openFolder: (folder = 'applications') => request('/api/open-folder', { method: 'POST', body: { folder } }),
  openApplicationFolder: (id) => request(`/api/applications/${id}/open-folder`, { method: 'POST' }),
  launchApply: (body) => request('/api/apply', { method: 'POST', body }),
  listLaunches: () => request('/api/apply'),
  stopScan: () => request('/api/scan/stop', { method: 'POST', body: {} }),
  getScanStatus: () => request('/api/scan/status'),
  startScan: (body) => request('/api/scan/start', { method: 'POST', body }),
  getScanResults: () => request('/api/scan/results'),
  tailorCv: (body) => request('/api/tailor-cv', { method: 'POST', body }),
  getAgentStatus: () => request('/api/agent/status'),
  getAgentConfig: () => request('/api/agent/config'),
  saveAgentConfig: (body) => request('/api/agent/config', { method: 'POST', body }),
  useBaseCv: (id) => request(`/api/applications/${id}/use-base-cv`, { method: 'POST' }),
}

export const STATUS_META = {
  pending: { title: 'Pendiente de envío', color: 'secondary', icon: 'mdi-clock-outline' },
  applied: { title: 'Enviada', color: 'info', icon: 'mdi-send' },
  interview: { title: 'Entrevista', color: 'warning', icon: 'mdi-account-voice' },
  offer: { title: 'Oferta / aceptada', color: 'success', icon: 'mdi-check-decagram' },
  rejected: { title: 'Rechazada', color: 'error', icon: 'mdi-close-circle' },
  withdrawn: { title: 'Retirada', color: 'grey', icon: 'mdi-undo' },
  not_sent: { title: 'No enviada', color: 'grey', icon: 'mdi-cancel' },
}

export function formatCompanyName(name) {
  if (!name || typeof name !== 'string') return ''
  return name.replace(/(^|[\s\-_]+)([a-z])/g, (_, boundary, c) => boundary + c.toUpperCase())
}
