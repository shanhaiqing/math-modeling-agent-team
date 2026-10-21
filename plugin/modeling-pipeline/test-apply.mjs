// Offline plugin test. It imports only index.js and a mock ctx: no DSH is loaded.
// It checks both registration and one real tool execution (pipeline_status -> Python kernel).
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { apply } from './index.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(here, '..', '..')
const runRoot = process.env.PIPELINE_TEST_ROOT || path.join(repoRoot, 'runs', 'plugin-test-run')

const registered = []
const ctx = {
  tools: {
    register(tool) {
      registered.push(tool)
      return () => {}
    },
  },
}

apply(ctx, { repoRoot })
const names = registered.map((tool) => tool.name)
const expected = [
  'pipeline_status',
  'pipeline_start',
  'pipeline_submit',
  'pipeline_gate',
  'pipeline_freshness',
  'pipeline_rework',
]
if (JSON.stringify(names) !== JSON.stringify(expected)) {
  throw new Error(`unexpected tool registration: ${JSON.stringify(names)}`)
}
for (const tool of registered) {
  if (!tool.description || !tool.parameters || !tool.output || typeof tool.execute !== 'function') {
    throw new Error(`incomplete tool definition: ${tool.name}`)
  }
}

if (!fs.existsSync(path.join(runRoot, 'run_state.json'))) {
  console.log(`ok: registration only (no test run at ${runRoot})`)
  process.exit(0)
}

const status = await registered.find((tool) => tool.name === 'pipeline_status').execute(
  { project_root: runRoot, view: 'brief' },
  {},
)
if (!status || status.run_id !== 'plugin-test-run') {
  throw new Error(`pipeline_status returned unexpected value: ${JSON.stringify(status)}`)
}
console.log(`ok: ${names.join(', ')}; pipeline_status stage=${status.stage} status=${status.status}`)
