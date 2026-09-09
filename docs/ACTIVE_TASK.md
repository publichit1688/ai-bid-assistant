# 当前活动任务

更新时间：2026-09-09

## 当前批次

P6-20：`1.5.2-rc.1` 签署记录本地文档提交。

状态：已完成。项目负责人授权的签署记录及状态同步已建立为独立本地文档提交，提交父级为最终候选 `e4cf9dd10bad4ef257fd92206dcdce582b2edc74`。本批未创建标签、推送、提升正式版本或部署。

## 已完成

- 新增可重复的纯合成隔离夹具脚本，创建临时SQLite、PDF、Word占位源文件及预生成Word预览PDF，不调用WPS或DeepSeek。
- 共享模式启动检查通过；根接口和存活探针匿名200，项目列表无凭据/错误凭据401、正确凭据200且响应携带请求ID。
- 授权Dashboard、PDF原件、Word预览接口、Word预览PDF和风险报告均返回200；PDF原件匿名访问返回401。
- 共享模式下文档入口匿名返回401、授权后返回404，确认FastAPI文档已关闭。
- 日志审计发现并修复Uvicorn默认访问日志输出原始文件名：生产入口关闭Uvicorn访问日志，Nginx模板关闭默认访问日志，保留应用安全归一化JSON日志。
- 修复后日志仅显示 `/uploads/<file>`，不包含测试密钥和原始文件名；前后端隔离服务均已正常停止。
- 浏览器确认无凭据时项目与Dashboard返回错误并自动打开凭据弹窗；刷新后凭据清除并再次进入未授权状态。
- 首次浏览器实测发现保存正确凭据后不会自动重试旧请求；已修复为立即重新加载项目列表与Dashboard。
- 修复后项目列表恢复2个隔离项目，Dashboard恢复统计，PDF和Word Blob均渲染1页且显示合成正文。
- 导出报告按钮触发带凭据的 `POST /api/report` 并返回200；浏览器扩展未捕获程序化Blob下载事件，因此以请求证据和既有报告内容测试共同验收。
- 浏览器控制台未出现测试凭据或Axios业务响应；记录既有Ant Design List/Alert弃用提示。
- P3-05备份第一小批代码已完成验证：SQLite一致性快照、上传/报告复制、SHA-256清单、不覆盖和符号链接拒绝。
- P3-05恢复第二小批代码已完成验证：拒绝已有目标、路径穿越、清单外文件、符号链接、哈希篡改、复制期变化及损坏SQLite，并通过同级临时目录原子落位。
- 新增高置信度秘密扫描脚本，只扫描源码、测试、部署模板和文档，不读取本地 `.env`、数据库、上传件或报告；命中时只输出文件、行号和规则，不输出疑似凭据内容。
- Python审计首次发现当前虚拟环境4个包共9条记录；已升级到明确修复版本并复扫为0。前端116个生产依赖审计为0个已知漏洞。
- 建立统一候选版本 `1.0.0-rc.1`，根版本文件、FastAPI元数据、前端包和锁文件由自动测试锁定一致。
- 新增一键发布检查入口，实际串联Python编译、完整pytest、秘密扫描、Python依赖审计、前端lint/build及npm生产依赖审计。
- 新增V1发布清单、回滚门禁和发布说明草案；明确候选版本不等于正式发布，未经用户确认不创建 `v1.0.0` 标签。
- 使用两条纯合成项目完成隔离生产和浏览器冻结回归；根/探针、401/200、文档关闭、PDF/Word预览、Dashboard周期、项目对比与报告接口通过。
- 修复凭据启用后项目中心可能不重试首次401的问题：由凭据状态变化统一重试项目与Dashboard，避免事件时序漏请求。
- AI摘要与AI对比均被非空测试Key加不可达本机Base URL隔离并返回安全502，未连接真实DeepSeek；非AI结果保持可用。
- 确认Git历史只有2个提交和4个跟踪文件；旧入口仅1个路由，现入口装配7组路由且所有启动链路指向 `app.main:app`，旧入口删除应进入候选基线而非恢复。
- 127个未跟踪候选按根目录、后端、前端、部署和文档完成分类；`.env`、数据库、上传、报告、真实样本、依赖和构建目录均经忽略规则核验，不在候选列表。
- 发现5个未引用的Vite模板文件及页面标题/模板favicon遗留；已登记为提交前清理项，没有在审计批次擅自删除。
- 形成单一原子候选基线提交建议和回滚边界，详见 `docs/V1_GIT_BASELINE_AUDIT.md`；本批未暂存、提交、推送或打标签。
- HTML语言改为 `zh-CN`，页面标题、描述、主题色和自有SVG favicon统一为AI标书助手品牌。
- Vite模板README改为项目实际启动/验证说明；删除未引用的 `icons.svg`、`hero.png`、`react.svg`、`vite.svg`，PDF worker保持不变。
- 新增前端品牌契约测试，防止模板标题/资源回归并确认PDF worker继续存在。

