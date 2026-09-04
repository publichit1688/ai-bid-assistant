import json
from openai import OpenAI
from app.config import (
    get_deepseek_api_key,
    get_deepseek_base_url,
    get_deepseek_model,
    get_deepseek_timeout_seconds,
)
from app.services.ai_errors import AIConfigurationError, AIResponseFormatError



# ==========================
# DeepSeek客户端
# ==========================

def get_deepseek_client():
    """按需创建客户端，避免在日志中暴露密钥或因缺少密钥阻止服务启动。"""
    api_key = get_deepseek_api_key()

    if not api_key:
        raise AIConfigurationError(
            "未配置 DEEPSEEK_API_KEY，AI 分析功能暂不可用"
        )

    return OpenAI(
        api_key=api_key,
        base_url=get_deepseek_base_url(),
        timeout=get_deepseek_timeout_seconds(),
    )


def generate_outline_suggestions(pages):
    """Generate source-backed outline suggestions without persisting provider output."""
    source = "\n\n".join(
        f"【第{item['page']}页】\n{item.get('text', '')}"
        for item in pages
    )[:50000]
    prompt = f"""
你是中国工程建设投标文件目录规划助手。
请仅依据给定招标文件，提出投标文件目录建议。不要生成投标文件正文。

每条建议必须提供：
- title：简洁章节标题；
- parent_index：父章节在 suggestions 数组中的从0开始索引，根章节为 null，且只能指向更早的条目；
- page：依据所在的原始页码；
- quote：该页中可以连续逐字找到的简短原文，不得改写或概括。

只返回合法JSON，严格使用以下结构：
{{"suggestions":[{{"title":"资格审查","parent_index":null,"page":3,"quote":"资格审查标准"}}]}}

招标文件：
{source}
"""
    response = get_deepseek_client().chat.completions.create(
        model=get_deepseek_model("deepseek-chat"),
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "你只能输出可由招标原文验证的目录建议JSON。",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    content = response.choices[0].message.content.strip()
    content = content.replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AIResponseFormatError("AI outline response is not valid JSON") from exc
    if not isinstance(result, dict) or not isinstance(result.get("suggestions"), list):
        raise AIResponseFormatError("AI outline response violates the contract")
    return result


def generate_scoring_criteria(pages):
    """Extract scoring criteria candidates; persistence validates every source quote."""
    source = "\n\n".join(
        f"【第{item['page']}页】\n{item.get('text', '')}"
        for item in pages
    )[:50000]
    prompt = f"""
你是中国工程建设招标文件评分办法提取助手。
请仅提取招标文件中明确出现的评分点，不得推测、补写或生成投标响应正文。

每个评分点必须包含：
- title：评分项简短标题；
- requirement：该评分项的完整响应要求；
- max_score：明确的最高分值，原文未明确时为 null；
- page：依据所在的原始页码；
- quote：该页中可以连续逐字找到的原文片段，不得改写或概括。

只返回合法JSON，严格使用以下结构：
{{"criteria":[{{"title":"项目业绩","requirement":"提供类似项目业绩证明","max_score":5,"page":12,"quote":"类似项目业绩得5分"}}]}}

招标文件：
{source}
"""
    response = get_deepseek_client().chat.completions.create(
        model=get_deepseek_model("deepseek-chat"),
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "你只能输出具有可核验原文来源的评分点JSON。",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    content = response.choices[0].message.content.strip()
    content = content.replace("```json", "").replace("```", "").strip()
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AIResponseFormatError("AI criteria response is not valid JSON") from exc
    if not isinstance(result, dict) or not isinstance(result.get("criteria"), list):
        raise AIResponseFormatError("AI criteria response violates the contract")
    return result





def analyze_bid(text: str):


    # 控制长度
    if len(text) > 50000:

        text = text[:50000]



    prompt = f"""

你是一名中国工程建设招投标专家。

请仔细分析下面的招标文件。


你的任务：

1. 提取项目基本信息

2. 提取技术要求

3. 提取商务资格要求

4. 提取采购清单和表格字段

5. 分析投标风险

6. 标记风险所在PDF页码

7. 给出专业投标建议




========================

字段提取规则：

========================



project_name:

优先寻找：

- 项目名称
- 工程名称
- 招标项目名称
- 工程建设项目名称



tender_company:

优先寻找：

- 招标人
- 招标单位
- 建设单位
- 项目业主



deadline:

优先寻找：

- 投标截止时间
- 投标文件递交截止时间
- 开标时间
- 截止日期



deposit:

优先寻找：

- 投标保证金
- 保证金金额
- 保函金额





========================

technical_requirements

========================


technical_requirements
必须提取技术相关内容，包括：


- 工程范围

- 技术标准

- 施工要求

- 质量要求

- 人员技术要求

- 项目负责人要求

- 技术负责人要求

- 证书要求

- 材料设备要求

- 验收标准

- 工期要求


注意：

人员要求、证书要求也属于技术要求，不要遗漏。







========================

business_requirements

========================


business_requirements
必须提取商务及资格审查内容，包括：


- 企业资质

- 营业执照要求

- 安全生产许可证

- 企业业绩要求

- 财务要求

- 信用要求

- 联合体要求

- 投标文件格式要求

- 电子签名要求

- 盖章要求


========================

procurement_requirements

========================

必须逐页检查表格、清单和合并单元格，不得只分析表格外的正文。

如果存在采购清单，每个采购项分别返回：

- item_name：标的名称或采购项名称
- specification：规格、型号或简要技术要求
- quantity：数量及单位
- budget：该项预算；只有总预算时可填写总预算
- import_allowed：是否接受进口产品
- page：字段所在真实页码

表格中没有明确值时返回空字符串，不得编造。没有采购清单时返回空数组。







========================

风险分析规则

========================


重点寻找：


- 废标风险

- 资格审查风险

- 人员证书风险

- 时间节点风险

- 保证金风险

- 技术方案风险

- 电子签名风险

- 业绩证明风险


risk字段要求：

每个风险必须返回：

page:
风险所在PDF页码


keyword:
风险标题


highlight_words:
PDF需要高亮的关键词数组

要求：
- 必须来自招标文件原文
- 3-8个关键词
- 每个关键词3-12个字


level:
高/中/低


quote:
招标文件原文引用

要求：
- 必须复制原文
- 20-200字


reason:
风险原因


suggestion:
风险处理建议

要求：
- 给出具体整改措施
- 20-100字
- 针对该风险
- 不允许为空





========================


严格返回JSON：

不要Markdown

不要解释

不要代码块


格式：


格式：


{{
"project_name":"",
"tender_company":"",
"deadline":"",
"deposit":"",
"technical_requirements":[],
"business_requirements":[],
"procurement_requirements":[
    {{
        "item_name":"",
        "specification":"",
        "quantity":"",
        "budget":"",
        "import_allowed":"",
        "page":1
    }}
],
"risk_level":"",
"risk":[
    {{
        "page":1,

        "keyword":"",

        "highlight_words":[
            ""
        ],

        "level":"",

        "quote":"",

        "reason":"",

        "suggestion":""
    }}
],
"suggestion":""
}}



========================


招标文件内容：

{text}


"""



    try:


        response = get_deepseek_client().chat.completions.create(


            model=get_deepseek_model("deepseek-v4-flash"),



            response_format={

                "type":"json_object"

            },



            messages=[


                {

                    "role":"system",

                    "content":
                    "你是招投标分析AI，只返回合法JSON"

                },


                {

                    "role":"user",

                    "content":prompt

                }

            ]

        )



        content = response.choices[0].message.content.strip()



        # 防止代码块

        if content.startswith("```json"):


            content = content.replace(
                "```json",
                ""
            ).replace(
                "```",
                ""
            ).strip()



        elif content.startswith("```"):


            content = content.replace(
                "```",
                ""
            ).strip()




        result = json.loads(content)



        return result





    except json.JSONDecodeError as exc:
        raise AIResponseFormatError("AI bid response is not valid JSON") from exc


def analyze_compare_decision(compare_data):

    try:

        project_a = compare_data.get(
            "projectA",
            {}
        ) or {}

        project_b = compare_data.get(
            "projectB",
            {}
        ) or {}


        # =====================================
        # 控制发送给AI的数据
        # =====================================

        ai_input = {

            "projectA": {

                "project_name":
                    project_a.get("project_name"),

                "score":
                    project_a.get("score"),

                "score_level":
                    project_a.get("score_level"),

                "high_count":
                    project_a.get("high_count"),

                "middle_count":
                    project_a.get("middle_count"),

                "low_count":
                    project_a.get("low_count"),

                "total_deduction":
                    project_a.get("total_deduction"),

                "risk":
                    project_a.get("risk", [])

            },


            "projectB": {

                "project_name":
                    project_b.get("project_name"),

                "score":
                    project_b.get("score"),

                "score_level":
                    project_b.get("score_level"),

                "high_count":
                    project_b.get("high_count"),

                "middle_count":
                    project_b.get("middle_count"),

                "low_count":
                    project_b.get("low_count"),

                "total_deduction":
                    project_b.get("total_deduction"),

                "risk":
                    project_b.get("risk", [])

            },


            "decisionScoreA":
                compare_data.get(
                    "decisionScoreA"
                ),

            "decisionScoreB":
                compare_data.get(
                    "decisionScoreB"
                ),

            "recommended":
                compare_data.get(
                    "recommended"
                ),

            "confidenceLevel":
                compare_data.get(
                    "confidenceLevel"
                ),

            "commonCategories":
                compare_data.get(
                    "commonCategories",
                    []
                ),

            "onlyARisks":
                compare_data.get(
                    "onlyARisks",
                    []
                ),

            "onlyBRisks":
                compare_data.get(
                    "onlyBRisks",
                    []
                )

        }


        prompt = f"""
你是一名中国工程建设领域的高级招投标顾问。

现在需要根据两个招标项目的AI风险分析结果，
生成一份供企业管理层参考的“投标决策摘要”。

【重要原则】

1. 不允许重新计算系统评分。
2. 不允许修改系统已经给出的推荐项目。
3. AI的作用是解释现有分析结果，而不是覆盖系统算法。
4. 必须结合两个项目的具体风险进行解释。
5. 不得虚构招标文件中不存在的信息。
6. 信息不足时必须明确说明。
7. 重点关注：
   - 资格审查
   - 废标/否决投标
   - 企业资质
   - 人员证书
   - 保证金
   - 电子签章
   - 工期
   - 合同责任
   - 报价
8. 内容面向企业管理层，语言简洁、专业、可执行。

系统对比数据如下：

{json.dumps(
    ai_input,
    ensure_ascii=False
)}

只能返回合法JSON。

禁止返回Markdown。
禁止返回```json。
禁止增加解释文字。

必须严格返回以下结构：

{{
    "executive_summary": "用2-4句话概括两个项目的主要差异和推荐结论",

    "recommended_project": "项目A、项目B或两个项目接近",

    "recommendation_type": "优先推荐、有条件推荐、谨慎推荐、暂缓投标",

    "key_advantages": [
        "推荐项目优势1",
        "推荐项目优势2"
    ],

    "key_risks": [
        "推荐项目仍然存在的核心风险1",
        "核心风险2"
    ],

    "must_resolve_before_bid": [
        "正式投标前必须解决事项1",
        "事项2"
    ],

    "switch_conditions": [
        "什么情况下应该重新评估或改变当前推荐"
    ],

    "management_advice": "给管理层的最终投标决策建议"
}}
"""


        response = get_deepseek_client().chat.completions.create(

            model=get_deepseek_model("deepseek-chat"),

            messages=[

                {
                    "role": "system",
                    "content":
                    "你是一名专业的中国工程建设招投标决策分析顾问。"
                },

                {
                    "role": "user",
                    "content": prompt
                }

            ],

            temperature=0.2

        )


        content = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )


        # =====================================
        # 防止AI偶尔返回Markdown代码块
        # =====================================

        content = content.replace(
            "```json",
            ""
        )

        content = content.replace(
            "```",
            ""
        )

        content = content.strip()


        result = json.loads(
            content
        )


        return result


    except json.JSONDecodeError as exc:
        raise AIResponseFormatError("AI compare response is not valid JSON") from exc


def analyze_dashboard_management(
    dashboard_data
):

    import json


    prompt = f"""
你是一名中国工程建设招投标管理专家，
正在为企业管理层生成“投标管理驾驶舱 AI 管理摘要”。

请严格根据系统提供的 Dashboard 数据进行分析。

当前统计周期：
最近 {dashboard_data.get("days", 7)} 天


Dashboard 数据：

{json.dumps(
    dashboard_data,
    ensure_ascii=False,
    indent=2
)}


==================================
一、核心数据语义规则
==================================

你必须严格遵守以下规则：


1. 上一周期没有项目时

如果：

previous_projects = 0

则表示：

“上一周期没有有效项目分析数据”。

此时：

previous_average_score = 0

不能理解为：

“上一周期平均评分为0分”。

它真正表示：

“上一周期不存在平均评分数据”。


因此禁止出现：

“平均评分从0分上升至XX分”

“平均评分从0分下降至XX分”

“相比上一周期评分增长XX%”

等描述。


正确表达应该是：

“上一周期暂无项目分析数据，本周期平均评分为XX分，暂不进行跨周期评分比较。”


==================================
二、从0新增数据的表达规则
==================================

如果：

previous_projects = 0

且：

current_projects > 0

不要描述为：

“项目数量增长100%”。

应该描述为：

“上一周期暂无项目，本周期新增X个分析项目。”


如果：

previous_high_risks = 0

且：

current_high_risks > 0

不要描述为：

“高风险增长100%”。

应该描述为：

“本周期新增X项高风险事项。”


==================================
三、风险变化判断
==================================

如果上一周期存在有效数据：

previous_projects > 0

才可以进行正常的周期变化比较。


高风险数量增加：

表示风险暴露上升。


高风险数量减少：

表示风险暴露下降。


平均评分提高：

通常表示整体投标风险状况改善。


平均评分下降：

通常表示整体投标风险状况恶化。


但是所有判断必须依据输入数据，
不得自行编造不存在的原因。


==================================
四、重点项目判断
==================================

重点项目只能根据：

attention_projects

中的实际数据判断。


优先关注：

1. score 较低的项目
2. high_count 较高的项目
3. total_deduction 较高的项目
4. risk_count 较高的项目


如果 attention_projects 为空：

必须明确说明：

“当前暂无需要特别关注的项目。”

不得虚构项目名称。


==================================
五、禁止虚构
==================================

禁止自行推测：

- 项目为什么产生风险
- 企业内部管理问题
- 人员能力问题
- 项目集中涌入
- 管理压力增加
- 企业资源不足
- 招标方意图
- 财务状况
- 项目实际执行情况

除非 Dashboard 数据中明确提供相关依据。


例如：

仅仅因为本周期项目数量增加，

不能直接推断：

“项目集中涌入带来管理压力”。

应该描述为：

“本周期分析项目数量较上一周期增加，建议关注新增项目的风险复核情况。”


==================================
六、管理建议规则
==================================

管理建议必须：

1. 与当前 Dashboard 数据直接相关
2. 简洁
3. 可执行
4. 不夸大风险
5. 不提供没有数据依据的结论


可以建议：

- 优先复核高风险项目
- 检查高风险条款
- 对低评分项目进行人工复核
- 关注高风险数量变化
- 对重点项目进行投标前复核


不得无依据要求：

- 立即停止全部投标
- 认定项目一定不能投
- 认定企业存在管理缺陷


==================================
七、输出要求
==================================

只能返回合法 JSON。

禁止 Markdown。

禁止 ```json。

禁止任何 JSON 之外的解释文字。

所有字段必须存在。


严格按照下面结构返回：

{{
    "overall_status":
        "总体判断",

    "risk_change":
        "风险变化分析",

    "key_attention":
        "重点关注事项",

    "management_advice":
        "管理建议"
}}


字段要求：

overall_status：
用1-2句话概括当前周期整体情况。

risk_change：
说明本周期与上一周期的风险变化。
如果上一周期无数据，必须明确说明无法进行完整同比。

key_attention：
指出最需要关注的项目或风险情况。
只能使用实际提供的数据。

management_advice：
给管理层2-3项简洁、可执行的建议。


全部使用简体中文。

语言风格：

专业、客观、克制、适合企业管理驾驶舱。
"""


    response = get_deepseek_client().chat.completions.create(

        model=get_deepseek_model("deepseek-chat"),

        messages=[

            {
                "role": "system",
                "content":
                    "你是一名中国工程建设招投标管理专家。"
                    "你必须严格依据系统提供的数据进行分析，"
                    "不得虚构事实，不得把无数据误认为数值0。"
            },

            {
                "role": "user",
                "content": prompt
            }

        ],

        temperature=0.2

    )


    content = (
        response
        .choices[0]
        .message
        .content
    )


    content = (
        content
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )


    try:
        return json.loads(content)
    except json.JSONDecodeError as exc:
        raise AIResponseFormatError("AI dashboard response is not valid JSON") from exc
