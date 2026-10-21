window.__ModuleLoader__.load({
  id: '@local/pipeline-console-3c',
  factory(require) {
    const React = require('react')
    const h = React.createElement

    const en = {
      title: 'Pipeline',
      subtitle: 'Local modeling-pipeline runs, gate decisions and figure feedback',
      refresh: 'Refresh',
      runs: 'Runs',
      noRuns: 'No runs found. Start one with pipeline_start.',
      selectRun: 'Select a run.',
      status: 'Status',
      stage: 'Stage',
      gate: 'Gate',
      next: 'Next',
      checks: 'Checks',
      errors: 'errors',
      warns: 'warns',
      rework: 'Rework',
      figures: 'Figures',
      artifacts: 'Artifacts',
      paper: 'Paper',
      open: 'Open',
      gatePacket: 'Gate packet',
      decisions: 'Recent gate decisions',
      gateAction: 'Gate action',
      gateReason: 'Reason (required, recorded verbatim)',
      gateScope: 'Scope',
      gateRootCause: 'Root cause',
      submit: 'Record decision',
      gateHint: 'This writes through the Kernel pipeline_gate path. It cannot be undone from this panel.',
      gateDone: 'Decision recorded.',
      gateFailed: 'Decision failed',
      feedback: 'Figure feedback',
      feedbackHint: 'Drag a rectangle on the figure, describe the overlap/structure problem, and send it to the Figures agent.',
      feedbackComment: 'What should change in this region?',
      feedbackSend: 'Send feedback',
      feedbackSent: 'Feedback recorded in decision_logs/figure_feedback.json. Ask the Figures agent to apply it.',
      feedbackFailed: 'Feedback failed',
      feedbackSelect: 'Select area',
      overlayEdit: 'Edit image',
      overlayHint: 'Add or select a text box, drag it anywhere, edit its content, then save. The original figure is not modified.',
      addText: 'Add text',
      saveAnnotations: 'Save',
      exportAnnotated: 'Export annotated',
      deleteElement: 'Delete',
      fontSize: 'Font size',
      textColor: 'Text color',
      background: 'Background',
      saved: 'Annotations saved.',
      exported: 'Annotated files created.',
      noAnnotations: 'No text boxes yet. Click Add text.',
      cancel: 'Cancel',
      reasonRequired: 'A reason is required.',
      selecting: 'Drag a rectangle on the figure.',
      review: 'Review',
      method: 'Method',
      coverage: 'Coverage',
      readOnly: 'Gate decisions write through the Kernel; figure feedback is recorded for the Figures agent.',
      loading: 'Loading…',
      updated: 'Updated',
      track: 'Track',
      profile: 'Profile',
      noFigures: 'No figures yet.',
      noDetail: 'No detail yet.',
      error: 'Error',
      empty: 'Nothing to show yet.',
      score: 'Score',
      high: 'High severity',
      recommend: 'Recommend',
      verdict: 'Verdict',
    }

    const zh = {
      title: '流水线',
      subtitle: '本地数模流水线 run 的只读视图',
      refresh: '刷新',
      runs: 'Run 列表',
      noRuns: '没有 run。先用 pipeline_start 开一局。',
      selectRun: '选择一个 run。',
      status: '状态',
      stage: '阶段',
      gate: '门',
      next: '下一步',
      checks: '机查',
      errors: '错误',
      warns: '警告',
      rework: '返工',
      figures: '图',
      artifacts: '产物',
      paper: '论文',
      open: '打开',
      gatePacket: '门包',
      decisions: '最近门决策',
      gateAction: '门决策',
      gateReason: '理由（必填，原样记录）',
      gateScope: '范围',
      gateRootCause: '根因',
      submit: '记录决策',
      gateHint: '这会走 Kernel pipeline_gate 路径，面板内不可撤销。',
      gateDone: '决策已记录。',
      gateFailed: '决策失败',
      feedback: '图反馈',
      feedbackHint: '在图上拖一个矩形，描述重叠/结构问题，发给 Figures agent。',
      feedbackComment: '这个区域应该怎么改？',
      feedbackSend: '发送反馈',
      feedbackSent: '反馈已写入 decision_logs/figure_feedback.json；让 Figures agent 读取并应用。',
      feedbackFailed: '反馈失败',
      feedbackSelect: '选择区域',
      overlayEdit: '编辑图',
      overlayHint: '新增/选中文字框，拖动到任意位置，修改内容后保存；原图不会被修改。',
      addText: '添加文字',
      saveAnnotations: '保存',
      exportAnnotated: '导出标注图',
      deleteElement: '删除',
      fontSize: '字号',
      textColor: '文字颜色',
      background: '背景',
      saved: '标注已保存。',
      exported: '标注图已生成。',
      noAnnotations: '还没有文字框。点“添加文字”。',
      cancel: '取消',
      reasonRequired: '必须填写理由。',
      selecting: '在图上拖一个矩形。',
      review: '评审',
      method: '方法学',
      coverage: '题面覆盖',
      readOnly: '门决策经 Kernel 写入；图反馈会记录给 Figures agent。',
      loading: '加载中…',
      updated: '更新时间',
      track: '题型',
      profile: '档位',
      noFigures: '还没有图。',
      noDetail: '还没有详情。',
      error: '错误',
      empty: '暂无内容。',
      score: '评分',
      high: '高危',
      recommend: '推荐',
      verdict: '结论',
    }

    async function fetchJson(url) {
      const response = await fetch(url, { cache: 'no-store' })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      return response.json()
    }

    function fileUrl(run, path) {
      return `/pipeline-console/file?run=${encodeURIComponent(run)}&path=${encodeURIComponent(path)}`
    }

    function statusTone(value) {
      const text = String(value || '').toUpperCase()
      if (text.includes('FAIL') || text.includes('ERROR')) return 'var(--dsw-alias-state-error-primary)'
      if (text.includes('WAIT') || text.includes('REVIEW')) return 'var(--dsw-alias-state-warn-primary)'
      if (text.includes('DELIVER') || text.includes('DONE') || text.includes('PASS')) return 'var(--dsw-alias-state-success-primary)'
      return 'var(--dsw-alias-label-secondary)'
    }

    function Chip({ label, value, color }) {
      return h('span', {
        style: {
          display: 'inline-flex', alignItems: 'center', gap: 4,
          padding: '2px 8px', borderRadius: 999,
          border: '1px solid var(--dsw-alias-border-l1)',
          background: 'var(--dsw-alias-bg-layer-2)',
          fontSize: 12, lineHeight: '18px', color: color || 'var(--dsw-alias-label-primary)',
          whiteSpace: 'nowrap',
        },
      }, h('span', { style: { color: 'var(--dsw-alias-label-secondary)' } }, `${label}:`), String(value ?? '—'))
    }

    function Section({ title, children }) {
      return h('section', { style: { marginTop: 18 } },
        h('h3', {
          style: {
            margin: '0 0 8px', fontSize: 13, fontWeight: 600,
            color: 'var(--dsw-alias-label-secondary)',
            textTransform: 'uppercase', letterSpacing: 0.4,
          },
        }, title),
        children)
    }

    function PipelineIcon({ size = 20, active = false }) {
      const color = active ? 'var(--dsw-alias-brand-primary)' : 'currentColor'
      return h('svg', {
        width: size, height: size, viewBox: '0 0 24 24', fill: 'none',
        stroke: color, strokeWidth: 1.7, strokeLinecap: 'round', strokeLinejoin: 'round',
        'aria-hidden': true, style: { display: 'block' },
      },
      h('rect', { x: 3, y: 4, width: 6, height: 4, rx: 1 }),
      h('rect', { x: 15, y: 4, width: 6, height: 4, rx: 1 }),
      h('rect', { x: 9, y: 16, width: 6, height: 4, rx: 1 }),
      h('path', { d: 'M6 8v4h12V8' }),
      h('path', { d: 'M12 12v4' }))
    }

    function FeedbackModal({ run, figure, t, onClose, onSent }) {
      const [box, setBox] = React.useState(null)
      const [start, setStart] = React.useState(null)
      const [comment, setComment] = React.useState('')
      const [busy, setBusy] = React.useState(false)
      const [error, setError] = React.useState(null)
      const [sent, setSent] = React.useState(null)
      const buttonStyle = {
        appearance: 'none', border: 'none', background: 'transparent',
        color: 'inherit', font: 'inherit', cursor: 'pointer', textAlign: 'left',
      }

      const clamp = (value) => Math.max(0, Math.min(1, value))
      function point(event) {
        const rect = event.currentTarget.getBoundingClientRect()
        return {
          x: clamp((event.clientX - rect.left) / rect.width),
          y: clamp((event.clientY - rect.top) / rect.height),
        }
      }
      function down(event) {
        event.preventDefault()
        if (event.currentTarget.setPointerCapture) event.currentTarget.setPointerCapture(event.pointerId)
        const current = point(event)
        setStart(current)
        setBox({ x: current.x, y: current.y, w: 0, h: 0 })
      }
      function move(event) {
        if (!start) return
        const current = point(event)
        setBox({
          x: Math.min(start.x, current.x),
          y: Math.min(start.y, current.y),
          w: Math.abs(current.x - start.x),
          h: Math.abs(current.y - start.y),
        })
      }
      function up() {
        setStart(null)
      }
      async function send() {
        if (!box || box.w < 0.01 || box.h < 0.01) {
          setError(t('selecting'))
          return
        }
        if (!comment.trim()) {
          setError(t('feedbackComment'))
          return
        }
        setBusy(true)
        setError(null)
        try {
          const response = await fetch('/pipeline-console/figure-feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ run, figure: figure.path, bbox: box, comment: comment.trim() }),
          })
          const data = await response.json()
          if (!response.ok || (data && data.error)) {
            throw new Error(data && data.error ? data.error : `HTTP ${response.status}`)
          }
          setSent(data.record)
          if (onSent) onSent(data.record)
        } catch (err) {
          setError(`${t('feedbackFailed')}: ${String(err.message || err)}`)
        } finally {
          setBusy(false)
        }
      }

      return h('div', {
        style: {
          position: 'fixed', inset: 0, zIndex: 1000,
          background: 'rgba(0, 0, 0, 0.55)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
        },
        onClick: onClose,
      },
      h('div', {
        onClick: (event) => event.stopPropagation(),
        style: {
          width: 'min(980px, 100%)', maxHeight: '92vh', overflow: 'auto',
          background: 'var(--dsw-alias-bg-overlay)',
          border: '1px solid var(--dsw-alias-border-l1)',
          borderRadius: 12, padding: 18,
          color: 'var(--dsw-alias-label-primary)',
        },
      },
      h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' } },
        h('h3', { style: { margin: 0, fontSize: 17 } }, `${t('feedback')} · ${figure.name}`),
        h('button', { type: 'button', onClick: onClose, style: { ...buttonStyle, fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } }, t('cancel'))),
      h('p', { style: { margin: '8px 0', fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } }, t('feedbackHint')),
      h('div', {
        onPointerDown: down,
        onPointerMove: move,
        onPointerUp: up,
        onPointerLeave: up,
        style: {
          position: 'relative', userSelect: 'none', touchAction: 'none',
          cursor: 'crosshair', border: '1px solid var(--dsw-alias-border-l1)',
          borderRadius: 8, overflow: 'hidden', background: 'var(--dsw-alias-bg-layer-2)',
        },
      },
      h('img', {
        src: fileUrl(run, figure.path),
        alt: figure.name,
        draggable: false,
        style: { display: 'block', width: '100%', height: 'auto', pointerEvents: 'none' },
      }),
      box ? h('div', {
        style: {
          position: 'absolute',
          left: `${box.x * 100}%`, top: `${box.y * 100}%`,
          width: `${box.w * 100}%`, height: `${box.h * 100}%`,
          border: '2px solid var(--dsw-alias-brand-primary)',
          background: 'rgba(36, 123, 191, 0.16)',
          boxSizing: 'border-box', pointerEvents: 'none',
        },
      }) : null),
      h('textarea', {
        value: comment,
        onChange: (event) => setComment(event.target.value),
        placeholder: t('feedbackComment'),
        rows: 3,
        style: {
          width: '100%', boxSizing: 'border-box', marginTop: 10, padding: '8px 10px',
          borderRadius: 8, font: 'inherit', fontSize: 13, resize: 'vertical',
          color: 'var(--dsw-alias-label-primary)',
          background: 'var(--dsw-alias-bg-layer-2)',
          border: '1px solid var(--dsw-alias-border-l2)',
        },
      }),
      error ? h('div', { style: { marginTop: 8, fontSize: 12, color: 'var(--dsw-alias-state-error-primary)' } }, error) : null,
      sent ? h('div', { style: { marginTop: 8, fontSize: 12, color: 'var(--dsw-alias-state-success-primary)' } }, t('feedbackSent')) : null,
      h('div', { style: { display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 12 } },
        h('button', { type: 'button', onClick: onClose, style: { ...buttonStyle, padding: '7px 12px', borderRadius: 8, fontSize: 12, border: '1px solid var(--dsw-alias-border-l2)', background: 'var(--dsw-alias-bg-layer-2)' } }, t('cancel')),
        h('button', {
          type: 'button',
          disabled: busy || Boolean(sent),
          onClick: send,
          style: {
            ...buttonStyle, padding: '7px 12px', borderRadius: 8, fontSize: 12,
            border: '1px solid var(--dsw-alias-border-l2)',
            background: 'var(--dsw-alias-brand-primary)', color: 'var(--dsw-alias-bg-base)',
            opacity: busy || sent ? 0.6 : 1,
          },
        }, sent ? t('feedbackSent') : t('feedbackSend')))))
    }

    function OverlayEditor({ run, figure, t, onClose }) {
      const [elements, setElements] = React.useState([])
      const [selectedId, setSelectedId] = React.useState(null)
      const [loading, setLoading] = React.useState(true)
      const [busy, setBusy] = React.useState(false)
      const [message, setMessage] = React.useState(null)
      const [exported, setExported] = React.useState(null)
      const [drag, setDrag] = React.useState(null)
      const [imageScale, setImageScale] = React.useState(1)
      const buttonStyle = {
        appearance: 'none', border: 'none', background: 'transparent',
        color: 'inherit', font: 'inherit', cursor: 'pointer', textAlign: 'left',
      }
      const selected = elements.find((element) => element.id === selectedId) || null

      React.useEffect(() => {
        let alive = true
        fetch(`/pipeline-console/annotations?run=${encodeURIComponent(run)}&figure=${encodeURIComponent(figure.path)}`)
          .then((response) => response.json())
          .then((value) => { if (alive) setElements(Array.isArray(value.elements) ? value.elements : []) })
          .catch((err) => { if (alive) setMessage({ type: 'error', text: String(err.message || err) }) })
          .finally(() => { if (alive) setLoading(false) })
        return () => { alive = false }
      }, [run, figure.path])

      const clamp = (value) => Math.max(0, Math.min(0.99, value))
      function update(id, patch) {
        setElements((list) => list.map((element) => element.id === id ? { ...element, ...patch } : element))
      }
      function addText() {
        const id = `el-${Date.now().toString(36)}`
        const element = {
          id, text: '新文字', x: 0.32, y: 0.42, w: 0.3, h: 0.08,
          fontSize: 20, color: '#222222', background: '#ffffff', align: 'left',
        }
        setElements((list) => [...list, element])
        setSelectedId(id)
      }
      function removeSelected() {
        if (!selectedId) return
        setElements((list) => list.filter((element) => element.id !== selectedId))
        setSelectedId(null)
      }
      function pointerDown(event, element) {
        event.stopPropagation()
        const rect = event.currentTarget.parentElement.getBoundingClientRect()
        setSelectedId(element.id)
        setDrag({
          id: element.id, startX: event.clientX, startY: event.clientY,
          origX: element.x, origY: element.y, width: rect.width, height: rect.height,
        })
        if (event.currentTarget.setPointerCapture) event.currentTarget.setPointerCapture(event.pointerId)
      }
      function pointerMove(event) {
        if (!drag) return
        const dx = (event.clientX - drag.startX) / Math.max(1, drag.width)
        const dy = (event.clientY - drag.startY) / Math.max(1, drag.height)
        update(drag.id, { x: clamp(drag.origX + dx), y: clamp(drag.origY + dy) })
      }
      function pointerUp() {
        setDrag(null)
      }
      async function save() {
        setBusy(true)
        setMessage(null)
        try {
          const response = await fetch('/pipeline-console/annotations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ run, figure: figure.path, elements }),
          })
          const data = await response.json()
          if (!response.ok || (data && data.error)) throw new Error(data && data.error ? data.error : `HTTP ${response.status}`)
          setMessage({ type: 'success', text: t('saved') })
        } catch (err) {
          setMessage({ type: 'error', text: String(err.message || err) })
        } finally {
          setBusy(false)
        }
      }
      async function exportAnnotated() {
        setBusy(true)
        setMessage(null)
        setExported(null)
        try {
          const saveResponse = await fetch('/pipeline-console/annotations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ run, figure: figure.path, elements }),
          })
          const saveData = await saveResponse.json()
          if (!saveResponse.ok || (saveData && saveData.error)) {
            throw new Error(saveData && saveData.error ? saveData.error : `save HTTP ${saveResponse.status}`)
          }
          const response = await fetch('/pipeline-console/annotations/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ run, figure: figure.path }),
          })
          const data = await response.json()
          if (!response.ok || (data && data.error)) throw new Error(data && data.error ? data.error : `HTTP ${response.status}`)
          setExported(data)
          setMessage({ type: 'success', text: t('exported') })
        } catch (err) {
          setMessage({ type: 'error', text: String(err.message || err) })
        } finally {
          setBusy(false)
        }
      }

      return h('div', {
        style: {
          position: 'fixed', inset: 0, zIndex: 1001,
          background: 'rgba(0, 0, 0, 0.58)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24,
        },
        onClick: onClose,
      },
      h('div', {
        onClick: (event) => event.stopPropagation(),
        style: {
          width: 'min(1180px, 100%)', maxHeight: '94vh', overflow: 'auto',
          background: 'var(--dsw-alias-bg-overlay)',
          border: '1px solid var(--dsw-alias-border-l1)',
          borderRadius: 12, padding: 18,
          color: 'var(--dsw-alias-label-primary)',
        },
      },
      h('div', { style: { display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' } },
        h('h3', { style: { margin: 0, fontSize: 17 } }, `${t('overlayEdit')} · ${figure.name}`),
        h('button', { type: 'button', onClick: onClose, style: { ...buttonStyle, color: 'var(--dsw-alias-label-secondary)', fontSize: 12 } }, t('cancel'))),
      h('p', { style: { margin: '8px 0', fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } }, t('overlayHint')),
      h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 } },
        h('button', { type: 'button', onClick: addText, style: { ...buttonStyle, padding: '6px 10px', borderRadius: 8, fontSize: 12, border: '1px solid var(--dsw-alias-border-l2)', background: 'var(--dsw-alias-bg-layer-2)' } }, t('addText')),
        h('button', { type: 'button', onClick: save, disabled: busy, style: { ...buttonStyle, padding: '6px 10px', borderRadius: 8, fontSize: 12, border: '1px solid var(--dsw-alias-border-l2)', background: 'var(--dsw-alias-bg-layer-2)', opacity: busy ? 0.6 : 1 } }, t('saveAnnotations')),
        h('button', { type: 'button', onClick: exportAnnotated, disabled: busy, style: { ...buttonStyle, padding: '6px 10px', borderRadius: 8, fontSize: 12, border: '1px solid var(--dsw-alias-border-l2)', background: 'var(--dsw-alias-brand-primary)', color: 'var(--dsw-alias-bg-base)', opacity: busy ? 0.6 : 1 } }, t('exportAnnotated'))),
      h('div', { style: { display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 260px', gap: 14, alignItems: 'start' } },
        h('div', {
          onPointerDown: () => setSelectedId(null),
          style: { position: 'relative', userSelect: 'none', border: '1px solid var(--dsw-alias-border-l1)', borderRadius: 8, overflow: 'hidden', background: 'var(--dsw-alias-bg-layer-2)' },
        },
        h('img', {
          src: fileUrl(run, figure.path), alt: figure.name, draggable: false,
          onLoad: (event) => {
            const image = event.currentTarget
            if (image.naturalWidth > 0) setImageScale(image.clientWidth / image.naturalWidth)
          },
          style: { display: 'block', width: '100%', height: 'auto', pointerEvents: 'none' },
        }),
        loading ? h('div', { style: { position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, color: 'var(--dsw-alias-label-secondary)', background: 'rgba(0,0,0,0.15)' } }, t('loading')) : null,
        elements.map((element) => h('div', {
          key: element.id,
          onPointerDown: (event) => pointerDown(event, element),
          onPointerMove: pointerMove,
          onPointerUp: pointerUp,
          onDoubleClick: () => setSelectedId(element.id),
          style: {
            position: 'absolute',
            left: `${element.x * 100}%`, top: `${element.y * 100}%`,
            width: `${element.w * 100}%`, height: `${element.h * 100}%`,
            border: selectedId === element.id ? '2px solid var(--dsw-alias-brand-primary)' : '1px dashed var(--dsw-alias-border-l2)',
            background: element.background || 'transparent',
            color: element.color || '#222222',
            fontSize: `${Math.max(6, (Number(element.fontSize) || 20) * imageScale)}px`,
            lineHeight: 1.2, padding: 2, overflow: 'hidden', whiteSpace: 'pre-wrap',
            boxSizing: 'border-box', cursor: 'move', userSelect: 'none',
          },
        }, element.text))),
        h('aside', { style: { border: '1px solid var(--dsw-alias-border-l1)', borderRadius: 8, padding: 12, background: 'var(--dsw-alias-bg-layer-2)' } },
          selected ? h('div', { style: { display: 'flex', flexDirection: 'column', gap: 10 } },
            h('div', { style: { fontSize: 12, fontWeight: 600 } }, `${t('overlayEdit')} · ${selected.id}`),
            h('textarea', {
              value: selected.text,
              onChange: (event) => update(selected.id, { text: event.target.value }),
              rows: 5,
              style: { width: '100%', boxSizing: 'border-box', padding: 8, borderRadius: 6, font: 'inherit', fontSize: 12, background: 'var(--dsw-alias-bg-base)', color: 'inherit', border: '1px solid var(--dsw-alias-border-l1)' },
            }),
            h('label', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } },
              `${t('fontSize')} `,
              h('input', { type: 'range', min: 8, max: 48, value: selected.fontSize, onChange: (event) => update(selected.id, { fontSize: Number(event.target.value) }), style: { width: '100%' } })),
            h('label', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } },
              `${t('textColor')} `,
              h('input', { type: 'color', value: selected.color, onChange: (event) => update(selected.id, { color: event.target.value }) })),
            h('label', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } },
              h('input', { type: 'checkbox', checked: selected.background !== null, onChange: (event) => update(selected.id, { background: event.target.checked ? '#ffffff' : null }) }),
              ` ${t('background')}`),
            h('button', { type: 'button', onClick: removeSelected, style: { ...buttonStyle, padding: '6px 10px', borderRadius: 8, fontSize: 12, border: '1px solid var(--dsw-alias-state-error-primary)', color: 'var(--dsw-alias-state-error-primary)' } }, t('deleteElement'))) :
            h('div', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } }, t('noAnnotations'))))),
      message ? h('div', { style: { marginTop: 10, fontSize: 12, color: message.type === 'success' ? 'var(--dsw-alias-state-success-primary)' : 'var(--dsw-alias-state-error-primary)' } }, message.text) : null,
      exported ? h('div', { style: { marginTop: 8, display: 'flex', gap: 10, fontSize: 12 } },
        h('a', { href: fileUrl(run, exported.png), target: '_blank', rel: 'noreferrer', style: { color: 'var(--dsw-alias-brand-primary)' } }, 'annotated PNG'),
        h('a', { href: fileUrl(run, exported.pdf), target: '_blank', rel: 'noreferrer', style: { color: 'var(--dsw-alias-brand-primary)' } }, 'annotated PDF')) : null,
      h('div', { style: { display: 'flex', justifyContent: 'flex-end', marginTop: 12 } },
        h('button', { type: 'button', onClick: onClose, style: { ...buttonStyle, padding: '7px 12px', borderRadius: 8, fontSize: 12, border: '1px solid var(--dsw-alias-border-l2)', background: 'var(--dsw-alias-bg-layer-2)' } }, t('cancel'))))
    }

    function PipelinePanel({ t }) {
      const [runs, setRuns] = React.useState([])
      const [selected, setSelected] = React.useState(null)
      const [detail, setDetail] = React.useState(null)
      const [error, setError] = React.useState(null)
      const [loading, setLoading] = React.useState(true)
      const [refreshToken, setRefreshToken] = React.useState(0)
      const [gateReason, setGateReason] = React.useState('')
      const [gateScope, setGateScope] = React.useState('local')
      const [gateRootCause, setGateRootCause] = React.useState('model_structure')
      const [gateBusy, setGateBusy] = React.useState(false)
      const [gateMessage, setGateMessage] = React.useState(null)
      const [feedbackFigure, setFeedbackFigure] = React.useState(null)
      const [overlayFigure, setOverlayFigure] = React.useState(null)

      React.useEffect(() => {
        let alive = true
        async function tick() {
          try {
            const data = await fetchJson('/pipeline-console/runs')
            if (!alive) return
            const list = data.runs || []
            setRuns(list)
            setError(null)
            setSelected((current) => current || (list[0] && list[0].id) || null)
          } catch (err) {
            if (alive) setError(String(err.message || err))
          } finally {
            if (alive) setLoading(false)
          }
        }
        tick()
        const timer = setInterval(tick, 5000)
        return () => { alive = false; clearInterval(timer) }
      }, [refreshToken])

      React.useEffect(() => {
        if (!selected) { setDetail(null); return undefined }
        let alive = true
        setDetail(null)
        fetchJson(`/pipeline-console/detail?run=${encodeURIComponent(selected)}`)
          .then((value) => { if (alive) setDetail(value) })
          .catch((err) => { if (alive) setError(String(err.message || err)) })
        return () => { alive = false }
      }, [selected, refreshToken])

      async function submitGate(decision) {
        const reason = gateReason.trim()
        if (!reason) {
          setGateMessage({ type: 'error', text: t('reasonRequired') })
          return
        }
        setGateBusy(true)
        setGateMessage(null)
        try {
          const response = await fetch('/pipeline-console/gate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              run: selected,
              gate: detail && detail.gate_packet ? detail.gate_packet.gate : (state && state.gate),
              decision,
              reason,
              scope: gateScope,
              root_cause: gateRootCause,
            }),
          })
          const data = await response.json()
          if (!response.ok || (data && data.error)) {
            throw new Error(data && data.error ? data.error : `HTTP ${response.status}`)
          }
          setGateMessage({ type: 'success', text: `${t('gateDone')} ${data.to || ''}`.trim() })
          setGateReason('')
          setRefreshToken((value) => value + 1)
        } catch (err) {
          setGateMessage({ type: 'error', text: `${t('gateFailed')}: ${String(err.message || err)}` })
        } finally {
          setGateBusy(false)
        }
      }

      const shellStyle = {
        height: '100%', overflow: 'auto', boxSizing: 'border-box',
        padding: '20px 24px 32px',
        background: 'var(--dsw-alias-bg-base)',
        color: 'var(--dsw-alias-label-primary)',
      }
      const headerStyle = {
        display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
        gap: 16, marginBottom: 18,
      }
      const gridStyle = {
        display: 'grid', gridTemplateColumns: '260px minmax(0, 1fr)',
        gap: 18, alignItems: 'start',
      }
      const sideStyle = {
        border: '1px solid var(--dsw-alias-border-l1)',
        background: 'var(--dsw-alias-bg-layer-1)',
        borderRadius: 10, padding: 10,
      }
      const paneStyle = {
        border: '1px solid var(--dsw-alias-border-l1)',
        background: 'var(--dsw-alias-bg-layer-1)',
        borderRadius: 10, padding: 18, minWidth: 0,
      }
      const buttonStyle = {
        appearance: 'none', border: 'none', background: 'transparent',
        color: 'inherit', font: 'inherit', cursor: 'pointer', textAlign: 'left',
      }
      const runButtonStyle = (active) => ({
        ...buttonStyle,
        display: 'block', width: '100%', padding: '9px 10px', borderRadius: 8,
        background: active ? 'var(--dsw-alias-bg-layer-2)' : 'transparent',
        border: active ? '1px solid var(--dsw-alias-border-l2)' : '1px solid transparent',
      })
      const selectedRun = runs.find((run) => run.id === selected) || null
      const state = detail && detail.state ? detail.state : null
      const checks = detail && detail.checks ? detail.checks : null
      const review = detail && detail.review ? detail.review : null
      const method = detail && detail.method ? detail.method : null
      const files = detail && detail.files ? detail.files : []
      const figures = detail && detail.figures ? detail.figures : []
      const gatePacket = detail && detail.gate_packet ? detail.gate_packet : null
      const gateOptions = gatePacket && Array.isArray(gatePacket.options) ? gatePacket.options : []
      const needsScope = gateOptions.some((option) => ['rollback', 'return_modeling', 'return_figures', 'return_writing'].includes(option.id))

      return h('div', { style: shellStyle },
        h('header', { style: headerStyle },
          h('div', null,
            h('h2', { style: { margin: 0, fontSize: 22, fontWeight: 650 } }, t('title')),
            h('p', { style: { margin: '6px 0 0', fontSize: 13, color: 'var(--dsw-alias-label-secondary)' } }, t('subtitle')),
            h('p', { style: { margin: '8px 0 0', fontSize: 12, color: 'var(--dsw-alias-state-warn-primary)' } }, t('readOnly')),
          ),
          h('button', {
            type: 'button',
            onClick: () => setRefreshToken((value) => value + 1),
            style: {
              ...buttonStyle,
              border: '1px solid var(--dsw-alias-border-l2)',
              borderRadius: 8, padding: '7px 12px', fontSize: 12,
              background: 'var(--dsw-alias-bg-layer-2)',
            },
          }, t('refresh'))),

        error ? h('div', {
          style: {
            marginBottom: 12, padding: '8px 10px', borderRadius: 8, fontSize: 12,
            color: 'var(--dsw-alias-state-error-primary)',
            border: '1px solid var(--dsw-alias-state-error-primary)',
            background: 'var(--dsw-alias-bg-layer-2)',
          },
        }, `${t('error')}: ${error}`) : null,

        h('div', { style: gridStyle },
          h('aside', { style: sideStyle },
            h('div', { style: { fontSize: 12, fontWeight: 600, color: 'var(--dsw-alias-label-secondary)', margin: '2px 4px 8px' } }, t('runs')),
            loading ? h('div', { style: { padding: 8, fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } }, t('loading')) :
              runs.length === 0 ? h('div', { style: { padding: 8, fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } }, t('noRuns')) :
                runs.map((run) => h('button', {
                  key: run.id,
                  type: 'button',
                  onClick: () => setSelected(run.id),
                  style: runButtonStyle(run.id === selected),
                },
                h('div', { style: { fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis' } }, run.id),
                h('div', { style: { marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 6, fontSize: 11, color: 'var(--dsw-alias-label-secondary)' } },
                  h('span', { style: { color: statusTone(run.status) } }, run.status || '—'),
                  h('span', null, run.stage || '—'),
                  run.gate ? h('span', { style: { color: 'var(--dsw-alias-state-warn-primary)' } }, run.gate) : null)))),
          h('main', { style: paneStyle },
            !selected ? h('p', { style: { fontSize: 13, color: 'var(--dsw-alias-label-secondary)' } }, t('selectRun')) :
              !detail ? h('p', { style: { fontSize: 13, color: 'var(--dsw-alias-label-secondary)' } }, t('loading')) :
                detail.error ? h('p', { style: { fontSize: 13, color: 'var(--dsw-alias-state-error-primary)' } }, detail.error) :
                  h('div', null,
                    h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center' } },
                      h('h3', { style: { margin: 0, fontSize: 18, fontWeight: 650 } }, selectedRun ? selectedRun.id : selected),
                      h(Chip, { label: t('status'), value: state && state.status, color: statusTone(state && state.status) }),
                      h(Chip, { label: t('stage'), value: state && state.stage }),
                      h(Chip, { label: t('gate'), value: state && state.gate }),
                      h(Chip, { label: t('track'), value: state && state.problem_track }),
                      h(Chip, { label: t('profile'), value: state && state.profile })),
                    state ? h('div', { style: { marginTop: 10, fontSize: 13, color: 'var(--dsw-alias-label-secondary)' } },
                      `${t('next')}: ${state.next_action || '—'}`,
                      state.updated_at ? ` · ${t('updated')}: ${state.updated_at}` : '') : null,

                    gateOptions.length ? h(Section, { title: `${t('gateAction')} · ${gatePacket.gate || ''}` },
                      h('div', { style: { display: 'flex', flexDirection: 'column', gap: 8 } },
                        h('div', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } }, t('gateHint')),
                        h('textarea', {
                          value: gateReason,
                          onChange: (event) => setGateReason(event.target.value),
                          placeholder: t('gateReason'),
                          rows: 2,
                          style: {
                            width: '100%', boxSizing: 'border-box', resize: 'vertical',
                            padding: '8px 10px', borderRadius: 8, font: 'inherit', fontSize: 13,
                            color: 'var(--dsw-alias-label-primary)',
                            background: 'var(--dsw-alias-bg-layer-2)',
                            border: '1px solid var(--dsw-alias-border-l2)',
                          },
                        }),
                        needsScope ? h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center' } },
                          h('label', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } },
                            `${t('gateScope')} `,
                            h('select', {
                              value: gateScope,
                              onChange: (event) => setGateScope(event.target.value),
                              style: { padding: '4px 6px', borderRadius: 6, font: 'inherit', background: 'var(--dsw-alias-bg-layer-2)', color: 'inherit', border: '1px solid var(--dsw-alias-border-l1)' },
                            },
                            h('option', { value: 'local' }, 'local'),
                            h('option', { value: 'root' }, 'root'))),
                          h('label', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } },
                            `${t('gateRootCause')} `,
                            h('select', {
                              value: gateRootCause,
                              onChange: (event) => setGateRootCause(event.target.value),
                              style: { padding: '4px 6px', borderRadius: 6, font: 'inherit', background: 'var(--dsw-alias-bg-layer-2)', color: 'inherit', border: '1px solid var(--dsw-alias-border-l1)' },
                            },
                            ['model_structure', 'method_mismatch', 'numeric_or_code', 'missing_verification', 'assumption', 'unknown']
                              .map((value) => h('option', { key: value, value }, value))))) : null,
                        h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 8 } },
                          gateOptions.map((option) => h('button', {
                            key: option.id,
                            type: 'button',
                            disabled: gateBusy,
                            onClick: () => submitGate(option.id),
                            style: {
                              ...buttonStyle,
                              padding: '7px 12px', borderRadius: 8, fontSize: 12,
                              border: '1px solid var(--dsw-alias-border-l2)',
                              background: option.id === 'approve' || option.id === 'proceed' || option.id === 'deliver'
                                ? 'var(--dsw-alias-brand-primary)'
                                : 'var(--dsw-alias-bg-layer-2)',
                              color: option.id === 'approve' || option.id === 'proceed' || option.id === 'deliver'
                                ? 'var(--dsw-alias-bg-base)'
                                : 'var(--dsw-alias-label-primary)',
                              opacity: gateBusy ? 0.6 : 1,
                            },
                          }, option.id))),
                        gateMessage ? h('div', {
                          style: {
                            fontSize: 12,
                            color: gateMessage.type === 'success'
                              ? 'var(--dsw-alias-state-success-primary)'
                              : 'var(--dsw-alias-state-error-primary)',
                          },
                        }, gateMessage.text) : null)) : null,

                    h(Section, { title: t('checks') },
                      checks ? h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 8, fontSize: 12 } },
                        h(Chip, { label: checks.stage || t('stage'), value: checks.ok ? 'PASS' : 'FAIL', color: checks.ok ? 'var(--dsw-alias-state-success-primary)' : 'var(--dsw-alias-state-error-primary)' }),
                        h(Chip, { label: t('errors'), value: checks.error_count ?? 0, color: checks.error_count ? 'var(--dsw-alias-state-error-primary)' : 'var(--dsw-alias-state-success-primary)' }),
                        h(Chip, { label: t('warns'), value: checks.warn_count ?? 0, color: checks.warn_count ? 'var(--dsw-alias-state-warn-primary)' : 'var(--dsw-alias-label-secondary)' })) :
                        h('span', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } }, t('empty'))),

                    state && state.rework && state.rework.active ? h(Section, { title: t('rework') },
                      h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 8 } },
                        h(Chip, { label: 'mode', value: state.rework.mode }),
                        h(Chip, { label: 'return', value: state.rework.return_to }),
                        h(Chip, { label: 'work', value: state.rework.work_stage }))) : null,

                    review || method ? h(Section, { title: `${t('review')} / ${t('method')}` },
                      h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 8 } },
                        review ? h(Chip, { label: t('verdict'), value: review.verdict || '—', color: statusTone(review.verdict) }) : null,
                        review && review.high_severity_count !== null ? h(Chip, { label: t('high'), value: review.high_severity_count, color: review.high_severity_count ? 'var(--dsw-alias-state-error-primary)' : 'var(--dsw-alias-state-success-primary)' }) : null,
                        review && review.total_score !== null ? h(Chip, { label: t('score'), value: review.total_score }) : null,
                        method ? h(Chip, { label: t('verdict'), value: method.verdict || '—', color: statusTone(method.verdict) }) : null,
                        method && method.recommend ? h(Chip, { label: t('recommend'), value: method.recommend.choice || method.recommend, color: statusTone(method.recommend.choice) }) : null)) : null,

                    h(Section, { title: t('artifacts') },
                      h('div', { style: { display: 'flex', flexWrap: 'wrap', gap: 10 } },
                        files.map((file) => file.exists ? h('a', {
                          key: file.path,
                          href: fileUrl(selected, file.path),
                          target: '_blank', rel: 'noreferrer',
                          style: {
                            display: 'inline-flex', alignItems: 'center', gap: 6,
                            padding: '6px 10px', borderRadius: 8, fontSize: 12,
                            color: 'var(--dsw-alias-brand-primary)',
                            border: '1px solid var(--dsw-alias-border-l1)',
                            background: 'var(--dsw-alias-bg-layer-2)', textDecoration: 'none',
                          },
                        }, `${file.label} ↗`) : h('span', { key: file.path, style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } }, `${file.label}: —`)))),

                    h(Section, { title: t('figures') },
                      figures.length === 0 ? h('span', { style: { fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } }, t('noFigures')) :
                        h('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 10 } },
                          figures.map((figure) => h('div', {
                            key: figure.path,
                            style: { display: 'flex', flexDirection: 'column', gap: 6 },
                          },
                          h('a', {
                            href: fileUrl(selected, figure.path),
                            target: '_blank', rel: 'noreferrer',
                            style: { display: 'block', textDecoration: 'none' },
                          },
                          h('img', {
                            src: fileUrl(selected, figure.path),
                            alt: figure.name,
                            loading: 'lazy',
                            style: {
                              width: '100%', maxHeight: 180, objectFit: 'contain',
                              borderRadius: 8, border: '1px solid var(--dsw-alias-border-l1)',
                              background: 'var(--dsw-alias-bg-layer-2)',
                            },
                          }),
                          h('div', { style: { marginTop: 4, fontSize: 11, color: 'var(--dsw-alias-label-secondary)', wordBreak: 'break-all' } }, figure.name)),
                          h('button', {
                            type: 'button',
                            onClick: () => setFeedbackFigure(figure),
                            style: {
                              ...buttonStyle, padding: '5px 8px', borderRadius: 6, fontSize: 11,
                              border: '1px solid var(--dsw-alias-border-l1)',
                              background: 'var(--dsw-alias-bg-layer-2)',
                              color: 'var(--dsw-alias-label-primary)',
                            },
                          }, t('feedbackSelect')),
                          h('button', {
                            type: 'button',
                            onClick: () => setOverlayFigure(figure),
                            style: {
                              ...buttonStyle, padding: '5px 8px', borderRadius: 6, fontSize: 11,
                              border: '1px solid var(--dsw-alias-border-l1)',
                              background: 'var(--dsw-alias-bg-layer-2)',
                              color: 'var(--dsw-alias-label-primary)',
                            },
                          }, t('overlayEdit'))))),

                    detail.gate_packet ? h(Section, { title: t('gatePacket') },
                      h('details', null,
                        h('summary', { style: { cursor: 'pointer', fontSize: 12, color: 'var(--dsw-alias-label-secondary)' } }, `${t('open')} JSON`),
                        h('pre', {
                          style: {
                            whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 11,
                            lineHeight: 1.5, maxHeight: 320, overflow: 'auto',
                            padding: 10, borderRadius: 8, margin: '8px 0 0',
                            background: 'var(--dsw-alias-bg-layer-2)',
                            border: '1px solid var(--dsw-alias-border-l1)',
                          },
                        }, JSON.stringify(detail.gate_packet, null, 2)))) : null,

                    detail.decisions && detail.decisions.length ? h(Section, { title: t('decisions') },
                      h('pre', {
                        style: {
                          whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 11,
                          lineHeight: 1.5, maxHeight: 220, overflow: 'auto',
                          padding: 10, borderRadius: 8, margin: 0,
                          background: 'var(--dsw-alias-bg-layer-2)',
                          border: '1px solid var(--dsw-alias-border-l1)',
                        },
                      }, JSON.stringify(detail.decisions, null, 2))) : null))),
        feedbackFigure ? h(FeedbackModal, {
          run: selected,
          figure: feedbackFigure,
          t,
          onClose: () => setFeedbackFigure(null),
          onSent: () => {
            setFeedbackFigure(null)
            setRefreshToken((value) => value + 1)
          },
        }) : null,
        overlayFigure ? h(OverlayEditor, {
          run: selected,
          figure: overlayFigure,
          t,
          onClose: () => setOverlayFigure(null),
        }) : null
      ))
    }

    return {
      inject: ['slots', 'locale'],
      apply(ctx) {
        const disposers = []
        try {
          disposers.push(ctx.locale.register('pipeline-console', 'en', en))
          disposers.push(ctx.locale.register('pipeline-console', 'zh', zh))
        } catch {
          // A re-activation may race the previous disposal; keep the last valid dictionary.
        }
        let t
        try { t = ctx.locale.bind('pipeline-console') } catch { t = (key) => key }

        disposers.push(ctx.slots.inject('sidebar.panellist', () => ctx.slots.register({
          name: 'sidebar.panellist',
          id: 'pipeline',
          order: 20,
          label: () => t('title'),
        }, PipelineIcon)))

        disposers.push(ctx.slots.inject('main', () => ctx.slots.register({
          name: 'main',
          key: 'pipeline',
        }, (props) => h(PipelinePanel, { ...props, t }))))

        ctx.effect(function* () {
          yield async () => {
            for (const dispose of disposers.splice(0)) dispose()
          }
        }, 'pipeline-console UI')
      },
    }
  },
})