## 下一批唯一目标

准备腾讯云 `1.5.2-rc.1` 候选门禁的安全交付与只读执行方案。签署已授权云端候选门禁，但候选代码交付路径尚未确认；在此之前不推送、不部署、不改动云端正式 `v1.5.1`。

## 已知限制

- 纯扫描样本1项风险无可靠OCR匹配时不画框，本样本未产生低风险项。
- 表格样本不覆盖多页密集、嵌套或大量跨页表格。
- 当前Word验证使用WPS，不代表Microsoft Word分页完全一致。
- 上传并发和解析超时仍需后续部署安全批次保护。
- Git工作区存在旧入口删除及大量未跟踪成果，发布前必须建立正式版本基线。

## 本批验证

- 腾讯云 COS 已开通，临时桶位于 `ap-chongqing`，访问权限为私有读写、单 AZ，当前文件数为 1；唯一对象为已验证 Git 官方安装包，未开启 CDN、自定义域名、版本控制、日志存储或其他付费附加功能。
- 用户开启 Chrome 本地文件访问权限后，文件选择器成功上传安装包；COS 页面显示“任务已完成（已成功 1 个）”、共 1 个文件，大小 62.32 MB，访问权限继承桶的私有读写策略。
- 项目负责人已明确确认执行 COS 中转的 Git 安装；自动化助手执行 ID `inv-k8e34g0636` 状态为命令成功，开始时间 22:20:17、结束时间 22:20:50、耗时 33 秒、ExitCode 0。
- 输出依次包含 `DOWNLOAD_GIT_FROM_COS`、`GIT_SHA256_OK`、`GIT_SIGNATURE_OK`、`git version 2.55.0.windows.5` 和 `GIT_INSTALL_OK`，证明下载、哈希、签名、安装和版本检查完整通过。
- 安装参数包含 `/NORESTART`，本批未主动重启。
- 项目负责人另行确认删除临时 COS 对象和空桶；对象删除后文件列表显示“共 0 个文件 / 暂无数据”，空桶删除并刷新后存储桶列表显示“共 0 项”，原桶名称不再出现。
- 直接打开已删除 `.exe` 对象地址被浏览器客户端下载策略拦截，未作为 404 证据；清理完成以腾讯云 COS 控制台的资源列表为权威证据。
- 云端只读预检首次执行 `inv-m8e3g9ggm6` 因 GitHub 连接重置以 ExitCode 1 结束；失败前确认 Git 2.55.0 可用、应用目录和数据目录均不存在、C 盘可用 76.68 GB，且未创建任何目录。
- 修复命令仅增加 OpenSSL、HTTP/1.1 与 4 次有限重试；复跑 `inv-k8e3mtg1f9` 用时 3 秒、ExitCode 0，第一轮远程读取即成功并输出 `DEPLOY_PREFLIGHT_OK`。
- 远程 `v1.5.1` annotated 标签对象为 `cf3aa454939812714bb377391a960459f90269b3`，解引用提交为 `b542d010d2679c0265fcd4cd50cd420fcd39954e`，与正式发布记录一致；远程 `main` 已前进到 `5cca7ad6...`，后续部署只固定标签，不跟随 `main`。
- 固定版本检出执行 `inv-k8e3t3gkdd` 状态为命令成功，开始时间 22:44:23、结束时间 22:44:47、耗时 24 秒、ExitCode 0。
- 输出确认 `CHECKOUT_HEAD b542d010...`、`CHECKOUT_TAG v1.5.1`、`CHECKOUT_VERSION 1.5.1`、`CHECKOUT_WORKTREE_CLEAN`、`DATA_ROOT_NOT_CREATED` 与 `CHECKOUT_V151_OK`；未创建生产数据目录或启动进程。
- Git 的 detached HEAD 提示来自按 annotated 发布标签检出，属于不可漂移的预期部署状态；后续更新必须显式选择版本标签，不在服务器上直接提交。
- 云端依赖命令固定应用 HEAD 为 `b542d010...`，并以 Git 工作树及两份依赖清单相对 HEAD 无差异作为 Windows 兼容的防篡改门禁；原始字节 SHA-256 因 Git CRLF 换行转换已停用。
- 依赖安装首次执行 `inv-k8e4580ep2` 在下载前因 `requirements.txt hash mismatch` 以 ExitCode 1 安全退出；修正后执行 `inv-m8e4ahgquk` 完成后端依赖安装和秘密扫描，云端 pytest 为 177 passed、1 failed、2 warnings。
- 云端唯一失败为 `test_backup_refuses_overwrite_and_symlinks`：符号链接拒绝生效，但目标目录仍存在。本地已将两个文件源的校验前置到目标创建前；聚焦回归 1 passed、1 skipped，完整回归 177 passed、1 skipped、1 warning。
- 后端清单目前是带上下界的兼容版本区间而非完全哈希锁定；前端由 `npm ci` 严格使用锁文件。命令不会创建 `.env` 或 `C:\AI-Bid-Data`，不会启动应用或调用 DeepSeek/OCR。
- 本机官方安装包 `Git-2.55.0.5-64-bit.exe` 大小65,343,712字节，SHA-256为 `D065A4E23C3D9A6B5073D609B5BE0830227EC3CA053C083BA385061DDFAF94C6`；Authenticode状态为Valid，签名证书指纹为 `2A1E97CBF0DFCDA15B0DA0AC9745014F989D4AD0`。
- 腾讯云 Git 单组件命令首次执行 `inv-k8de5mgbc2` 因 `CRYPT_E_REVOCATION_OFFLINE` 退出；加入 `--ssl-no-revoke` 后 `inv-k8de8v0pr2` 因连接重置退出；加入HTTP/1.1和全错误重试后 `inv-k8debe0tii` 已进入官方CDN但约15–20 KB/s，最终按1200秒命令上限标记为超时。三次均未到达哈希、签名或安装阶段。
- 超时后只读预检于2026-09-08 10:53:35以ExitCode 0结束：Git为 `NOT_INSTALLED`，WPS已知路径不存在；随后路径诊断再次确认 `C:\Windows\py.exe` 可定位Python 3.14.6，`C:\Program Files\nodejs\node.exe` 为v24.18.0，`npm.cmd` 为11.16.0。
- 本批未安装 Git/WPS、未重启服务器、未上传应用或用户数据、未创建生产密钥，也未调用 DeepSeek/OCR；仅按授权创建临时 COS 桶并上传已验证的 Git 官方安装包。
- 腾讯云自动化助手首次运行环境命令 `inv-m8cwbw04rf` 在下载 Git for Windows 官方 GitHub 发布包时30分钟超时，安装阶段未开始。
- 分步命令 `inv-m8dd3a009e` 成功下载 Python/Node 官方安装包，两个 Authenticode 签名有效且 Python SHA-256 与官方值一致；Python和Node安装器均返回成功，脚本因预期 Python 路径不存在而以 ExitCode 1结束。
- 安装后只读预检 `inv-m8dd63gqra` 与路径诊断 `inv-m8dd7tggs7` 均 ExitCode 0：`py` 注册 Python 3.14.6，实际解释器为 `C:\Program\python.exe`；Node为 `v24.18.0`，npm为 `11.16.0`。
- 本批未安装Git/WPS、未重启服务器、未创建生产密钥、未调用DeepSeek/OCR，也未上传数据库、标书或报告。

