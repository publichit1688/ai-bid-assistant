import os
import struct
import zipfile

import fitz   # pymupdf
import olefile
from olefile.olefile import NotOleFileError

from docx import Document
from app.services.ocr import get_ocr_client, get_ocr_max_pages, ocr_is_needed
from app.services.word_preview import ensure_word_preview_pdf


class DocumentParseError(ValueError):
    """Raised when an accepted document cannot be converted to usable text."""


def _paginate_text(full_text, page_size=3000):
    return [
        {"page": i // page_size + 1, "text": full_text[i:i + page_size]}
        for i in range(0, len(full_text), page_size)
    ]




# =====================================
# 统一入口
# =====================================

def parse_document(filepath):


    ext = os.path.splitext(filepath)[1].lower()



    if ext == ".pdf":

        return read_pdf(filepath)



    elif ext in {".docx", ".doc"}:

        if ext == ".docx":
            validate_docx_container(filepath)

        # Word 文件先由版式引擎转换成 PDF，再按转换后的真实页进行
        # 文本提取和风险定位，保证分析页码与用户看到的预览一致。
        preview_pdf = ensure_word_preview_pdf(filepath)
        return read_pdf(str(preview_pdf))



    else:

        raise DocumentParseError("仅支持 PDF、DOCX 和 DOC 文件")







# =====================================
# PDF解析
# 返回真实页码
# =====================================

def read_pdf(path):

    pages = []
    scanned_indexes = []
    doc = open_pdf_document(path)

    with doc:
        for index, page in enumerate(doc):
            text = page.get_text()
            pages.append({"page": index + 1, "text": text})
            if ocr_is_needed(text) and page.get_images(full=True):
                scanned_indexes.append(index)

        max_ocr_pages = get_ocr_max_pages()
        if len(scanned_indexes) > max_ocr_pages:
            raise DocumentParseError(
                f"扫描页共 {len(scanned_indexes)} 页，超过单次 OCR 上限 {max_ocr_pages} 页"
            )
        if scanned_indexes:
            ocr_client = get_ocr_client()
            for index in scanned_indexes:
                ocr_result = ocr_client.recognize_pdf_page(doc[index])
                text = str(ocr_result.get("text") or "")
                if not text.strip():
                    raise DocumentParseError(
                        f"第 {index + 1} 页未识别到可分析的文字内容"
                    )
                pages[index]["text"] = text
                pages[index]["text_source"] = "baidu_ocr"
                pages[index]["ocr_lines"] = ocr_result.get("lines") or []

    if not any(item["text"].strip() for item in pages):
        raise DocumentParseError("PDF 文件未提取到可分析的文字内容")



    print("====================")

    print(
        "PDF页数:",
        len(pages)
    )


    print("====================")



    return pages


def open_pdf_document(path):
    """Open PDF from bytes so malformed input cannot lock its upload path."""
    try:
        with open(path, "rb") as source:
            pdf_content = source.read()
        if not pdf_content.startswith(b"%PDF-"):
            raise DocumentParseError("PDF 文件已损坏或格式无法识别")
    except DocumentParseError:
        raise
    except OSError as exc:
        raise DocumentParseError("PDF 文件无法读取") from exc

    try:
        # Parse from memory so malformed PDFs cannot leave a Windows file
        # handle attached to the request's temporary upload.
        return fitz.open(stream=pdf_content, filetype="pdf")
    except (OSError, RuntimeError, ValueError) as exc:
        raise DocumentParseError("PDF 文件已损坏或格式无法识别") from exc







# =====================================
# DOCX解析
# DOCX没有真实页码
# 按3000字符模拟分页
# =====================================

def read_docx(path):


    doc = Document(path)



    full_text = ""



    for paragraph in doc.paragraphs:


        full_text += (

            paragraph.text

            + "\n"

        )





    pages = _paginate_text(full_text)





    return pages


def validate_docx_container(path):
    """Reject malformed DOCX locally before invoking Word/WPS automation."""
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            required = {"[Content_Types].xml", "word/document.xml"}
            if not required.issubset(names):
                raise DocumentParseError("DOCX 文件结构不完整或格式无法识别")
            for name in required:
                archive.read(name)
    except DocumentParseError:
        raise
    except (OSError, RuntimeError, zipfile.BadZipFile, KeyError) as exc:
        raise DocumentParseError("DOCX 文件已损坏或格式无法识别") from exc


def _read_u16(data, offset):
    return struct.unpack_from("<H", data, offset)[0]


def _read_u32(data, offset):
    return struct.unpack_from("<I", data, offset)[0]


def _extract_doc_piece_table(word_stream, table_stream):
    """Extract Word 97-2003 text using the CLX piece table."""
    if len(word_stream) < 34:
        raise DocumentParseError("DOC 文件结构不完整")

    flags = _read_u16(word_stream, 10)
    if flags & 0x0100:
        raise DocumentParseError("暂不支持加密的 DOC 文件，请先解除密码或另存为 DOCX")

    offset = 32
    csw = _read_u16(word_stream, offset)
    offset += 2 + csw * 2
    cslw = _read_u16(word_stream, offset)
    offset += 2 + cslw * 4
    pair_count = _read_u16(word_stream, offset)
    offset += 2
    clx_index = 33
    if pair_count <= clx_index or offset + (clx_index + 1) * 8 > len(word_stream):
        raise DocumentParseError("DOC 文件缺少文本索引")

    fc_clx = _read_u32(word_stream, offset + clx_index * 8)
    lcb_clx = _read_u32(word_stream, offset + clx_index * 8 + 4)
    clx = table_stream[fc_clx:fc_clx + lcb_clx]
    cursor = 0
    while cursor < len(clx) and clx[cursor] == 0x01:
        if cursor + 3 > len(clx):
            raise DocumentParseError("DOC 文本索引已损坏")
        cursor += 3 + _read_u16(clx, cursor + 1)
    if cursor + 5 > len(clx) or clx[cursor] != 0x02:
        raise DocumentParseError("DOC 文件未包含可读取的文本段")

    plc_length = _read_u32(clx, cursor + 1)
    plc = clx[cursor + 5:cursor + 5 + plc_length]
    if plc_length < 4 or (plc_length - 4) % 12:
        raise DocumentParseError("DOC 文本段索引格式无效")
    piece_count = (plc_length - 4) // 12
    cp_values = [_read_u32(plc, i * 4) for i in range(piece_count + 1)]
    pcd_offset = 4 * (piece_count + 1)
    parts = []
    for index in range(piece_count):
        char_count = cp_values[index + 1] - cp_values[index]
        fc_value = _read_u32(plc, pcd_offset + index * 8 + 2)
        compressed = bool(fc_value & 0x40000000)
        file_offset = fc_value & 0x3FFFFFFF
        if compressed:
            file_offset //= 2
            raw = word_stream[file_offset:file_offset + char_count]
            parts.append(raw.decode("cp1252", errors="replace"))
        else:
            raw = word_stream[file_offset:file_offset + char_count * 2]
            parts.append(raw.decode("utf-16le", errors="replace"))
    return "".join(parts)


def read_doc(path):
    """Read legacy binary Word documents without requiring Microsoft Word."""
    try:
        with olefile.OleFileIO(path) as container:
            if not container.exists("WordDocument"):
                raise DocumentParseError("不是有效的 Word 97-2003 DOC 文件")
            word_stream = container.openstream("WordDocument").read()
            flags = _read_u16(word_stream, 10)
            table_name = "1Table" if flags & 0x0200 else "0Table"
            if not container.exists(table_name):
                raise DocumentParseError("DOC 文件缺少文本索引流")
            table_stream = container.openstream(table_name).read()
            full_text = _extract_doc_piece_table(word_stream, table_stream)
    except DocumentParseError:
        raise
    except (OSError, NotOleFileError, struct.error) as exc:
        raise DocumentParseError("DOC 文件已损坏或格式无法识别") from exc

    full_text = full_text.replace("\r", "\n").replace("\x0b", "\n").replace("\x0c", "\n")
    full_text = "".join(char for char in full_text if char in "\n\t" or ord(char) >= 32)
    if not full_text.strip():
        raise DocumentParseError("DOC 文件未提取到可分析的文字内容")
    return _paginate_text(full_text)
