import { execFile } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { promisify } from 'node:util'

const execFileAsync = promisify(execFile)

export const inject = ['tools']

export const name = 'modeling-pipeline'

function findRepoRoot(projectRoot, config) {
  if (config && config.repoRoot) return path.resolve(config.repoRoot)
  let dir = path.resolve(projectRoot)
  for (let i = 0; i < 10; i += 1) {
    if (fs.existsSync(path.join(dir, 'system', 'framework.json'))) return dir
    const parent = path.dirname(dir)
    if (parent === dir) break
    dir = parent
  }
  return process.cwd()
}

function kernelPaths(projectRoot, config) {
  const repoRoot = findRepoRoot(projectRoot, config)
  const kernelPath = (config && config.kernelPath) || path.join(repoRoot, 'tools', 'pipeline_kernel.py')
  let python = config && config.python
  if (!python) {
    const venv = path.join(repoRoot, '.venv', 'Scripts', 'python.exe')
    python = fs.existsSync(venv) ? venv : (process.platform === 'win32' ? 'python' : 'python3')
  }
  return { repoRoot, kernelPath, python }
}

async function runKernel(projectRoot, config, args) {
  const { kernelPath, python } = kernelPaths(projectRoot, config)
  if (!fs.existsSync(kernelPath)) {
    throw new Error(`pipeline kernel not found: ${kernelPath}`)
  }
  const timeout = (config && config.timeoutMs) || 180000
  try {
    const { stdout } = await execFileAsync(python, [kernelPath, ...args], {
      cwd: path.resolve(projectRoot),
      timeout,
      maxBuffer: 16 * 1024 * 1024,
      windowsHide: true,
    })
    return JSON.parse(stdout)
  } catch (error) {
    const stdout = typeof error?.stdout === 'string' ? error.stdout : ''
    if (stdout.trim()) {
      try {
        return JSON.parse(stdout)
      } catch {
        // fall through to the infrastructure error
      }
    }
    const stderr = typeof error?.stderr === 'string' ? error.stderr.slice(0, 1500) : ''
    throw new Error(`pipeline kernel failed: ${error?.message || String(error)}${stderr ? `\n${stderr}` : ''}`)
  }
}

function textOutput() {
  return {
    schema: { type: 'object' },
    render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
  }
}

// Property node for the standard JSON Schema parameter map. Required-ness is
// expressed in the root `required` array, not on the property node.
function projectRootProp() {
  return {
    type: 'string',
    description: 'Absolute path to the run project root that contains run_state.json (or will after start).',
  }
}

function toolStatus(config) {
  return {
    name: 'pipeline_status',
    description: 'Read the pipeline run state. Use view=brief before decisions, view=gate for the current human gate packet, view=artifacts to inspect hashes, view=budget for time/token use. Read-only; never changes state.',
    parameters: {
      type: 'object',
      properties: {
        project_root: projectRootProp(),
        view: {
          type: 'string',
          enum: ['full', 'brief', 'gate', 'budget', 'artifacts'],
          description: 'Which projection to return. Defaults to brief.',
        },
      },
      required: ['project_root'],
    },
    output: textOutput(),
    async execute(args) {
      return runKernel(args.project_root, config, [
        'status', '--project-root', args.project_root, '--view', args.view || 'brief',
      ])
    },
  }
}