- P6-16从 `backend` 使用既有 `.venv` 运行部署模板、生产启动、运行检查、备份和恢复聚焦回归：17 passed、1 skipped；跳过项仍为当前Windows无符号链接权限，保留1个既有Starlette/httpx弃用提示。
- 前端 `npm run build` 通过，正式版本为 `1.5.1`；Dashboard图表块仍为585.56 kB，保留已审计提醒。
- 秘密扫描和差异格式检查通过；测试只使用隔离临时目录并已清理，未读取真实 `.env`、用户数据库、上传文件或报告。
- 本批没有连接真实服务器、注册Windows/Linux服务、修改Nginx、调用DeepSeek/OCR或执行部署。

- P6-15推送前确认远程 `main=82f3383` 是本地 `main=f30d618` 的历史祖先，远程不存在 `v1.5.1`，满足安全快进和无标签冲突条件。
- Windows Schannel首次在读取GitHub回包时出现 `SEC_E_MESSAGE_ALTERED`；改为单次命令使用OpenSSL后推送成功，没有永久修改Git SSL配置。
- GitHub远程复核：`main=f30d61833cb719b4658ceb28497f31cb0ae0afe6`；`v1.5.1` 标签对象为 `cf3aa454939812714bb377391a960459f90269b3`，解引用到 `b542d010d2679c0265fcd4cd50cd420fcd39954e`，与本地一致。
- 推送范围仅为 `main` 和 `v1.5.1`；未部署，真实配置、数据库、上传文件、报告和回归原件均未进入Git。

- P6-14仅暂存 `CHANGELOG.md`、`TASKS.md`、`docs/ACTIVE_TASK.md`、`docs/PROJECT_STATE.md` 和 `docs/V1_5_1_RELEASE_NOTES.md` 5份标签状态文档。
- 提交前标签 `v1.5.1` 仍解引用到 `b542d01`，版本保持 `1.5.1`；差异格式和秘密扫描通过。
- 本批只创建一个本地文档提交；未移动标签、推送或部署。

- P6-13创建本地annotated标签对象 `cf3aa454...`，标签 `v1.5.1` 解引用后精确指向正式发布提交 `b542d010d2679c0265fcd4cd50cd420fcd39954e`。
- 标签说明为 `AI Bid Assistant v1.5.1`；创建前确认同名标签不存在，创建后HEAD保持不变。
- 本批未推送或部署，未调用外部模型，也未访问或修改用户数据。

