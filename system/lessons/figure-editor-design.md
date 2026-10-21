# 图编辑/反馈：设计边界与阶段

## 用户想要什么

写论文时对图不满意，可以：

1. 双击选中重叠部分并拖动；选中的可能是一个词条，也可能是整张图；
2. 删除/修改选中词条的内容；
3. 在空白处拉矩形，自己填内容；
4. 也可以点选后与 agent 交互，让 agent 重画。

目标像 Word 一样“所见即所得”。

## 为什么不能直接对 PNG 硬做

论文图现在是 **PDF/PNG 渲染结果**，不是可编辑对象图：

- matplotlib 图：文字、线、柱是绘制指令，PNG 里只剩像素；
- TikZ 图：PDF 里是绘制指令，不是“文本框对象”；
- 直接拖像素只能移动整块图像，不能移动“一个词条”；
- 用 OCR 猜文本框再覆盖，字体/基线/中文渲染不可靠，容易产生“看起来能改、实际是假编辑”。

所以要把“编辑”分成三层，逐层做。

## 分层方案

### Phase 3b（已完成）：区域反馈给 agent

- 用户在图上拖一个矩形，写“这里重叠/这个标签应该移到右上/这个单位和图注不一致”；
- Host 写入 `<run>/decision_logs/figure_feedback.json`：
  ```json
  {
    "id": "FB-...",
    "figure": "result_bundle/figures/fig06_q3_assembly_flow.png",
    "bbox": { "x": 0.1, "y": 0.2, "w": 0.3, "h": 0.12 },
    "comment": "说明框压住零配件8，请移到图下方",
    "status": "pending"
  }
  ```
- Figures agent 读到后改 **源代码**（TikZ/matplotlib）并重生成图；
- 这是最稳的“与 agent 交互”路径，不伪造编辑能力。

### Phase 3c-1（已完成，`pipeline-console-3c`）：overlay 文本框编辑器

- 在 PNG/PDF 预览上叠一层“注释对象”：
  - 双击选中已有 **overlay 文本框**；
  - 拖动、删除、改内容、改字号/颜色；
  - 空白处拉矩形 → 新建文本框；
  - 保存 `figure_annotations.json`；
  - 导出合成 PNG/PDF（原图不动，注释层叠加）。
- 适合：补标签、加 callout、遮挡错位文字、在空白处加说明。
- 不适合：真正移动“原图里已有的文字”（原图是像素/绘制指令，overlay 只能盖住，不能移走）。

数据模型：
```json
{
  "figure": "result_bundle/figures/fig06_q3_assembly_flow.png",
  "version": 1,
  "elements": [
    {
      "id": "el-1",
      "type": "text",
      "x": 0.62, "y": 0.78,
      "w": 0.3, "h": 0.08,
      "text": "成品不检测，不合格拆解",
      "fontSize": 10,
      "color": "#222222",
      "align": "left"
    }
  ]
}
```

### Phase 3c-2（可选，风险高）：PDF 文本对象编辑

- 用 PyMuPDF 抽取 PDF 文本 span（bbox/font/size/color）；
- 预览时把每个 span 变成可选对象；
- 移动/删除时：先 redact 原位置，再用同字体插入新文本；
- 难点：中文字体嵌入、基线、旋转、公式、TikZ 路径；容易“改一处崩一片”。
- 只建议对简单文字图做，且必须保留原始 PDF 备份和 diff。

### Phase 3c-3（长期）：结构化图对象

- 图不再由“一次 matplotlib 脚本”直接输出，而是先生成 **figure spec**（元素树：标题/轴/线/标注/文本框）；
- 用户编辑 spec，agent 重新渲染；
- 这是最像 Word 的路径，但需要改 figure-studio 的生成管线，工作量大。

## 交互设计（Phase 3c-1）

- 双击：选中最近元素；拖动：移动；Delete：删除；双击文字：编辑内容；
- 空白处拖矩形：新建文本框；
- 工具栏：撤销/重做、保存、导出 PNG/PDF、发送给 Figures agent；
- 所有修改先写 `figure_annotations.json`，不直接改 `result_bundle/figures/*.pdf`；
- 导出时生成 `figXX.annotated.png` / `.pdf`，论文由 writer 引用 annotated 版本；
- 保留原图与注释 JSON，可回溯。

## 建议顺序

1. **已完成**：3b 的区域反馈解决“重叠/错位”最高频问题；
2. **已完成**：3c-1 overlay 文本框，满足“空白处加字、遮挡、补标签”；
3. **再评估**：是否值得做 3c-2 直接改 PDF 文本；
4. **长期**：3c-3 结构化图对象。

## 3c-1 已实现细节

- Bundle：`plugin/pipeline-console-3c`（`@local/pipeline-console-3c`，0.3.0）；旧 3b 停用。
- 图卡片按钮：**Select area**（3b 区域反馈）和 **Edit image**（3c overlay 编辑器）。
- overlay 编辑器：新增文字、选中、拖动、删除；改文本、字号、文字颜色、背景；保存；导出。
- 数据：`<run>/decision_logs/figure_annotations.json`：
  ```json
  {"run_id":"...","figures":{"result_bundle/figures/figXX.png":{"elements":[{"id":"el-1","text":"...","x":0.1,"y":0.2,"w":0.3,"h":0.08,"fontSize":20,"color":"#222222","background":"#ffffff"}],"updated_at":"..."}}}
  ```
- Host API：`GET|POST /pipeline-console/annotations`、`POST /pipeline-console/annotations/export`。
- 导出：`tools/annotate_figure.py` 用 Pillow 叠加文字，输出 `figXX.annotated.png` / `.pdf`；原图不变。
- 已验证：GET/POST/export 通过；annotated PNG/PDF 生成。**拖拽/字体预览的视觉体验仍需浏览器确认**。

不要先做“像素级拖字”——那会得到一个看起来像 Word、实际导出后字体/位置全变的编辑器。