function toolStart(config) {
  return {
    name: 'pipeline_start',
    description: 'Create a new pipeline run (run_state.json) after the human confirms the project root, problem track, contest profile and run profile. Creates the run directories and initial state; does not run checks.',
    parameters: {
      type: 'object',
      properties: {
        project_root: projectRootProp(),
        track: {
          type: 'string',
          enum: ['opt', 'stats'],
          description: 'Problem track from G0. No default: opt and stats are different pipelines.',
        },
        profile: {
          type: 'string',
          enum: ['quality', 'balanced', 'economy'],
          description: 'Run profile. Defaults to balanced; use quality for the formal competition.',
        },
        contest_profile: {
          type: 'string',
          enum: ['cumcm', 'shuwei_zh', 'shuwei_en'],
          description: 'Contest format profile. Defaults to cumcm.',
        },
        run_id: {
          type: 'string',
          description: 'Optional run id; otherwise a timestamp id is generated.',
        },
        contest_year: {
          type: 'number',
          description: 'Contest year used by compliance checks; defaults to the current year.',
        },
        force: {
          type: 'boolean',
          description: 'Overwrite an existing run_state.json. Use only with explicit human approval.',
        },
      },
      required: ['project_root', 'track'],
    },
    output: textOutput(),
    async execute(args) {
      const cmd = [
        'start', '--project-root', args.project_root,
        '--track', args.track,
        '--profile', args.profile || 'balanced',
        '--contest-profile', args.contest_profile || 'cumcm',
      ]
      if (args.run_id) cmd.push('--run-id', args.run_id)
      if (args.contest_year) cmd.push('--contest-year', String(args.contest_year))
      if (args.force) cmd.push('--force')
      return runKernel(args.project_root, config, cmd)
    },
  }
}

function toolSubmit(config) {
  return {
    name: 'pipeline_submit',
    description: 'Submit the current stage for deterministic checks and possible advancement. Only the stage owner should call it. It runs the real check commands; a failure returns structured findings and keeps the stage. Never use it for a human gate stage (METHOD_GATE, MODEL_REVIEW, DRAFT_REVIEW, ADJUDICATION, DELIVER).',
    parameters: {
      type: 'object',
      properties: {
        project_root: projectRootProp(),
        stage: {
          type: 'string',
          description: 'Stage being submitted, e.g. INTAKE, MODELING, METHOD, FIGURES, WRITING, REVIEW, FIX_R1, RE_REVIEW_R1, COMPLIANCE.',
        },
        role: {
          type: 'string',
          description: 'Role submitting, e.g. lead, solver, method, figures, writer, reviewer.',
        },
        produced_by: {
          type: 'string',
          description: 'The role that actually produced the artifacts. Used for provenance; the kernel rejects a producer that is not the stage owner.',
        },
        summary: {
          type: 'string',
          description: 'One-line summary of what was produced or fixed.',
        },
      },
      required: ['project_root', 'stage', 'role', 'produced_by'],
    },
    output: textOutput(),
    async execute(args) {
      return runKernel(args.project_root, config, [
        'submit', '--project-root', args.project_root,
        '--stage', args.stage,
        '--role', args.role,
        '--produced-by', args.produced_by,
        '--summary', args.summary || '',
      ])
    },
  }
}

function toolGate(config) {
  return {
    name: 'pipeline_gate',
    description: 'Record a human gate decision after the human has actually answered. Approval binds the current artifact hashes. Return decisions create the kernel rework brief and, for root causes, the failure dossier. Never call it to bypass a missing submit or a failed check.',
    parameters: {
      type: 'object',
      properties: {
        project_root: projectRootProp(),
        gate: {
          type: 'string',
          enum: ['G0', 'G1', 'G2', 'G3', 'G4', 'G5'],
          description: 'Gate id.',
        },
        decision: {
          type: 'string',
          description: 'One of the gate options, e.g. approve, fix, proceed, rollback, return_modeling, return_figures, return_writing, accept, deliver, stop.',
        },
        reason: {
          type: 'string',
          description: 'The human reason, recorded verbatim. Required even for approve.',
        },
        return_target: {
          type: 'string',
          description: 'Optional explicit return target; the kernel otherwise computes the earliest stale downstream stage.',
        },
        scope: {
          type: 'string',
          enum: ['local', 'root'],
          description: 'Return scope. local -> resume; root -> fresh_dossier. Defaults to root for safety.',
        },
        root_cause: {
          type: 'string',
          description: 'Failure dossier root cause: method_mismatch, model_structure, data_or_leakage, numeric_or_code, missing_verification, assumption, writing_or_compliance, unknown.',
        },
      },
      required: ['project_root', 'gate', 'decision', 'reason'],
    },
    output: textOutput(),
    async execute(args) {
      const cmd = [
        'gate', '--project-root', args.project_root,
        '--gate', args.gate,
        '--decision', args.decision,
        '--reason', args.reason,
      ]
      if (args.return_target) cmd.push('--return-target', args.return_target)
      if (args.scope) cmd.push('--scope', args.scope)
      if (args.root_cause) cmd.push('--root-cause', args.root_cause)
      return runKernel(args.project_root, config, cmd)
    },
  }
}