- P6-12将根版本、FastAPI版本契约和前端包/锁文件由 `1.5.1-rc.1` 统一提升为正式 `1.5.1`。
- 从仓库根目录复跑统一正式发布门禁：177 passed、1 skipped，秘密扫描、Python依赖审计、前端lint/build通过；最后的npm审计首次因受限网络TLS连接中断，按相同 `npm audit --omit=dev` 在允许联网环境重跑后为0个已知漏洞，正式门禁全部组成项通过。
- 新增 `docs/V1_5_1_RELEASE_NOTES.md`，记录维护范围、保持能力、已知限制和未授权动作边界。
- 本批只创建本地正式发布提交；未创建或移动标签，未推送、部署或调用真实外部模型。

- P6-11仅暂存6份签署与状态文档，候选代码提交 `814c4bf` 保持为父提交；提交前差异格式与秘密扫描通过。
- 本批按授权创建一个独立本地文档提交；未修改 `VERSION` 或前端包版本，未创建标签、推送或部署。

- 项目负责人于2026-09-05明确确认签署 `1.5.1-rc.1` 候选版本验收，最终候选提交为 `814c4bf`。
- 签署范围明确排除标签、推送、正式版本提升和部署；本批未执行这些动作，也未调用DeepSeek或访问用户数据。
- 验收签署单、候选审计、项目状态、任务清单和变更日志已同步；签署记录尚未提交，等待另行授权。

- P6-10签署前确认HEAD为 `814c4bf8be0198d0e48b1d93ee3bb035bfb93700`，父提交为正式 `1.5.0` 提交 `a4295e60...`；候选提交没有标签，`v1.5.0` 仍指向父提交。
- `git show` 和 `git diff-tree` 确认候选仅含22个审计文件，1562行新增、789行删除；提交差异格式检查通过。
- 从 `backend` 使用既有 `.venv` 复跑版本、品牌/懒加载和文档预览边界聚焦回归：12 passed、1个既有Starlette/httpx弃用警告。
- 首次从仓库根目录直接运行聚焦测试因模块搜索路径不符合项目入口而出现12个导入错误；已按 `TESTING.md` 改从 `backend` 运行并全部通过，候选代码无需修改。
- 新增 `docs/V1_5_1_ACCEPTANCE_SIGNOFF.md`，明确候选范围、门禁证据、已知限制、数据/回滚边界和待负责人确认文本。

- P6-09将根版本、FastAPI版本契约和前端包/锁文件统一为 `1.5.1-rc.1`，并按授权复跑统一候选门禁。
- 候选提交仅包含P6维护源码、测试、审计文档和版本同步文件；真实配置、数据库、上传、报告、真实样本、依赖和构建产物继续排除。
- 本批只创建一个本地候选提交；没有创建或移动标签，没有推送或部署。最终提交哈希以Git历史及本次交付报告为准。

- P6-08从仓库根目录运行统一发布门禁：Python编译、完整pytest、秘密扫描、Python依赖审计、前端lint/build及npm生产依赖审计全部通过。
- 完整后端回归177 passed、1 skipped、1个既有Starlette/httpx弃用警告；跳过项仍为当前Windows无符号链接权限。
- Python与前端生产依赖均为0个已知漏洞；秘密扫描通过；前端构建保留585.56 kB图表块提醒，没有提高警告阈值。
- 暂存区为空；审计时11个已跟踪修改、6个未跟踪源码/文档，加上新审计文档后形成18个未来候选文件。
- Git忽略边界确认真实 `.env`、`bid.db`、上传、报告、真实样本、`node_modules` 和 `dist` 被排除；跟踪范围只存在安全模板 `.env.example`。
- `v1.5.0` 为annotated tag：标签对象 `8095a315...` 解引用后仍指向HEAD `a4295e60...`；根/后端/前端版本契约保持 `1.5.0`。
- 原子提交与 `git revert` 回滚建议已记录在 `docs/P6_MAINTENANCE_CANDIDATE_AUDIT.md`；本批未暂存、提交、推送、打标签或部署。

- P6-07将 `DashboardChart` 从 `echarts-for-react` 完整入口改为其ESM core，并通过 `echarts/core` 注册Bar、Line、Pie、Grid、Legend、Tooltip、LabelLayout和CanvasRenderer；四处option及Dashboard状态仍留在 `App`。
- 首次使用CommonJS `lib/core` 时，生产构建通过但Vite开发页出现“Element type is invalid”空白页；浏览器回归捕获后立即改为包内ESM core并重新验证，没有带错进入后续任务。
- 最终Dashboard图表块由1136.66 kB（gzip377.43 kB）降至585.56 kB（gzip198.59 kB），分别减少551.10 kB（48.5%）和178.84 kB（47.4%）。
- 默认Dashboard正常首次JS由约2062.78 kB（gzip673.61 kB）降至约1511.68 kB（gzip494.77 kB）；入口、工作台和文档预览块保持原体积。
- 隔离浏览器确认4个ECharts实例/Canvas正常，1280px页面无横向溢出；切换最近30天后周期比较和两张趋势文案同步更新，4个图表实例仍存在。
- 重点关注项目可穿透到两页PDF分析页并显示1项风险；页面切换后Dashboard图表正常卸载，浏览器控制台0错误0警告。
- 最终前端lint与manifest构建通过；品牌/拆包和核心接口聚焦回归13 passed、1个既有Starlette/httpx弃用警告。隔离AI使用非真实Key与不可达本机地址，未连接真实DeepSeek。

