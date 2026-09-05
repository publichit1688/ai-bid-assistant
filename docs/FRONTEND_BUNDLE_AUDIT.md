# 前端拆包边界审计

日期：2026-09-04

状态：P6-02至P6-07审计、三阶段拆分、收尾复核和ECharts模块化引入均已完成。不移动 `v1.5.0` 标签。

## 当前基线

- Vite 8.1.4生产构建转换3763个模块。
- 当前主JavaScript包约2421.34 kB，gzip约774.99 kB，超过500 kB提醒阈值。
- `frontend/src/App.jsx` 为9733行、约232 kB；工作台、Dashboard、项目对比、文档预览和风险检查器均在同一静态入口。
- `frontend/src/index.css` 为405行、约6.7 kB，不是当前首要拆分对象。
- 当前入口静态导入Ant Design、ECharts封装和react-pdf；因此即使用户只进入其中一个页面，相关模块仍会进入初始依赖图。

依赖目录磁盘体积仅用于识别重依赖方向，不等于最终bundle占比：Ant Design约48.7 MB、ECharts约60.3 MB、pdfjs-dist约36.9 MB、echarts-for-react约0.5 MB、react-pdf约0.55 MB。最终收益必须以每次生产构建产物为准。

## 已确认页面边界

1. `WorkbenchPage`
   - 已是独立顶级组件，通过明确props接收工作台数据和操作回调。
   - 当前仍与 `App` 位于同一文件，无法形成异步chunk。
   - 抽离风险最低，适合作为第一轮结构验证；预计主要减少入口业务代码，不会单独卸载Ant Design。

2. Dashboard与ECharts
   - Dashboard由 `showDashboard` 条件渲染，4处图表均使用 `ReactECharts`。
   - ECharts只服务Dashboard图表，是最有价值的重依赖异步边界。
   - 当前图表配置、统计状态、预警穿透和页面JSX与 `App` 高度交织；必须先抽出纯展示组件和明确props，不能直接用 `manualChunks` 掩盖耦合。

3. 文档预览与react-pdf
   - PDF/Word预览仅在已有预览URL、兼容页或错误时渲染。
   - `Document`、`Page`、文字层/注释层CSS及PDF worker当前均从入口加载。
   - 该边界潜在收益高，但关联响应式宽度、对象URL、翻页、OCR坐标框、风险原文跳转和高亮，是最高回归风险区域之一。

4. 项目对比与风险检查器
   - 对比区域按选择和结果条件渲染，但主要复用入口已有Ant Design组件，没有独占重依赖。
   - 风险检查器与当前文件、预览页码和高亮状态双向联动，不适合作为第一轮拆分对象。

## 推荐实施顺序

### 第一阶段：工作台页面抽离

- 将 `WorkbenchPage` 移入独立页面模块，通过 `React.lazy` 和 `Suspense` 按需加载。
- 保持现有props契约、项目切换、审核、映射、材料编辑和409冲突处理不变。
- 验证：lint、build、工作台契约测试及合成浏览器的入口/空状态/项目切换。

### 第二阶段：Dashboard展示层与ECharts抽离

- 先把Dashboard JSX和图表option输入整理为纯展示props，再让页面模块静态导入 `echarts-for-react`、由入口异步加载页面模块。
- 保持Dashboard周期切换、预警穿透、AI摘要缓存和项目选择行为不变。
- 验证初始chunk不再静态依赖ECharts，并完成Dashboard合成浏览器回归。

### 第三阶段：文档预览模块抽离

- 将react-pdf、图层CSS和PDF展示逻辑放入按需模块；对象URL生命周期和数据请求仍由明确的上层边界管理。
- 必须锁定响应式宽度、PDF/Word页数、翻页、OCR框、风险定位与高亮行为后再实施。
- 验证PDF、DOC/DOCX、扫描PDF三类合成或已授权样本，不以单纯构建通过代替浏览器验证。

### 第四阶段：评估剩余共享依赖

- 对比各阶段构建产物后，再决定是否配置Vite `manualChunks`。
- 不以人为拆出一个仍被入口同步请求的大vendor文件作为完成；目标是减少初始加载，而不仅是消除警告。

## 暂不采用