function toolFreshness(config) {
  return {
    name: 'pipeline_freshness',
    description: 'Before spawning or resuming a solver/reviewer, record and get the freshness mode: resume (local fix), fresh (new context), fresh_dossier (root cause with failure dossier + plan gate + regression checks), or fresh_independent (review second opinion). The kernel records the decision; do not decide it silently.',
    parameters: {
      type: 'object',
      properties: {
        project_root: projectRootProp(),
        role: {
          type: 'string',
          enum: ['solver', 'reviewer'],
          description: 'Role being spawned or resumed.',
        },
        trigger: {
          type: 'string',
          description: 'Trigger, e.g. initial, local_fix, method_blocked, model_change, high_failure, human_request, context_lost.',
        },
        scope: {
          type: 'string',
          enum: ['local', 'root'],
          description: 'Defect scope. Defaults to local.',
        },
        affected: {
          type: 'number',
          description: 'Number of affected subproblems; 2 or more tends to force fresh_dossier.',
        },
        context_lost: {
          type: 'boolean',
          description: 'The previous child/session was lost; force a fresh mode.',
        },
        human_request: {
          type: 'boolean',
          description: 'The human asked for a second opinion or a fresh attempt.',
        },
        child_id: {
          type: 'string',
          description: 'Child/session id to store for a later resume.',
        },
        round: {
          type: 'number',
          description: 'Review round: 1 for R1, 2 for R2. Defaults to 1.',
        },
      },
      required: ['project_root', 'role', 'trigger'],
    },
    output: textOutput(),
    async execute(args) {
      const cmd = [
        'freshness', '--project-root', args.project_root,
        '--role', args.role,
        '--trigger', args.trigger,
        '--scope', args.scope || 'local',
        '--affected', String(args.affected ?? 1),
        '--round', String(args.round ?? 1),
      ]
      if (args.context_lost) cmd.push('--context-lost')
      if (args.human_request) cmd.push('--human-request')
      if (args.child_id) cmd.push('--child-id', args.child_id)
      return runKernel(args.project_root, config, cmd)
    },
  }
}

function toolRework(config) {
  return {
    name: 'pipeline_rework',
    description: 'Rework helpers. validate-plan: check failure_dossier + rework_plan before the fresh solver writes code. run-regressions: run the plan acceptance tests. route: compute the earliest stale downstream stage. Never skip validate-plan for a fresh_dossier rework.',
    parameters: {
      type: 'object',
      properties: {
        project_root: projectRootProp(),
        action: {
          type: 'string',
          enum: ['validate-plan', 'run-regressions', 'route'],
          description: 'Which rework helper to run.',
        },
      },
      required: ['project_root', 'action'],
    },
    output: textOutput(),
    async execute(args) {
      const command = {
        'validate-plan': 'validate-rework-plan',
        'run-regressions': 'run-regressions',
        route: 'route',
      }[args.action]
      if (!command) throw new Error(`unknown rework action: ${args.action}`)
      return runKernel(args.project_root, config, [command, '--project-root', args.project_root])
    },
  }
}

export function apply(ctx, config = {}) {
  if (!ctx.tools || typeof ctx.tools.register !== 'function') {
    throw new Error('modeling-pipeline requires the tools service')
  }
  const tools = [
    toolStatus(config),
    toolStart(config),
    toolSubmit(config),
    toolGate(config),
    toolFreshness(config),
    toolRework(config),
  ]
  // Direct registration mirrors shipped tool plugins (for example dsh-tool-schedule).
  // Do not use ctx.effect here: its callback is a generator-style disposer contract,
  // and a plain function caused the activation failure on the first install.
  for (const tool of tools) {
    ctx.tools.register(tool)
  }
}
