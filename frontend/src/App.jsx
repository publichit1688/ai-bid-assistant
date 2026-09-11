import "./pdf-highlight.css";

import {
  DashboardOutlined,
  ExportOutlined,
  FileSearchOutlined,
  LineChartOutlined,
  ProjectOutlined,
  SwapOutlined,
  TrophyOutlined,
  UnorderedListOutlined,
  UploadOutlined
} from "@ant-design/icons";


import {
  Layout,
  Button,
  Upload,
  Card,
  Typography,
  message,
  Alert,
  Empty,
  Spin,
  Tag,
  Divider,
  Input,
  Select,
  Popconfirm,
  Segmented,
  Modal
} from "antd";


import {
    lazy,
    Suspense,
    useState,
    useEffect,
    useRef
} from "react";


import {
    apiClient,
    clearAccessToken,
    hasAccessToken,
    setAccessToken,
    toApiPath
} from "./api";


import "react-pdf/dist/Page/TextLayer.css";
import "react-pdf/dist/Page/AnnotationLayer.css";




const {
  Sider,
  Header,
  Content
}=Layout;

const WorkbenchPage = lazy(()=>import("./pages/WorkbenchPage.jsx"));
const DashboardChart = lazy(()=>import("./components/DashboardChart.jsx"));
const DocumentPreview = lazy(()=>import("./components/DocumentPreview.jsx"));


function AsyncDashboardChart({option, style}){
    return (
        <Suspense
            fallback={
                <div
                    className="dashboard-chart-loading"
                    style={{
                        ...style,
                        display:"flex",
                        alignItems:"center",
                        justifyContent:"center"
                    }}
                >
                    <Spin size="small" />
                </div>
            }
        >
            <DashboardChart option={option} style={style} />
        </Suspense>
    );
}


function isWordFile(filename){
    return /\.docx?$/i.test(String(filename || ""));
}


function formatProcurementRequirement(item){
    if(typeof item === "string"){
        return item;
    }
    if(!item || typeof item !== "object"){
        return "";
    }
    return [
        ["标的", item.item_name],
        ["规格/要求", item.specification],
        ["数量", item.quantity],
        ["预算", item.budget],
        ["进口产品", item.import_allowed],
        ["页码", item.page]
    ]
        .filter(([,value])=>value !== undefined && value !== null && value !== "")
        .map(([label,value])=>`${label}：${value}`)
        .join("；");
}


function CompareRow({
    label,
    valueA,
    valueB
}){

    const cellStyle = {
        padding:"12px",
        borderTop:"1px solid #eee"
    };




    return (
        <>
            <div
                style={{
                    ...cellStyle,
                    fontWeight:"bold",
                    background:"#fafafa"
                }}
            >
                {label}
            </div>

            <div
                style={cellStyle}
            >
                {valueA}
            </div>

            <div
                style={cellStyle}
            >
                {valueB}
            </div>
        </>
    );

}

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

// WorkbenchPage is loaded only when the user opens the intelligent bid workspace.


