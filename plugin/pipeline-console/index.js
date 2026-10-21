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

  ctx.effect(function* () {
    yield async () => {
      for (const dispose of disposers.splice(0)) dispose()
    }
  }, 'pipeline-console routes')
}
