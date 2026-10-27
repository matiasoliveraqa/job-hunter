import test from 'node:test'
import assert from 'node:assert/strict'
import http from 'node:http'
import { app, addAllowedPort, sanitizeCvHtml, isAllowedAtsHost, startServer } from '../server/index.js'

function makeRequest({ port, path = '/', method = 'GET', headers = {}, body = null }) {
  return new Promise((resolve, reject) => {
    const req = http.request(
      `http://127.0.0.1:${port}${path}`,
      { method, headers },
      (res) => {
        let data = ''
        res.on('data', (c) => (data += c))
        res.on('end', () => {
          let json = null
          try {
            json = JSON.parse(data)
          } catch {}
          resolve({ status: res.statusCode, headers: res.headers, text: data, json })
        })
      }
    )
    req.on('error', reject)
    if (body) req.write(typeof body === 'string' ? body : JSON.stringify(body))
    req.end()
  })
}

test('sanitizeCvHtml neutralizes scripts, event handlers, and remote tracker images while preserving styles', () => {
  const dirty = `
    <h1>Senior QA Engineer</h1>
    <script>alert("xss")</script>
    <style>@import url("https://attacker.com/evil.css"); body { color: red; }</style>
    <link rel="stylesheet" href="https://attacker.com/evil.css">
    <img src="https://attacker.com/leak?cookie=1" onerror="steal()" alt="avatar" />
    <iframe src="https://malicious.org"></iframe>
    <svg><animate onbegin="alert(1)" attributeName="x" dur="1s"></svg>
    <a href="javascript:doEvil()" onclick="steal()">Click me</a>
    <p onload="runCode()">Content</p>
  `
  const cleaned = sanitizeCvHtml(dirty)
  assert.ok(!cleaned.includes('<script'), 'Should strip script tags')
  assert.ok(cleaned.includes('<style'), 'Should preserve style tags')
  assert.ok(!cleaned.includes('@import'), 'Should strip @import')
  assert.ok(!cleaned.includes('alert('), 'Should strip script contents')
  assert.ok(!cleaned.includes('<iframe'), 'Should strip iframe tags')
  assert.ok(!cleaned.includes('<link'), 'Should strip link tags')
  assert.ok(!cleaned.includes('onclick'), 'Should strip onclick')
  assert.ok(!cleaned.includes('onerror'), 'Should strip onerror')
  assert.ok(!cleaned.includes('onload'), 'Should strip onload')
  assert.ok(!cleaned.includes('onbegin'), 'Should strip onbegin')
  assert.ok(!cleaned.includes('javascript:'), 'Should strip javascript: URLs')
  assert.ok(!cleaned.includes('https://attacker.com/leak'), 'Should neutralize remote image tracker src')
  assert.ok(cleaned.includes('<h1>Senior QA Engineer</h1>'), 'Should preserve safe tags')
  assert.ok(cleaned.includes('color: red;'), 'Should preserve safe CSS')
})

test('isAllowedAtsHost strictly validates ATS domains and prevents query parameter escapes', () => {
  assert.strictEqual(isAllowedAtsHost('https://job-boards.greenhouse.io/corp/jobs/1'), true)
  assert.strictEqual(isAllowedAtsHost('https://boards.greenhouse.io/corp/jobs/1'), true)
  assert.strictEqual(isAllowedAtsHost('https://jobs.ashbyhq.com/corp/1'), true)
  assert.strictEqual(isAllowedAtsHost('https://jobs.lever.co/corp/1'), true)
  assert.strictEqual(isAllowedAtsHost('https://apply.workable.com/corp/j/123/'), true)
  assert.strictEqual(isAllowedAtsHost('https://jobs.workable.com/corp/123/'), true)
  assert.strictEqual(isAllowedAtsHost('https://corp.breezy.hr/p/123-job'), true)
  assert.strictEqual(isAllowedAtsHost('https://corp.recruitee.com/o/job-slug'), true)
  assert.strictEqual(isAllowedAtsHost('https://careers.recruitee.com/o/job-slug'), true)
  assert.strictEqual(isAllowedAtsHost('https://corp.bamboohr.com/careers/123'), true)
  assert.strictEqual(isAllowedAtsHost('https://corp.bamboohr.co.uk/careers/123'), true)

  // Query parameter bypass attempts on arbitrary domains
  assert.strictEqual(isAllowedAtsHost('https://evil.com/phish?gh_jid=1'), false)
  assert.strictEqual(isAllowedAtsHost('https://evil.com/x?ashby_jid='), false)
  assert.strictEqual(isAllowedAtsHost('https://attacker.io/steal?lever-origin=a'), false)
  assert.strictEqual(isAllowedAtsHost('https://evil.com/phishing-form'), false)
})

