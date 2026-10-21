import fs from 'node:fs/promises'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'

const execFileAsync = promisify(execFile)
const RUN_ID_RE = /^[A-Za-z0-9._-]+$/
const MIME = {
  '.pdf': 'application/pdf',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.json': 'application/json; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.tex': 'text/plain; charset=utf-8',
  '.zip': 'application/zip',
}

function sendJson(res, status, value) {
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
  })
  res.end(JSON.stringify(value))
}

async function readJson(file) {
  try {
    return JSON.parse(await fs.readFile(file, 'utf8'))
  } catch {
    return null
  }
}

async function jsonlTail(file, count) {
  try {
    const text = await fs.readFile(file, 'utf8')
    return text.trim().split(/\r?\n/).slice(-count).map((line) => {
      try { return JSON.parse(line) } catch { return null }
    }).filter(Boolean)
  } catch {
    return []
  }
}

function isInside(root, target) {
  const rel = path.relative(root, target)
  return rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel))
}

function readBody(req, limit = 1024 * 1024) {
  return new Promise((resolve, reject) => {
    let size = 0
    const chunks = []
    req.on('data', (chunk) => {
      size += chunk.length
      if (size > limit) {
        reject(new Error('request body too large'))
        req.destroy()
        return
      }
      chunks.push(chunk)
    })
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')))
    req.on('error', reject)
  })
}

export const inject = ['webServer']
export const name = 'pipeline-console'