- 不直接把整个Ant Design强制切成单一vendor chunk：入口与各页面广泛使用其组件，可能只改变文件名和缓存边界，不减少首屏请求。
- 不一次性拆分9733行 `App.jsx`：回归面过大，容易破坏PDF高亮、Dashboard穿透和工作台修订状态。
- 不在没有浏览器回归证据时移动react-pdf初始化或PDF worker路径。
- 不通过提高 `chunkSizeWarningLimit` 隐藏问题。

## 第一实施批建议

P6-03只抽离 `WorkbenchPage` 并建立懒加载边界，不同时修改Dashboard、ECharts或文档预览。若构建未产生独立工作台chunk，或工作台合成回归失败，则先修复或回退该批，不进入后续拆分。

## P6-03第一小批结果

- `WorkbenchPage` 已移入 `frontend/src/pages/WorkbenchPage.jsx`，主入口通过 `React.lazy`/`Suspense` 加载。
- 生产构建生成独立工作台chunk 9.25 kB（gzip 3.20 kB）。
- 主包由2421.34 kB降至2412.47 kB，gzip由774.99 kB降至773.02 kB。
- lint、build和props边界契约通过。
- 隔离合成浏览器已验证异步入口、空状态、项目切换、AI确认取消及章节/映射/材料弹窗，控制台0错误0警告。P6-03完成。

## P6-04第一小批结果

- 新增纯展示 `DashboardChart`，由其独占导入 `echarts-for-react`；主入口通过 `React.lazy`/`Suspense` 渲染4处图表。
- 图表option、Dashboard周期状态、预警穿透和AI缓存数据流没有搬迁，文档预览与风险检查器未修改。
- 主入口由2412.47 kB降至1269.76 kB，gzip由773.02 kB降至393.76 kB；ECharts形成1136.65 kB（gzip 377.43 kB）异步chunk。
- Dashboard是默认页面，因此该异步块仍会在默认页面渲染时请求；本批成果是解除主入口同步依赖和建立后续页面边界，不宣称默认首屏总下载量已经下降。
- lint、build及5项聚焦契约测试通过；周期切换与预警穿透的隔离浏览器回归留待第二小批。

## P6-04第二小批结果

- 隔离浏览器确认4个ECharts实例正常创建，7天切换30天后摘要、周期对比和趋势标题同步更新。
- 重点关注项目可进入PDF分析页，风险检查器自动展开并显示合成高风险、扣分和第1页定位；控制台0错误0警告。
- 首轮回归发现Dashboard聚合块意外位于项目循环之外，导致多项目时只统计最后一条；已修复缩进并新增双项目契约测试，项目中心与Dashboard恢复一致。
- 完整后端171 passed、1 skipped；前端lint/build通过。P6-04完成。

## P6-05第一小批结果

- 文档预览现状、职责边界、6组机器契约、推荐拆分顺序和禁止项已独立记录在 `docs/DOCUMENT_PREVIEW_BOUNDARY_AUDIT.md`。
- 聚焦回归16 passed，前端lint/build通过；本批未修改预览运行代码，构建产物保持P6-04基线。
- 下一批只提取纯展示组件；Blob读取与回收、Word协调和风险点击仍由 `App` 管理。

## P6-05第二小批结果

- `DocumentPreview` 已形成独立懒加载边界，主入口不再静态导入 `react-pdf`；文字层和注释层CSS暂时保留入口静态导入，避免同时改变样式时序。
- 主入口降至346.23 kB（gzip107.71 kB），预览chunk为347.44 kB（gzip103.79 kB），Card共享chunk为460.94 kB（gzip150.10 kB）。
- Blob生命周期、Word协调、风险页映射、页码/宽度状态和风险点击仍归 `App`；16项聚焦测试及lint/build通过。
- 仍需隔离浏览器确认PDF/Word渲染、响应式宽度、翻页、风险高亮和OCR叠框，不能仅凭构建产物判定P6-05完成。

## P6-05第三小批结果