function App(){

const [credentialOpen,setCredentialOpen]=useState(false);
const [credentialDraft,setCredentialDraft]=useState("");
const [credentialConfigured,setCredentialConfigured]=useState(hasAccessToken());
const [credentialError,setCredentialError]=useState("");

function saveAccessCredential(){
    const value = credentialDraft.trim();
    if(value.length < 32){
        setCredentialError("访问密钥至少需要 32 位。请使用部署管理员提供的密钥。");
        return;
    }
    setAccessToken(value);
    setCredentialConfigured(true);
    setCredentialDraft("");
    setCredentialError("");
    setCredentialOpen(false);
    message.success("访问凭据已在当前页面内存中启用");
}

function removeAccessCredential(){
    clearAccessToken();
    setCredentialConfigured(false);
    setCredentialDraft("");
    setCredentialError("");
    message.success("已清除当前页面的访问凭据");
}

useEffect(()=>{
    const showCredentialPrompt = ()=>{
        setCredentialError("访问凭据无效或已失效，请重新输入。");
        setCredentialOpen(true);
    };
    window.addEventListener("app-auth-required", showCredentialPrompt);
    return ()=>window.removeEventListener("app-auth-required", showCredentialPrompt);
},[]);

function highlightKeyword(words,level){


if(!words || words.length===0){

return;

}


// 清除旧高亮

document
.querySelectorAll(
".highlight-high,.highlight-middle,.highlight-low"
)
.forEach(el=>{

el.classList.remove(
"highlight-high",
"highlight-middle",
"highlight-low"
);

});



setTimeout(()=>{


const spans =
document.querySelectorAll(
".react-pdf__Page__textContent span"
);



let className="highlight-low";



if(level?.includes("高")){

className="highlight-high";

}
else if(level?.includes("中")){

className="highlight-middle";

}




spans.forEach(span=>{


const text =
span.innerText.trim();



words.forEach(word=>{


if(

word &&

text.includes(word)

){


span.classList.add(
className
);


}


});


});



},1200);



}

const [files,setFiles]=useState([]);

const [searchText,setSearchText]=useState("");

const [riskFilter,setRiskFilter]=useState("全部");

const [currentFile,setCurrentFile]=useState(null);


const [result,setResult]=useState(null);


const [risks,setRisks]=useState([]);

const [score,setScore]=useState(0);

const [dashboardRiskFocus, setDashboardRiskFocus] = useState(false);



// V2.2 评分总览
const [scoreLevel,setScoreLevel]=useState("");
const [highCount,setHighCount]=useState(0);
const [middleCount,setMiddleCount]=useState(0);
const [lowCount,setLowCount]=useState(0);
const [totalDeduction,setTotalDeduction]=useState(0);

const [loading,setLoading]=useState(false);



const [pdfUrl,setPdfUrl]=useState("");

const [docxPreviewPages,setDocxPreviewPages]=useState([]);

const [previewError,setPreviewError]=useState("");

const [previewSourceFormat,setPreviewSourceFormat]=useState("");

const [wordPreviewRiskPages,setWordPreviewRiskPages]=useState({});

const [previewRenderer,setPreviewRenderer]=useState("");

const [numPages,setNumPages]=useState(0);

const [pageNumber,setPageNumber]=useState(1);

const [,setHighlightText]=useState("");

const [activeRisk,setActiveRisk]=useState(null);

const [activeRiskPreviewPage,setActiveRiskPreviewPage]=useState(null);


// ======================
// 项目对比
// 最多选择2个项目
// ======================

const [compareFiles,setCompareFiles] = useState([]);

const [compareResult,setCompareResult] = useState(null);

const [compareLoading,setCompareLoading] = useState(false);

const [aiDecision,setAiDecision] = useState(null);

const [aiDecisionLoading,setAiDecisionLoading] = useState(false);

// ======================
// Dashboard V1
// ======================

const [dashboard,setDashboard] = useState(null);




// Dashboard 趋势时间范围
const [trendDays,setTrendDays] = useState(7);

const [dashboardLoading,setDashboardLoading] = useState(false);

const [filesError,setFilesError] = useState("");

const [dashboardError,setDashboardError] = useState("");

const [showDashboard,setShowDashboard] = useState(true);

const [showWorkbench,setShowWorkbench] = useState(false);
const [workbench,setWorkbench] = useState(null);
const [workbenchLoading,setWorkbenchLoading] = useState(false);
const [workbenchAiLoading,setWorkbenchAiLoading] = useState("");
const [workbenchReviewLoading,setWorkbenchReviewLoading] = useState("");
const [workbenchError,setWorkbenchError] = useState("");
const [materialEditorOpen,setMaterialEditorOpen] = useState(false);
const [materialSaving,setMaterialSaving] = useState(false);
const [materialDraft,setMaterialDraft] = useState(null);
const [sectionEditorOpen,setSectionEditorOpen] = useState(false);
const [sectionSaving,setSectionSaving] = useState(false);
const [sectionTitleDraft,setSectionTitleDraft] = useState("");
const [mappingEditorOpen,setMappingEditorOpen] = useState(false);
const [mappingSaving,setMappingSaving] = useState(false);
const [mappingDraft,setMappingDraft] = useState(null);


const [
    aiManagementSummary,
    setAiManagementSummary
] = useState(null);


const [
    aiManagementLoading,
    setAiManagementLoading
] = useState(false);


// ======================
// Dashboard V2.5.2
// AI摘要缓存
// ======================

const aiSummaryCacheRef =
    useRef({});

const riskSectionRef =
    useRef(null);

const pdfObjectUrlRef =
    useRef("");

const [leftCollapsed, setLeftCollapsed] = useState(false);

const [rightCollapsed, setRightCollapsed] = useState(false);

function clearPdfObjectUrl(){
    if(pdfObjectUrlRef.current){
        window.URL.revokeObjectURL(pdfObjectUrlRef.current);
        pdfObjectUrlRef.current = "";
    }
}

async function loadProtectedPdf(filepath){
    clearPdfObjectUrl();
    const response = await apiClient.get(toApiPath(filepath), {
        responseType:"blob"
    });
    const objectUrl = window.URL.createObjectURL(response.data);
    pdfObjectUrlRef.current = objectUrl;
    setPdfUrl(objectUrl);
}

useEffect(()=>()=>clearPdfObjectUrl(),[]);

async function loadDocumentPreview(fileData){
    setPageNumber(1);
    setNumPages(0);
    setPreviewError("");
    setPreviewSourceFormat("");
    setWordPreviewRiskPages({});
    setPreviewRenderer("");
    setActiveRiskPreviewPage(null);

    if(isWordFile(fileData?.filename)){
        setPdfUrl("");
        try{
            const response = await apiClient.get(
                `/api/files/${fileData.id}/preview`
            );
            if(response.data?.pagination === "rendered" && response.data?.filepath){
                setDocxPreviewPages([]);
                setPreviewSourceFormat(response.data?.source_format || "word");
                setNumPages(Number(response.data?.num_pages) || 0);
                setWordPreviewRiskPages(response.data?.risk_page_map || {});
                setPreviewRenderer(response.data?.renderer || "unknown");
                await loadProtectedPdf(response.data.filepath);
            }
            else{
                const pages = Array.isArray(response.data?.pages)
                    ? response.data.pages
                    : [];
                setDocxPreviewPages(pages);
                setPreviewSourceFormat(response.data?.format || "word");
                setNumPages(pages.length);
            }
        }
        catch(error){
            setDocxPreviewPages([]);
            const detail = error.response?.data?.detail;
            setPreviewError(
                (typeof detail === "string" ? detail : detail?.message)
                || "Word 文档版式预览加载失败，分析结果仍可正常查看。"
            );
        }
        return;
    }

    setDocxPreviewPages([]);
    if(fileData?.filepath){
        setPreviewSourceFormat("pdf");
        try{
            await loadProtectedPdf(fileData.filepath);
        }
        catch(error){
            setPdfUrl("");
            const detail = error.response?.data?.detail;
            setPreviewError(
                (typeof detail === "string" ? detail : detail?.message)
                || "PDF 预览加载失败，请确认访问凭据和后端服务。"
            );
        }
    }
    else{
        setPdfUrl("");
    }
}

async function exportReport(){


try{


const res=await apiClient.post(

"/api/report",

{
    ...(result || {}),
    risk:risks.map((risk,index)=>({
        ...risk,
        report_page:
            Number(wordPreviewRiskPages[String(index)])
            || risk.page
    })),
    score:score,
    score_level:scoreLevel,
    high_count:highCount,
    middle_count:middleCount,
    low_count:lowCount,
    total_deduction:totalDeduction
},

{
responseType:"blob"
}

);



const url=
window.URL.createObjectURL(
new Blob([res.data])
);



const a=document.createElement("a");


a.href=url;


a.download=
"AI投标风险分析报告.docx";


a.click();


}

catch{

message.error(
"报告生成失败"
);

}


}



// ======================
// 页面初始化
// 加载历史文件
// ======================

useEffect(()=>{

    loadFiles();

},[]);


useEffect(()=>{

    if(!credentialConfigured){
        return;
    }

    loadFiles();
    loadDashboard();

    // 凭据从未启用切换为已启用时，统一重试首次401的核心请求。
    // eslint-disable-next-line react-hooks/exhaustive-deps
},[credentialConfigured]);


// ======================
// Dashboard
// 7天 / 30天切换时重新加载
// ======================

useEffect(()=>{

    loadDashboard();

    // 仅在趋势周期变化时刷新；loadDashboard 使用当前渲染周期的数据。
    // eslint-disable-next-line react-hooks/exhaustive-deps
},[trendDays]);


async function loadFiles(){


try{

setFilesError("");


const res=await apiClient.get(

"/api/files"

);



setFiles(

res.data

);



}

catch{

setFilesError("项目记录读取失败，请确认后端服务后重试。");


message.error(
"读取历史文件失败"
);


}



}


// ======================
// Dashboard V1
// 获取统计数据
// ======================

async function loadDashboard(){

    setDashboardLoading(true);
    setDashboardError("");

    try{

        const res = await apiClient.get(
            "/api/dashboard",
            {
                 params:{
                     days:trendDays
               }
           }
       );

        // ======================
        // 保存Dashboard数据
        // ======================

        setDashboard(
            res.data
        );


        // ======================
        // V2.5 AI管理摘要
        // ======================

        await loadAiManagementSummary(
            res.data
        );




        setDashboard(
            res.data
        );

    }

    catch{
        setAiManagementSummary(null);

        setDashboardError(
            "Dashboard 数据读取失败，请确认后端服务后重试。"
        );

        message.error(
            "Dashboard数据读取失败"
        );

    }

    finally{

        setDashboardLoading(false);

    }

}


function createDashboardFingerprint(
    dashboardData,
    days
){

    if(!dashboardData){
        return "";
    }


    const fingerprintData = {

        days:days,

        total_projects:
            dashboardData.total_projects,

        total_risks:
            dashboardData.total_risks,

        average_score:
            dashboardData.average_score,

        risk_distribution:
            dashboardData.risk_distribution,

        score_distribution:
            dashboardData.score_distribution,

        period_comparison:
            dashboardData.period_comparison,

        attention_projects:
            dashboardData.attention_projects

    };


    return JSON.stringify(
        fingerprintData
    );

}


async function loadAiManagementSummary(
    dashboardData
){

    if(!dashboardData){
        return;
    }


    // ======================
    // V2.5.2
    // 创建当前数据指纹
    // ======================

    const cacheKey =
        createDashboardFingerprint(
            dashboardData,
            trendDays
        );


    // ======================
    // 先检查缓存
    // ======================

    if(
         aiSummaryCacheRef.current[
        cacheKey
        ]
    ){

        setAiManagementSummary(
            aiSummaryCacheRef.current[
            cacheKey
            ]
        );

        return;
    }


    setAiManagementLoading(true);


    try{

        const res = await apiClient.post(

            "/api/dashboard/ai-summary",

            {
                days:
                    trendDays,

                total_projects:
                    dashboardData.total_projects,

                total_risks:
                    dashboardData.total_risks,

                average_score:
                    dashboardData.average_score,

                risk_distribution:
                    dashboardData.risk_distribution,

                score_distribution:
                    dashboardData.score_distribution,

                period_comparison:
                    dashboardData.period_comparison,

                attention_projects:
                    dashboardData.attention_projects
            }

        );


        if(
            res.data
            &&
            res.data.success
            &&
            res.data.summary
        ){

            const summary =
                res.data.summary;


            // ======================
            // 保存当前显示内容
            // ======================

            setAiManagementSummary(
                summary
            );


            // ======================
            // V2.5.2
            // 写入缓存
            // ======================


            aiSummaryCacheRef.current[
               cacheKey
            ] = summary;


            setAiManagementSummary(
               summary
           );


        }

        else{

            setAiManagementSummary(null);

        }

    }

    catch{
        setAiManagementSummary(null);
    }

    finally{

        setAiManagementLoading(false);

    }

}


// ======================
// 选择上传文件
// ======================


function beforeUpload(file){

const supported = /\.(pdf|docx|doc)$/i.test(file.name || "");
if(!supported){
message.error("仅支持 PDF、DOCX 和 DOC 文件");
return Upload.LIST_IGNORE;
}


setCurrentFile({


id:null,


filename:file.name,


file:file


});

setPdfUrl("");
setDocxPreviewPages([]);
setPreviewError("");




return false;


}









// ======================
// 开始分析
// ======================


async function startAnalyze(){


if(!currentFile?.file){


message.warning(
"请先选择文件"
);


return;


}



setLoading(true);

setActiveRisk(null);
setActiveRiskPreviewPage(null);
setRisks([]);
setResult(null);

try{


let formData=new FormData();



formData.append(

"file",

currentFile.file

);




const res=await apiClient.post(

"/api/upload",

formData

);

message.success(
"分析完成"
);




const analysis =
res.data.analysis || res.data;



setResult(
analysis
);

// ======================
// V2.2 后端评分总览
// ======================

setScore(
    res.data.score ?? 0
);

setScoreLevel(
    res.data.score_level || ""
);

setHighCount(
    res.data.high_count ?? 0
);

setMiddleCount(
    res.data.middle_count ?? 0
);

setLowCount(
    res.data.low_count ?? 0
);

setTotalDeduction(
    res.data.total_deduction ?? 0
);

setRisks(
    analysis.risk || []
);

setScore(
    res.data.score ?? 0
);


// 计算投标评分




await loadDocumentPreview(res.data);



loadFiles();



}

catch(e){


message.error(
e.response?.data?.detail?.message || "分析失败"
);


}


setLoading(false);



}









// ======================
// 点击历史文件
// ======================

async function loadWorkbench(item=currentFile){
    if(!item){
        setWorkbench(null);
        setWorkbenchError("");
        return;
    }
    setCurrentFile(item);
    setWorkbenchLoading(true);
    setWorkbenchError("");
    try{
        const response = await apiClient.post(
            "/api/workspaces",
            {bid_file_id:item.id}
        );
        setWorkbench(response.data);
    }
    catch{
        setWorkbench(null);
        setWorkbenchError("智能编标工作台读取失败，请确认后端服务后重试。");
    }
    finally{
        setWorkbenchLoading(false);
    }
}

async function reviewWorkbenchSuggestion(kind,id,decision){
    if(!workbench){
        return;
    }
    const loadingKey = `${kind}-${id}-${decision}`;
    const path = kind === "section"
        ? `/api/workspaces/${workbench.id}/sections/${id}/review`
        : `/api/workspaces/${workbench.id}/criteria/${id}/review`;
    setWorkbenchReviewLoading(loadingKey);
    setWorkbenchError("");
    try{
        const response = await apiClient.post(
            path,
            {revision:workbench.revision, decision}
        );
        setWorkbench(response.data);
        message.success(decision === "accept" ? "建议已接受" : "建议已拒绝");
    }
    catch(error){
        if(error.response?.status === 409){
            setWorkbenchError("工作台已被更新，请点击刷新后再审核。");
        }
        else{
            setWorkbenchError("建议审核失败，请稍后重试。");
        }
    }
    finally{
        setWorkbenchReviewLoading("");
    }
}

async function runWorkbenchAi(kind){
    if(!workbench || workbenchAiLoading){
        return;
    }
    const isOutline = kind === "outline";
    const path = isOutline
        ? `/api/workspaces/${workbench.id}/outline-suggestions`
        : `/api/workspaces/${workbench.id}/criteria-extractions`;
    setWorkbenchAiLoading(kind);
    setWorkbenchError("");
    try{
        const response = await apiClient.post(path, {revision:workbench.revision});
        setWorkbench(response.data);
        const warningCount = Array.isArray(response.data?.warnings)
            ? response.data.warnings.length
            : 0;
        const resultLabel = isOutline ? "目录建议" : "评分点建议";
        message.success(
            warningCount > 0
                ? `${resultLabel}已生成，${warningCount} 条因来源无法验证未采用，请人工审核。`
                : `${resultLabel}已生成，请人工审核后使用。`
        );
    }
    catch(error){
        if(error.response?.status === 409){
            setWorkbenchError("工作台已被更新，请点击刷新后再调用 AI。");
        }
        else{
            const detail = error.response?.data?.detail;
            setWorkbenchError(
                (typeof detail === "string" ? detail : detail?.message)
                || (isOutline ? "目录建议生成失败，请稍后重试。" : "评分点提取失败，请稍后重试。")
            );
        }
    }
    finally{
        setWorkbenchAiLoading("");
    }
}

function openMaterialEditor(material){
    setMaterialDraft({
        id:material.id,
        title:material.title,
        material_status:material.material_status,
        owner_name:material.owner_name || "",
        notes:material.notes || "",
        original_owner_name:material.owner_name || "",
        original_notes:material.notes || "",
        original_status:material.material_status
    });
    setMaterialEditorOpen(true);
}

function openMaterialCreator(){
    const firstCriterion = (workbench?.criteria || []).find(
        (criterion)=>criterion.review_status === "confirmed"
    );
    const firstSection = (workbench?.sections || []).find(
        (section)=>section.review_status === "confirmed"
    );
    setMaterialDraft({
        id:null,
        title:"",
        criterion_id:firstCriterion?.id,
        section_id:firstCriterion ? undefined : firstSection?.id,
        material_status:"pending",
        owner_name:"",
        notes:""
    });
    setMaterialEditorOpen(true);
}

function closeMaterialEditor(){
    if(materialSaving){
        return;
    }
    setMaterialEditorOpen(false);
    setMaterialDraft(null);
}

async function saveMaterialEditor(){
    if(!workbench || !materialDraft){
        return;
    }
    const title = materialDraft.title.trim();
    const ownerName = materialDraft.owner_name.trim();
    const notes = materialDraft.notes.trim();
    const isCreating = !materialDraft.id;
    if(isCreating && !title){
        message.warning("请输入材料名称");
        return;
    }
    if(isCreating && !materialDraft.criterion_id && !materialDraft.section_id){
        message.warning("请至少关联一个已确认评分点或目录章节");
        return;
    }
    if(
        !isCreating
        &&
        ownerName === materialDraft.original_owner_name
        && notes === materialDraft.original_notes
        && materialDraft.material_status === materialDraft.original_status
    ){
        message.info("材料信息没有变化");
        return;
    }
    setMaterialSaving(true);
    setWorkbenchError("");
    try{
        const payload = {
                revision:workbench.revision,
                material_status:materialDraft.material_status,
                owner_name:ownerName || null,
                notes:notes || null
        };
        if(isCreating){
            payload.title = title;
            payload.criterion_id = materialDraft.criterion_id || null;
            payload.section_id = materialDraft.section_id || null;
        }
        const response = isCreating
            ? await apiClient.post(`/api/workspaces/${workbench.id}/materials`, payload)
            : await apiClient.patch(`/api/workspaces/${workbench.id}/materials/${materialDraft.id}`, payload);
        setWorkbench(response.data);
        setMaterialEditorOpen(false);
        setMaterialDraft(null);
        message.success(isCreating ? "响应材料已新增" : "响应材料已更新");
    }
    catch(error){
        if(error.response?.status === 409){
            setWorkbenchError(`工作台已被更新，请刷新后重新${isCreating ? "新增" : "编辑"}材料。`);
            setMaterialEditorOpen(false);
            setMaterialDraft(null);
        }
        else{
            const detail = error.response?.data?.detail;
            message.error(
                (typeof detail === "string" ? detail : detail?.message)
                || "响应材料保存失败，请稍后重试。"
            );
        }
    }
    finally{
        setMaterialSaving(false);
    }
}

function openSectionEditor(){
    setSectionTitleDraft("");
    setSectionEditorOpen(true);
}

function closeSectionEditor(){
    if(sectionSaving){
        return;
    }
    setSectionEditorOpen(false);
    setSectionTitleDraft("");
}

async function saveSectionEditor(){
    if(!workbench){
        return;
    }
    const title = sectionTitleDraft.trim();
    if(!title){
        message.warning("请输入章节标题");
        return;
    }
    setSectionSaving(true);
    setWorkbenchError("");
    try{
        const response = await apiClient.post(
            `/api/workspaces/${workbench.id}/sections`,
            {revision:workbench.revision, title}
        );
        setWorkbench(response.data);
        setSectionEditorOpen(false);
        setSectionTitleDraft("");
        message.success("目录章节已新增");
    }
    catch(error){
        if(error.response?.status === 409){
            setWorkbenchError("工作台已被更新，请刷新后重新新增章节。");
            setSectionEditorOpen(false);
            setSectionTitleDraft("");
        }
        else{
            message.error(error.response?.data?.detail?.message || "目录章节新增失败，请稍后重试。");
        }
    }
    finally{
        setSectionSaving(false);
    }
}

function openMappingEditor(criterion){
    const confirmedSections = (workbench?.sections || []).filter(
        (section)=>section.review_status === "confirmed"
    );
    const existing = (workbench?.mappings || []).find(
        (mapping)=>mapping.criterion_id === criterion.id
    );
    setMappingDraft({
        criterion_id:criterion.id,
        criterion_title:criterion.title,
        section_id:existing?.section_id || confirmedSections[0]?.id,
        rationale:existing?.rationale || ""
    });
    setMappingEditorOpen(true);
}

function closeMappingEditor(){
    if(mappingSaving){
        return;
    }
    setMappingEditorOpen(false);
    setMappingDraft(null);
}

function selectMappingSection(sectionId){
    const existing = (workbench?.mappings || []).find(
        (mapping)=>mapping.criterion_id === mappingDraft?.criterion_id
            && mapping.section_id === sectionId
    );
    setMappingDraft({
        ...mappingDraft,
        section_id:sectionId,
        rationale:existing?.rationale || ""
    });
}

async function saveMappingEditor(){
    if(!workbench || !mappingDraft?.section_id){
        message.warning("请选择一个已确认目录章节");
        return;
    }
    setMappingSaving(true);
    setWorkbenchError("");
    try{
        const response = await apiClient.put(
            `/api/workspaces/${workbench.id}/mappings`,
            {
                revision:workbench.revision,
                mappings:[{
                    criterion_id:mappingDraft.criterion_id,
                    section_id:mappingDraft.section_id,
                    rationale:mappingDraft.rationale.trim() || null
                }]
            }
        );
        setWorkbench(response.data);
        setMappingEditorOpen(false);
        setMappingDraft(null);
        message.success("评分点映射已保存");
    }
    catch(error){
        if(error.response?.status === 409){
            setWorkbenchError("工作台已被更新，请刷新后重新设置映射。");
            setMappingEditorOpen(false);
            setMappingDraft(null);
        }
        else{
            message.error(error.response?.data?.detail?.message || "评分点映射保存失败，请稍后重试。");
        }
    }
    finally{
        setMappingSaving(false);
    }
}

async function selectFile(item){

    setCurrentFile(item);

    setActiveRisk(null);
    setActiveRiskPreviewPage(null);

    setPageNumber(1);

    setHighlightText("");


    try{

        const res = await apiClient.get(

            `/api/files/${item.id}`

        );


        // ======================
        // AI分析结果
        // ======================

        setResult(
            res.data.analysis
        );


        // ======================
        // 风险列表
        // ======================

        setRisks(
            res.data.risk || []
        );


        // ======================
        // V2.2 历史评分总览
        // ======================

        setScore(
            res.data.score ?? 0
        );

        setScoreLevel(
            res.data.score_level || ""
        );

        setHighCount(
            res.data.high_count ?? 0
        );

        setMiddleCount(
            res.data.middle_count ?? 0
        );

        setLowCount(
            res.data.low_count ?? 0
        );

        setTotalDeduction(
            res.data.total_deduction ?? 0
        );


        // ======================
        // PDF地址
        // ======================

        await loadDocumentPreview(res.data);

    }

    catch{

        message.error(
            "读取失败"
        );

    }

}

// ======================
// Dashboard
// 点击项目进入分析详情
// ======================

async function openDashboardProject(item){

    // 从驾驶舱进入风险项目时，自动展开风险检查器
    setRightCollapsed(false);

    // 标记：这次是从管理驾驶舱进入
    setDashboardRiskFocus(true);

    // 先切换到标书分析页面
    setShowDashboard(false);
    setShowWorkbench(false);

    // 使用现有历史文件读取逻辑
    await selectFile(item);

    // 等待页面渲染完成后，自动滚动到风险分析区域
    setTimeout(() => {

        riskSectionRef.current?.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }, 500);


    // 几秒后取消高风险强调
    setTimeout(() => {

        setDashboardRiskFocus(false);

    }, 4500);

}


async function deleteFile(
    id,
    deleteOriginal = false
){

    try{

        const res = await apiClient.delete(

            `/api/files/${id}`,

            {
                params:{
                    delete_original:
                    deleteOriginal
                }
            }

        );


        if(!res.data.success){

            message.error(
                res.data.error || "删除失败"
            );

            return;

        }


        message.success(
            res.data.message
        );


        // 如果删除的是当前正在查看的项目
        if(currentFile?.id === id){

            setCurrentFile(null);

            setResult(null);

            setRisks([]);

            setActiveRisk(null);
            setActiveRiskPreviewPage(null);

            setPdfUrl("");

            setDocxPreviewPages([]);
            setWordPreviewRiskPages({});

            setPreviewError("");

            setScore(0);

            setScoreLevel("");

            setHighCount(0);

            setMiddleCount(0);

            setLowCount(0);

            setTotalDeduction(0);

            setPageNumber(1);

        }


        await loadFiles();

    }

    catch{

        message.error(
            "删除失败"
        );

    }

}

// ======================
// 加入 / 取消项目对比
// ======================

function toggleCompare(item){

    // 是否已经选择
    const exists = compareFiles.some(
        file => file.id === item.id
    );


    // 已选择 → 再点一次取消
    if(exists){

        setCompareFiles(
            compareFiles.filter(
                file => file.id !== item.id
            )
        );

        return;
    }


    // 最多只能选2个
    if(compareFiles.length >= 2){

        message.warning(
            "最多只能选择2个项目进行对比"
        );

        return;
    }


    // 加入对比
    setCompareFiles([
        ...compareFiles,
        item
    ]);

}

// ======================
// 开始项目对比
// ======================

// ======================
// 风险语义分类
// ======================

function getRiskCategory(risk){

    const text = String(
        [
            risk.keyword || "",
            risk.reason || "",
            risk.quote || ""
        ].join(" ")
    ).toLowerCase();


    const categories = [

        {
            name:"资格审查风险",
            keywords:[
                "资格审查",
                "资格条件",
                "资格要求",
                "资格不符"
            ]
        },

        {
            name:"企业资质风险",
            keywords:[
                "企业资质",
                "资质证书",
                "施工资质",
                "专业承包",
                "总承包"
            ]
        },

        {
            name:"人员资格风险",
            keywords:[
                "项目负责人",
                "技术负责人",
                "建造师",
                "负责人",
                "人员证书",
                "b证",
                "a证",
                "c证"
            ]
        },

        {
            name:"在建项目风险",
            keywords:[
                "在建工程",
                "在建项目",
                "不得任职",
                "同时任职"
            ]
        },

        {
            name:"电子签名风险",
            keywords:[
                "电子签名",
                "数字证书",
                "ca证书",
                "电子签章",
                "签章"
            ]
        },

        {
            name:"盖章风险",
            keywords:[
                "公章",
                "法人章",
                "盖章",
                "加盖"
            ]
        },

        {
            name:"投标保证金风险",
            keywords:[
                "投标保证金",
                "保证金",
                "保函",
                "银行保函"
            ]
        },

        {
            name:"联合体风险",
            keywords:[
                "联合体",
                "联合体协议",
                "牵头人"
            ]
        },

        {
            name:"业绩要求风险",
            keywords:[
                "类似业绩",
                "企业业绩",
                "项目业绩",
                "业绩证明"
            ]
        },

        {
            name:"信用风险",
            keywords:[
                "信用",
                "失信",
                "信用中国",
                "黑名单"
            ]
        },

        {
            name:"安全生产风险",
            keywords:[
                "安全生产许可证",
                "安全生产考核",
                "安全证书"
            ]
        },

        {
            name:"截止时间风险",
            keywords:[
                "投标截止",
                "递交截止",
                "开标时间",
                "截止时间"
            ]
        },

        {
            name:"投标文件格式风险",
            keywords:[
                "投标文件格式",
                "文件格式",
                "pdf格式",
                "扫描件",
                "目录"
            ]
        },

        {
            name:"工程量清单风险",
            keywords:[
                "工程量清单",
                "已标价工程量清单",
                "清单填报",
                "造价"
            ]
        },

        {
            name:"技术方案风险",
            keywords:[
                "技术方案",
                "施工组织设计",
                "施工方案",
                "技术要求"
            ]
        }

    ];


    for(const category of categories){

        if(
            category.keywords.some(
                word => text.includes(
                    word.toLowerCase()
                )
            )
        ){

            return category.name;

        }

    }


    // 没匹配到时使用AI原风险标题
    return (
        risk.keyword
        ||
        "其他风险"
    );

}



async function startCompare(){

    if(compareFiles.length !== 2){

        message.warning(
            "请选择两个项目进行对比"
        );




        return;
    }


    setCompareLoading(true);

    setAiDecision(null);


    try{

        const [resA,resB] = await Promise.all([

            apiClient.get(
                `/api/files/${compareFiles[0].id}`
            ),

            apiClient.get(
                `/api/files/${compareFiles[1].id}`
            )

        ]);


        const projectA = resA.data;

        const projectB = resB.data;



// ======================
// V2.1 语义风险对比
// ======================

const risksA = projectA.risk || [];
const risksB = projectB.risk || [];


// 给风险增加category

const semanticRisksA = risksA.map(
    risk => ({
        ...risk,
        category:
        getRiskCategory(risk)
    })
);


const semanticRisksB = risksB.map(
    risk => ({
        ...risk,
        category:
        getRiskCategory(risk)
    })
);

// ======================
// 风险等级强度
// ======================

function getRiskStrength(risk){

    const level = String(
        risk?.level || ""
    );

    if(level.includes("高")){
        return 3;
    }

    if(level.includes("中")){
        return 2;
    }

    if(level.includes("低")){
        return 1;
    }

    return 0;

}


// 获取两个项目所有风险类别

const categoriesA = [
    ...new Set(
        semanticRisksA.map(
            risk => risk.category
        )
    )
];


const categoriesB = [
    ...new Set(
        semanticRisksB.map(
            risk => risk.category
        )
    )
];


// ======================
// 共同风险类别
// ======================

const commonCategories =
categoriesA.filter(
    category =>
    categoriesB.includes(category)
);

// ======================
// V2.2 共同风险强度对比
// ======================

const riskStrengthCompare =
commonCategories.map(category=>{


    // 找项目A该类别中最严重的一条风险
    const risksOfA =
    semanticRisksA.filter(
        risk =>
        risk.category === category
    );


    const risksOfB =
    semanticRisksB.filter(
        risk =>
        risk.category === category
    );


    const strongestA =
    [...risksOfA].sort(
        (a,b)=>
        getRiskStrength(b)
        -
        getRiskStrength(a)
    )[0];


    const strongestB =
    [...risksOfB].sort(
        (a,b)=>
        getRiskStrength(b)
        -
        getRiskStrength(a)
    )[0];


    const strengthA =
    getRiskStrength(strongestA);


    const strengthB =
    getRiskStrength(strongestB);


let stronger;

let compareReason;


// ======================
// 第一层：比较风险等级
// ======================

if(strengthA > strengthB){

    stronger = "A";

    compareReason =
    "项目A风险等级更高";

}
else if(strengthB > strengthA){

    stronger = "B";

    compareReason =
    "项目B风险等级更高";

}


// ======================
// 第二层：等级相同，再比较扣分
// ======================

else{

    const deductionA =
    strongestA?.deduction ?? 0;


    const deductionB =
    strongestB?.deduction ?? 0;


    if(deductionA > deductionB){

        stronger = "A";

        compareReason =
        "风险等级相同，但项目A扣分更高";

    }

    else if(deductionB > deductionA){

        stronger = "B";

        compareReason =
        "风险等级相同，但项目B扣分更高";

    }

    else{

        stronger = "相同";

        compareReason =
        "风险等级和扣分均相同";

    }

}





    return {

        category,

        riskA: strongestA,

        riskB: strongestB,

        strengthA,

        strengthB,

        deductionA:
        strongestA?.deduction ?? 0,

        deductionB:
        strongestB?.deduction ?? 0,

        stronger,

        compareReason
    };

});


// ======================
// A独有风险
// ======================

const onlyACategories =
categoriesA.filter(
    category =>
    !categoriesB.includes(category)
);


// ======================
// B独有风险
// ======================

const onlyBCategories =
categoriesB.filter(
    category =>
    !categoriesA.includes(category)
);


// ======================
// 对应风险详情
// ======================

const commonRisks =
semanticRisksA.filter(
    risk =>
    commonCategories.includes(
        risk.category
    )
);


const onlyARisks =
semanticRisksA.filter(
    risk =>
    onlyACategories.includes(
        risk.category
    )
);


const onlyBRisks =
semanticRisksB.filter(
    risk =>
    onlyBCategories.includes(
        risk.category
    )
);


// ======================
// 推荐项目
// ======================

// ======================
// V2.4 综合推荐评分
// ======================

let decisionScoreA =
    projectA.score ?? 0;

let decisionScoreB =
    projectB.score ?? 0;


// ======================
// 1. 高风险数量惩罚
// ======================

const highPenaltyA =
    (projectA.high_count ?? 0) * 5;

const highPenaltyB =
    (projectB.high_count ?? 0) * 5;


decisionScoreA -= highPenaltyA;

decisionScoreB -= highPenaltyB;


// ======================
// 2. 独有高风险惩罚
// 每个独有高风险额外 -8
// ======================

const onlyAHighCount =
    onlyARisks.filter(
        risk =>
        risk.level?.includes("高")
    ).length;


const onlyBHighCount =
    onlyBRisks.filter(
        risk =>
        risk.level?.includes("高")
    ).length;


// ======================
// 2. 独有高风险惩罚
// ======================

const uniqueHighPenaltyA =
    onlyAHighCount * 8;

const uniqueHighPenaltyB =
    onlyBHighCount * 8;


decisionScoreA -= uniqueHighPenaltyA;

decisionScoreB -= uniqueHighPenaltyB;


// ======================
// 3. 共同风险强度惩罚
// ======================

let commonStrengthPenaltyA = 0;

let commonStrengthPenaltyB = 0;


riskStrengthCompare.forEach(
    item => {

        if(item.stronger === "A"){

            commonStrengthPenaltyA += 3;

        }

        else if(item.stronger === "B"){

            commonStrengthPenaltyB += 3;

        }

    }
);


decisionScoreA -=
    commonStrengthPenaltyA;

decisionScoreB -=
    commonStrengthPenaltyB;


// ======================
// 4. 最低不小于0
// ======================

decisionScoreA =
Math.max(
    decisionScoreA,
    0
);

decisionScoreB =
Math.max(
    decisionScoreB,
    0
);


// ======================
// 5. 最终推荐
// ======================

let recommended = "持平";

let recommendationReason = "";


if(
    decisionScoreA
    >
    decisionScoreB
){

    recommended = "A";

    recommendationReason =
        "项目A综合风险更低，优先推荐项目A";

}
else if(
    decisionScoreB
    >
    decisionScoreA
){

    recommended = "B";

    recommendationReason =
        "项目B综合风险更低，优先推荐项目B";

}

// ======================
// V2.6 推荐置信度
// ======================

const scoreDifference =
Math.abs(
    decisionScoreA
    -
    decisionScoreB
);


let confidenceLevel = "";

let confidenceText = "";

let confidenceColor = "default";


if(scoreDifference >= 20){

    confidenceLevel = "高置信";

    confidenceText =
        "两个项目综合风险差异明显，推荐结果可信度较高。";

    confidenceColor = "green";

}

else if(scoreDifference >= 10){

    confidenceLevel = "中高置信";

    confidenceText =
        "两个项目存在较明显差异，推荐结果具有较强参考价值。";

    confidenceColor = "blue";

}

else if(scoreDifference >= 5){

    confidenceLevel = "中等置信";

    confidenceText =
        "两个项目存在一定差异，建议结合利润空间、中标概率和资源投入进一步判断。";

    confidenceColor = "orange";

}

else if(scoreDifference > 0){

    confidenceLevel = "低置信";

    confidenceText =
        "两个项目综合风险非常接近，不建议仅根据当前评分做最终决策。";

    confidenceColor = "gold";

}

else{

    confidenceLevel = "持平";

    confidenceText =
        "两个项目综合指数相同，建议重点比较商务条件、利润空间和企业资源匹配度。";

    confidenceColor = "default";

}

if(scoreDifference < 5){

    recommended = "持平";

    recommendationReason =
        "两个项目综合指数差距较小，当前无法形成明显推荐。";

}

    setCompareResult({

          projectA,

          projectB,

          commonRisks,

          onlyARisks,

         onlyBRisks,

         commonCategories,

          onlyACategories,

          onlyBCategories,

          riskStrengthCompare,

          recommended,
            recommendationReason,
            decisionScoreA,
            decisionScoreB,

           baseScoreA:
            projectA.score ?? 0,

            baseScoreB:
            projectB.score ?? 0,

            highPenaltyA,
           highPenaltyB,

           uniqueHighPenaltyA,
          uniqueHighPenaltyB,

          commonStrengthPenaltyA,
          commonStrengthPenaltyB,

          scoreDifference,
           confidenceLevel,
          confidenceText,
          confidenceColor,

            onlyAHighCount,
            onlyBHighCount


        });

// ======================
// V2.2 AI决策摘要
// ======================

setAiDecisionLoading(true);

try{

    const aiRes = await apiClient.post(

        "/api/compare/ai-decision",

        {

            projectA,
            projectB,

            commonRisks,
            onlyARisks,
            onlyBRisks,

            commonCategories,
            onlyACategories,
            onlyBCategories,

            riskStrengthCompare,

            recommended,
            recommendationReason,

            decisionScoreA,
            decisionScoreB,

            scoreDifference,
            confidenceLevel

        }

    );


if(aiRes.data.success){

    const decision =
        aiRes.data.ai_decision;


    setAiDecision(
        decision
    );


    // ======================
    // 同步写入 compareResult
    // ======================

    setCompareResult(
        prev => ({

            ...prev,

            aiDecision:
            decision

        })
    );


}

    else{

        message.warning(
            "项目对比完成，但AI决策摘要生成失败"
        );

    }

}

catch{
    message.warning(
        "项目对比完成，但AI决策摘要暂未生成"
    );

}

finally{

    setAiDecisionLoading(false);

}

        message.success(
            "项目对比完成"
        );

    }

    catch{

        message.error(
            "项目对比失败"
        );

    }

    finally{

        setCompareLoading(false);

    }

}

// ======================
// 导出项目对比报告
// ======================

async function exportCompareReport(){

    if(!compareResult){

        message.warning(
            "请先完成项目对比"
        );

        return;

    }


    try{

        const res = await apiClient.post(

            "/api/compare-report",

            {
                 ...compareResult,

                 aiDecision:
                 aiDecision
                 ||
                 compareResult.aiDecision
                 ||
                 null
            },

            {
                responseType:"blob"
            }

        );


        const url =
        window.URL.createObjectURL(
            new Blob([res.data])
        );


        const link =
        document.createElement("a");


        link.href = url;

        link.download =
        "AI投标项目对比分析报告.docx";


        document.body.appendChild(
            link
        );


        link.click();


        link.remove();


        window.URL.revokeObjectURL(
            url
        );


        message.success(
            "项目对比报告导出成功"
        );

    }

    catch{

        message.error(
            "项目对比报告导出失败"
        );

    }

}

// ======================
// 历史文件搜索 + 风险筛选
// ======================

const filteredFiles = files.filter((item)=>{

    const keyword = searchText
        .trim()
        .toLowerCase();


    // ======================
    // 搜索条件
    // ======================

    const filename = String(
        item.filename || ""
    ).toLowerCase();


    const projectName = String(
        item.project_name || ""
    ).toLowerCase();


    const matchSearch =
        !keyword
        ||
        filename.includes(keyword)
        ||
        projectName.includes(keyword);


    // ======================
    // 风险等级条件
    // ======================

    const itemRiskLevel = String(
        item.score_level || ""
    );


    const matchRisk =
        riskFilter === "全部"
        ||
        itemRiskLevel === riskFilter;


    // 两个条件必须同时满足

    return (
        matchSearch
        &&
        matchRisk
    );

});


// ======================
// Dashboard V2.2
// 风险等级环形图
// ======================

const riskChartOption = {

    tooltip:{
        trigger:"item"
    },

    legend:{
        bottom:0
    },

    series:[
        {
            name:"风险等级",

            type:"pie",

            radius:[
                "55%",
                "75%"
            ],

            label:{
                show:true,
                formatter:"{b}\n{c}项"
            },

            data:[
                {
                    value:
                        dashboard?.risk_distribution?.high ?? 0,

                    name:"高风险",

                    itemStyle:{
                        color:"#ff4d4f"
                    }
                },

                {
                    value:
                        dashboard?.risk_distribution?.middle ?? 0,

                    name:"中风险",

                    itemStyle:{
                        color:"#fa8c16"
                    }
                },

                {
                    value:
                        dashboard?.risk_distribution?.low ?? 0,

                    name:"低风险",

                    itemStyle:{
                        color:"#52c41a"
                    }
                }
            ]
        }
    ]

};

// ======================
// Dashboard V2.3
// 最近7天项目分析趋势
// ======================

const analysisTrendOption = {

    tooltip:{
        trigger:"axis"
    },

    grid:{
        left:45,
        right:20,
        top:35,
        bottom:45
    },

    xAxis:{
        type:"category",

        data:
        (dashboard?.analysis_trend || []).map(
            item =>
            item.date.slice(5)
        )
    },

    yAxis:{
        type:"value",
        minInterval:1
    },

    series:[
        {
            name:"分析项目数",

            type:"line",

            smooth:true,

            symbolSize:8,

            data:
            (dashboard?.analysis_trend || []).map(
                item =>
                item.project_count
            ),

            itemStyle:{
                color:"#1677ff"
            },

            lineStyle:{
                width:3
            },

            areaStyle:{
                opacity:0.12
            },

            label:{
                show:true,
                position:"top"
            }
        }
    ]

};



// ======================
// Dashboard V2.2
// 项目评分分布柱状图
// ======================

const scoreChartOption = {

    tooltip:{
        trigger:"axis"
    },

    grid:{
        left:40,
        right:20,
        top:30,
        bottom:40
    },

    xAxis:{
        type:"category",

        data:[
            "0-39",
            "40-59",
            "60-79",
            "80-100"
        ],

        axisTick:{
            alignWithLabel:true
        }
    },

    yAxis:{
        type:"value",

        minInterval:1
    },

    series:[
        {
            name:"项目数量",

            type:"bar",

            barWidth:"45%",

            data:[
                {
                    value:
                        dashboard?.score_distribution?.["0_39"] ?? 0,

                    itemStyle:{
                        color:"#ff4d4f"
                    }
                },

                {
                    value:
                        dashboard?.score_distribution?.["40_59"] ?? 0,

                    itemStyle:{
                        color:"#fa8c16"
                    }
                },

                {
                    value:
                        dashboard?.score_distribution?.["60_79"] ?? 0,

                    itemStyle:{
                        color:"#1677ff"
                    }
                },

                {
                    value:
                        dashboard?.score_distribution?.["80_100"] ?? 0,

                    itemStyle:{
                        color:"#52c41a"
                    }
                }
            ],

            label:{
                show:true,
                position:"top",
                formatter:"{c}个"
            }
        }
    ]

};

// ======================
// Dashboard V2.3
// 最近7天风险趋势
// ======================

const riskTrendOption = {

    tooltip:{
        trigger:"axis",
        axisPointer:{
            type:"shadow"
        }
    },

    legend:{
        top:0
    },

    grid:{
        left:45,
        right:20,
        top:50,
        bottom:45
    },

    xAxis:{
        type:"category",

        data:
        (dashboard?.analysis_trend || []).map(
            item =>
            item.date.slice(5)
        ),
        axisLabel:{
           interval:
                trendDays === 30
                ? 4
                : 0
}

    },

    yAxis:{
        type:"value",
        minInterval:1
    },

    series:[
        {
            name:"高风险",
            type:"bar",
            stack:"risk",

            data:
            (dashboard?.analysis_trend || []).map(
                item =>
                item.high_risk_count
            ),

            itemStyle:{
                color:"#ff4d4f"
            }
        },

        {
            name:"中风险",
            type:"bar",
            stack:"risk",

            data:
            (dashboard?.analysis_trend || []).map(
                item =>
                item.middle_risk_count
            ),

            itemStyle:{
                color:"#fa8c16"
            }
        },

        {
            name:"低风险",
            type:"bar",
            stack:"risk",

            data:
            (dashboard?.analysis_trend || []).map(
                item =>
                item.low_risk_count
            ),

            itemStyle:{
                color:"#52c41a"
            }
        }
    ]

};


// ======================
// Dashboard V2.4.1
// 周期变化文案
// ======================

function formatPeriodChange(
    current,
    previous,
    percent,
    unit
){

    if(previous === 0){

        if(current === 0){

            return {
                text:`较前${trendDays}天：无变化`,
                color:"#999"
            };

        }

        return {
            text:`较前${trendDays}天：新增 ${current}${unit}`,
            color:"#1677ff"
        };

    }


    if(percent > 0){

        return {
            text:`较前${trendDays}天 ↑ ${Math.abs(percent)}%`,
            color:"#ff4d4f"
        };

    }


    if(percent < 0){

        return {
            text:`较前${trendDays}天 ↓ ${Math.abs(percent)}%`,
            color:"#52c41a"
        };

    }


    return {
        text:`较前${trendDays}天 → 0%`,
        color:"#999"
    };

}


// 项目分析量：增加通常不是坏事
function formatProjectChange(
    current,
    previous,
    percent
){

    const result = formatPeriodChange(
        current,
        previous,
        percent,
        "个"
    );


    if(
        previous > 0
        &&
        percent > 0
    ){

        result.color = "#52c41a";

    }

    return result;

}



const projectChangeDisplay =
formatProjectChange(

    dashboard?.period_comparison
        ?.current_projects ?? 0,

    dashboard?.period_comparison
        ?.previous_projects ?? 0,

    dashboard?.period_comparison
        ?.project_change_percent ?? 0

);


const highRiskChangeDisplay =
formatPeriodChange(

    dashboard?.period_comparison
        ?.current_high_risks ?? 0,

    dashboard?.period_comparison
        ?.previous_high_risks ?? 0,

    dashboard?.period_comparison
        ?.high_risk_change_percent ?? 0,

    "项"

);

// ======================
// Dashboard V2.6
// AI 管理预警颜色配置
// ======================

const alertLevelConfig = {

    red:{
        background:"#fff1f0",
        border:"#ff4d4f",
        color:"#cf1322",
        label:"高预警"
    },

    orange:{
        background:"#fff7e6",
        border:"#fa8c16",
        color:"#d46b08",
        label:"重点关注"
    },

    yellow:{
        background:"#fffbe6",
        border:"#fadb14",
        color:"#ad8b00",
        label:"一般预警"
    },

    green:{
        background:"#f6ffed",
        border:"#52c41a",
        color:"#389e0d",
        label:"正常"
    }

};


// ======================
// 当前管理预警数据
// ======================

const managementAlert =
    dashboard?.management_alert
    ||
    null;


// ======================
// 当前预警样式
// ======================

const currentAlertConfig =
    alertLevelConfig[
        managementAlert?.alert_level
    ]
    ||
    alertLevelConfig.green;


// ⭐ 页面真正的主 return
return (


<Layout

className="app-shell"

style={{

height:"100vh"

}}

>





{/* ==================
左侧文件
================== */}


<Sider
    className={`app-left-sider ${leftCollapsed ? "is-collapsed" : ""}`}
    width={
        leftCollapsed
            ? 56
            : 280
    }
    theme="light"
    style={{
        padding:leftCollapsed ? 8 : 16,
        background:"#f7f9fc",
        borderRight:"1px solid #e8e8e8",
        overflow:"auto",
        transition:"all 0.25s ease"
    }}
>

    {/* ==============================
        项目中心标题
    ============================== */}

{/* ==============================
    项目中心标题 + 收起按钮
============================== */}

<div
    style={{
        display:"flex",
        flexDirection:
            leftCollapsed
                ? "column"
                : "row",
        justifyContent:
            leftCollapsed
                ? "center"
                : "space-between",
        alignItems:"center",
        gap:8,
        marginBottom:leftCollapsed ? 0 : 18
    }}
>

    {
        !leftCollapsed
        &&
        (
            <div
                style={{
                    display:"flex",
                    alignItems:"center",
                    gap:8,
                    minWidth:0
                }}
            >

                <div
                    style={{
                        width:34,
                        height:34,
                        borderRadius:9,
                        background:"#e6f4ff",
                        display:"flex",
                        alignItems:"center",
                        justifyContent:"center",
                        fontSize:17,
                        flexShrink:0
                    }}
                >
                    📁
                </div>


                <div>

                    <div
                        style={{
                            fontSize:17,
                            fontWeight:700,
                            color:"#262626"
                        }}
                    >
                        项目中心
                    </div>

                    <div
                        style={{
                            marginTop:2,
                            fontSize:11,
                            color:"#8c8c8c"
                        }}
                    >
                        招标项目与历史分析
                    </div>

                </div>

            </div>
        )
    }


    <Button
        type="text"
        size="small"
        title={
            leftCollapsed
                ? "展开项目中心"
                : "收起项目中心"
        }
        onClick={()=>{
            setLeftCollapsed(
                !leftCollapsed
            );
        }}
        style={{
            width:32,
            height:32,
            padding:0,
            borderRadius:8,
            fontWeight:700,
            color:"#1677ff",
            background:
                leftCollapsed
                    ? "#e6f4ff"
                    : "transparent"
        }}
    >
        {
            leftCollapsed
                ? "▶"
                : "◀"
        }
    </Button>

</div>





    {/* ==============================
        搜索
    ============================== */}

<div
    style={{
        display:
            leftCollapsed
                ? "none"
                : "block"
    }}
>


    <Input.Search
        placeholder="搜索项目名称 / 文件名"
        allowClear
        value={searchText}
        onChange={(e)=>{

            setSearchText(
                e.target.value
            );

        }}
        style={{
            marginBottom:12
        }}
    />



    {/* ==============================
        风险筛选
    ============================== */}

    <Select
        value={riskFilter}
        onChange={(value)=>{

            setRiskFilter(value);

        }}
        style={{
            width:"100%",
            marginBottom:16
        }}
        options={[

            {
                value:"全部",
                label:"全部风险等级"
            },

            {
                value:"低风险",
                label:"🟢 低风险"
            },

            {
                value:"中低风险",
                label:"🟡 中低风险"
            },

            {
                value:"中风险",
                label:"🟠 中风险"
            },

            {
                value:"高风险",
                label:"🔴 高风险"
            },

            {
                value:"极高风险",
                label:"⛔ 极高风险"
            }

        ]}
    />



    {/* ==============================
        项目列表
    ============================== */}

    {
        filesError &&
        <Alert
            className="app-inline-alert"
            type="error"
            showIcon
            title={filesError}
            closable
            onClose={()=>setFilesError("")}
        />
    }

    {
        filteredFiles.length === 0
            ? <EmptyState description="暂无项目记录" />
            : (
                <div role="list" aria-label="项目列表">
                    {filteredFiles.map((item)=>(

            <Card
                key={item.id}
                role="listitem"
                hoverable
                onClick={()=>{
                    if(showWorkbench){
                        loadWorkbench(item);
                    }
                    else{
                        selectFile(item);
                    }
                }}
                style={{
                    marginBottom:12,
                    cursor:"pointer",
                    borderRadius:10,

                    border:
                        currentFile?.id === item.id
                            ? "1px solid #1677ff"
                            : "1px solid #e8e8e8",

                    background:
                        currentFile?.id === item.id
                            ? "#f0f7ff"
                            : "#ffffff",

                    boxShadow:
                        currentFile?.id === item.id
                            ? "0 3px 12px rgba(22,119,255,0.12)"
                            : "0 2px 8px rgba(0,0,0,0.035)"
                }}
                styles={{
                    body:{
                        padding:14
                    }
                }}
            >

                {/* ==============================
                    项目名称
                ============================== */}

                <div
                    style={{
                        display:"flex",
                        alignItems:"flex-start",
                        gap:8
                    }}
                >

                    <div
                        style={{
                            flexShrink:0,
                            marginTop:1,
                            fontSize:16
                        }}
                    >
                        📄
                    </div>


                    <div
                        style={{
                            minWidth:0,
                            flex:1
                        }}
                    >

                        <div
                            title={
                                item.project_name
                                ||
                                item.filename
                            }
                            style={{
                                fontSize:14,
                                fontWeight:650,
                                color:"#262626",
                                lineHeight:1.55,
                                display:"-webkit-box",
                                WebkitLineClamp:2,
                                WebkitBoxOrient:"vertical",
                                overflow:"hidden"
                            }}
                        >
                            {
                                item.project_name
                                ||
                                item.filename
                            }
                        </div>


                        {
                            item.project_name
                            &&
                            item.filename
                            &&
                            (
                                <div
                                    style={{
                                        marginTop:3,
                                        color:"#8c8c8c",
                                        fontSize:11,
                                        whiteSpace:"nowrap",
                                        overflow:"hidden",
                                        textOverflow:"ellipsis"
                                    }}
                                >
                                    {item.filename}
                                </div>
                            )
                        }

                    </div>

                </div>



                {/* ==============================
                    评分与风险
                ============================== */}

                <div
                    style={{
                        display:"flex",
                        alignItems:"center",
                        gap:6,
                        flexWrap:"wrap",
                        marginTop:12
                    }}
                >

                    <Tag
                        color={
                            (item.score ?? 0) >= 70
                                ? "green"
                                :
                            (item.score ?? 0) >= 40
                                ? "orange"
                                :
                                "red"
                        }
                        style={{
                            margin:0
                        }}
                    >
                        评分 {item.score ?? 0} 分
                    </Tag>


                    <Tag
                        color={
                            (item.risk_count ?? 0) > 0
                                ? "red"
                                : "green"
                        }
                        style={{
                            margin:0
                        }}
                    >
                        风险 {item.risk_count ?? 0} 项
                    </Tag>

                </div>



                {/* ==============================
                    主要操作
                ============================== */}

                <div
                    style={{
                        display:"grid",
                        gridTemplateColumns:"1fr 1fr",
                        gap:8,
                        marginTop:12
                    }}
                >

                    <Button
                        size="small"
                        type="primary"
                        ghost
                        onClick={(e)=>{

                            e.stopPropagation();
                            setShowDashboard(false);
                            setShowWorkbench(false);
                            selectFile(item);

                        }}
                    >
                        查看分析
                    </Button>


                    <Button
                        size="small"
                        type={
                            compareFiles.some(
                                file => file.id === item.id
                            )
                                ? "primary"
                                : "default"
                        }
                        onClick={(e)=>{

                            e.stopPropagation();

                            toggleCompare(item);

                        }}
                    >
                        {
                            compareFiles.some(
                                file => file.id === item.id
                            )
                                ? "✓ 已加入对比"
                                : "＋ 加入对比"
                        }
                    </Button>

                </div>



                {/* ==============================
                    次要操作
                ============================== */}

                <div
                    style={{
                        display:"flex",
                        alignItems:"center",
                        justifyContent:"flex-end",
                        gap:4,
                        marginTop:8,
                        paddingTop:8,
                        borderTop:"1px solid #f0f0f0"
                    }}
                >

                    {/* 只删除数据库记录 */}
                    <Popconfirm
                        title="仅删除历史记录？"
                        description="原始 PDF / DOCX 文件会保留在服务器中"
                        okText="确认删除"
                        cancelText="取消"
                        onConfirm={(e)=>{

                            e?.stopPropagation();

                            deleteFile(
                                item.id,
                                false
                            );

                        }}
                    >

                        <Button
                            type="text"
                            size="small"
                            onClick={(e)=>{
                                e.stopPropagation();
                            }}
                            style={{
                                color:"#8c8c8c",
                                fontSize:12,
                                padding:"0 5px"
                            }}
                        >
                            删除记录
                        </Button>

                    </Popconfirm>



                    {/* 删除数据库记录 + 原文件 */}
                    <Popconfirm
                        title="删除历史记录和原文件？"
                        description="原始 PDF / DOCX 也会永久删除，无法恢复"
                        okText="全部删除"
                        cancelText="取消"
                        okButtonProps={{
                            danger:true
                        }}
                        onConfirm={(e)=>{

                            e?.stopPropagation();

                            deleteFile(
                                item.id,
                                true
                            );

                        }}
                    >

                        <Button
                            type="text"
                            danger
                            size="small"
                            onClick={(e)=>{
                                e.stopPropagation();
                            }}
                            style={{
                                fontSize:12,
                                padding:"0 5px"
                            }}
                        >
                            删除文件
                        </Button>

                    </Popconfirm>

                </div>

            </Card>

                    ))}
                </div>
            )
    }

</div>

</Sider>




<Layout className="app-main-layout">






{/* ==================
顶部
================== */}


<Header
    className="app-header"
    style={{
        height:72,
        background:"#ffffff",
        display:"flex",
        justifyContent:"space-between",
        alignItems:"center",
        padding:"0 28px",
        borderBottom:"1px solid #f0f0f0",
        boxShadow:"0 2px 10px rgba(0,0,0,0.04)",
        position:"relative",
        zIndex:10
    }}
>

    {/* ==============================
        左侧：品牌区域
    ============================== */}

    <div
        className="app-brand"
        style={{
            display:"flex",
            alignItems:"center",
            gap:12
        }}
    >

        {/* Logo */}
        <div
            style={{
                width:42,
                height:42,
                borderRadius:10,
                background:"linear-gradient(135deg, #1677ff 0%, #4096ff 100%)",
                display:"flex",
                alignItems:"center",
                justifyContent:"center",
                color:"#ffffff",
                fontSize:18,
                fontWeight:700,
                boxShadow:"0 4px 12px rgba(22,119,255,0.22)"
            }}
        >
            AI
        </div>


        {/* 产品名称 */}
        <div className="app-brand-copy">

            <div
                className="app-brand-subtitle"
                style={{
                    fontSize:20,
                    fontWeight:700,
                    color:"#1f1f1f",
                    lineHeight:1.25,
                    letterSpacing:"0.2px"
                }}
            >
                AI 标书助手
            </div>

            <div
                style={{
                    marginTop:3,
                    fontSize:12,
                    color:"#8c8c8c",
                    lineHeight:1
                }}
            >
                智能投标决策平台
            </div>

        </div>

    </div>


    {/* ==============================
        右侧：导航
    ============================== */}

    <div style={{display:"flex",alignItems:"center",gap:10}}>
    <Button
        onClick={()=>{
            setCredentialError("");
            setCredentialOpen(true);
        }}
    >
        {credentialConfigured ? "访问凭据已启用" : "设置访问凭据"}
    </Button>

    <div
        className="app-nav"
        style={{
            display:"flex",
            alignItems:"center",
            gap:6,
            padding:4,
            background:"#f5f7fa",
            borderRadius:10
        }}
    >

        <Button
            type="text"
            onClick={()=>{
                setShowDashboard(true);
                setShowWorkbench(false);
            }}
            style={{
                height:38,
                padding:"0 18px",
                borderRadius:8,
                border:"none",
                fontWeight:showDashboard ? 600 : 400,

                color:
                    showDashboard
                    ? "#1677ff"
                    : "#595959",

                background:
                    showDashboard
                    ? "#ffffff"
                    : "transparent",

                boxShadow:
                    showDashboard
                    ? "0 2px 8px rgba(0,0,0,0.08)"
                    : "none"
            }}
        >
            <DashboardOutlined />
            <span className="app-nav-label">管理驾驶舱</span>
        </Button>


        <Button
            type="text"
            onClick={()=>{
                setShowDashboard(false);
                setShowWorkbench(false);
            }}
            style={{
                height:38,
                padding:"0 18px",
                borderRadius:8,
                border:"none",
                fontWeight:!showDashboard && !showWorkbench ? 600 : 400,

                color:
                    !showDashboard && !showWorkbench
                    ? "#1677ff"
                    : "#595959",

                background:
                    !showDashboard && !showWorkbench
                    ? "#ffffff"
                    : "transparent",

                boxShadow:
                    !showDashboard && !showWorkbench
                    ? "0 2px 8px rgba(0,0,0,0.08)"
                    : "none"
            }}
        >
            <FileSearchOutlined />
            <span className="app-nav-label">标书分析</span>
        </Button>

        <Button
            type="text"
            onClick={()=>{
                setShowDashboard(false);
                setShowWorkbench(true);
                loadWorkbench();
            }}
            style={{
                height:38,
                padding:"0 18px",
                borderRadius:8,
                border:"none",
                fontWeight:showWorkbench ? 600 : 400,
                color:showWorkbench ? "#1677ff" : "#595959",
                background:showWorkbench ? "#ffffff" : "transparent",
                boxShadow:showWorkbench ? "0 2px 8px rgba(0,0,0,0.08)" : "none"
            }}
        >
            <ProjectOutlined />
            <span className="app-nav-label">智能编标</span>
        </Button>

    </div>
    </div>

</Header>

<Modal
    title="部署访问凭据"
    open={credentialOpen}
    okText="在当前页面启用"
    cancelText="取消"
    onOk={saveAccessCredential}
    onCancel={()=>{
        setCredentialDraft("");
        setCredentialError("");
        setCredentialOpen(false);
    }}
    destroyOnHidden
>
    <Alert
        type="info"
        showIcon
        message="凭据仅保存在当前页面内存中"
        description="不会写入源码、URL 或 localStorage；刷新或关闭页面后需要重新输入。"
        style={{marginBottom:16}}
    />
    <Input.Password
        value={credentialDraft}
        autoComplete="off"
        placeholder="输入部署管理员提供的访问密钥"
        onChange={(event)=>{
            setCredentialDraft(event.target.value);
            setCredentialError("");
        }}
        onPressEnter={saveAccessCredential}
        status={credentialError ? "error" : ""}
    />
    {credentialError && (
        <Typography.Text type="danger">{credentialError}</Typography.Text>
    )}
    {credentialConfigured && (
        <Button danger type="link" onClick={removeAccessCredential} style={{paddingLeft:0}}>
            清除当前页面凭据
        </Button>
    )}
</Modal>

<Modal
    title={mappingDraft ? `设置评分点映射：${mappingDraft.criterion_title}` : "设置评分点映射"}
    open={mappingEditorOpen}
    okText="保存映射"
    cancelText="取消"
    confirmLoading={mappingSaving}
    onOk={saveMappingEditor}
    onCancel={closeMappingEditor}
    destroyOnHidden
>
    {mappingDraft && (
        <div className="material-editor-fields">
            <label>
                <span>已确认目录章节</span>
                <Select
                    value={mappingDraft.section_id}
                    placeholder="选择响应章节"
                    onChange={selectMappingSection}
                    options={(workbench?.sections || [])
                        .filter((section)=>section.review_status === "confirmed")
                        .map((section)=>({value:section.id, label:section.title}))}
                />
            </label>
            <label>
                <span>人工映射说明</span>
                <Input.TextArea
                    value={mappingDraft.rationale}
                    maxLength={2000}
                    autoSize={{minRows:3, maxRows:6}}
                    placeholder="说明该章节如何响应评分点（可选）"
                    onChange={(event)=>setMappingDraft({...mappingDraft, rationale:event.target.value})}
                />
            </label>
            <Alert
                type="info"
                showIcon
                title="当前操作只新增或更新所选关系"
                description="不会删除其他已有映射，也不会由AI自动选择章节。"
            />
        </div>
    )}
</Modal>

<Modal
    title="新增目录章节"
    open={sectionEditorOpen}
    okText="新增"
    cancelText="取消"
    confirmLoading={sectionSaving}
    onOk={saveSectionEditor}
    onCancel={closeSectionEditor}
    destroyOnHidden
>
    <Typography.Text type="secondary">
        当前仅新增顶级人工章节；创建后可用于评分点映射。
    </Typography.Text>
    <Input
        value={sectionTitleDraft}
        maxLength={200}
        showCount
        autoFocus
        placeholder="例如：技术响应方案"
        onChange={(event)=>setSectionTitleDraft(event.target.value)}
        onPressEnter={saveSectionEditor}
        style={{marginTop:12}}
    />
</Modal>

<Modal
    title={materialDraft?.id ? `编辑响应材料：${materialDraft.title}` : "新增响应材料"}
    open={materialEditorOpen}
    okText="保存"
    cancelText="取消"
    confirmLoading={materialSaving}
    onOk={saveMaterialEditor}
    onCancel={closeMaterialEditor}
    destroyOnHidden
>
    {materialDraft && (
        <div className="material-editor-fields">
            {!materialDraft.id && (
                <>
                    <label>
                        <span>材料名称</span>
                        <Input
                            value={materialDraft.title}
                            maxLength={200}
                            showCount
                            autoFocus
                            placeholder="例如：营业执照复印件"
                            onChange={(event)=>setMaterialDraft({...materialDraft, title:event.target.value})}
                        />
                    </label>
                    <label>
                        <span>关联评分点（可选）</span>
                        <Select
                            allowClear
                            value={materialDraft.criterion_id}
                            placeholder="选择已确认评分点"
                            onChange={(value)=>setMaterialDraft({...materialDraft, criterion_id:value})}
                            options={(workbench?.criteria || [])
                                .filter((criterion)=>criterion.review_status === "confirmed")
                                .map((criterion)=>({value:criterion.id, label:criterion.title}))}
                        />
                    </label>
                    <label>
                        <span>关联目录章节（可选）</span>
                        <Select
                            allowClear
                            value={materialDraft.section_id}
                            placeholder="选择已确认目录章节"
                            onChange={(value)=>setMaterialDraft({...materialDraft, section_id:value})}
                            options={(workbench?.sections || [])
                                .filter((section)=>section.review_status === "confirmed")
                                .map((section)=>({value:section.id, label:section.title}))}
                        />
                    </label>
                </>
            )}
            <label>
                <span>材料状态</span>
                <Select
                    value={materialDraft.material_status}
                    onChange={(value)=>setMaterialDraft({...materialDraft, material_status:value})}
                    options={[
                        {value:"pending", label:"待准备"},
                        {value:"in_progress", label:"进行中"},
                        {value:"completed", label:"已完成"},
                        {value:"blocked", label:"阻塞"}
                    ]}
                />
            </label>
            <label>
                <span>责任人</span>
                <Input
                    value={materialDraft.owner_name}
                    maxLength={200}
                    placeholder="人工填写；留空表示未指定"
                    onChange={(event)=>setMaterialDraft({...materialDraft, owner_name:event.target.value})}
                />
            </label>
            <label>
                <span>材料说明</span>
                <Input.TextArea
                    value={materialDraft.notes}
                    maxLength={4000}
                    autoSize={{minRows:3, maxRows:8}}
                    placeholder="填写准备要求、缺口或复核说明"
                    onChange={(event)=>setMaterialDraft({...materialDraft, notes:event.target.value})}
                />
            </label>
            <Alert
                type="info"
                showIcon
                title="材料信息均由人工维护"
                description="新增时至少关联一个已确认评分点或目录章节；系统不会自动分派人员或生成标书正文。"
            />
        </div>
    )}
</Modal>







<Content

className="app-content"

>

<div className="app-content-inner">

{showWorkbench ? (
    <Suspense fallback={<LoadingState text="正在加载智能编标工作台..." />}>
        <WorkbenchPage
            currentFile={currentFile}
            workspace={workbench}
            loading={workbenchLoading}
            aiLoading={workbenchAiLoading}
            reviewLoading={workbenchReviewLoading}
            error={workbenchError}
            onReload={()=>loadWorkbench()}
            onRunAi={runWorkbenchAi}
            onReview={reviewWorkbenchSuggestion}
            onEditMaterial={openMaterialEditor}
            onAddMaterial={openMaterialCreator}
            onAddSection={openSectionEditor}
            onMapCriterion={openMappingEditor}
        />
    </Suspense>
) : (
<>

{
    showDashboard
    ?

    <div className="dashboard-page">

        <Typography.Title
            level={2}
            className="page-title"
        >
            <DashboardOutlined />
            投标管理驾驶舱
        </Typography.Title>

        {
            dashboardError &&
            <Alert
                className="app-inline-alert"
                type="error"
                showIcon
                title={dashboardError}
                closable
                onClose={()=>setDashboardError("")}
            />
        }

{/*
======================
Dashboard V2.6
AI 管理预警
====================== */}

      <Card
    style={{
        marginBottom:20,
        background:
            currentAlertConfig.background,
        border:
            `1px solid ${currentAlertConfig.border}`
    }}
>

    <div
        style={{
            display:"flex",
            justifyContent:"space-between",
            alignItems:"center",
            marginBottom:12
        }}
    >

        <div
            style={{
                fontSize:18,
                fontWeight:"bold",
                color:
                    currentAlertConfig.color
            }}
        >
            🚨 AI 管理预警
        </div>


        <Tag
            color={
                managementAlert?.alert_level === "red"
                ? "red"
                :
                managementAlert?.alert_level === "orange"
                ? "orange"
                :
                managementAlert?.alert_level === "yellow"
                ? "gold"
                :
                "green"
            }
        >
            {
                currentAlertConfig.label
            }
        </Tag>

    </div>


    <div
        style={{
            fontSize:16,
            fontWeight:"bold",
            marginBottom:12
        }}
    >
        {
            managementAlert?.alert_title
            ||
            "当前暂无管理预警"
        }
    </div>


    {
        managementAlert?.alerts?.length
        ?
        (
            <div>

                {
                    managementAlert.alerts.map(
                        (alert,index)=>(
                            <div
                                key={
                                    alert.type
                                    ||
                                    index
                                }
                                style={{
                                    padding:"10px 12px",
                                    marginBottom:8,
                                    background:"#fff",
                                    borderRadius:6,
                                    borderLeft:
                                        alert.level === "high"
                                        ? "4px solid #ff4d4f"
                                        :
                                        alert.level === "medium"
                                        ? "4px solid #fa8c16"
                                        :
                                        "4px solid #fadb14"
                                }}
                            >

                                <div
                                    style={{
                                        fontWeight:"bold",
                                        marginBottom:4
                                    }}
                                >
                                    {
                                        alert.level === "high"
                                        ? "🔴 "
                                        :
                                        alert.level === "medium"
                                        ? "🟠 "
                                        :
                                        "🟡 "
                                    }

                                    {alert.title}
                                </div>


                                <div
                                    style={{
                                        color:"#666",
                                        lineHeight:1.7
                                    }}
                                >
                                    {alert.message}
                                </div>

                                {
                                    alert.action
                                    &&
                                    (
                                       <div
                                      style={{
                marginTop:10,
                padding:"10px 12px",
                background:"#fafafa",
                borderRadius:6
                                            }}
                                         >

                                         <div
                style={{
                    fontWeight:"bold",
                    marginBottom:4,
                    color:"#1677ff"
                }}
            >
                💡 建议处置
                                         </div>


                                         <div
                style={{
                    color:"#555",
                    lineHeight:1.7
                }}
            >
                {alert.action}
                                         </div>

                                         </div>
                                    )
                                }

                                    {
                                        alert.target_projects
                                        &&
                                        alert.target_projects.length > 0
                                        &&
                                        (
        <div
            style={{
                marginTop:10,
                padding:"10px 12px",
                background:"#ffffff",
                borderRadius:6,
                border:"1px solid #e8e8e8"
            }}
        >

            <div
                style={{
                    fontWeight:"bold",
                    marginBottom:8,
                    color:"#333"
                }}
            >
                📌 关联项目
            </div>


            {
                alert.target_projects.map(
                    (project) => (

                        <div
                            key={project.id}
                            onClick={() => openDashboardProject(project)}
                            style={{
                                padding:"10px 12px",
                                marginBottom:6,
                                border:"1px solid #f0f0f0",
                                borderRadius:6,
                                cursor:"pointer",
                                background:"#fafafa"
                            }}
                        >

                            <div
                                style={{
                                    fontWeight:"bold",
                                    marginBottom:8
                                }}
                            >
                                {
                                    project.project_name
                                    ||
                                    project.filename
                                }
                            </div>


                            <div
                                style={{
                                    display:"flex",
                                    alignItems:"center",
                                    gap:8,
                                    flexWrap:"wrap"
                                }}
                            >

                                <Tag color="blue">
                                    {project.score} 分
                                </Tag>

                                <Tag color="red">
                                    高风险 {project.high_count} 项
                                </Tag>

                                <Tag>
                                    风险 {project.risk_count} 项
                                </Tag>

                                <span
                                    style={{
                                        marginLeft:"auto",
                                        color:"#1677ff",
                                        fontWeight:500
                                    }}
                                >
                                    查看分析 →
                                </span>

                            </div>

                        </div>

                    )
                )
            }

        </div>
                                        )
                                    }


                            </div>
                        )
                    )
                }

            </div>
        )
        :
        (
            <div
                style={{
                    color:"#666"
                }}
            >
                当前没有需要特别处理的管理预警。
            </div>
        )
    }

     </Card>


       <div
    style={{
        display:"grid",
        gridTemplateColumns:"repeat(auto-fit, minmax(220px, 1fr))",
        gap:18,
        marginBottom:24
    }}
>

    {/* ==============================
        已分析项目
    ============================== */}

    <Card
        style={{
            borderRadius:12,
            border:"1px solid #e8eef8",
            boxShadow:"0 4px 16px rgba(0,0,0,0.05)",
            overflow:"hidden"
        }}
        styles={{
            body:{
                padding:20
            }
        }}
    >

        <div
            style={{
                display:"flex",
                justifyContent:"space-between",
                alignItems:"flex-start"
            }}
        >

            <div>

                <div
                    style={{
                        fontSize:14,
                        color:"#8c8c8c",
                        fontWeight:500
                    }}
                >
                    已分析项目
                </div>

                <div
                    style={{
                        fontSize:36,
                        lineHeight:1.2,
                        fontWeight:700,
                        color:"#1f1f1f",
                        marginTop:10
                    }}
                >
                    {
                        dashboard?.total_projects ?? 0
                    }
                </div>

            </div>


            <div
                style={{
                    width:44,
                    height:44,
                    borderRadius:12,
                    background:"#e6f4ff",
                    display:"flex",
                    justifyContent:"center",
                    alignItems:"center",
                    fontSize:21
                }}
            >
                📁
            </div>

        </div>


        <div
            style={{
                marginTop:14,
                paddingTop:12,
                borderTop:"1px solid #f0f0f0",
                fontSize:13,
                color:"#8c8c8c"
            }}
        >
            当前累计完成分析的招标项目
        </div>

    </Card>



    {/* ==============================
        高风险项目
    ============================== */}

    <Card
        style={{
            borderRadius:12,
            border:"1px solid #ffe1df",
            boxShadow:"0 4px 16px rgba(0,0,0,0.05)",
            overflow:"hidden"
        }}
        styles={{
            body:{
                padding:20
            }
        }}
    >

        <div
            style={{
                display:"flex",
                justifyContent:"space-between",
                alignItems:"flex-start"
            }}
        >

            <div>

                <div
                    style={{
                        fontSize:14,
                        color:"#8c8c8c",
                        fontWeight:500
                    }}
                >
                    高风险项目
                </div>

                <div
                    style={{
                        fontSize:36,
                        lineHeight:1.2,
                        fontWeight:700,
                        color:"#cf1322",
                        marginTop:10
                    }}
                >
                    {
                        dashboard?.high_risk_projects ?? 0
                    }
                </div>

            </div>


            <div
                style={{
                    width:44,
                    height:44,
                    borderRadius:12,
                    background:"#fff1f0",
                    display:"flex",
                    justifyContent:"center",
                    alignItems:"center",
                    fontSize:21
                }}
            >
                🚨
            </div>

        </div>


        <div
            style={{
                marginTop:14,
                paddingTop:12,
                borderTop:"1px solid #f0f0f0",
                fontSize:13,
                color:"#cf1322"
            }}
        >
            建议优先安排人工复核
        </div>

    </Card>



    {/* ==============================
        累计风险
    ============================== */}

    <Card
        style={{
            borderRadius:12,
            border:"1px solid #ffe7ba",
            boxShadow:"0 4px 16px rgba(0,0,0,0.05)",
            overflow:"hidden"
        }}
        styles={{
            body:{
                padding:20
            }
        }}
    >

        <div
            style={{
                display:"flex",
                justifyContent:"space-between",
                alignItems:"flex-start"
            }}
        >

            <div>

                <div
                    style={{
                        fontSize:14,
                        color:"#8c8c8c",
                        fontWeight:500
                    }}
                >
                    累计风险事项
                </div>

                <div
                    style={{
                        fontSize:36,
                        lineHeight:1.2,
                        fontWeight:700,
                        color:"#d46b08",
                        marginTop:10
                    }}
                >
                    {
                        dashboard?.total_risks ?? 0
                    }
                </div>

            </div>


            <div
                style={{
                    width:44,
                    height:44,
                    borderRadius:12,
                    background:"#fff7e6",
                    display:"flex",
                    justifyContent:"center",
                    alignItems:"center",
                    fontSize:21
                }}
            >
                ⚠️
            </div>

        </div>


        <div
            style={{
                marginTop:14,
                paddingTop:12,
                borderTop:"1px solid #f0f0f0",
                fontSize:13,
                color:"#8c8c8c"
            }}
        >
            AI 累计识别出的风险事项
        </div>

    </Card>



    {/* ==============================
        平均评分
    ============================== */}

    <Card
        style={{
            borderRadius:12,
            border:"1px solid #d9f7be",
            boxShadow:"0 4px 16px rgba(0,0,0,0.05)",
            overflow:"hidden"
        }}
        styles={{
            body:{
                padding:20
            }
        }}
    >

        <div
            style={{
                display:"flex",
                justifyContent:"space-between",
                alignItems:"flex-start"
            }}
        >

            <div>

                <div
                    style={{
                        fontSize:14,
                        color:"#8c8c8c",
                        fontWeight:500
                    }}
                >
                    平均评分
                </div>

                <div
                    style={{
                        fontSize:36,
                        lineHeight:1.2,
                        fontWeight:700,
                        marginTop:10,

                        color:
                            (dashboard?.average_score ?? 0) >= 70
                                ? "#389e0d"
                                :
                            (dashboard?.average_score ?? 0) >= 40
                                ? "#d46b08"
                                :
                                "#cf1322"
                    }}
                >
                    {
                        dashboard?.average_score ?? 0
                    }
                </div>

            </div>


            <div
                style={{
                    width:44,
                    height:44,
                    borderRadius:12,
                    background:"#f6ffed",
                    display:"flex",
                    justifyContent:"center",
                    alignItems:"center",
                    fontSize:21
                }}
            >
                📈
            </div>

        </div>


        <div
            style={{
                marginTop:14,
                paddingTop:12,
                borderTop:"1px solid #f0f0f0",
                fontSize:13,
                color:"#8c8c8c"
            }}
        >
            当前项目综合投标建议指数
        </div>

    </Card>

       </div>

        <div
            className="dashboard-chart-grid"
    style={{
        display:"grid",
        gridTemplateColumns:"1fr 1fr",
        gap:16,
        marginBottom:20
    }}
>

    {/* ======================
    风险等级分布
    ====================== */}

       <Card title="📊 风险等级分布">

       <AsyncDashboardChart
        option={riskChartOption}
        style={{
            height:300
        }}
        />

        </Card>

    {/*
    ======================
    项目评分分布
    ====================== */}

     <Card title="📈 项目评分分布">

     <AsyncDashboardChart
        option={scoreChartOption}
        style={{
            height:300
        }}
      />

     </Card>


        </div>


<Card
    style={{
        marginBottom:24,
        borderRadius:14,
        border:"1px solid #e8eef8",
        boxShadow:"0 4px 18px rgba(0,0,0,0.05)",
        overflow:"hidden"
    }}
    styles={{
        body:{
            padding:0
        }
    }}
>

    {/* ==============================
        顶部标题区域
    ============================== */}

    <div
        style={{
            padding:"18px 20px",
            borderBottom:"1px solid #f0f0f0",
            background:"linear-gradient(180deg, #fafcff 0%, #ffffff 100%)"
        }}
    >

        <div
            style={{
                display:"flex",
                justifyContent:"space-between",
                alignItems:"center",
                gap:16
            }}
        >

            <div
                style={{
                    display:"flex",
                    alignItems:"center",
                    gap:12
                }}
            >

                <div
                    style={{
                        width:42,
                        height:42,
                        borderRadius:10,
                        background:"#e6f4ff",
                        display:"flex",
                        alignItems:"center",
                        justifyContent:"center",
                        fontSize:20
                    }}
                >
                    🤖
                </div>


                <div>

                    <div
                        className="management-summary-grid"
                        style={{
                            fontSize:18,
                            fontWeight:700,
                            color:"#262626"
                        }}
                    >
                        AI 管理摘要
                    </div>

                    <div
                        style={{
                            marginTop:3,
                            fontSize:12,
                            color:"#8c8c8c"
                        }}
                    >
                        基于最近 {trendDays} 天项目、风险与评分数据生成管理判断
                    </div>

                </div>

            </div>


            {
                !aiManagementLoading
                &&
                aiManagementSummary
                &&
                (
                    <Tag
                        color="blue"
                        style={{
                            margin:0,
                            padding:"4px 10px",
                            borderRadius:6,
                            fontWeight:600
                        }}
                    >
                        AI 已分析
                    </Tag>
                )
            }

        </div>

    </div>



    {/* ==============================
        内容区域
    ============================== */}

    <div
        style={{
            padding:"20px"
        }}
    >

        {
            aiManagementLoading
            ?
            (
                <div
                    style={{
                        padding:"36px 20px",
                        textAlign:"center"
                    }}
                >

                    <Spin size="large" />

                    <div
                        style={{
                            marginTop:14,
                            color:"#8c8c8c",
                            fontSize:14
                        }}
                    >
                        AI 正在分析最近 {trendDays} 天管理数据...
                    </div>

                </div>
            )
            :
            aiManagementSummary
            ?
            (
                <div>

                    {/* ==============================
                        总体判断
                    ============================== */}

                    <div
                        style={{
                            padding:"16px 18px",
                            background:"#f7faff",
                            border:"1px solid #e6f4ff",
                            borderRadius:10,
                            marginBottom:16
                        }}
                    >

                        <div
                            style={{
                                display:"flex",
                                alignItems:"center",
                                gap:8,
                                fontSize:14,
                                fontWeight:700,
                                color:"#1677ff",
                                marginBottom:8
                            }}
                        >
                            📌 总体判断
                        </div>


                        <div
                            style={{
                                color:"#434343",
                                lineHeight:1.9,
                                fontSize:14
                            }}
                        >
                            {
                                aiManagementSummary.overall_status
                            }
                        </div>

                    </div>



                    {/* ==============================
                        风险变化 + 重点关注
                    ============================== */}

                    <div
                        style={{
                            display:"grid",
                            gridTemplateColumns:"repeat(auto-fit, minmax(280px, 1fr))",
                            gap:16,
                            marginBottom:16
                        }}
                    >

                        {/* 风险变化 */}
                        <div
                            style={{
                                padding:"16px",
                                border:"1px solid #f0f0f0",
                                borderRadius:10,
                                background:"#ffffff"
                            }}
                        >

                            <div
                                style={{
                                    display:"flex",
                                    alignItems:"center",
                                    gap:8,
                                    fontSize:14,
                                    fontWeight:700,
                                    color:"#262626",
                                    marginBottom:8
                                }}
                            >
                                📈 风险变化
                            </div>


                            <div
                                style={{
                                    color:"#595959",
                                    lineHeight:1.9,
                                    fontSize:14
                                }}
                            >
                                {
                                    aiManagementSummary.risk_change
                                }
                            </div>

                        </div>



                        {/* 重点关注 */}
                        <div
                            style={{
                                padding:"16px",
                                border:"1px solid #f0f0f0",
                                borderRadius:10,
                                background:"#ffffff"
                            }}
                        >

                            <div
                                style={{
                                    display:"flex",
                                    alignItems:"center",
                                    gap:8,
                                    fontSize:14,
                                    fontWeight:700,
                                    color:"#262626",
                                    marginBottom:8
                                }}
                            >
                                🎯 重点关注
                            </div>


                            <div
                                style={{
                                    color:"#595959",
                                    lineHeight:1.9,
                                    fontSize:14
                                }}
                            >
                                {
                                    aiManagementSummary.key_attention
                                }
                            </div>

                        </div>

                    </div>



                    {/* ==============================
                        管理建议
                    ============================== */}

                    <div
                        style={{
                            padding:"16px 18px",
                            background:"#f6ffed",
                            border:"1px solid #d9f7be",
                            borderRadius:10
                        }}
                    >

                        <div
                            style={{
                                display:"flex",
                                alignItems:"center",
                                gap:8,
                                fontSize:14,
                                fontWeight:700,
                                color:"#389e0d",
                                marginBottom:8
                            }}
                        >
                            💡 管理建议
                        </div>


                        <div
                            style={{
                                color:"#434343",
                                lineHeight:1.9,
                                fontSize:14
                            }}
                        >
                            {
                                aiManagementSummary.management_advice
                            }
                        </div>

                    </div>

                </div>
            )
            :
            (
                <div
                    style={{
                        padding:"32px 20px",
                        textAlign:"center"
                    }}
                >

                    <div
                        style={{
                            fontSize:28,
                            marginBottom:8
                        }}
                    >
                        🤖
                    </div>

                    <div
                        style={{
                            color:"#595959",
                            fontWeight:600,
                            marginBottom:4
                        }}
                    >
                        暂无 AI 管理摘要
                    </div>

                    <div
                        style={{
                            color:"#8c8c8c",
                            fontSize:13
                        }}
                    >
                        完成项目分析后，系统将自动生成管理判断
                    </div>

                </div>
            )
        }

    </div>

</Card>

        <div
    style={{
        display:"flex",
        justifyContent:"space-between",
        alignItems:"center",
        marginTop:20,
        marginBottom:12
    }}
>

    <Typography.Title
        level={4}
        className="section-title"
    >
        <LineChartOutlined />
        趋势分析
    </Typography.Title>


    <Segmented
        value={trendDays}
        options={[
            {
                label:"最近7天",
                value:7
            },
            {
                label:"最近30天",
                value:30
            }
        ]}
        onChange={(value)=>{
            setTrendDays(value);
        }}
    />

        </div>



{/* ======================
Dashboard V2.4
周期对比
====================== */}

<div
    className="dashboard-trend-grid"
    style={{
        marginTop:24,
        marginBottom:28
    }}
>

    {/* ==============================
        周期对比标题
    ============================== */}

    <div
        style={{
            display:"flex",
            justifyContent:"space-between",
            alignItems:"center",
            marginBottom:12
        }}
    >

        <div>

            <div
                style={{
                    fontSize:17,
                    fontWeight:700,
                    color:"#262626"
                }}
            >
                   周期经营对比
            </div>

            <div
                style={{
                    marginTop:3,
                    fontSize:12,
                    color:"#8c8c8c"
                }}
            >
                对比最近 {trendDays} 天与前 {trendDays} 天项目表现
            </div>

        </div>




    </div>



    {/* ==============================
        三项核心指标
    ============================== */}

    <div
        style={{
            display:"grid",
            gridTemplateColumns:"repeat(auto-fit, minmax(240px, 1fr))",
            gap:16
        }}
    >

        {/* ==============================
            项目分析量
        ============================== */}

        <Card
            style={{
                borderRadius:12,
                border:"1px solid #e8eef8",
                boxShadow:"0 3px 12px rgba(0,0,0,0.04)"
            }}
            styles={{
                body:{
                    padding:18
                }
            }}
        >

            <div
                style={{
                    display:"flex",
                    justifyContent:"space-between",
                    alignItems:"flex-start"
                }}
            >

                <div>

                    <div
                        style={{
                            fontSize:13,
                            color:"#8c8c8c",
                            fontWeight:500
                        }}
                    >
                        项目分析量
                    </div>


                    <div
                        style={{
                            marginTop:8,
                            display:"flex",
                            alignItems:"baseline",
                            gap:4
                        }}
                    >

                        <span
                            style={{
                                fontSize:30,
                                fontWeight:700,
                                color:"#262626"
                            }}
                        >
                            {
                                dashboard?.period_comparison
                                    ?.current_projects ?? 0
                            }
                        </span>


                        <span
                            style={{
                                fontSize:13,
                                color:"#8c8c8c"
                            }}
                        >
                            个
                        </span>

                    </div>

                </div>


                <div
                    style={{
                        width:40,
                        height:40,
                        borderRadius:10,
                        background:"#e6f4ff",
                        display:"flex",
                        justifyContent:"center",
                        alignItems:"center",
                        fontSize:19
                    }}
                >
                    📁
                </div>

            </div>


            <div
                style={{
                    marginTop:14,
                    paddingTop:12,
                    borderTop:"1px solid #f0f0f0",
                    fontSize:13,
                    fontWeight:500,
                    color:projectChangeDisplay.color
                }}
            >
                {projectChangeDisplay.text}
            </div>

        </Card>



        {/* ==============================
            高风险数量
        ============================== */}

        <Card
            style={{
                borderRadius:12,
                border:"1px solid #ffe1df",
                boxShadow:"0 3px 12px rgba(0,0,0,0.04)"
            }}
            styles={{
                body:{
                    padding:18
                }
            }}
        >

            <div
                style={{
                    display:"flex",
                    justifyContent:"space-between",
                    alignItems:"flex-start"
                }}
            >

                <div>

                    <div
                        style={{
                            fontSize:13,
                            color:"#8c8c8c",
                            fontWeight:500
                        }}
                    >
                        高风险事项
                    </div>


                    <div
                        style={{
                            marginTop:8,
                            display:"flex",
                            alignItems:"baseline",
                            gap:4
                        }}
                    >

                        <span
                            style={{
                                fontSize:30,
                                fontWeight:700,
                                color:"#cf1322"
                            }}
                        >
                            {
                                dashboard?.period_comparison
                                    ?.current_high_risks ?? 0
                            }
                        </span>


                        <span
                            style={{
                                fontSize:13,
                                color:"#8c8c8c"
                            }}
                        >
                            项
                        </span>

                    </div>

                </div>


                <div
                    style={{
                        width:40,
                        height:40,
                        borderRadius:10,
                        background:"#fff1f0",
                        display:"flex",
                        justifyContent:"center",
                        alignItems:"center",
                        fontSize:19
                    }}
                >
                    🚨
                </div>

            </div>


            <div
                style={{
                    marginTop:14,
                    paddingTop:12,
                    borderTop:"1px solid #f0f0f0",
                    fontSize:13,
                    fontWeight:500,
                    color:highRiskChangeDisplay.color
                }}
            >
                {highRiskChangeDisplay.text}
            </div>

        </Card>



        {/* ==============================
            周期平均评分
        ============================== */}

        <Card
            style={{
                borderRadius:12,
                border:"1px solid #d9f7be",
                boxShadow:"0 3px 12px rgba(0,0,0,0.04)"
            }}
            styles={{
                body:{
                    padding:18
                }
            }}
        >

            <div
                style={{
                    display:"flex",
                    justifyContent:"space-between",
                    alignItems:"flex-start"
                }}
            >

                <div>

                    <div
                        style={{
                            fontSize:13,
                            color:"#8c8c8c",
                            fontWeight:500
                        }}
                    >
                        周期平均评分
                    </div>


                    <div
                        style={{
                            marginTop:8,
                            display:"flex",
                            alignItems:"baseline",
                            gap:4
                        }}
                    >

                        <span
                            style={{
                                fontSize:30,
                                fontWeight:700,

                                color:
                                    (
                                        dashboard?.period_comparison
                                            ?.current_average_score ?? 0
                                    ) >= 70
                                        ? "#389e0d"
                                        :
                                    (
                                        dashboard?.period_comparison
                                            ?.current_average_score ?? 0
                                    ) >= 40
                                        ? "#d46b08"
                                        :
                                        "#cf1322"
                            }}
                        >
                            {
                                dashboard?.period_comparison
                                    ?.current_average_score ?? 0
                            }
                        </span>


                        <span
                            style={{
                                fontSize:13,
                                color:"#8c8c8c"
                            }}
                        >
                            分
                        </span>

                    </div>

                </div>


                <div
                    style={{
                        width:40,
                        height:40,
                        borderRadius:10,
                        background:"#f6ffed",
                        display:"flex",
                        justifyContent:"center",
                        alignItems:"center",
                        fontSize:19
                    }}
                >
                    ⭐
                </div>

            </div>


            <div
                style={{
                    marginTop:14,
                    paddingTop:12,
                    borderTop:"1px solid #f0f0f0",
                    fontSize:13,
                    fontWeight:500,

                    color:
                        (
                            dashboard?.period_comparison
                                ?.average_score_change ?? 0
                        ) > 0
                            ? "#389e0d"
                            :
                        (
                            dashboard?.period_comparison
                                ?.average_score_change ?? 0
                        ) < 0
                            ? "#cf1322"
                            :
                            "#8c8c8c"
                }}
            >

                {
                    (
                        dashboard?.period_comparison
                            ?.average_score_change ?? 0
                    ) > 0
                        ? "↑ "
                        :
                    (
                        dashboard?.period_comparison
                            ?.average_score_change ?? 0
                    ) < 0
                        ? "↓ "
                        :
                        "→ "
                }

                较前 {trendDays} 天

                {" "}

                {
                    Math.abs(
                        dashboard?.period_comparison
                            ?.average_score_change ?? 0
                    )
                }

                分

            </div>

        </Card>

    </div>

</div>



<div
    style={{
        display:"grid",
        gridTemplateColumns:"repeat(auto-fit, minmax(360px, 1fr))",
        gap:18,
        marginTop:18,
        marginBottom:24,
        width:"100%"
    }}
>

    {/* ==============================
        项目分析趋势
    ============================== */}

    <Card
        style={{
            width:"100%",
            borderRadius:14,
            border:"1px solid #e8eef8",
            boxShadow:"0 4px 16px rgba(0,0,0,0.045)",
            overflow:"hidden"
        }}
        styles={{
            body:{
                padding:"16px 18px 10px"
            }
        }}
        title={
            <div
                style={{
                    padding:"4px 0"
                }}
            >

                <div
                    style={{
                        display:"flex",
                        alignItems:"center",
                        gap:8,
                        fontSize:16,
                        fontWeight:700,
                        color:"#262626"
                    }}
                >
                    📈 项目分析趋势
                </div>

                <div
                    style={{
                        marginTop:3,
                        fontSize:12,
                        fontWeight:400,
                        color:"#8c8c8c"
                    }}
                >
                    最近 {trendDays} 天项目分析数量变化
                </div>

            </div>
        }
        extra={
            <Tag
                color="blue"
                style={{
                    margin:0,
                    borderRadius:6
                }}
            >
                {trendDays} 天
            </Tag>
        }
    >

        <AsyncDashboardChart
            option={analysisTrendOption}
            style={{
                height:300,
                width:"100%"
            }}
        />

    </Card>



    {/* ==============================
        风险趋势
    ============================== */}

    <Card
        style={{
            width:"100%",
            borderRadius:14,
            border:"1px solid #e8eef8",
            boxShadow:"0 4px 16px rgba(0,0,0,0.045)",
            overflow:"hidden"
        }}
        styles={{
            body:{
                padding:"16px 18px 10px"
            }
        }}
        title={
            <div
                style={{
                    padding:"4px 0"
                }}
            >

                <div
                    style={{
                        display:"flex",
                        alignItems:"center",
                        gap:8,
                        fontSize:16,
                        fontWeight:700,
                        color:"#262626"
                    }}
                >
                    📉 风险变化趋势
                </div>

                <div
                    style={{
                        marginTop:3,
                        fontSize:12,
                        fontWeight:400,
                        color:"#8c8c8c"
                    }}
                >
                    最近 {trendDays} 天高、中、低风险事项变化
                </div>

            </div>
        }
        extra={
            <Tag
                color="red"
                style={{
                    margin:0,
                    borderRadius:6
                }}
            >
                风险监测
            </Tag>
        }
    >

        <AsyncDashboardChart
            option={riskTrendOption}
            style={{
                height:300,
                width:"100%"
            }}
        />

    </Card>

</div>


<Card
    title="🕒 最近分析项目"
    style={{
        marginBottom:20
    }}
>

    {
        dashboardLoading
        ?

        <LoadingState text="正在加载最近分析项目..." />

        :

        dashboard?.recent_projects?.length
        ?

        dashboard.recent_projects.map(
            (item,index)=>(

                <div
                    className="dashboard-project-row"
                    key={item.id || index}
                    style={{
                        display:"grid",
                        gridTemplateColumns:"2fr 100px 100px 120px",
                        gap:12,
                        padding:"12px 0",
                        borderBottom:
                            index <
                            dashboard.recent_projects.length - 1
                            ?
                            "1px solid #eee"
                            :
                            "none",
                        alignItems:"center"
                    }}
                >

                    <div>

                        <b>
                            {
                                item.project_name
                                ||
                                item.filename
                            }
                        </b>

                        <div
                            style={{
                                color:"#999",
                                fontSize:12,
                                marginTop:4
                            }}
                        >
                            {item.filename}
                        </div>

                    </div>


                    <div>

                        <Tag
                            color={
                                (item.score ?? 0) >= 70
                                ? "green"
                                :
                                (item.score ?? 0) >= 40
                                ? "orange"
                                :
                                "red"
                            }
                        >
                            {item.score ?? 0}分
                        </Tag>

                    </div>


                    <div>

                        ⚠ {item.risk_count ?? 0} 项

                    </div>


                    <div
                        style={{
                            color:"#999",
                            fontSize:12
                        }}
                    >
                        {
                            item.created_time
                            ? item.created_time.slice(0,10)
                            : ""
                        }
                    </div>

<div>

    <Button
        type="link"
        onClick={()=>{
            openDashboardProject(item);
        }}
    >
        查看 →
    </Button>

</div>


                </div>

            )
        )

        :

        <EmptyState description="暂无最近分析项目" />
    }

</Card>



{/* ======================
Dashboard V1
重点关注项目
====================== */}

<Card
    title="🚨 重点关注项目"
    style={{
        marginBottom:20
    }}
>

    {
        dashboardLoading
        ?

        <LoadingState text="正在加载重点关注项目..." />

        :

        (
            dashboard?.attention_projects || []
            ).length > 0

           ?

        (
           dashboard?.attention_projects || []
        )
        .map(
            (item,index)=>(

                <div
                    className="dashboard-project-row"
                    key={item.id || index}
                    style={{
                        display:"grid",
                        gridTemplateColumns:
                            "2fr 100px 100px 130px",
                        gap:12,
                        padding:"14px 0",
                        borderBottom:"1px solid #eee",
                        alignItems:"center"
                    }}
                >

                    {/* 项目名称 */}

                    <div>

                        <div
                            style={{
                                fontWeight:"bold"
                            }}
                        >
                            {
                                item.project_name
                                ||
                                item.filename
                            }
                        </div>

                        <div
                            style={{
                                fontSize:12,
                                color:"#999",
                                marginTop:4
                            }}
                        >
                            {item.filename}
                        </div>

                    </div>


                    {/* 评分 */}

                    <div>

                        <Tag color="red">

                            {item.score ?? 0}分

                        </Tag>

                    </div>


                    {/* 风险 */}

                    <div>

                        ⚠ {item.risk_count ?? 0} 项

                    </div>


                    {/* 操作 */}

                    <div>

                        <Button
                            type="link"
                            danger
                            onClick={()=>{
                                openDashboardProject(item);
                            }}
                        >
                            查看分析 →
                        </Button>

                    </div>

                </div>

            )
        )

        :

        <EmptyState description="当前没有需要重点关注的项目" />
    }

</Card>


    </div>

    :

    <>
    </>
}

{/*

==================
项目对比顶部栏
================== */}

{
    compareFiles.length > 0 &&

    <Card
        className="section-card comparison-toolbar"
        style={{
            border:"1px solid #1677ff"
        }}
    >

        <div
            className="comparison-grid"
            style={{
                display:"flex",
                justifyContent:"space-between",
                alignItems:"center",
                gap:20
            }}
        >

            {/* 左侧：已选择项目 */}

            <div
                style={{
                    flex:1
                }}
            >

                <div className="card-title">
                    <SwapOutlined />
                    项目对比
                </div>


                <div
                    style={{
                        marginTop:10,
                        display:"flex",
                        alignItems:"center",
                        gap:10,
                        flexWrap:"wrap"
                    }}
                >

                    {
                        compareFiles.map(
                            (item)=>(

                                <Tag
                                    color="blue"
                                    key={item.id}
                                    closable

                                    onClose={(e)=>{

                                        e.preventDefault();

                                        toggleCompare(item);

                                    }}
                                >

                                    {
                                        item.project_name
                                        ||
                                        item.filename
                                    }

                                </Tag>

                            )
                        )
                    }


                    {
                        compareFiles.length === 1 &&

                        <span
                            style={{
                                color:"#999"
                            }}
                        >
                            VS 请选择第二个项目
                        </span>
                    }


                    {
                        compareFiles.length === 2 &&

                        <Tag color="purple">
                            VS
                        </Tag>
                    }

                </div>

            </div>


            {/* 右侧按钮 */}

            <Button

                 type="primary"

                 disabled={
                  compareFiles.length !== 2
            }

                  loading={compareLoading}

                   onClick={startCompare}

               >
                       开始对比
             </Button>

        </div>

    </Card>
}


{/* ==================
项目对比结果
================== */}

{
    compareResult &&

    <Card
        className="section-card"
    >

        <Typography.Title level={3} className="section-title section-title-spaced">
            <SwapOutlined />
            项目对比结果
        </Typography.Title>

<Button

    type="primary"

    onClick={
        exportCompareReport
    }

    style={{
        marginBottom:16
    }}

    icon={<ExportOutlined />}

>
    导出项目对比报告
</Button>


        <div
            style={{
                display:"grid",
                gridTemplateColumns:"180px 1fr 1fr",
                border:"1px solid #eee"
            }}
        >

            {/* 表头 */}

            <div
                style={{
                    padding:12,
                    fontWeight:"bold",
                    background:"#fafafa"
                }}
            >
                对比项
            </div>


            <div
                style={{
                    padding:12,
                    fontWeight:"bold",
                    background:"#e6f4ff"
                }}
            >
                {
                    compareResult.projectA.project_name
                    ||
                    compareResult.projectA.filename
                }
            </div>


            <div
                style={{
                    padding:12,
                    fontWeight:"bold",
                    background:"#f6ffed"
                }}
            >
                {
                    compareResult.projectB.project_name
                    ||
                    compareResult.projectB.filename
                }
            </div>


            {/* AI评分 */}

            <CompareRow
                label="AI评分"

                valueA={
                    `${compareResult.projectA.score ?? 0}分`
                }

                valueB={
                    `${compareResult.projectB.score ?? 0}分`
                }
            />


            {/* 风险等级 */}

            <CompareRow
                label="风险等级"

                valueA={
                    compareResult.projectA.score_level
                    ||
                    "未评级"
                }

                valueB={
                    compareResult.projectB.score_level
                    ||
                    "未评级"
                }
            />


            {/* 风险总数 */}

            <CompareRow
                label="风险总数"

                valueA={
                    `${compareResult.projectA.risk_count ?? 0}项`
                }

                valueB={
                    `${compareResult.projectB.risk_count ?? 0}项`
                }
            />


            {/* 高风险 */}

            <CompareRow
                label="🔴 高风险"

                valueA={
                    `${compareResult.projectA.high_count ?? 0}项`
                }

                valueB={
                    `${compareResult.projectB.high_count ?? 0}项`
                }
            />


            {/* 中风险 */}

            <CompareRow
                label="🟠 中风险"

                valueA={
                    `${compareResult.projectA.middle_count ?? 0}项`
                }

                valueB={
                    `${compareResult.projectB.middle_count ?? 0}项`
                }
            />


            {/* 低风险 */}

            <CompareRow
                label="🟢 低风险"

                valueA={
                    `${compareResult.projectA.low_count ?? 0}项`
                }

                valueB={
                    `${compareResult.projectB.low_count ?? 0}项`
                }
            />


            {/* 总扣分 */}

            <CompareRow
                label="风险总扣分"

                valueA={
                    `-${compareResult.projectA.total_deduction ?? 0}分`
                }

                valueB={
                    `-${compareResult.projectB.total_deduction ?? 0}分`
                }
            />


            {/* 招标单位 */}

            <CompareRow
                label="招标单位"

                valueA={
                    compareResult.projectA.analysis?.tender_company
                    ||
                    "未找到"
                }

                valueB={
                    compareResult.projectB.analysis?.tender_company
                    ||
                    "未找到"
                }
            />


            {/* 投标截止 */}

            <CompareRow
                label="投标截止"

                valueA={
                    compareResult.projectA.analysis?.deadline
                    ||
                    "未找到"
                }

                valueB={
                    compareResult.projectB.analysis?.deadline
                    ||
                    "未找到"
                }
            />

        </div>

<Divider />


<Typography.Title level={4} className="section-title section-title-spaced">
    <FileSearchOutlined />
    智能差异分析
</Typography.Title>


{/* ==================
综合推荐
================== */}

<Card
    style={{
        marginBottom:16,
        background:"#fafafa"
    }}
>

    <Typography.Title
        level={4}
        className="section-title section-title-spaced"
    >
        <TrophyOutlined />
        综合推荐
    </Typography.Title>


    <div
        className="comparison-score-cards"
        style={{
            display:"grid",
            gridTemplateColumns:"1fr 1fr",
            gap:12,
            marginBottom:16
        }}
    >

        <div
            style={{
                padding:12,
                background:"#e6f4ff",
                borderRadius:6
            }}
        >

            <b>
                项目A综合指数
            </b>

            <div
                style={{
                    fontSize:28,
                    fontWeight:"bold",
                    marginTop:6
                }}
            >
                {compareResult.decisionScoreA}
            </div>

        </div>


        <div
            style={{
                padding:12,
                background:"#f6ffed",
                borderRadius:6
            }}
        >

            <b>
                项目B综合指数
            </b>

            <div
                style={{
                    fontSize:28,
                    fontWeight:"bold",
                    marginTop:6
                }}
            >
                {compareResult.decisionScoreB}
            </div>

        </div>

    </div>


    <div
        style={{
            padding:12,
            background:"#fff7e6",
            borderRadius:6
        }}
    >

<Divider />


<Typography.Title
    level={5}
    className="section-title section-title-spaced"
>
    <UnorderedListOutlined />
    推荐评分明细
</Typography.Title>


<div
    className="comparison-grid comparison-score-grid"
    style={{
        display:"grid",
        gridTemplateColumns:"160px 1fr 1fr",
        border:"1px solid #eee",
        marginBottom:16
    }}
>

    {/* 表头 */}

    <div
        style={{
            padding:10,
            fontWeight:"bold",
            background:"#fafafa"
        }}
    >
        评分项
    </div>


    <div
        style={{
            padding:10,
            fontWeight:"bold",
            background:"#e6f4ff"
        }}
    >
        项目A
    </div>


    <div
        style={{
            padding:10,
            fontWeight:"bold",
            background:"#f6ffed"
        }}
    >
        项目B
    </div>


    <CompareRow
        label="原始AI评分"

        valueA={
            `${compareResult.baseScoreA}分`
        }

        valueB={
            `${compareResult.baseScoreB}分`
        }
    />


    <CompareRow
        label="高风险惩罚"

        valueA={
            `-${compareResult.highPenaltyA}分`
        }

        valueB={
            `-${compareResult.highPenaltyB}分`
        }
    />


    <CompareRow
        label="独有高风险惩罚"

        valueA={
            `-${compareResult.uniqueHighPenaltyA}分`
        }

        valueB={
            `-${compareResult.uniqueHighPenaltyB}分`
        }
    />


    <CompareRow
        label="共同风险强度惩罚"

        valueA={
            `-${compareResult.commonStrengthPenaltyA}分`
        }

        valueB={
            `-${compareResult.commonStrengthPenaltyB}分`
        }
    />


    <CompareRow
        label="最终综合指数"

        valueA={
            `${compareResult.decisionScoreA}分`
        }

        valueB={
            `${compareResult.decisionScoreB}分`
        }
    />

</div>

        <b>
            推荐结果：
        </b>

        {
            compareResult.recommended === "A"
            ?
            (
                compareResult.projectA.project_name
                ||
                compareResult.projectA.filename
            )
            :
            compareResult.recommended === "B"
            ?
            (
                compareResult.projectB.project_name
                ||
                compareResult.projectB.filename
            )
            :
            "两个项目接近"
        }


        <div
            style={{
                marginTop:8
            }}
        >

            {
                compareResult.recommendationReason
            }

        </div>

    </div>

<div
    style={{
        marginTop:12
    }}
>

    <b>
        推荐置信度：
    </b>

    <Tag
        color={
            compareResult.confidenceColor
        }
        style={{
            marginLeft:8
        }}
    >
        {compareResult.confidenceLevel}
    </Tag>

</div>


<div
    style={{
        marginTop:8,
        color:"#666",
        lineHeight:1.8
    }}
>

    综合指数差值：

    <b>
        {compareResult.scoreDifference}分
    </b>

    <br/>

    {
        compareResult.confidenceText
    }

</div>


{/* ==================
V2.2 AI决策摘要
================== */}

<Card
    title="🤖 AI 决策摘要"
    style={{
        marginBottom:16
    }}
>

    {
        aiDecisionLoading
        ?

        <div
            style={{
                textAlign:"center",
                padding:20
            }}
        >
            <Spin />

            <div
                style={{
                    marginTop:10,
                    color:"#666"
                }}
            >
                AI正在生成管理层决策摘要...
            </div>
        </div>

        :

        aiDecision
        ?

        <>
            <div
                style={{
                    padding:12,
                    background:"#e6f4ff",
                    borderRadius:6,
                    marginBottom:15,
                    lineHeight:1.8
                }}
            >

                <b>
                    📌 执行摘要
                </b>

                <div
                    className="comparison-risk-grid"
                    style={{
                        marginTop:6
                    }}
                >
                    {aiDecision.executive_summary}
                </div>

            </div>


            <p>
                <b>
                    推荐类型：
                </b>

                <Tag
                    color="blue"
                    style={{
                        marginLeft:8
                    }}
                >
                    {
                        aiDecision.recommendation_type
                        ||
                        "未评估"
                    }
                </Tag>
            </p>


            <Divider />


            <h4>
                ✅ 推荐项目主要优势
            </h4>

            {
                aiDecision.key_advantages?.length
                ?

                aiDecision.key_advantages.map(
                    (item,index)=>(

                        <p key={index}>
                            {index + 1}. {item}
                        </p>

                    )
                )

                :

                <p>
                    暂无
                </p>
            }


            <h4>
                ⚠ 推荐项目核心风险
            </h4>

            {
                aiDecision.key_risks?.length
                ?

                aiDecision.key_risks.map(
                    (item,index)=>(

                        <p key={index}>
                            {index + 1}. {item}
                        </p>

                    )
                )

                :

                <p>
                    暂无
                </p>
            }


            <h4>
                🔧 投标前必须处理
            </h4>

            {
                aiDecision.must_resolve_before_bid?.length
                ?

                aiDecision.must_resolve_before_bid.map(
                    (item,index)=>(

                        <p key={index}>
                            {index + 1}. {item}
                        </p>

                    )
                )

                :

                <p>
                    暂无
                </p>
            }


            <h4>
                🔄 改变推荐的条件
            </h4>

            {
                aiDecision.switch_conditions?.length
                ?

                aiDecision.switch_conditions.map(
                    (item,index)=>(

                        <p key={index}>
                            {index + 1}. {item}
                        </p>

                    )
                )

                :

                <p>
                    暂无
                </p>
            }


            <div
                style={{
                    marginTop:15,
                    padding:12,
                    background:"#f6ffed",
                    borderLeft:"4px solid #52c41a",
                    lineHeight:1.8
                }}
            >

                <b>
                    🧭 管理层建议
                </b>

                <div
                    style={{
                        marginTop:6
                    }}
                >
                    {
                        aiDecision.management_advice
                    }
                </div>

            </div>

        </>

        :

        <span
            style={{
                color:"#999"
            }}
        >
            暂未生成AI决策摘要
        </span>
    }

</Card>


</Card>


{/* ==================
共同风险
================== */}

{/* ==================
V2.2 风险强度对比
================== */}

<Card
    title="📊 共同风险强度对比"
    style={{
        marginBottom:16
    }}
>

{
    !compareResult.riskStrengthCompare?.length
    ?

    <EmptyState description="暂无可比较的共同风险" />

    :

    compareResult.riskStrengthCompare.map(
        (item,index)=>(

            <div
                key={index}
                style={{
                    padding:"12px 0",
                    borderBottom:
                    index <
                    compareResult.riskStrengthCompare.length - 1
                    ?
                    "1px solid #eee"
                    :
                    "none"
                }}
            >

                <div
                    style={{
                        fontWeight:"bold",
                        marginBottom:10
                    }}
                >
                    {item.category}
                </div>


                <div
                    style={{
                        display:"grid",
                        gridTemplateColumns:"1fr 1fr",
                        gap:12
                    }}
                >

                    {/* 项目A */}

                    <div
                        style={{
                            background:"#e6f4ff",
                            padding:10,
                            borderRadius:6
                        }}
                    >

                        <b>
                            项目A
                        </b>

                        <div
                            style={{
                                marginTop:6
                            }}
                        >
                            <Tag
                                color={
                                    item.riskA?.level?.includes("高")
                                    ? "red"
                                    :
                                    item.riskA?.level?.includes("中")
                                    ? "orange"
                                    :
                                    "green"
                                }
                            >
                                {item.riskA?.level || "未知"}风险
                            </Tag>

                            <Tag color="volcano">
                                -{item.deductionA}分
                            </Tag>
                        </div>

                        <div
                            style={{
                                marginTop:6
                            }}
                        >
                            {item.riskA?.keyword}
                        </div>

                    </div>


                    {/* 项目B */}

                    <div
                        style={{
                            background:"#f6ffed",
                            padding:10,
                            borderRadius:6
                        }}
                    >

                        <b>
                            项目B
                        </b>

                        <div
                            style={{
                                marginTop:6
                            }}
                        >
                            <Tag
                                color={
                                    item.riskB?.level?.includes("高")
                                    ? "red"
                                    :
                                    item.riskB?.level?.includes("中")
                                    ? "orange"
                                    :
                                    "green"
                                }
                            >
                                {item.riskB?.level || "未知"}风险
                            </Tag>

                            <Tag color="volcano">
                                -{item.deductionB}分
                            </Tag>
                        </div>

                        <div
                            style={{
                                marginTop:6
                            }}
                        >
                            {item.riskB?.keyword}
                        </div>

                    </div>

                </div>


                {/* 对比结论 */}

                <div
                    style={{
                        marginTop:10,
                        padding:8,
                        background:"#fafafa",
                        borderRadius:4
                    }}
                >

                    <b>
                        对比结论：
                    </b>


                   {
                      item.stronger === "A"
                       ?
                      `项目A该项风险更高，应优先核查项目A。${item.compareReason ? " 原因：" + item.compareReason : ""}`
                       :
                        item.stronger === "B"
                        ?
                       `项目B该项风险更高，应优先核查项目B。${item.compareReason ? " 原因：" + item.compareReason : ""}`
                       :
                        `两个项目该项风险强度基本相同。${item.compareReason ? " 原因：" + item.compareReason : ""}`
                    }


                </div>

            </div>

        )
    )
}

</Card>



<Card
    title="⚠ 两个项目共同风险"
    style={{
        marginBottom:16
    }}
>

    {
        compareResult.commonRisks.length === 0
        ?

        <span>
            暂未发现相同风险
        </span>

        :

        (
            compareResult.commonCategories?.length === 0
    ?

    <span>
        暂未发现共同风险类别
    </span>

    :

    compareResult.commonCategories?.map(
        (category,index)=>(

            <Tag
                key={index}
                color="orange"
                style={{
                    marginBottom:8
                }}
            >

                {category}

            </Tag>

        )
    )
        )

    }

</Card>


{/* ==================
A 独有风险
================== */}

<Card
    title={
        "🔵 项目A独有风险"
    }
    style={{
        marginBottom:16
    }}
>

    {
        compareResult.onlyARisks.length === 0
        ?

        <EmptyState description="项目 A 无独有风险" />

        :

        compareResult.onlyARisks.map(
            (risk,index)=>(

                <div
                    key={index}
                    style={{
                        marginBottom:12,
                        paddingBottom:12,
                        borderBottom:"1px solid #eee"
                    }}
                >

                    <Tag
                        color={
                            risk.level?.includes("高")
                            ? "red"
                            :
                            risk.level?.includes("中")
                            ? "orange"
                            :
                            "green"
                        }
                    >
                        {risk.level}风险
                    </Tag>

                    <b>
                    <div>

                    <b>
                     {risk.category}
                    </b>

                    <div
                     style={{
                       marginTop:4,
                       color:"#666"
                    }}
                    >
                      {risk.keyword}
                      </div>

                    </div>
                    </b>

                    <div
                        style={{
                            marginTop:5
                        }}
                    >
                        第 {risk.page} 页
                    </div>

                </div>

            )
        )
    }

</Card>


{/* ==================
B 独有风险
================== */}

<Card
    title="🟢 项目B独有风险"
>

    {
        compareResult.onlyBRisks.length === 0
        ?

        <EmptyState description="项目 B 无独有风险" />

        :

        compareResult.onlyBRisks.map(
            (risk,index)=>(

                <div
                    key={index}
                    style={{
                        marginBottom:12,
                        paddingBottom:12,
                        borderBottom:"1px solid #eee"
                    }}
                >

                    <Tag
                        color={
                            risk.level?.includes("高")
                            ? "red"
                            :
                            risk.level?.includes("中")
                            ? "orange"
                            :
                            "green"
                        }
                    >
                        {risk.level}风险
                    </Tag>

                    <b>
                        {risk.keyword}
                    </b>

                    <div
                        style={{
                            marginTop:5
                        }}
                    >
                        第 {risk.page} 页
                    </div>

                </div>

            )
        )
    }

</Card>



    </Card>
}

<Card>


<Upload


beforeUpload={beforeUpload}

accept=".pdf,.docx,.doc"


maxCount={1}


showUploadList={true}



>


<Button

icon={<UploadOutlined/>}

>

选择招标文件

</Button>


</Upload>



<br/><br/>




<Button

type="primary"

loading={loading}

onClick={startAnalyze}

>


开始智能分析


</Button>



</Card>






{/* ==============================
    PDF / DOCX 响应式预览
============================== */}

{
    (pdfUrl || docxPreviewPages.length > 0 || previewError)
    && (
        <Suspense fallback={<LoadingState text="正在加载文档预览..." />}>
            <DocumentPreview
                activeRisk={activeRisk}
                docxPreviewPages={docxPreviewPages}
                numPages={numPages}
                onDocumentLoad={(pdf)=>setNumPages(pdf.numPages)}
                onNextPage={()=>setPageNumber(pageNumber + 1)}
                onPreviousPage={()=>setPageNumber(pageNumber - 1)}
                pageNumber={pageNumber}
                pdfUrl={pdfUrl}
                previewError={previewError}
                previewRenderer={previewRenderer}
                previewSourceFormat={previewSourceFormat}
            />
        </Suspense>
    )
}
</>
)}

</div>

</Content>


</Layout>




{/* ==================
右侧AI
================== */}

{!showWorkbench && (
<Sider
    className={`app-right-sider ${rightCollapsed ? "is-collapsed" : ""}`}
    width={
        rightCollapsed
            ? 56
            : 400
    }
    theme="light"
    style={{
        padding:rightCollapsed ? 8 : 16,
        overflow:"auto",
        background:"#f7f9fc",
        borderLeft:"1px solid #e8e8e8",
        transition:"all 0.25s ease"
    }}
>

    {/* ==============================
        风险检查器标题
    ============================== */}

{/* ==============================
    风险检查器标题 + 收起按钮
============================== */}

<div
    style={{
        display:"flex",
        flexDirection:rightCollapsed ? "column" : "row",
        justifyContent:rightCollapsed ? "center" : "space-between",
        alignItems:"center",
        gap:8,
        marginBottom:rightCollapsed ? 0 : 16
    }}
>

    {
        !rightCollapsed
        &&
        (
            <div
                style={{
                    minWidth:0,
                    flex:1
                }}
            >

                <div
                    style={{
                        fontSize:18,
                        fontWeight:700,
                        color:"#262626"
                    }}
                >
                    风险检查器
                </div>

                <div
                    style={{
                        marginTop:3,
                        fontSize:12,
                        color:"#8c8c8c"
                    }}
                >
                    AI 投标风险识别与决策辅助
                </div>

            </div>
        )
    }


    {
        !rightCollapsed
        &&
        (
            <Button
                type="primary"
                size="small"
                onClick={exportReport}
            >
                导出报告
            </Button>
        )
    }


    <Button
        type="text"
        size="small"
        title={
            rightCollapsed
                ? "展开风险检查器"
                : "收起风险检查器"
        }
        onClick={()=>{
            setRightCollapsed(
                !rightCollapsed
            );
        }}
        style={{
            width:32,
            height:32,
            padding:0,
            flexShrink:0,
            borderRadius:8,
            fontWeight:700,
            color:"#1677ff",
            background:rightCollapsed
                ? "#e6f4ff"
                : "transparent"
        }}
    >
        {
            rightCollapsed
                ? "◀"
                : "▶"
        }
    </Button>

</div>



<div
    style={{
        display:rightCollapsed
            ? "none"
            : "block"
    }}
>

    {/* ==============================
        投标建议指数
    ============================== */}

    <Card
        style={{
            marginBottom:16,
            borderRadius:12,
            border:"1px solid #e8eef8",
            boxShadow:"0 3px 14px rgba(0,0,0,0.04)"
        }}
        styles={{
            body:{
                padding:18
            }
        }}
    >

        <div
            style={{
                display:"flex",
                justifyContent:"space-between",
                alignItems:"flex-start",
                gap:12
            }}
        >

            <div>

                <div
                    style={{
                        fontSize:13,
                        color:"#8c8c8c",
                        fontWeight:500
                    }}
                >
                    投标建议指数
                </div>


                <div
                    style={{
                        display:"flex",
                        alignItems:"baseline",
                        gap:4,
                        marginTop:6
                    }}
                >

                    <span
                        style={{
                            fontSize:38,
                            lineHeight:1.15,
                            fontWeight:700,
                            color:
                                score >= 85
                                    ? "#389e0d"
                                    :
                                score >= 60
                                    ? "#d46b08"
                                    :
                                    "#cf1322"
                        }}
                    >
                        {score}
                    </span>

                    <span
                        style={{
                            color:"#8c8c8c",
                            fontSize:13
                        }}
                    >
                        分
                    </span>

                </div>

            </div>


            <Tag
                color={
                    score >= 85
                        ? "green"
                        :
                    score >= 60
                        ? "orange"
                        :
                        "red"
                }
                style={{
                    margin:0,
                    padding:"4px 10px",
                    borderRadius:6,
                    fontWeight:600
                }}
            >
                {scoreLevel || "待分析"}
            </Tag>

        </div>



        {/* 风险数量 */}

        <div
            style={{
                display:"grid",
                gridTemplateColumns:"repeat(3, 1fr)",
                gap:8,
                marginTop:18,
                padding:"12px 0",
                borderTop:"1px solid #f0f0f0",
                borderBottom:"1px solid #f0f0f0"
            }}
        >

            <div
                style={{
                    textAlign:"center",
                    borderRight:"1px solid #f0f0f0"
                }}
            >
                <div
                    style={{
                        fontSize:20,
                        fontWeight:700,
                        color:"#cf1322"
                    }}
                >
                    {highCount}
                </div>

                <div
                    style={{
                        marginTop:2,
                        fontSize:12,
                        color:"#8c8c8c"
                    }}
                >
                    高风险
                </div>
            </div>


            <div
                style={{
                    textAlign:"center",
                    borderRight:"1px solid #f0f0f0"
                }}
            >
                <div
                    style={{
                        fontSize:20,
                        fontWeight:700,
                        color:"#d46b08"
                    }}
                >
                    {middleCount}
                </div>

                <div
                    style={{
                        marginTop:2,
                        fontSize:12,
                        color:"#8c8c8c"
                    }}
                >
                    中风险
                </div>
            </div>


            <div
                style={{
                    textAlign:"center"
                }}
            >
                <div
                    style={{
                        fontSize:20,
                        fontWeight:700,
                        color:"#389e0d"
                    }}
                >
                    {lowCount}
                </div>

                <div
                    style={{
                        marginTop:2,
                        fontSize:12,
                        color:"#8c8c8c"
                    }}
                >
                    低风险
                </div>
            </div>

        </div>



        {/* 评分计算 */}

        <div
            style={{
                marginTop:14,
                fontSize:13,
                lineHeight:2
            }}
        >

            <div
                style={{
                    display:"flex",
                    justifyContent:"space-between",
                    color:"#595959"
                }}
            >
                <span>基础分</span>

                <span
                    style={{
                        fontWeight:600,
                        color:"#262626"
                    }}
                >
                    100 分
                </span>
            </div>


            <div
                style={{
                    display:"flex",
                    justifyContent:"space-between",
                    color:"#595959"
                }}
            >
                <span>风险总扣分</span>

                <span
                    style={{
                        fontWeight:600,
                        color:"#cf1322"
                    }}
                >
                    -{totalDeduction} 分
                </span>
            </div>


            <div
                style={{
                    display:"flex",
                    justifyContent:"space-between",
                    marginTop:4,
                    paddingTop:6,
                    borderTop:"1px dashed #e8e8e8"
                }}
            >
                <span
                    style={{
                        fontWeight:600
                    }}
                >
                    最终得分
                </span>

                <span
                    style={{
                        fontWeight:700,
                        color:
                            score >= 85
                                ? "#389e0d"
                                :
                            score >= 60
                                ? "#d46b08"
                                :
                                "#cf1322"
                    }}
                >
                    {score} 分
                </span>
            </div>

        </div>



        {/* 投标结论 */}

        <div
            style={{
                marginTop:12,
                padding:"10px 12px",
                borderRadius:8,
                background:
                    score >= 85
                        ? "#f6ffed"
                        :
                    score >= 70
                        ? "#fffbe6"
                        :
                    score >= 60
                        ? "#fff7e6"
                        :
                        "#fff1f0",
                fontSize:13,
                color:"#595959",
                lineHeight:1.7
            }}
        >
            {
                score >= 85
                    ? "🟢 低风险，可以重点跟进"
                    :
                score >= 70
                    ? "🟡 中低风险，建议重点核查关键条款"
                    :
                score >= 60
                    ? "🟠 中风险，需要整改后再投标"
                    :
                score >= 40
                    ? "🔴 高风险，建议谨慎投标"
                    :
                    "⛔ 极高风险，建议暂缓投标"
            }
        </div>

    </Card>


    {/* ==============================
        Loading
    ============================== */}

    {
        loading
        &&
        (
            <Card
                style={{
                    marginBottom:16,
                    borderRadius:12,
                    textAlign:"center"
                }}
            >
                <Spin />

                <div
                    style={{
                        marginTop:10,
                        color:"#8c8c8c",
                        fontSize:13
                    }}
                >
                    AI 正在分析标书内容...
                </div>
            </Card>
        )
    }



    {/* ==============================
        项目基本信息
    ============================== */}

    {
        result
        &&
        (
            <Card
                style={{
                    marginBottom:16,
                    borderRadius:12,
                    border:"1px solid #e8e8e8"
                }}
                styles={{
                    body:{
                        padding:16
                    }
                }}
            >

                <div
                    style={{
                        fontSize:15,
                        fontWeight:700,
                        color:"#262626",
                        marginBottom:12
                    }}
                >
                    项目信息
                </div>


                <div
                    style={{
                        display:"grid",
                        gap:9,
                        fontSize:13
                    }}
                >

                    <div>
                        <span
                            style={{
                                color:"#8c8c8c"
                            }}
                        >
                            项目名称：
                        </span>

                        <span
                            style={{
                                color:"#262626",
                                fontWeight:500
                            }}
                        >
                            {result.project_name || "未找到"}
                        </span>
                    </div>


                    <div>
                        <span
                            style={{
                                color:"#8c8c8c"
                            }}
                        >
                            招标单位：
                        </span>

                        <span>
                            {result.tender_company || "未找到"}
                        </span>
                    </div>


                    <div>
                        <span
                            style={{
                                color:"#8c8c8c"
                            }}
                        >
                            截止时间：
                        </span>

                        <span>
                            {result.deadline || "未找到"}
                        </span>
                    </div>


                    <div>
                        <span
                            style={{
                                color:"#8c8c8c"
                            }}
                        >
                            保证金：
                        </span>

                        <span>
                            {result.deposit || "未找到"}
                        </span>
                    </div>

                </div>



                <Divider
                    style={{
                        margin:"14px 0"
                    }}
                />



                {/* 技术要求 */}

                <div
                    style={{
                        fontSize:14,
                        fontWeight:700,
                        marginBottom:8
                    }}
                >
                    技术要求
                </div>

                <div
                    style={{
                        display:"flex",
                        flexWrap:"wrap",
                        gap:6
                    }}
                >

                    {
                        result.technical_requirements?.map(
                            (x,i)=>(
                                <Tag
                                    color="blue"
                                    key={i}
                                    style={{
                                        margin:0,
                                        whiteSpace:"normal",
                                        lineHeight:1.6
                                    }}
                                >
                                    {
                                        typeof x === "string"
                                            ? x
                                            :
                                            `${x.item || ""}${x.content ? "：" + x.content : ""}`
                                    }
                                </Tag>
                            )
                        )
                    }

                </div>



                <Divider
                    style={{
                        margin:"14px 0"
                    }}
                />



                {/* 商务要求 */}

                <div
                    style={{
                        fontSize:14,
                        fontWeight:700,
                        marginBottom:8
                    }}
                >
                    商务要求
                </div>

                <div
                    style={{
                        display:"flex",
                        flexWrap:"wrap",
                        gap:6
                    }}
                >

                    {
                        result.business_requirements?.map(
                            (x,i)=>(
                                <Tag
                                    color="green"
                                    key={i}
                                    style={{
                                        margin:0,
                                        whiteSpace:"normal",
                                        lineHeight:1.6
                                    }}
                                >
                                    {
                                        typeof x === "string"
                                            ? x
                                            :
                                            `${x.item || ""}${x.content ? "：" + x.content : ""}`
                                    }
                                </Tag>
                            )
                        )
                    }

                </div>

                {
                    Array.isArray(result.procurement_requirements)
                    && result.procurement_requirements.length > 0
                    && (
                        <>
                            <Divider style={{margin:"14px 0"}} />
                            <div
                                style={{
                                    fontSize:14,
                                    fontWeight:700,
                                    marginBottom:8
                                }}
                            >
                                采购清单
                            </div>
                            <div
                                style={{
                                    display:"flex",
                                    flexDirection:"column",
                                    gap:6
                                }}
                            >
                                {result.procurement_requirements.map((item,index)=>(
                                    <Tag
                                        color="cyan"
                                        key={index}
                                        style={{
                                            margin:0,
                                            whiteSpace:"normal",
                                            lineHeight:1.6
                                        }}
                                    >
                                        {formatProcurementRequirement(item)}
                                    </Tag>
                                ))}
                            </div>
                        </>
                    )
                }

            </Card>
        )
    }



    {/* ==============================
        当前选中风险详情
    ============================== */}

    {
        activeRisk
        &&
        (
            <Card
                style={{
                    marginBottom:16,
                    borderRadius:12,
                    border:
                        activeRisk.level?.includes("高")
                            ? "1px solid #ffccc7"
                            :
                        activeRisk.level?.includes("中")
                            ? "1px solid #ffd591"
                            :
                            "1px solid #b7eb8f",
                    background:"#ffffff"
                }}
                styles={{
                    body:{
                        padding:16
                    }
                }}
            >

                <div
                    style={{
                        display:"flex",
                        justifyContent:"space-between",
                        alignItems:"center",
                        gap:8,
                        marginBottom:12
                    }}
                >

                    <div
                        style={{
                            fontSize:15,
                            fontWeight:700
                        }}
                    >
                        当前风险详情
                    </div>


                    <div
                        style={{
                            display:"flex",
                            gap:6
                        }}
                    >

                        <Tag
                            color={
                                activeRisk.level?.includes("高")
                                    ? "red"
                                    :
                                activeRisk.level?.includes("中")
                                    ? "orange"
                                    :
                                    "green"
                            }
                            style={{
                                margin:0
                            }}
                        >
                            {activeRisk.level}风险
                        </Tag>


                        <Tag
                            color="volcano"
                            style={{
                                margin:0
                            }}
                        >
                            -{activeRisk.deduction ?? 0}分
                        </Tag>

                    </div>

                </div>



                <div
                    style={{
                        display:"flex",
                        gap:6,
                        flexWrap:"wrap",
                        marginBottom:12
                    }}
                >

                    {
                        activeRisk.page
                        &&
                        (
                            <Tag
                                style={{
                                    margin:0
                                }}
                            >
                                第 {activeRiskPreviewPage || activeRisk.page} 页
                            </Tag>
                        )
                    }


                    {
                        activeRisk.keyword
                        &&
                        (
                            <Tag
                                color="blue"
                                style={{
                                    margin:0
                                }}
                            >
                                {activeRisk.keyword}
                            </Tag>
                        )
                    }

                </div>



                <div
                    style={{
                        marginBottom:12
                    }}
                >

                    <div
                        style={{
                            fontSize:13,
                            fontWeight:600,
                            color:"#595959",
                            marginBottom:5
                        }}
                    >
                        风险原因
                    </div>

                    <div
                        style={{
                            color:"#595959",
                            lineHeight:1.8,
                            fontSize:13
                        }}
                    >
                        {activeRisk.reason}
                    </div>

                </div>



                {
                    activeRisk.deduction_reason
                    &&
                    (
                        <div
                            style={{
                                marginBottom:12,
                                padding:"10px 12px",
                                background:"#fff7e6",
                                borderLeft:"3px solid #fa8c16",
                                borderRadius:6
                            }}
                        >

                            <div
                                style={{
                                    fontWeight:600,
                                    marginBottom:4,
                                    color:"#d46b08",
                                    fontSize:13
                                }}
                            >
                                扣分依据
                            </div>

                            <div
                                style={{
                                    color:"#595959",
                                    lineHeight:1.7,
                                    fontSize:13
                                }}
                            >
                                {activeRisk.deduction_reason}
                            </div>

                        </div>
                    )
                }



                {
                    activeRisk.quote
                    &&
                    (
                        <div
                            style={{
                                marginBottom:12
                            }}
                        >

                            <div
                                style={{
                                    fontWeight:600,
                                    color:"#595959",
                                    fontSize:13,
                                    marginBottom:5
                                }}
                            >
                                原文依据
                            </div>

                            <div
                                style={{
                                    padding:"10px 12px",
                                    background:"#fafafa",
                                    borderLeft:"3px solid #d9d9d9",
                                    borderRadius:6,
                                    color:"#595959",
                                    lineHeight:1.7,
                                    fontSize:13
                                }}
                            >
                                {activeRisk.quote}
                            </div>

                        </div>
                    )
                }



                {
                    activeRisk.suggestion
                    &&
                    (
                        <div
                            style={{
                                padding:"10px 12px",
                                background:"#f6ffed",
                                border:"1px solid #d9f7be",
                                borderRadius:6
                            }}
                        >

                            <div
                                style={{
                                    fontWeight:600,
                                    color:"#389e0d",
                                    fontSize:13,
                                    marginBottom:4
                                }}
                            >
                                处理建议
                            </div>

                            <div
                                style={{
                                    color:"#595959",
                                    lineHeight:1.7,
                                    fontSize:13
                                }}
                            >
                                {activeRisk.suggestion}
                            </div>

                        </div>
                    )
                }

            </Card>
        )
    }



    {/* ==============================
        风险列表
    ============================== */}

    <div
        ref={riskSectionRef}
        style={{
            display:"flex",
            justifyContent:"space-between",
            alignItems:"center",
            marginTop:6,
            marginBottom:12
        }}
    >

        <div>

            <div
                style={{
                    fontSize:17,
                    fontWeight:700,
                    color:"#262626"
                }}
            >
                风险分析
            </div>

            <div
                style={{
                    marginTop:2,
                    fontSize:12,
                    color:"#8c8c8c"
                }}
            >
                点击风险可定位原文并高亮
            </div>

        </div>


        <Tag
            color="red"
            style={{
                margin:0
            }}
        >
            共 {risks.length} 项
        </Tag>

    </div>



    {
        risks.length > 0
        ?
        risks.map(
            (item,index)=>(

                <Card
                    key={index}
                    onClick={()=>{

                        const mappedPage = Number(wordPreviewRiskPages[String(index)]);
                        const requestedPage = mappedPage || Number(item.page) || 1;
                        const targetPage = numPages > 0
                            ? Math.min(Math.max(requestedPage, 1), numPages)
                            : Math.max(requestedPage, 1);

                        setActiveRisk(item);

                        setActiveRiskPreviewPage(targetPage);

                        setPageNumber(
                            targetPage
                        );

                        // 等 PDF 渲染后高亮
                        setTimeout(()=>{

                            highlightKeyword(
                                item.highlight_words,
                                item.level
                            );

                        },1200);

                    }}
                    style={{
                        marginBottom:10,
                        cursor:"pointer",
                        borderRadius:10,

                        border:
                            dashboardRiskFocus
                            &&
                            item.level?.includes("高")
                                ? "2px solid #ff4d4f"
                                :
                            activeRisk === item
                                ? "1px solid #1677ff"
                                :
                                "1px solid #e8e8e8",

                        background:
                            dashboardRiskFocus
                            &&
                            item.level?.includes("高")
                                ? "#fff1f0"
                                :
                            activeRisk === item
                                ? "#f0f7ff"
                                :
                                "#ffffff",

                        boxShadow:
                            dashboardRiskFocus
                            &&
                            item.level?.includes("高")
                                ? "0 0 12px rgba(255,77,79,0.22)"
                                :
                            activeRisk === item
                                ? "0 3px 10px rgba(22,119,255,0.10)"
                                :
                                "0 2px 8px rgba(0,0,0,0.03)",

                        transition:"all 0.3s ease"
                    }}
                    styles={{
                        body:{
                            padding:14
                        }
                    }}
                >

                    {/* 风险顶部 */}

                    <div
                        style={{
                            display:"flex",
                            justifyContent:"space-between",
                            alignItems:"center",
                            gap:8,
                            marginBottom:10
                        }}
                    >

                        <div
                            style={{
                                display:"flex",
                                gap:6,
                                flexWrap:"wrap"
                            }}
                        >

                            <Tag
                                color={
                                    item.level?.includes("高")
                                        ? "red"
                                        :
                                    item.level?.includes("中")
                                        ? "orange"
                                        :
                                        "green"
                                }
                                style={{
                                    margin:0
                                }}
                            >
                                {item.level}风险
                            </Tag>


                            <Tag
                                color="volcano"
                                style={{
                                    margin:0
                                }}
                            >
                                -{item.deduction ?? 0}分
                            </Tag>

                        </div>


                        <span
                            style={{
                                fontSize:12,
                                color:"#8c8c8c",
                                flexShrink:0
                            }}
                        >
                            第 {item.page ?? "-"} 页
                        </span>

                    </div>



                    {/* 关键词 */}

                    {
                        item.keyword
                        &&
                        (
                            <div
                                style={{
                                    marginBottom:8,
                                    fontSize:13
                                }}
                            >

                                <span
                                    style={{
                                        color:"#8c8c8c"
                                    }}
                                >
                                    关键词：
                                </span>

                                <span
                                    style={{
                                        color:"#262626",
                                        fontWeight:500
                                    }}
                                >
                                    {item.keyword}
                                </span>

                            </div>
                        )
                    }



                    {/* 风险原因 */}

                    <div
                        style={{
                            color:"#595959",
                            lineHeight:1.75,
                            fontSize:13
                        }}
                    >
                        {item.reason}
                    </div>



                    {/* 扣分依据 */}

                    {
                        item.deduction_reason
                        &&
                        (
                            <div
                                style={{
                                    marginTop:10,
                                    padding:"9px 10px",
                                    background:"#fff7e6",
                                    borderLeft:"3px solid #fa8c16",
                                    borderRadius:6,
                                    fontSize:12,
                                    lineHeight:1.7,
                                    color:"#595959"
                                }}
                            >

                                <div
                                    style={{
                                        fontWeight:600,
                                        color:"#d46b08",
                                        marginBottom:3
                                    }}
                                >
                                    扣分依据
                                </div>

                                {item.deduction_reason}

                            </div>
                        )
                    }



                    <div
                        style={{
                            marginTop:10,
                            paddingTop:8,
                            borderTop:"1px solid #f0f0f0",
                            color:"#1677ff",
                            fontSize:12,
                            fontWeight:500
                        }}
                    >
                        点击定位原文 →
                    </div>

                </Card>

            )
        )
        :
        (
            <EmptyState description="暂无风险分析结果" />
        )
    }
    </div>

</Sider>
)}






</Layout>


);


}



export default App;