- P6-06使用 `vite build --manifest` 核对真实构建图：入口明确动态引用 `WorkbenchPage`、`DashboardChart` 和 `DocumentPreview`，没有退化为静态导入。
- 首屏静态JS约926.12 kB（gzip296.18 kB）；默认Dashboard立即增加1136.66 kB（gzip377.43 kB）的图表块，正常首次进入合计约2062.78 kB（gzip673.61 kB，不含CSS）。
- 智能编标工作台仅增加9.32 kB（gzip3.23 kB），共享Ant Design块已在入口加载；文档预览只在打开PDF/Word后增加约347.78 kB（gzip103.99 kB，含极小浏览器兼容动态块）。
- 依赖源码确认 `echarts-for-react` 默认入口执行 `import * as echarts from 'echarts'`，当前图表实际只使用pie、line、bar以及tooltip、legend、grid、xAxis、yAxis，完整ECharts入口是剩余大块的明确来源。
- 审计结论：继续拆工作台或预览收益低且增加回归风险；把Dashboard再包一层也不会减少默认首屏下载。下一批只评估ECharts模块化引入，不提高警告阈值、不改Dashboard功能。
- 前端生产manifest构建通过；聚焦静态契约与前端lint在本批收尾门禁中复验。

- P6-05第三小批使用独立SQLite、上传和报告目录，以及两页合成PDF和两页预生成Word预览PDF；未访问用户数据库/上传文件，未调用WPS、百度OCR或DeepSeek。
- PDF异步预览显示2页，上一页/下一页边界正常；风险点击定位第2页，文字层出现高风险高亮，合成OCR框按10%/8%/48%/5%归一化坐标覆盖。
- Word版式预览显示2页及本机办公软件来源；风险原始页为第1页，`risk_page_map`正确跳转渲染第2页并出现中风险文字高亮。
- 首次浏览器测量发现懒加载竞态导致495px容器内画布仍按700px渲染；将 `ResizeObserver` 与宽度状态移入实际挂载的 `DocumentPreview` 后，复测画布宽度等于495px且页面无横向溢出。
- 快速切换文档时 `react-pdf` 记录一条 `AbortException: TextLayer task cancelled`；依赖源码确认这是卸载进行中文字层任务的取消提示，最终Word页码与高亮正常。未修改第三方依赖、未关闭文字层，作为已知非功能性告警保留。
- 完整后端回归177 passed、1 skipped、1个既有Starlette/httpx弃用警告；跳过项仍为当前Windows无符号链接权限。前端lint/build通过。
- 最新构建主入口345.92 kB（gzip107.59 kB），文档预览347.68 kB（gzip103.88 kB），Card共享块460.94 kB（gzip150.10 kB），Dashboard/ECharts块1136.66 kB（gzip377.43 kB）；保留大chunk提醒供P6-06审计。

- P6-05第二小批新增懒加载 `DocumentPreview`，入口仅在存在URL、兼容页或错误时请求预览组件；`react-pdf`和worker初始化已移入组件。
- Blob获取与对象URL回收、Word rendered/text分支、`risk_page_map`、页码/宽度状态、风险点击和文字高亮调度继续留在 `App`，没有扩大拆分范围。
- 前端lint/build通过；主入口由1269.76 kB（gzip393.76 kB）降至346.23 kB（gzip107.71 kB），预览chunk为347.44 kB（gzip103.79 kB），Card共享chunk为460.94 kB（gzip150.10 kB）。
- 预览边界、Word渲染页映射和风险定位聚焦回归16 passed、1个既有Starlette/httpx弃用警告。
- 本批未启动业务服务或浏览器，未调用WPS、百度OCR、DeepSeek，也未访问用户数据库和上传文件。

- P6-05第一小批新增 `test_frontend_preview_boundary.py`，6项契约锁定PDF worker/Blob生命周期、700px响应式上限、文字与注释层、翻页边界、Word rendered/text分支、风险映射和OCR叠框。
- 前端边界、后端Word预览及风险定位聚焦回归16 passed、1个既有Starlette/httpx弃用警告。
- 前端lint/build通过；构建产物保持主入口1269.76 kB、Dashboard/ECharts异步块1136.65 kB、工作台块9.25 kB，仍有大chunk提醒。
- 本批只新增测试和审计文档，未启动浏览器或业务服务，未调用WPS、百度OCR、DeepSeek，也未访问用户数据库和上传文件。

