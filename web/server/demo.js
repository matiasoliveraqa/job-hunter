import path from 'node:path'

/**
 * Demo mode never touches real data. Uses fictional profile and CV files
 * and local mock postings for demonstration.
 */
export const MOCK_PREFIX = '/mock/'

export function createDemo({ root, host, port: initialPort }) {
  const demoDir = path.join(root, 'web', 'demo')
  const mockPosting = path.join(root, 'web', 'public', 'mock', 'greenhouse', 'demo-corp', 'jobs', '1.html')
  let currentPort = initialPort

  return {
    setPort(p) {
      currentPort = p
    },
    profilePath: path.join(demoDir, 'profile.json'),
    cvPath: path.join(demoDir, 'demo_cv.pdf'),
    get postingUrl() {
      return `http://${host}:${currentPort}/mock/greenhouse/demo-corp/jobs/1.html`
    },

    // True only for URLs served by this app's own mock folder.
    isMockUrl(value) {
      try {
        const u = new URL(value)
        return (
          u.pathname.startsWith(MOCK_PREFIX) &&
          (u.host === `${host}:${currentPort}` || u.host === `localhost:${currentPort}`)
        )
      } catch {
        return false
      }
    },
  }
}
