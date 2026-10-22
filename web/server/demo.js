import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'

/**
 * Demo mode never touches real data. The demo agent runs inside a throwaway
 * folder (outside the repository) that only contains fictional files copied
 * from web/demo and the local mock posting.
 */
export const MOCK_PREFIX = '/mock/'

export function createDemo({ root, host, port }) {
  const demoDir = path.join(root, 'web', 'demo')
  const mockPosting = path.join(root, 'web', 'public', 'mock', 'greenhouse', 'demo-corp', 'jobs', '1.html')

  return {
    profilePath: path.join(demoDir, 'profile.json'),
    cvPath: path.join(demoDir, 'demo_cv.pdf'),
    postingUrl: `http://${host}:${port}/mock/greenhouse/demo-corp/jobs/1.html`,

    // True only for URLs served by this app's own mock folder.
    isMockUrl(value) {
      try {
        const u = new URL(value)
        return u.pathname.startsWith(MOCK_PREFIX) && u.host === `${host}:${port}`
      } catch {
        return false
      }
    },

    async prepareSandbox() {
      const sandbox = path.join(os.tmpdir(), 'jobhunter-demo')
      await fs.rm(sandbox, { recursive: true, force: true })
      await fs.mkdir(sandbox, { recursive: true })
      await fs.copyFile(path.join(demoDir, 'profile.json'), path.join(sandbox, 'profile.json'))
      await fs.copyFile(path.join(demoDir, 'cv.md'), path.join(sandbox, 'cv.md'))
      await fs.copyFile(path.join(demoDir, 'applications.json'), path.join(sandbox, 'applications.json'))
      await fs.copyFile(mockPosting, path.join(sandbox, 'posting.html'))
      return sandbox
    },
  }
}