- P6-04第二小批在独立SQLite、上传和报告目录运行：Dashboard创建4个ECharts实例，累计2个项目/1项高风险，7天切换30天后周期文案和统计同步更新。
- 重点关注列表的 `Auth PDF Project` 可穿透到标书分析页，PDF显示第1/1页，风险检查器展开并显示1项合成高风险、20分扣分及第1页定位；浏览器控制台0错误0警告。
- 首轮隔离页面暴露Dashboard只统计最后一条项目：项目中心为1项风险而Dashboard为0。已修复聚合块缩进并新增双项目回归，修复后接口和页面均为1项。
- Python编译通过；完整后端回归171 passed、1 skipped、1个既有Starlette/httpx弃用警告，跳过项仍为当前Windows无符号链接权限。
- 前端lint/build通过；主入口1269.76 kB、Dashboard/ECharts异步块1136.65 kB、工作台块9.25 kB，保留大chunk提醒。
- AI使用非空测试Key并固定到不可达 `127.0.0.1:9`，未连接真实DeepSeek；测试页面及8015/5185服务已关闭，隔离数据待最终安全清理。

- P6-04第一小批前端lint/build通过；主入口由约2412.47 kB（gzip 773.02 kB）降至1269.76 kB（gzip 393.76 kB），ECharts生成1136.65 kB（gzip 377.43 kB）异步chunk，工作台chunk保持9.25 kB。
- Dashboard图表懒加载契约聚焦回归5 passed、1个既有Starlette/httpx弃用警告；锁定入口不再静态导入ECharts、4处option仍由原Dashboard状态生成。
- 本批没有启动业务服务、调用DeepSeek、访问用户数据库或移动 `v1.5.0` 标签；Dashboard交互浏览器回归留待P6-04第二小批。

- P6-03第二小批使用全新合成环境完成浏览器回归：工作台异步入口及未选项目空状态正常；PDF项目显示修订、目录、评分点和操作入口；Word项目形成隔离空工作台。
- AI目录确认提示展示“发送当前文件并消耗额度”，测试点击取消；新增章节、评分点映射和新增材料弹窗均正常打开并取消，没有执行真实业务写入。
- 浏览器控制台0错误0警告；Dashboard初始化AI使用非真实测试Key并固定到不可达 `127.0.0.1:9`，安全返回502，未连接真实DeepSeek。
- 临时浏览器页面、后端8012和前端5182服务均已关闭；合成数据目录清理后复核端口与工作区。

- P6-03第一小批前端lint/build通过；生成独立 `WorkbenchPage` chunk 9.25 kB（gzip 3.20 kB），主包由2421.34 kB降至2412.47 kB（gzip 773.02 kB）。
- 工作台懒加载与props契约聚焦回归4 passed、1个既有Starlette/httpx弃用警告；首次lint发现搬迁后残留的 `ReloadOutlined` 导入，移除后复跑通过。
- 浏览器交互回归留待P6-03第二小批，未以构建通过代替最终页面验收。

- P6-02只读审计确认 `App.jsx` 9733行、约232 kB，生产主包约2421.34 kB、gzip约774.99 kB；入口静态依赖Ant Design、ECharts和react-pdf。
- 拆包顺序与禁止项已写入 `docs/FRONTEND_BUNDLE_AUDIT.md`；本批不改Vite配置或运行代码，使用现有P6-01 lint/build结果作为构建基线。

- P6-01前端 `npm run lint` 和 `npm run build` 通过；项目中心弃用列表已不再进入生产包，构建主包由约2.46 MB降至约2.42 MB，仍保留大包提醒。
- 新增项目中心列表契约测试，锁定不再导入/渲染Ant Design `List`，并保留列表、列表项及空状态语义。

- 正式 `1.5.0` 完整发布门禁通过：Python编译通过；后端167 passed、1 skipped、1个既有弃用警告；秘密扫描通过；Python依赖审计0个已知漏洞；前端lint/build通过；npm生产依赖审计0个已知漏洞。
- 前端构建保留既有约2.46 MB主包拆分提醒；跳过项仍为当前Windows无符号链接权限，均不阻塞正式版本。
- 版本一致性契约确认根版本、FastAPI及前端包/锁文件均为 `1.5.0`；本地正式发布提交和 `v1.5.0` 标签按本批Git结果建立，不推送、不部署。

- 签署记录提交前仅暂存6个指定文档，秘密扫描与暂存差异格式检查通过；候选提交 `33ad2bc` 保持在父提交历史中，未创建标签、推送、提升正式版本或部署。

- 签署内容与候选身份复核：用户确认版本 `1.5.0-rc.1`、最终候选 `33ad2bc` 及“不创建标签、不推送、不提升正式版本”边界；Git HEAD仍为完整哈希 `33ad2bcee8752475caa53feecb2a336c6777cef7`，HEAD无标签。
- 验收记录、项目状态、活动任务、任务清单和变更日志已同步；秘密扫描与差异格式检查通过。

