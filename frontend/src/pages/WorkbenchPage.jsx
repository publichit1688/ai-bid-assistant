import {
    Alert,
    Button,
    Card,
    Empty,
    Popconfirm,
    Spin,
    Tag,
    Typography
} from "antd";
import {
    FileSearchOutlined,
    ProjectOutlined,
    ReloadOutlined,
    TrophyOutlined,
    UnorderedListOutlined
} from "@ant-design/icons";

function LoadingState({text="正在加载..."}){
    return (
        <div className="app-state app-state-loading">
            <Spin />
            <span>{text}</span>
        </div>
    );
}

function EmptyState({description}){
    return (
        <div className="app-state">
            <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={description}
            />
        </div>
    );
}

export default function WorkbenchPage({
    currentFile,
    workspace,
    loading,
    aiLoading,
    reviewLoading,
    error,
    onReload,
    onRunAi,
    onReview,
    onEditMaterial,
    onAddMaterial,
    onAddSection,
    onMapCriterion
}){
    const sourceById = new Map(
        (workspace?.source_references || []).map((source)=>[source.id, source])
    );
    const mappedCriterionIds = new Set(
        (workspace?.mappings || [])
            .filter((mapping)=>mapping.coverage_status === "confirmed")
            .map((mapping)=>mapping.criterion_id)
    );
    const sectionById = new Map(
        (workspace?.sections || []).map((section)=>[section.id, section])
    );
    const confirmedSections = (workspace?.sections || []).filter(
        (section)=>section.review_status === "confirmed"
    );
    const materialStatus = {
        pending:{label:"待准备", color:"default"},
        in_progress:{label:"进行中", color:"processing"},
        completed:{label:"已完成", color:"success"},
        blocked:{label:"阻塞", color:"error"}
    };

    return (
        <div className="workbench-page">
            <div className="workbench-heading">
                <div>
                    <Typography.Title level={2} className="page-title">
                        <ProjectOutlined />
                        智能编标工作台
                    </Typography.Title>
                    <Typography.Text type="secondary">
                        {currentFile
                            ? currentFile.project_name || currentFile.filename
                            : "请先从左侧项目中心选择一个项目"}
                    </Typography.Text>
                </div>
                <div className="workbench-heading-actions">
                    <Popconfirm
                        title="使用 AI 生成目录建议？"
                        description="系统会将当前招标文件内容发送给已配置模型并消耗调用额度；结果仅作为待审核建议。"
                        okText="确认调用"
                        cancelText="取消"
                        onConfirm={()=>onRunAi("outline")}
                    >
                        <Button
                            type="primary"
                            disabled={!workspace || Boolean(aiLoading)}
                            loading={aiLoading === "outline"}
                        >
                            生成目录建议
                        </Button>
                    </Popconfirm>
                    <Popconfirm
                        title="使用 AI 提取评分点？"
                        description="系统会将当前招标文件内容发送给已配置模型并消耗调用额度；结果仅作为待审核建议。"
                        okText="确认调用"
                        cancelText="取消"
                        onConfirm={()=>onRunAi("criteria")}
                    >
                        <Button
                            disabled={!workspace || Boolean(aiLoading)}
                            loading={aiLoading === "criteria"}
                        >
                            提取评分点
                        </Button>
                    </Popconfirm>
                    <Button
                        icon={<ReloadOutlined />}
                        disabled={!currentFile || Boolean(aiLoading)}
                        loading={loading}
                        onClick={onReload}
                    >
                        刷新
                    </Button>
                </div>
            </div>

            <Alert
                className="app-inline-alert"
                type="info"
                showIcon
                title="当前为人工审核工作台"
                description="支持建议审核和材料状态维护；不会自动分派责任人、生成正文或整本标书。"
            />
            {error && <Alert className="app-inline-alert" type="error" showIcon title={error} />}
            {loading ? (
                <LoadingState text="正在加载智能编标工作台..." />
            ) : !currentFile ? (
                <EmptyState description="请从左侧项目中心选择需要编标的项目" />
            ) : !workspace ? (
                <EmptyState description="工作台数据尚未加载" />
            ) : (
                <>
                    <div className="workbench-summary">
                        <Card size="small"><Typography.Text type="secondary">当前修订</Typography.Text><strong>{workspace.revision}</strong></Card>
                        <Card size="small"><Typography.Text type="secondary">已覆盖评分点</Typography.Text><strong>{workspace.coverage?.confirmed ?? 0}</strong></Card>
                        <Card size="small"><Typography.Text type="secondary">评分点缺口</Typography.Text><strong>{workspace.coverage?.gap ?? 0}</strong></Card>
                        <Card size="small"><Typography.Text type="secondary">阻塞材料</Typography.Text><strong>{workspace.material_summary?.blocked ?? 0}</strong></Card>
                    </div>
                    <div className="workbench-columns">
                        <Card
                            className="section-card"
                            title={<span className="card-title"><UnorderedListOutlined />投标目录</span>}
                            extra={<Button size="small" type="primary" ghost onClick={onAddSection}>新增章节</Button>}
                        >
                            {(workspace.sections || []).length ? workspace.sections.map((section)=>(
                                <div className="workbench-item workbench-item-stacked" key={section.id}>
                                    <div className="workbench-item-row">
                                        <div className="workbench-item-title">{section.title}</div>
                                        <Tag color={section.review_status === "confirmed" ? "success" : section.review_status === "rejected" ? "default" : "warning"}>
                                            {section.review_status === "confirmed" ? "已确认" : section.review_status === "rejected" ? "已拒绝" : "待审核"}
                                        </Tag>
                                    </div>
                                    {section.origin === "ai" && section.review_status === "suggested" && (
                                        <div className="workbench-review-actions">
                                            <Button
                                                size="small"
                                                type="primary"
                                                loading={reviewLoading === `section-${section.id}-accept`}
                                                disabled={Boolean(reviewLoading)}
                                                onClick={()=>onReview("section", section.id, "accept")}
                                            >
                                                接受
                                            </Button>
                                            <Popconfirm
                                                title="拒绝这条目录建议？"
                                                description="原文引用会保留在修订记录中。"
                                                okText="确认拒绝"
                                                cancelText="取消"
                                                onConfirm={()=>onReview("section", section.id, "reject")}
                                            >
                                                <Button size="small" danger disabled={Boolean(reviewLoading)}>拒绝</Button>
                                            </Popconfirm>
                                        </div>
                                    )}
                                </div>
                            )) : <EmptyState description="尚未建立投标目录" />}
                        </Card>
                        <Card className="section-card" title={<span className="card-title"><TrophyOutlined />评分点覆盖</span>}>
                            {(workspace.criteria || []).length ? workspace.criteria.map((criterion)=>{
                                const source = sourceById.get(criterion.source_ref_id);
                                const criterionMappings = (workspace.mappings || []).filter(
                                    (mapping)=>mapping.criterion_id === criterion.id
                                );
                                return (
                                    <div className="workbench-item workbench-item-stacked" key={criterion.id}>
                                        <div className="workbench-item-row">
                                            <div className="workbench-item-title">{criterion.title}</div>
                                            <Tag color={criterion.review_status === "suggested" ? "warning" : criterion.review_status === "rejected" ? "default" : mappedCriterionIds.has(criterion.id) ? "success" : "error"}>
                                                {criterion.review_status === "suggested" ? "待审核" : criterion.review_status === "rejected" ? "已拒绝" : mappedCriterionIds.has(criterion.id) ? "已覆盖" : "缺口"}
                                            </Tag>
                                        </div>
                                        <Typography.Text type="secondary">{criterion.requirement}</Typography.Text>
                                        {source && <Typography.Text className="workbench-source">第 {source.page} 页：{source.quote}</Typography.Text>}
                                        {criterionMappings.length > 0 && (
                                            <div className="workbench-mapping-tags">
                                                {criterionMappings.map((mapping)=>(
                                                    <Tag color="blue" key={mapping.id}>
                                                        {sectionById.get(mapping.section_id)?.title || `章节 #${mapping.section_id}`}
                                                    </Tag>
                                                ))}
                                            </div>
                                        )}
                                        {criterion.review_status === "suggested" && (
                                            <div className="workbench-review-actions">
                                                <Button
                                                    size="small"
                                                    type="primary"
                                                    loading={reviewLoading === `criterion-${criterion.id}-accept`}
                                                    disabled={Boolean(reviewLoading)}
                                                    onClick={()=>onReview("criterion", criterion.id, "accept")}
                                                >
                                                    接受
                                                </Button>
                                                <Popconfirm
                                                    title="拒绝这条评分点建议？"
                                                    description="原文引用会保留在修订记录中。"
                                                    okText="确认拒绝"
                                                    cancelText="取消"
                                                    onConfirm={()=>onReview("criterion", criterion.id, "reject")}
                                                >
                                                    <Button size="small" danger disabled={Boolean(reviewLoading)}>拒绝</Button>
                                                </Popconfirm>
                                            </div>
                                        )}
                                        {criterion.review_status === "confirmed" && (
                                            <div className="workbench-review-actions">
                                                <Button
                                                    size="small"
                                                    disabled={confirmedSections.length === 0}
                                                    title={confirmedSections.length === 0 ? "请先新增或确认目录章节" : ""}
                                                    onClick={()=>onMapCriterion(criterion)}
                                                >
                                                    {criterionMappings.length > 0 ? "管理映射" : "添加映射"}
                                                </Button>
                                            </div>
                                        )}
                                    </div>
                                );
                            }) : <EmptyState description="尚未提取评分点" />}
                        </Card>
                        <Card
                            className="section-card"
                            title={<span className="card-title"><FileSearchOutlined />响应材料</span>}
                            extra={(
                                <Button
                                    size="small"
                                    type="primary"
                                    ghost
                                    disabled={confirmedSections.length === 0 && (workspace.criteria || []).every((criterion)=>criterion.review_status !== "confirmed")}
                                    title={confirmedSections.length === 0 && (workspace.criteria || []).every((criterion)=>criterion.review_status !== "confirmed") ? "请先确认评分点或目录章节" : ""}
                                    onClick={onAddMaterial}
                                >
                                    新增材料
                                </Button>
                            )}
                        >
                            {(workspace.materials || []).length ? workspace.materials.map((material)=>{
                                const status = materialStatus[material.material_status] || materialStatus.pending;
                                return (
                                    <div className="workbench-item workbench-item-stacked" key={material.id}>
                                        <div className="workbench-item-row">
                                            <div className="workbench-item-title">{material.title}</div>
                                            <Tag color={status.color}>{status.label}</Tag>
                                        </div>
                                        <Typography.Text type="secondary">责任人：{material.owner_name || "未指定"}</Typography.Text>
                                        {material.notes && <Typography.Text>{material.notes}</Typography.Text>}
                                        <div className="workbench-review-actions">
                                            <Button size="small" onClick={()=>onEditMaterial(material)}>
                                                编辑材料
                                            </Button>
                                        </div>
                                    </div>
                                );
                            }) : <EmptyState description="尚未登记响应材料" />}
                        </Card>
                    </div>
                </>
            )}
        </div>
    );
}
