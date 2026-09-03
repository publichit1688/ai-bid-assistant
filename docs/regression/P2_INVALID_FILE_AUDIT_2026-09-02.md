# P2 异常文件安全回归

日期：2026-09-02

本批样本全部由测试代码人工构造，不包含真实业务数据，不调用 WPS、百度 OCR 或 DeepSeek。

## 覆盖结果

| 场景 | HTTP | 错误代码 | 外部调用 | 上传残留 | 数据库残留 |
| --- | ---: | --- | --- | ---: | ---: |
| 结构损坏但带合法文件头的 PDF | 422 | `DOCUMENT_PARSE_ERROR` | 无 | 0 | 0 |
| 非法 ZIP/Word 结构的 DOCX | 422 | `DOCUMENT_PARSE_ERROR` | 无 | 0 | 0 |
| 不支持的扩展名 | 415 | `UNSUPPORTED_FILE_TYPE` | 无 | 0 | 0 |

## 发现与修复

首次真实字节测试中，结构损坏 PDF 虽返回422，但PyMuPDF按路径打开后在Windows保留文件句柄，导致 `.uploading.pdf` 清理失败。修复后PDF从请求临时文件读取为内存字节流，再由PyMuPDF解析；损坏输入不再锁住上传路径。

DOCX增加本地容器预检：必须是有效ZIP并包含 `[Content_Types].xml` 与 `word/document.xml`，否则在调用Microsoft Word/WPS前返回422。测试同时锁定损坏文件不得进入DeepSeek。

## 结论

三类异常输入均具备明确、可识别的客户端错误，失败事务不会留下文件或数据库记录，也不会产生第三方调用和费用。异常文件覆盖通过。
