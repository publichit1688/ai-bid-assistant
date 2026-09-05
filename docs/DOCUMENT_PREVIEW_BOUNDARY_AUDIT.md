# 文档预览异步边界审计

日期：2026-09-05

状态：P6-05已完成；审计、展示层抽离、响应式竞态修复及隔离浏览器视觉回归均通过。未调用WPS、OCR或DeepSeek。

## 当前真实链路

1. PDF文件通过带鉴权的Axios请求读取Blob，前端创建对象URL并交给 `react-pdf`。
2. DOC/DOCX先请求 `/api/files/{id}/preview`。正常路径由Microsoft Word或WPS转换成真实分页PDF，再复用同一Blob和 `react-pdf` 链路。
3. 后端无法返回渲染PDF时才使用 `pages` 文本数组兼容预览；这不是当前主要Word预览路径。
4. 风险点击先应用Word的 `risk_page_map`，将目标页限制在真实页数内，再切页并对PDF文字层追加等级高亮。
5. 扫描页风险框使用0到1归一化坐标，按当前页和风险等级叠加在PDF页面容器上。

## 当前耦合边界

| 职责 | 当前所有者 | 拆分时必须保持 |
| --- | --- | --- |
| PDF运行时与worker | `App.jsx` 顶层 | worker继续使用同源 `/pdf.worker.min.mjs` |
| 受保护文件读取 | `loadProtectedPdf` | Axios鉴权、Blob响应、旧URL回收、卸载回收 |
| Word预览协调 | `loadDocumentPreview` | rendered PDF优先、renderer元数据、`risk_page_map`、文本回退 |
| 响应式尺寸 | `pdfContainerRef`/`ResizeObserver` | 容器实宽、700px上限、卸载断开观察器 |
| 页面渲染 | `Document`/`Page` | 文字层、注释层、页数回写、当前页、翻页禁用 |
| 风险定位 | 风险卡片回调与 `highlightKeyword` | 映射页优先、页码钳制、渲染后文字层高亮 |
| OCR叠框 | 预览JSX与 `pdf-highlight.css` | 仅当前风险页、归一化四坐标、三种等级样式 |

## 新增机器契约

`backend/tests/test_frontend_preview_boundary.py` 固定以下六组行为：

- `react-pdf` worker和受保护Blob生命周期；
- `ResizeObserver`驱动、最大700px的响应式宽度；
- `Document`/`Page`文字层、注释层、页码和翻页边界；
- Word渲染PDF优先与文本兼容回退分支；
- Word风险页映射、页码钳制及PDF文字层高亮；
- OCR框按当前页、归一化坐标和风险等级渲染。

这些测试是拆分保护网，不替代浏览器视觉回归。

## 推荐最小拆分顺序

1. 第二小批仅提取 `DocumentPreview` 展示组件；状态、Blob请求、对象URL生命周期、Word接口协调和风险点击继续留在 `App`。
2. 组件通过明确props接收URL、页码、页数、宽度、错误、来源格式、渲染器、文本兼容页、当前风险及翻页回调。
3. 先保持文字层和注释层CSS为入口静态样式，避免首次拆分同时改变PDF.js样式加载时序。
4. 生产构建必须生成独立预览chunk，并确认非分析页面入口不再静态导入 `react-pdf`。
5. 第三小批使用隔离合成PDF和预生成Word预览PDF，完成PDF/Word切换、翻页、宽度、风险跳页和控制台回归；需要OCR框时使用合成坐标，不连接百度OCR。

## 本阶段禁止项

- 不同时迁移Blob请求、对象URL回收和展示组件。
- 不改变Word主引擎/WPS回退顺序或后端 `risk_page_map`。
- 不删除文本兼容预览分支。
- 不关闭文字层或注释层来换取包体积。
- 不改变OCR坐标单位、叠层定位或风险等级颜色。
- 不以提高Vite警告阈值、同步vendor分块或测试通过替代浏览器回归。

## P6-05第二小批结果

- `DocumentPreview` 已移入 `frontend/src/components/DocumentPreview.jsx`，内部负责 `react-pdf` worker、PDF/兼容文本展示、翻页控件和OCR叠框。
- `App` 通过 `React.lazy`/`Suspense` 按需加载组件；Blob请求和回收、Word接口协调、页码与宽度状态、风险点击及文字高亮调度没有搬迁。
- 主入口由1269.76 kB降至346.23 kB，gzip由393.76 kB降至107.71 kB；预览生成347.44 kB（gzip103.79 kB）异步chunk。
- 构建另生成460.94 kB（gzip150.10 kB）的Card共享chunk；Dashboard/ECharts块仍为1136.66 kB（gzip377.43 kB）。
- 16项聚焦契约、前端lint/build通过；浏览器视觉回归留待第三小批，P6-05尚未完成。

## P6-05第三小批结果

- 隔离夹具扩展为两页PDF和两页预生成Word预览PDF；PDF风险位于第2页并带合成OCR框，Word风险保留原始页1并映射到渲染页2。
- PDF/Word异步加载、上一页/下一页边界、风险跳页、文字层高亮、Word页映射和OCR归一化叠框均通过浏览器验证。
- 首轮实测发现495px容器中的PDF画布仍为700px：原因是入口的宽度副作用先于懒加载组件挂载执行。`ResizeObserver`、容器ref和宽度状态已移入 `DocumentPreview`，复测画布与容器同为495px。
- 快速从PDF切换Word时观察到一次react-pdf文字层取消告警；最终Word第2页及中风险高亮正常。依赖在业务错误回调前自行记录取消信息，本批未修改依赖或关闭文字层。
- 完整后端177 passed、1 skipped，前端lint/build通过；最新预览chunk为347.68 kB（gzip103.88 kB）。P6-05完成。