- 候选身份复核：`HEAD` 为 `33ad2bcee8752475caa53feecb2a336c6777cef7`，HEAD无标签，既有 `v1.0.0` 标签仍指向 `c0bfd6304a5c8f92d2708c0042d32744e3dce9dc`；35个候选文件未命中配置、数据库、上传、报告、真实样本、依赖或构建产物边界。
- 版本与工作台边界聚焦回归：4 passed、1个既有Starlette/httpx弃用警告。首次从仓库根目录执行因 `app` 导入路径错误在夹具阶段失败，改为按项目约定从 `backend` 使用现有 `.venv` 后全部通过。
- 秘密扫描与差异格式检查通过；本批未调用DeepSeek，未触碰用户数据库、上传文件及报告。

- 统一候选门禁：后端167 passed、1 skipped、1个既有弃用警告；Python依赖审计0个已知漏洞；前端lint/build通过。
- npm在线安全端点连续两次连接重置；使用本机最新缓存执行 `npm audit --offline --omit=dev --audit-level=low`，结果0个已知漏洞。
- 版本一致性契约通过；秘密扫描通过。候选暂存前再次核对忽略边界和差异格式。

- Python编译通过；完整后端回归167 passed、1 skipped、1个既有弃用警告，跳过项为当前Windows无符号链接权限。
- V1.5迁移聚焦回归5 passed、1个既有弃用警告；覆盖旧数据保留、两版迁移幂等和残缺同名表拒绝。
- 前端 `npm run lint` 和 `npm run build` 通过；保留既有约2.46 MB主包提醒。
- 候选忽略边界确认 `.env`、数据库、上传、报告、真实样本、依赖和构建目录不进入Git；本批未调用DeepSeek或触碰用户数据。

- 纯合成浏览器闭环通过：修订1→6、目录/评分点审核、人工映射、材料新增/阻塞编辑、项目隔离和空状态均符合预期；1024px文档宽度无溢出。
- AI确认提示通过且点击取消；Dashboard初始化AI仅命中不可达 `127.0.0.1:9` 测试地址并安全502，未连接真实DeepSeek。
- 浏览器控制台仅有既有Ant Design `List`弃用提醒；前后端停止后8000/5173端口均关闭。
- 前端 `npm run lint` 和 `npm run build` 通过；工作台最小闭环与材料聚焦回归3 passed，1个既有弃用警告。

- 前端 `npm run lint`：通过，0错误、0警告；`npm run build`：通过，保留既有约2.46 MB主包提醒。
- 响应材料后端聚焦回归：2 passed，1个既有弃用警告；覆盖人工新增、已确认目标约束、四态汇总、修订快照和过期写入保护。
- 本批未启动业务服务或调用DeepSeek，未触碰用户数据库、上传文件及报告。

- 前端 `npm run lint`：通过，0错误、0警告；`npm run build`：通过，保留既有约2.46 MB主包提醒。
- AI目录建议与评分点后端聚焦回归：13 passed，1个既有弃用警告；首次固定pytest临时目录因Windows权限未进入用例，改用唯一 `--basetemp` 后全部通过。
- 本批没有启动业务服务、点击确认入口或调用真实DeepSeek；未触碰用户数据库、上传文件及报告。

- 前端 `npm run lint`：通过，0错误、0警告；`npm run build`：通过，保留既有约2.45 MB主包提醒。
- 映射及最小闭环后端聚焦回归：3 passed，1个既有弃用警告；覆盖同工作台确认对象、重复关系更新、覆盖统计、修订快照和旧修订冲突。

- 前端 `npm run lint`：通过，0错误、0警告；`npm run build`：通过，保留既有约2.45 MB主包提醒。
- 工作台章节接口聚焦回归：9 passed，1个既有弃用警告；覆盖人工新增、标题清理、排序、跨工作台父级和修订冲突。

- 前端 `npm run lint`：通过，0错误、0警告；`npm run build`：通过，保留既有约2.45 MB主包提醒。
- 响应材料接口聚焦回归：2 passed，1个既有弃用警告；覆盖责任人清空、说明和状态更新、修订快照及冲突保护。

- 前端 `npm run lint`：通过，0错误、0警告；`npm run build`：通过，保留既有约2.45 MB主包提醒。
- 目录/评分点审核后端聚焦回归：13 passed，1个既有弃用警告。
- 临时Vite浏览器只读验收：智能编标导航、工作台标题、未选项目空状态和风险检查器隐藏通过；后端刻意未启动，未执行真实审核写入或DeepSeek调用，临时5173服务已停止。

- 前端 `npm run lint`：通过，0错误、0警告。
- 前端 `npm run build`：通过；保留既有约2.45 MB主包拆分提醒。