test('Web server host authorization and API endpoints', async (t) => {
  const server = http.createServer(app)
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
  const port = server.address().port

  t.after(() => {
    server.close()
  })

  await t.test('Rejects request without allowed port in Host header', async () => {
    const res = await makeRequest({
      port,
      path: '/api/applications',
      headers: { host: `127.0.0.1:${port}` },
    })
    assert.strictEqual(res.status, 403)
    assert.strictEqual(res.json?.error, 'Host no permitido')
  })

  await t.test('Accepts request after dynamic port registration', async () => {
    addAllowedPort(port)
    const res = await makeRequest({
      port,
      path: '/api/applications',
      headers: { host: `127.0.0.1:${port}` },
    })
    assert.strictEqual(res.status, 200)
    assert.ok(Array.isArray(res.json))
  })

  await t.test('Rejects foreign host header (DNS rebinding prevention)', async () => {
    const res = await makeRequest({
      port,
      path: '/api/applications',
      headers: { host: 'evil-attacker.com' },
    })
    assert.strictEqual(res.status, 403)
    assert.strictEqual(res.json?.error, 'Host no permitido')
  })

  await t.test('/api/chat is completely deleted (returns 404)', async () => {
    const res = await makeRequest({
      port,
      path: '/api/chat',
      method: 'POST',
      headers: {
        host: `127.0.0.1:${port}`,
        'content-type': 'application/json',
      },
      body: { message: 'Hello' },
    })
    assert.strictEqual(res.status, 404)
  })

  await t.test('POST /api/apply rejects unallowed external domains', async () => {
    const res = await makeRequest({
      port,
      path: '/api/apply',
      method: 'POST',
      headers: {
        host: `127.0.0.1:${port}`,
        'content-type': 'application/json',
      },
      body: {
        url: 'https://evil-phishing.com/apply',
        company: 'EvilCorp',
        role: 'Engineer',
      },
    })
    assert.strictEqual(res.status, 400)
    assert.ok(res.json?.error?.includes('Dominio no permitido'))
  })

  await t.test('POST /api/apply rejects query param bypass attempts', async () => {
    for (const evilUrl of [
      'https://evil.com/phish?gh_jid=1',
      'https://evil.com/x?ashby_jid=',
      'https://attacker.io/steal?lever-origin=a',
    ]) {
      const res = await makeRequest({
        port,
        path: '/api/apply',
        method: 'POST',
        headers: {
          host: `127.0.0.1:${port}`,
          'content-type': 'application/json',
        },
        body: {
          url: evilUrl,
          company: 'EvilCorp',
          role: 'Engineer',
        },
      })
      assert.strictEqual(res.status, 400, `Expected 400 for ${evilUrl}`)
      assert.ok(res.json?.error?.includes('Dominio no permitido'))
    }
  })

  await t.test('POST /api/applications rejects unallowed external domains', async () => {
    const res = await makeRequest({
      port,
      path: '/api/applications',
      method: 'POST',
      headers: {
        host: `127.0.0.1:${port}`,
        'content-type': 'application/json',
      },
      body: {
        company: 'EvilCorp',
        role: 'Engineer',
        url: 'https://evil.com/phishing-form',
      },
    })
    assert.strictEqual(res.status, 400)
    assert.ok(res.json?.error?.includes('Dominio no permitido'))
  })

  await t.test('POST /api/apply resolves company/role via applicationId without ReferenceError', async () => {
    const appRes = await makeRequest({
      port,
      path: '/api/applications',
      method: 'POST',
      headers: {
        host: `127.0.0.1:${port}`,
        'content-type': 'application/json',
      },
      body: {
        company: 'TargetCorp',
        role: 'QA Engineer',
        url: 'https://job-boards.greenhouse.io/targetcorp/jobs/12345',
      },
    })
    assert.ok(appRes.status === 200 || appRes.status === 201)
    const appId = appRes.json?.id
    assert.ok(appId)

    const applyRes = await makeRequest({
      port,
      path: '/api/apply',
      method: 'POST',
      headers: {
        host: `127.0.0.1:${port}`,
        'content-type': 'application/json',
      },
      body: {
        url: 'https://job-boards.greenhouse.io/targetcorp/jobs/12345',
        applicationId: appId,
        dryRun: true,
      },
    })
    assert.strictEqual(applyRes.status, 202)
    assert.strictEqual(applyRes.json?.company, 'TargetCorp')
    assert.strictEqual(applyRes.json?.role, 'QA Engineer')
  })

  await t.test('POST /api/tailor-cv requires company and role', async () => {
    const res = await makeRequest({
      port,
      path: '/api/tailor-cv',
      method: 'POST',
      headers: {
        host: `127.0.0.1:${port}`,
        'content-type': 'application/json',
      },
      body: { company: '' },
    })
    assert.strictEqual(res.status, 400)
    assert.strictEqual(res.json?.error, 'company y role son requeridos')
  })

  await t.test('GET /api/profile/cv returns base CV metadata', async () => {
    const res = await makeRequest({
      port,
      path: '/api/profile/cv',
      headers: {
        host: `127.0.0.1:${port}`,
      },
    })
    assert.strictEqual(res.status, 200)
    assert.ok(typeof res.json?.exists === 'boolean')
  })

  await t.test('POST /api/profile/upload-cv rejects unsupported extensions', async () => {
    const res = await makeRequest({
      port,
      path: '/api/profile/upload-cv',
      method: 'POST',
      headers: {
        host: `127.0.0.1:${port}`,
        'content-type': 'application/json',
      },
      body: {
        filename: 'malicious.exe',
        base64: Buffer.from('test').toString('base64'),
      },
    })
    assert.strictEqual(res.status, 400)
    assert.ok(res.json?.error?.includes('Solo se permiten'))
  })

  await t.test('GET /api/scan/status returns scan state and matches array', async () => {
    const res = await makeRequest({
      port,
      path: '/api/scan/status',
      headers: { host: `127.0.0.1:${port}` },
    })
    assert.strictEqual(res.status, 200)
    assert.strictEqual(typeof res.json?.isScanning, 'boolean')
    assert.ok(Array.isArray(res.json?.matches))
  })

  await t.test('GET /api/scan/results returns matches array', async () => {
    const res = await makeRequest({
      port,
      path: '/api/scan/results',
      headers: { host: `127.0.0.1:${port}` },
    })
    assert.strictEqual(res.status, 200)
    assert.ok(Array.isArray(res.json?.matches))
  })

  await t.test('POST /api/scan/stop safely terminates any active scan', async () => {
    const res = await makeRequest({
      port,
      path: '/api/scan/stop',
      method: 'POST',
      headers: {
        host: `127.0.0.1:${port}`,
        'content-type': 'application/json',
      },
      body: {},
    })
    assert.strictEqual(res.status, 200)
    assert.strictEqual(typeof res.json?.stopped, 'boolean')
  })

  await t.test('POST /api/open-folder safely opens folder cross-platform', async () => {
    const res = await makeRequest({
      port,
      path: '/api/open-folder',
      method: 'POST',
      headers: {
        host: `127.0.0.1:${port}`,
        'content-type': 'application/json',
      },
      body: { folder: 'applications' },
    })
    assert.strictEqual(res.status, 200)
    assert.strictEqual(res.json?.ok, true)
    assert.ok(typeof res.json?.path === 'string')
    assert.ok(typeof res.json?.platform === 'string')
  })

  await t.test('GET /api/exclusions and POST /api/exclusions/import work properly', async () => {
    const listRes = await makeRequest({
      port,
      path: '/api/exclusions',
      headers: { host: `127.0.0.1:${port}` },
    })
    assert.strictEqual(listRes.status, 200)
    assert.ok(Array.isArray(listRes.json))

    const importRes = await makeRequest({
      port,
      path: '/api/exclusions/import',
      method: 'POST',
      headers: {
        host: `127.0.0.1:${port}`,
        'content-type': 'application/json',
      },
      body: [{ company: 'test_company_dummy_xyz', reason: 'Unit test exclusion' }],
    })
    assert.strictEqual(importRes.status, 200)
    assert.ok(typeof importRes.json?.added === 'number')

    // Clean up the dummy exclusion
    const delRes = await makeRequest({
      port,
      path: '/api/exclusions/test_company_dummy_xyz',
      method: 'DELETE',
      headers: { host: `127.0.0.1:${port}` },
    })
    assert.strictEqual(delRes.status, 204)
  })

  await t.test('POST /api/system/update runs updater and returns JSON status', async () => {
    const updateRes = await makeRequest({
      port,
      path: '/api/system/update',
      method: 'POST',
      headers: { host: `127.0.0.1:${port}` },
    })
    assert.strictEqual(updateRes.status, 200)
    assert.strictEqual(updateRes.json?.ok, true)
    assert.ok(typeof updateRes.json?.output === 'string')
  })

  await t.test('PUT /api/profile accepts all 7 enabled platforms', async () => {
    const profileRes = await makeRequest({
      port,
      path: '/api/profile',
      method: 'GET',
      headers: { host: `127.0.0.1:${port}` },
    })
    assert.strictEqual(profileRes.status, 200)
    const existing = profileRes.json || {}
    existing.ats_settings = {
      ...(existing.ats_settings || {}),
      enabled_platforms: ['ashby', 'greenhouse', 'lever', 'workable', 'breezy', 'recruitee', 'bamboohr'],
    }
    const putRes = await makeRequest({
      port,
      path: '/api/profile',
      method: 'PUT',
      headers: {
        host: `127.0.0.1:${port}`,
        'content-type': 'application/json',
      },
      body: existing,
    })
    assert.strictEqual(putRes.status, 200)
    assert.deepStrictEqual(putRes.json?.ats_settings?.enabled_platforms, [
      'ashby',
      'greenhouse',
      'lever',
      'workable',
      'breezy',
      'recruitee',
      'bamboohr',
    ])
  })
})

test('Dynamic port fallback EADDRINUSE binds to next port and authorizes Host', async () => {
  const dummy = http.createServer((_req, res) => res.end('dummy'))
  await new Promise((resolve) => dummy.listen(0, '127.0.0.1', resolve))
  const occupiedPort = dummy.address().port

  try {
    const server = await startServer(occupiedPort, 3)
    const activePort = server.address().port
    assert.strictEqual(activePort, occupiedPort + 1, 'Server should bind to next available port')

    const res = await makeRequest({
      port: activePort,
      path: '/api/applications',
      headers: { host: `127.0.0.1:${activePort}` },
    })
    assert.strictEqual(res.status, 200, 'Fallback port must be authorized and return 200')
    assert.ok(Array.isArray(res.json))
    server.close()
  } finally {
    dummy.close()
  }
})