- 两页PDF和两页Word渲染PDF的异步加载、翻页、风险跳页、文字高亮、Word页映射和合成OCR框已完成隔离浏览器验证。
- 浏览器暴露懒加载后的响应式竞态：宽度观察器先于组件挂载退出。将该展示职责移入 `DocumentPreview` 后，495px容器与画布宽度一致。
- 最新构建：主入口345.92 kB（gzip107.59 kB）、文档预览347.68 kB（gzip103.88 kB）、Card共享块460.94 kB（gzip150.10 kB）、Dashboard/ECharts块1136.66 kB（gzip377.43 kB）。
- P6-05完成；P6-06只审计实际加载边界和剩余大块收益，不以继续拆分为预设结论。

## P6-06拆包收尾审计

生产构建使用 `vite build --manifest`，入口的 `dynamicImports` 明确包含：

- `src/pages/WorkbenchPage.jsx`
- `src/components/DashboardChart.jsx`
- `src/components/DocumentPreview.jsx`

### 实际加载成本

| 场景 | 新增JS（未压缩） | 新增gzip | 结论 |
| --- | ---: | ---: | --- |
| 应用静态入口及递归共享依赖 | 926.12 kB | 296.18 kB | 所有页面基础成本 |
| 默认Dashboard图表 | 1136.66 kB | 377.43 kB | 默认页面立即渲染，仍属于首次进入成本 |
| 智能编标工作台 | 9.32 kB | 3.23 kB | 共享依赖已在入口加载，按需收益明确 |
| PDF/Word文档预览 | 约347.78 kB | 约103.99 kB | 仅打开文档后加载，含0.10 kB兼容动态块 |

因此正常首次打开Dashboard的JS合计约2062.78 kB（gzip673.61 kB，不含CSS）。Dashboard图表虽已建立独立边界，但因为Dashboard是默认页面，它改善的是依赖边界和加载调度，不等于减少正常首屏总下载量。

### 剩余大块来源

`DashboardChart.jsx` 当前导入 `echarts-for-react` 默认入口；该入口明确执行 `import * as echarts from 'echarts'`。现有四张图实际使用：

- `pie`、`line`、`bar` 三类series；
- `tooltip`、`legend`、`grid` 组件；
- 类目/数值坐标轴；
- Canvas渲染。

这说明1136.66 kB块的首选优化方向是使用 `echarts/core` 与 `echarts-for-react` core入口注册实际模块，而不是继续拆Dashboard展示代码。

### 决策

- 不再继续拆分工作台或文档预览内部子组件，增量收益不足以覆盖状态/高亮回归风险。
- 不单独懒加载整个Dashboard页面：它仍是默认入口，额外边界不会降低正常首次访问下载量。
- 不调整 `chunkSizeWarningLimit`，警告继续作为可量化门禁。
- 不对Ant Design使用非公开深层导入；Card和typography共享块已属于入口公共依赖，稳定性优先。
- P6-07只做ECharts模块化引入，必须保持四处option、周期切换、响应式布局和预警穿透，并以构建体积与隔离浏览器双重验收。

## P6-07 ECharts模块化结果

- `DashboardChart.jsx` 改用 `echarts-for-react/esm/core` 和 `echarts/core`，只注册Bar、Line、Pie、Grid、Legend、Tooltip、LabelLayout和CanvasRenderer。
- 初版使用CommonJS `lib/core`，生产构建虽通过，但Vite浏览器运行时把模块对象当作React组件并导致空白页；回归发现后切换ESM core，最终浏览器控制台0错误0警告。
- 图表块从1136.66 kB（gzip377.43 kB）降至585.56 kB（gzip198.59 kB），未压缩减少48.5%，gzip减少47.4%。
- 默认Dashboard首次JS从约2062.78 kB（gzip673.61 kB）降至约1511.68 kB（gzip494.77 kB）。
- 浏览器确认4个图表实例与Canvas正常；最近7天切换30天后周期比较、项目趋势和风险趋势文案同步更新，图表实例数量保持4。
- 1280px下四个Canvas宽度为495/495/507/507px，页面宽度与视口同为1280px，没有横向溢出。
- 重点关注项目继续穿透到两页PDF分析和1项风险，Dashboard图表离开页面后正常卸载。
- 仍保留大于500 kB的构建提醒；不提高阈值。继续删除已注册模块会直接影响现有图表，P6阶段不再进行无证据的微拆分。