export function apply(ctx, config = {}) {
  const repoRoot = path.resolve(config.repoRoot || process.cwd())
  const runsDir = path.resolve(repoRoot, config.runsDir || 'runs')
  const python = config.python || (
    existsSync(path.join(repoRoot, '.venv', 'Scripts', 'python.exe'))
      ? path.join(repoRoot, '.venv', 'Scripts', 'python.exe')
      : 'python'
  )
  const kernel = config.kernelPath || path.join(repoRoot, 'tools', 'pipeline_kernel.py')
  const annotator = config.annotator || path.join(repoRoot, 'tools', 'annotate_figure.py')
  const disposers = []

  function runPath(id) {
    if (!RUN_ID_RE.test(id)) throw new Error('invalid run id')
    const target = path.resolve(runsDir, id)
    if (!isInside(runsDir, target)) throw new Error('run path escapes runsDir')
    return target
  }

  async function listRuns() {
    const entries = await fs.readdir(runsDir, { withFileTypes: true })
    const runs = []
    for (const entry of entries) {
      if (!entry.isDirectory() || !RUN_ID_RE.test(entry.name)) continue
      const root = path.join(runsDir, entry.name)
      const state = await readJson(path.join(root, 'run_state.json'))
      if (!state) continue
      const stat = await fs.stat(path.join(root, 'run_state.json')).catch(() => null)
      runs.push({
        id: entry.name,
        status: state.status || null,
        stage: state.stage || null,
        gate: state.gate || null,
        next_action: state.next_action || null,
        profile: state.profile || null,
        track: state.problem_track || null,
        contest_profile: state.contest_profile || null,
        updated_at: state.updated_at || null,
        mtime: stat ? stat.mtime.toISOString() : null,
        rework: Boolean(state.rework && state.rework.active),
      })
    }
    runs.sort((a, b) => String(b.updated_at || b.mtime || '').localeCompare(String(a.updated_at || a.mtime || '')))
    return { repoRoot, runsDir, runs }
  }

  async function gatePacket(root) {
    if (!existsSync(kernel)) return { error: `kernel not found: ${kernel}` }
    try {
      const { stdout } = await execFileAsync(python, [
        kernel, 'status', '--project-root', root, '--view', 'gate',
      ], {
        cwd: repoRoot,
        timeout: 20000,
        maxBuffer: 4 * 1024 * 1024,
        windowsHide: true,
      })
      return JSON.parse(stdout)
    } catch (error) {
      const stdout = typeof error?.stdout === 'string' ? error.stdout : ''
      if (stdout.trim()) {
        try { return JSON.parse(stdout) } catch { /* keep the infrastructure error */ }
      }
      return { error: String(error?.message || error) }
    }
  }

  async function runKernel(root, args) {
    try {
      const { stdout } = await execFileAsync(python, [kernel, ...args], {
        cwd: repoRoot,
        timeout: 30000,
        maxBuffer: 4 * 1024 * 1024,
        windowsHide: true,
      })
      return JSON.parse(stdout)
    } catch (error) {
      const stdout = typeof error?.stdout === 'string' ? error.stdout : ''
      if (stdout.trim()) {
        try { return JSON.parse(stdout) } catch { /* keep the infrastructure error */ }
      }
      throw new Error(`kernel failed: ${String(error?.message || error)}`)
    }
  }

  async function appendFigureFeedback(root, record) {
    const dir = path.join(root, 'decision_logs')
    await fs.mkdir(dir, { recursive: true })
    const file = path.join(dir, 'figure_feedback.json')
    const current = await readJson(file)
    const items = Array.isArray(current) ? current : []
    items.push(record)
    await fs.writeFile(file, JSON.stringify(items.slice(-100), null, 2), 'utf8')
  }

  function annotationsPath(root) {
    return path.join(root, 'decision_logs', 'figure_annotations.json')
  }

  async function readAnnotations(root) {
    const payload = await readJson(annotationsPath(root))
    return payload && typeof payload === 'object' && payload.figures && typeof payload.figures === 'object'
      ? payload
      : { run_id: path.basename(root), figures: {} }
  }

  function clampNumber(value, min, max, fallback) {
    const number = Number(value)
    return Number.isFinite(number) ? Math.min(max, Math.max(min, number)) : fallback
  }

  function sanitizeElement(element, index) {
    if (!element || typeof element !== 'object') throw new Error(`element ${index} must be an object`)
    const text = String(element.text || '').slice(0, 2000)
    if (!text.trim()) throw new Error(`element ${index} text is empty`)
    const color = typeof element.color === 'string' && /^#[0-9a-fA-F]{6}$/.test(element.color)
      ? element.color : '#222222'
    const background = element.background === null ? null
      : (typeof element.background === 'string' && /^#[0-9a-fA-F]{6}$/.test(element.background)
        ? element.background : '#ffffff')
    return {
      id: String(element.id || `el-${index + 1}`),
      text,
      x: clampNumber(element.x, 0, 0.99, 0.1),
      y: clampNumber(element.y, 0, 0.99, 0.1),
      w: clampNumber(element.w, 0.02, 1, 0.25),
      h: clampNumber(element.h, 0.01, 1, 0.08),
      fontSize: clampNumber(element.fontSize, 8, 96, 20),
      color,
      background,
      align: element.align === 'center' ? 'center' : 'left',
    }
  }

  async function writeAnnotations(root, runId, figure, elements) {
    const payload = await readAnnotations(root)
    payload.run_id = runId
    payload.figures = payload.figures || {}
    payload.figures[figure] = {
      elements: elements.slice(0, 100).map((element, index) => sanitizeElement(element, index)),
      updated_at: new Date().toISOString(),
    }
    await fs.mkdir(path.join(root, 'decision_logs'), { recursive: true })
    await fs.writeFile(annotationsPath(root), JSON.stringify(payload, null, 2), 'utf8')
    return payload.figures[figure]
  }

  async function exportAnnotations(root, figure) {
    if (!existsSync(annotator)) throw new Error(`annotator not found: ${annotator}`)
    const { stdout } = await execFileAsync(python, [
      annotator, '--run-root', root, '--figure', figure,
    ], {
      cwd: repoRoot,
      timeout: 60000,
      maxBuffer: 4 * 1024 * 1024,
      windowsHide: true,
    })
    return JSON.parse(stdout)
  }

  function assertFigure(figure) {
    if (!figure.startsWith('result_bundle/figures/') || !figure.toLowerCase().endsWith('.png')) {
      throw new Error('figure must be a result_bundle/figures/*.png path')
    }
  }

  async function listFigures(root) {
    const dir = path.join(root, 'result_bundle', 'figures')
    try {
      const names = await fs.readdir(dir)
      return names
        .filter((name) => name.toLowerCase().endsWith('.png'))
        .sort()
        .map((name) => ({ name, path: `result_bundle/figures/${name}` }))
    } catch {
      return []
    }
  }

  async function listFiles(root) {
    const candidates = [
      ['paper.pdf', '论文 PDF'],
      ['paper.tex', '论文 LaTeX'],
      ['submission/支撑材料.zip', '支撑材料 ZIP'],
      ['submission/MD5.txt', 'MD5'],
      ['decision_logs/abstract_candidates.md', '摘要候选'],
      ['handoff_notes_2.md', '写作交接'],
    ]
    const files = []
    for (const [rel, label] of candidates) {
      const stat = await fs.stat(path.join(root, rel)).catch(() => null)
      files.push({
        path: rel,
        label,
        exists: Boolean(stat),
        size: stat ? stat.size : null,
      })
    }
    return files
  }

  async function detail(id) {
    const root = runPath(id)
    const state = await readJson(path.join(root, 'run_state.json'))
    if (!state) return { error: 'run_state.json not found' }
    const review = await readJson(path.join(root, 'decision_logs', 'review_report.json'))
    const method = await readJson(path.join(root, 'decision_logs', 'method_critique.json'))
    const coverage = await readJson(path.join(root, 'decision_logs', 'problem_coverage.json'))
    return {
      run: id,
      state,
      checks: await readJson(path.join(root, 'checks_summary.json')),
      gate_packet: await gatePacket(root),
      review: review ? {
        verdict: review.verdict || null,
        round: review.round || null,
        high_severity_count: review.high_severity_count ?? null,
        total_score: review.total_score ?? review.score ?? null,
      } : null,
      method: method ? {
        verdict: method.verdict || null,
        recommend: method.recommend || null,
      } : null,
      coverage,
      figures: await listFigures(root),
      files: await listFiles(root),
      decisions: await jsonlTail(path.join(root, 'gate_decisions.jsonl'), 8),
    }
  }

  function route(handler) {
    return async (req, res) => {
      try {
        await handler(req, res)
      } catch (error) {
        sendJson(res, 500, { error: String(error?.message || error) })
      }
    }
  }

  disposers.push(ctx.webServer.register({
    kind: 'exact',
    path: '/pipeline-console/runs',
    handler: route(async (req, res) => {
      sendJson(res, 200, await listRuns())
    }),
  }))

  disposers.push(ctx.webServer.register({
    kind: 'exact',
    path: '/pipeline-console/detail',
    handler: route(async (req, res) => {
      const url = new URL(req.url || '/', 'http://localhost')
      const id = url.searchParams.get('run') || ''
      const value = await detail(id)
      sendJson(res, value.error ? 404 : 200, value)
    }),
  }))

  disposers.push(ctx.webServer.register({
    kind: 'exact',
    path: '/pipeline-console/file',
    handler: route(async (req, res) => {
      const url = new URL(req.url || '/', 'http://localhost')
      const id = url.searchParams.get('run') || ''
      const rel = url.searchParams.get('path') || ''
      const root = runPath(id)
      const target = path.resolve(root, rel)
      if (!isInside(root, target)) {
        sendJson(res, 403, { error: 'path escapes run root' })
        return
      }
      const data = await fs.readFile(target)
      res.writeHead(200, {
        'Content-Type': MIME[path.extname(target).toLowerCase()] || 'application/octet-stream',
        'Content-Length': data.length,
        'Cache-Control': 'no-store',
      })
      res.end(data)
    }),
  }))

  disposers.push(ctx.webServer.register({
    kind: 'exact',
    path: '/pipeline-console/gate',
    handler: route(async (req, res) => {
      if (req.method !== 'POST') {
        sendJson(res, 405, { error: 'POST only' })
        return
      }
      const body = JSON.parse((await readBody(req)) || '{}')
      const id = String(body.run || '')
      const root = runPath(id)
      const gate = String(body.gate || '')
      const decision = String(body.decision || '')
      const reason = String(body.reason || '').trim()
      if (!gate || !decision || !reason) {
        sendJson(res, 400, { error: 'gate, decision and reason are required' })
        return
      }
      const args = [
        'gate', '--project-root', root,
        '--gate', gate, '--decision', decision,
        '--reason', reason,
      ]
      if (body.scope) args.push('--scope', String(body.scope))
      if (body.root_cause) args.push('--root-cause', String(body.root_cause))
      if (body.return_target) args.push('--return-target', String(body.return_target))
      const result = await runKernel(root, args)
      sendJson(res, result && result.ok === false ? 400 : 200, result)
    }),
  }))

  disposers.push(ctx.webServer.register({
    kind: 'exact',
    path: '/pipeline-console/figure-feedback',
    handler: route(async (req, res) => {
      if (req.method !== 'POST') {
        sendJson(res, 405, { error: 'POST only' })
        return
      }
      const body = JSON.parse((await readBody(req)) || '{}')
      const id = String(body.run || '')
      const root = runPath(id)
      const figure = String(body.figure || '')
      const comment = String(body.comment || '').trim()
      const raw = body.bbox && typeof body.bbox === 'object' ? body.bbox : null
      const bbox = raw ? {
        x: Number(raw.x), y: Number(raw.y), w: Number(raw.w), h: Number(raw.h),
      } : null
      if (!figure.startsWith('result_bundle/figures/') || !figure.toLowerCase().endsWith('.png')) {
        sendJson(res, 400, { error: 'figure must be a result_bundle/figures/*.png path' })
        return
      }
      if (!comment) {
        sendJson(res, 400, { error: 'comment is required' })
        return
      }
      if (!bbox || ![bbox.x, bbox.y, bbox.w, bbox.h].every(Number.isFinite)
        || bbox.w <= 0 || bbox.h <= 0 || bbox.x < 0 || bbox.y < 0
        || bbox.x + bbox.w > 1.0001 || bbox.y + bbox.h > 1.0001) {
        sendJson(res, 400, { error: 'bbox must be normalized within [0,1]' })
        return
      }
      const target = path.resolve(root, figure)
      if (!isInside(root, target)) {
        sendJson(res, 403, { error: 'figure path escapes run root' })
        return
      }
      const record = {
        id: `FB-${Date.now().toString(36)}`,
        created_at: new Date().toISOString(),
        run: id,
        figure,
        bbox,
        comment,
        status: 'pending',
        source: 'pipeline-console',
      }
      await appendFigureFeedback(root, record)
      sendJson(res, 200, { ok: true, record })
    }),
  }))

  disposers.push(ctx.webServer.register({
    kind: 'exact',
    path: '/pipeline-console/annotations',
    handler: route(async (req, res) => {
      if (req.method === 'GET') {
        const url = new URL(req.url || '/', 'http://localhost')
        const id = url.searchParams.get('run') || ''
        const figure = url.searchParams.get('figure') || ''
        assertFigure(figure)
        const root = runPath(id)
        const payload = await readAnnotations(root)
        const record = payload.figures[figure] || { elements: [] }
        sendJson(res, 200, { run: id, figure, elements: record.elements || [] })
        return
      }
      if (req.method !== 'POST') {
        sendJson(res, 405, { error: 'GET or POST only' })
        return
      }
      const body = JSON.parse((await readBody(req)) || '{}')
      const id = String(body.run || '')
      const root = runPath(id)
      const figure = String(body.figure || '')
      assertFigure(figure)
      if (!Array.isArray(body.elements)) {
        sendJson(res, 400, { error: 'elements must be an array' })
        return
      }
      const record = await writeAnnotations(root, id, figure, body.elements)
      sendJson(res, 200, { ok: true, run: id, figure, elements: record.elements, updated_at: record.updated_at })
    }),
  }))

  disposers.push(ctx.webServer.register({
    kind: 'exact',
    path: '/pipeline-console/annotations/export',
    handler: route(async (req, res) => {
      if (req.method !== 'POST') {
        sendJson(res, 405, { error: 'POST only' })
        return
      }
      const body = JSON.parse((await readBody(req)) || '{}')
      const id = String(body.run || '')
      const root = runPath(id)
      const figure = String(body.figure || '')
      assertFigure(figure)
      const result = await exportAnnotations(root, figure)
      sendJson(res, 200, result)
    }),
  }))

  ctx.effect(function* () {
    yield async () => {
      for (const dispose of disposers.splice(0)) dispose()
    }
  }, 'pipeline-console routes')
}
