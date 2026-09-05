import {
    FilePdfOutlined,
    FileWordOutlined
} from "@ant-design/icons";
import {
    Alert,
    Button,
    Card
} from "antd";
import {
    Document,
    Page,
    pdfjs
} from "react-pdf";
import {
    useEffect,
    useRef,
    useState
} from "react";


pdfjs.GlobalWorkerOptions.workerSrc =
    window.location.origin + "/pdf.worker.min.mjs";


function renderHighlightedDocxText(text, highlightWords){
    const words = Array.isArray(highlightWords)
        ? highlightWords.filter((word)=>typeof word === "string" && word.length > 0)
        : [];

    if(words.length === 0){
        return text;
    }

    const escapedWords = words.map((word)=>
        word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    );
    const matcher = new RegExp(`(${escapedWords.join("|")})`, "g");
    const wordSet = new Set(words);

    return String(text || "").split(matcher).map((part,index)=>
        wordSet.has(part)
            ? <mark className="docx-preview-highlight" key={`${part}-${index}`}>{part}</mark>
            : part
    );
}


function getOcrHighlightClass(level){
    if(String(level || "").includes("高")){
        return "ocr-highlight-box ocr-highlight-high";
    }
    if(String(level || "").includes("中")){
        return "ocr-highlight-box ocr-highlight-middle";
    }
    return "ocr-highlight-box ocr-highlight-low";
}


export default function DocumentPreview({
    activeRisk,
    docxPreviewPages,
    numPages,
    onDocumentLoad,
    onNextPage,
    onPreviousPage,
    pageNumber,
    pdfUrl,
    previewError,
    previewRenderer,
    previewSourceFormat
}){
    const pdfContainerRef = useRef(null);
    const [pdfPageWidth, setPdfPageWidth] = useState(700);

    useEffect(()=>{
        const container = pdfContainerRef.current;

        if(!pdfUrl || !container){
            return undefined;
        }

        const updatePdfWidth = ()=>{
            const availableWidth =
                Math.floor(container.getBoundingClientRect().width);

            if(availableWidth > 0){
                setPdfPageWidth(Math.min(700, availableWidth));
            }
        };

        updatePdfWidth();

        const resizeObserver = new ResizeObserver(updatePdfWidth);
        resizeObserver.observe(container);

        return ()=>resizeObserver.disconnect();
    },[pdfUrl]);

    return (
        <Card
            className="section-card pdf-preview-card"
            style={{overflow:"hidden"}}
        >
            <div
                style={{
                    display:"flex",
                    justifyContent:"space-between",
                    alignItems:"center",
                    marginBottom:16
                }}
            >
                <div>
                    <div className="card-title card-title-large">
                        {previewSourceFormat === "pdf" ? <FilePdfOutlined /> : <FileWordOutlined />}
                        {
                            previewSourceFormat === "pdf"
                                ? "PDF 预览"
                                : previewSourceFormat
                                    ? "Word 版式预览"
                                    : "文档预览"
                        }
                    </div>
                    <div
                        style={{
                            marginTop:3,
                            fontSize:12,
                            color:"#8c8c8c"
                        }}
                    >
                        {
                            pdfUrl
                                ? previewSourceFormat === "pdf"
                                    ? "页面将根据窗口宽度自动缩放"
                                    : `已使用 ${
                                        previewRenderer === "microsoft_word"
                                            ? "Microsoft Word"
                                            : previewRenderer === "wps"
                                                ? "WPS Office"
                                                : "本机办公软件"
                                    } 转换，页数按渲染结果计算`
                                : "兼容模式文本预览"
                        }
                    </div>
                </div>
            </div>

            {
                previewError
                    ? <Alert type="warning" showIcon message={previewError} />
                    : pdfUrl
                        ? (
                            <div
                                ref={pdfContainerRef}
                                className="pdf-responsive-container"
                                style={{display:"flex", justifyContent:"center"}}
                            >
                                <Document file={pdfUrl} onLoadSuccess={onDocumentLoad}>
                                    <div
                                        id={`page-${pageNumber}`}
                                        style={{
                                            display:"flex",
                                            justifyContent:"center",
                                            width:"100%"
                                        }}
                                    >
                                        <div className="document-preview-page-shell">
                                            <div className="pdf-page-overlay-host">
                                                <Page
                                                    pageNumber={pageNumber}
                                                    renderTextLayer={true}
                                                    renderAnnotationLayer={true}
                                                    width={pdfPageWidth}
                                                />
                                                {
                                                    Number(activeRisk?.page) === pageNumber
                                                    && Array.isArray(activeRisk?.ocr_highlight_boxes)
                                                    && activeRisk.ocr_highlight_boxes.length > 0
                                                    && (
                                                        <div className="ocr-highlight-layer" aria-hidden="true">
                                                            {activeRisk.ocr_highlight_boxes.map((box,index)=>(
                                                                <span
                                                                    key={`${box.x}-${box.y}-${index}`}
                                                                    className={getOcrHighlightClass(activeRisk.level)}
                                                                    style={{
                                                                        left:`${Number(box.x) * 100}%`,
                                                                        top:`${Number(box.y) * 100}%`,
                                                                        width:`${Number(box.width) * 100}%`,
                                                                        height:`${Number(box.height) * 100}%`
                                                                    }}
                                                                />
                                                            ))}
                                                        </div>
                                                    )
                                                }
                                            </div>
                                            {numPages > 0 && (
                                                <div className="document-page-number">
                                                    第 {pageNumber} 页 / 共 {numPages} 页
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </Document>
                            </div>
                        )
                        : (
                            <div id={`page-${pageNumber}`} className="docx-preview-page">
                                <div className="docx-preview-content">
                                    {
                                        renderHighlightedDocxText(
                                            docxPreviewPages[pageNumber - 1]?.text || "",
                                            activeRisk?.highlight_words
                                        )
                                    }
                                </div>
                                <div className="document-page-number">
                                    第 {pageNumber} 页 / 共 {numPages} 页
                                </div>
                            </div>
                        )
            }

            {!previewError && (
                <div
                    style={{
                        display:"flex",
                        justifyContent:"center",
                        alignItems:"center",
                        gap:16,
                        marginTop:20,
                        flexWrap:"wrap"
                    }}
                >
                    <Button disabled={pageNumber <= 1} onClick={onPreviousPage}>
                        上一页
                    </Button>
                    <span style={{fontSize:13, color:"#595959"}}>
                        第 {pageNumber} 页 / 共 {numPages} 页
                    </span>
                    <Button disabled={pageNumber >= numPages} onClick={onNextPage}>
                        下一页
                    </Button>
                </div>
            )}
        </Card>
    );
}