- 工作台最小闭环聚焦回归：1 passed；覆盖目录、来源评分点、审核、映射、材料、四态汇总、连续7个修订、最终快照和旧修订冲突。
- Python编译与秘密扫描通过；完整后端回归：167 passed、1 skipped、1个既有弃用警告。跳过项仍为当前Windows无符号链接权限。

- 响应材料API聚焦回归：2 passed；覆盖新增、列表、人工更新、四态汇总、修订快照、跨工作台/未确认目标拒绝、空更新和并发冲突。
- Python编译检查通过；完整后端回归：166 passed、1 skipped、1个既有弃用警告。跳过项仍为当前Windows无符号链接权限。

- 工作台迁移与机器契约聚焦回归：8 passed；覆盖基础库升级、第二版本幂等、旧工作台数据保留、响应材料字段和状态契约，以及残缺材料表拒绝且不登记成功。
- Python编译检查通过；完整后端回归：164 passed、1 skipped、1个既有弃用警告。跳过项仍为当前Windows无符号链接权限。

- 工作台机器可读契约与设计边界测试：3 passed；JSON结构校验、秘密扫描和新增文件行尾检查通过。
- 完整后端回归：141 passed、1 skipped、1个既有弃用警告；本批未修改前端运行代码或数据库。

- 隔离共享模式HTTP回归：根/存活探针、401、错误凭据、项目列表、Dashboard、PDF、Word预览、报告和文档关闭契约通过。
- `npm run lint`：通过，0错误、0警告；`npm run build`：通过，保留既有约2.44 MB主包警告。
- Python编译检查通过；完整后端回归：125 passed，1个已知弃用警告。
- 修复后运行日志确认只有安全归一化路径，不再出现原始上传文件名。
- Edge扩展浏览器回归通过：401弹窗、正确凭据自动恢复项目/Dashboard、PDF/Word页面、报告请求、刷新清除凭据及控制台秘密检查完成。
- `npm run lint`与`npm run build`通过；完整后端回归：126 passed、1 skipped、1个已知弃用警告。
- Windows当前权限不允许创建符号链接，备份符号链接拒绝用例跳过；实现仍包含显式拒绝逻辑。
- 安全恢复聚焦测试：7 passed、1 skipped、1个已知弃用警告；全部使用合成SQLite、上传件和报告。
- Python编译与差异格式检查通过；完整后端回归：132 passed、1 skipped、1个已知弃用警告。
- 秘密扫描通过；秘密扫描聚焦测试2 passed。Python当前环境与前端生产依赖复扫均为0个已知漏洞。
- Python编译和完整后端回归通过：134 passed、1 skipped、1个既有弃用警告；前端lint/build通过，保留既有约2.44 MB主包警告。
- `scripts/verify_release.ps1`端到端通过：135 passed、1 skipped、Python/npm均0个已知漏洞、秘密扫描及前端lint/build通过；保留既有弃用和约2.44 MB主包提醒。
- 隔离生产HTTP与浏览器冻结回归通过，详细证据见 `docs/V1_FREEZE_REGRESSION.md`；两类AI请求只命中不可达测试地址，服务结束后隔离端口已关闭。
- 凭据重试修复后重新执行统一发布入口：135 passed、1 skipped，秘密扫描、Python/npm依赖审计、前端lint/build全部通过。
- Git只读审计：2个提交、4个历史跟踪文件、127个未跟踪候选、1个超过1 MiB的必要PDF worker；历史高置信度秘密扫描0命中，用户数据和本机配置忽略规则通过。
- 品牌聚焦测试2 passed；前端lint/build与秘密扫描通过，保留既有约2.44 MB主包提醒。
- 第四小批完成后统一发布入口再次通过：137 passed、1 skipped，Python/npm均无已知漏洞，秘密扫描和前端lint/build通过；保留既有弃用和约2.44 MB主包提醒。
- 候选提交前复验发现固定pytest临时目录受Windows残留权限影响，固定pip-audit缓存也产生权限降级警告；发布门禁已改用每次唯一测试目录和审计缓存并增加契约测试，避免旧缓存阻塞或干扰后续验证。
- 最终发布入口通过：138 passed、1 skipped，秘密扫描、Python/npm依赖审计和前端lint/build全部通过；候选暂存区不包含真实配置、数据库、上传件、报告、授权样本或构建依赖。
- 签署前从仓库根目录执行生产预检时发现相对默认路径随当前目录漂移；生产入口已固定切换到 `backend/`，避免误生成根目录数据库和存储目录，并新增启动契约断言。
- 正式 `1.0.0` 完整发布门禁通过；发布脚本成功提示已改为同时适用于候选版和正式版的中性文案。
- 本批未调用百度 OCR 或 WPS，未触碰用户数据库和上传文件。隔离启动时空的 `DEEPSEEK_API_KEY` 未覆盖本机 `.env`，意外产生1次真实Dashboard AI调用；未输出密钥，后续隔离启动必须同时使用非空测试Key和不可达测试Base URL。
