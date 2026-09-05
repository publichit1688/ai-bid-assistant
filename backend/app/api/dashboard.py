import hashlib
import json

from app.models import DashboardAICache

from fastapi import APIRouter

from app.database import SessionLocal
from app.models import (
    BidFile,
    DashboardAICache
)
from app.services.llm import analyze_dashboard_management
from app.services.risk_scoring import calculate_risk_summary
from app.services.ai_errors import AIResponseFormatError, to_ai_http_exception


from datetime import datetime, timedelta


router = APIRouter()


def normalize_dashboard_ai_data(data):
    source = data if isinstance(data, dict) else {}
    normalized = {
        "days": source.get("days", 7),
        "total_projects": source.get("total_projects", 0),
        "total_risks": source.get("total_risks", 0),
        "average_score": source.get("average_score", 0),
        "risk_distribution": source.get("risk_distribution") or {},
        "score_distribution": source.get("score_distribution") or {},
        "period_comparison": source.get("period_comparison") or {},
        "attention_projects": source.get("attention_projects") or [],
    }
    try:
        normalized["days"] = int(normalized["days"])
    except (TypeError, ValueError, OverflowError):
        normalized["days"] = 7
    if normalized["days"] not in (7, 30):
        normalized["days"] = 7
    return normalized


def dashboard_ai_fingerprint(data):
    fingerprint_source = json.dumps(
        normalize_dashboard_ai_data(data),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()


# ==================================
# Dashboard
# GET /api/dashboard
# ==================================


def build_dashboard_alerts(
    period_comparison,
    attention_projects
):

    alerts = []


    current_projects = (
        period_comparison.get(
            "current_projects",
            0
        )
    )

    previous_projects = (
        period_comparison.get(
            "previous_projects",
            0
        )
    )


    current_high_risks = (
        period_comparison.get(
            "current_high_risks",
            0
        )
    )

    previous_high_risks = (
        period_comparison.get(
            "previous_high_risks",
            0
        )
    )


    current_average_score = (
        period_comparison.get(
            "current_average_score",
            0
        )
    )

    previous_average_score = (
        period_comparison.get(
            "previous_average_score",
            0
        )
    )


    # ==================================
    # 1. 高风险数量预警
    # ==================================

    if (
        previous_high_risks > 0
        and
        current_high_risks > previous_high_risks
    ):

        alerts.append({

            "type":
                "high_risk_increase",

            "level":
                "high",

            "title":
                "高风险数量上升",

            "message":
                (
                    f"本周期高风险事项为"
                    f"{current_high_risks}项，"
                    f"上一周期为"
                    f"{previous_high_risks}项。"
                ),

            "action":
                (
                    "建议立即复核本周期新增高风险事项，"
                    "优先确认资格条件、废标条款、"
                    "商务付款及重大技术偏差，"
                    "明确风险责任人和处理时限。"
                ),

        })


    elif (
        previous_high_risks == 0
        and
        current_high_risks > 0
    ):

        alerts.append({

            "type":
                "new_high_risk",

            "level":
                "high",

            "title":
                "本周期新增高风险事项",

            "message":
                (
                    f"上一周期暂无高风险数据，"
                    f"本周期识别"
                    f"{current_high_risks}项高风险事项。"
                ),

            "action":
                (
                    "建议对新增高风险事项逐项建立复核清单，"
                    "由商务、技术及项目负责人联合确认，"
                    "在风险处理完成前谨慎推进投标决策。"
                ),

        })



    # ==================================
    # 2. 平均评分下降预警
    # 只有前后两个周期都有项目时才比较
    # ==================================

    if (
        current_projects > 0
        and previous_projects > 0
        and current_average_score < previous_average_score
    ):

        score_drop = round(
            previous_average_score - current_average_score,
            1
        )

        alerts.append({
            "type": "average_score_drop",
            "level": "medium",
            "title": "周期平均评分下降",
            "message": (
                f"本周期共分析{current_projects}个项目，"
                f"平均风险评分为{current_average_score}分，"
                f"较上一周期下降{score_drop}分，"
                f"项目整体风险水平明显上升。"
            ),
            "action": (
                "建议对比上一周期项目，定位评分下降的主要扣分项，"
                "重点检查是否存在重复性风险，必要时提高项目准入标准。"
            )
        })


    # ==================================
    # 3. 极低评分项目
    # ==================================

    very_low_projects = [

        item
        for item in (
            attention_projects
            or
            []
        )

        if (
            item.get(
                "score",
                100
            )
            <
            40
        )

    ]


    if very_low_projects:

        target_projects = []

        for project in very_low_projects:

            target_projects.append({
                "id": project.get("id"),
                "project_name": project.get("project_name"),
                "filename": project.get("filename"),
                "score": project.get("score", 0),
                "high_count": project.get("high_count", 0),
                "risk_count": project.get("risk_count", 0)
            })


        alerts.append({
            "type": "very_low_score_projects",
            "level": "high",
            "title": "存在极低评分项目",
            "message": f"当前共有{len(very_low_projects)}个项目评分低于40分，建议优先人工复核。",
            "action": "建议优先暂停低评分项目的最终投标决策，由商务、技术及项目负责人进行专项复核，确认重大风险可控后再决定是否继续投标。",
            "target_projects": target_projects
        })


    # ==================================
    # 4. 高风险集中项目
    # ==================================

    concentrated_projects = [

        item
        for item in (
            attention_projects
            or
            []
        )

        if (
            item.get(
                "high_count",
                0
            )
            >=
            3
        )

    ]


    if concentrated_projects:

        top_project = sorted(

            concentrated_projects,

            key=lambda x:
                x.get(
                    "high_count",
                    0
                ),

            reverse=True

        )[0]


        alerts.append({
            "type": "risk_concentration",
            "level": "high",
            "title": "项目高风险事项集中",
            "message": (
                f"项目“{top_project.get('project_name') or top_project.get('filename')}”"
                f"包含{top_project.get('high_count', 0)}项高风险事项。"
            ),
            "action": (
                "建议将该项目列入重点关注名单，逐项核查高风险条款，"
                "明确可接受风险、需澄清风险和不可接受风险，"
                "形成专项投标决策意见。"
            ),
            "target_projects": [
                {
                    "id": top_project.get("id"),
                    "project_name": top_project.get("project_name"),
                    "filename": top_project.get("filename"),
                    "score": top_project.get("score", 0),
                    "high_count": top_project.get("high_count", 0),
                    "risk_count": top_project.get("risk_count", 0)
                }
            ]
        })

    # ==================================
    # 5. 生成总体预警级别
    # ==================================

    high_alert_count = len([

        item
        for item in alerts

        if item.get(
            "level"
        )
        ==
        "high"

    ])


    medium_alert_count = len([

        item
        for item in alerts

        if item.get(
            "level"
        )
        ==
        "medium"

    ])


    if high_alert_count >= 2:

        alert_level = "red"

        alert_title = (
            "当前投标风险处于高预警状态"
        )


    elif (
        high_alert_count == 1
        or
        medium_alert_count >= 2
    ):

        alert_level = "orange"

        alert_title = (
            "当前存在需要重点关注的投标风险"
        )


    elif alerts:

        alert_level = "yellow"

        alert_title = (
            "当前存在一般风险变化"
        )


    else:

        alert_level = "green"

        alert_title = (
            "当前未发现明显管理预警"
        )


    return {

        "alert_level":
            alert_level,

        "alert_title":
            alert_title,

        "alert_count":
            len(alerts),

        "alerts":
            alerts

    }

@router.get("/dashboard")
def get_dashboard(
    days: int = 7
    ):

# ==================================
# Dashboard V2.3
# 趋势时间范围
# ==================================

    if days not in [7, 30]:
       days = 7


    db = SessionLocal()

    try:

        files = db.query(
            BidFile
        ).all()


        total_projects = len(
            files
        )


        # 没有项目
        if total_projects == 0:

            return {

                "total_projects": 0,

                "high_risk_projects": 0,

                "total_risks": 0,

                "average_score": 0,

                "management_alert": {

                  "alert_level":
                   "green",

                  "alert_title":
                   "当前暂无项目数据",

                  "alert_count":
                    0,

                 "alerts":
                  []

                },



                "risk_distribution": {
                 "high": 0,

                 "middle": 0,

                 "low": 0
                },

                "score_distribution": {
                    "0_39": 0,
                    "40_59": 0,
                    "60_79": 0,
                    "80_100": 0
                },

                "recent_projects": [],

                "attention_projects": [],

                "analysis_trend": []





            }


        all_projects = []

        total_risks = 0

        total_score = 0

         # ==================================
           # Dashboard V2.3
         # 最近7天趋势
         # ==================================

        today = datetime.now().date()


        # ==================================
        # Dashboard V2.4
        # 周期对比统计
        # ==================================

        current_period = {
            "project_count": 0,
            "high_risk_count": 0,
            "score_total": 0
        }


        previous_period = {
            "project_count": 0,
            "high_risk_count": 0,
            "score_total": 0
        }


        # 当前周期开始日期
        current_start = (
            today
            -
            timedelta(days=days - 1)
        )


        # 上一周期结束日期
        previous_end = (
            current_start
            -
            timedelta(days=1)
        )


        # 上一周期开始日期
        previous_start = (
            previous_end
            -
            timedelta(days=days - 1)
        )


        # ==================================
        # Dashboard V2.3
        # 趋势数据初始化
        # ==================================

        trend_map = {}


        for i in range(
            days - 1,
            -1,
            -1
        ):

            day = today - timedelta(
                days=i
            )

            key = day.strftime(
                "%Y-%m-%d"
            )

            trend_map[key] = {

                "date": key,

                "project_count": 0,

                "risk_count": 0,

                "high_risk_count": 0,

                "middle_risk_count": 0,

                "low_risk_count": 0,

                "average_score_total": 0,

                "average_score_count": 0

            }



        # ==================================
        # Dashboard V2.1
        # 风险等级分布
        # ==================================

        risk_distribution = {

            "high": 0,

            "middle": 0,

            "low": 0

        }


        # ==================================
        # Dashboard V2.1
        # 项目评分分布
        # ==================================

        score_distribution = {

            "0_39": 0,

            "40_59": 0,

            "60_79": 0,

            "80_100": 0

        }


        # ==================================
        # 遍历所有项目
        # ==================================

        for item in files:

            risk_data = []


            if item.risk:

                try:

                    risk_data = json.loads(
                        item.risk
                    )

                except Exception:

                    risk_data = []


            summary = calculate_risk_summary(
                risk_data
            )


            # ==================================
            # V2.3 最近7天趋势统计
            # ==================================

            created_date = None


            if item.created_time:

                try:

                    created_date = (
                        item.created_time.date()
                    )

                except Exception:

                    created_date = None

            # ==================================
            # Dashboard V2.4
            # 当前周期 / 上一周期统计
            # ==================================

            if created_date:

                # ==============================
                # 当前周期
                # ==============================

                if (
                    current_start
                    <= created_date
                    <= today
                ):



                    current_period[
                        "project_count"
                    ] += 1

                    current_period[
                        "high_risk_count"
                    ] += summary[
                        "high_count"
                    ]

                    current_period[
                        "score_total"
                    ] += summary[
                        "score"
                    ]


                # ==============================
                # 上一周期
                # ==============================

                elif (
                    previous_start
                    <= created_date
                    <= previous_end
                ):

                    previous_period[
                        "project_count"
                    ] += 1

                    previous_period[
                        "high_risk_count"
                    ] += summary[
                        "high_count"
                    ]

                    previous_period[
                        "score_total"
                    ] += summary[
                        "score"
                    ]



                if created_date:

                    date_key = (
                        created_date.strftime(
                            "%Y-%m-%d"
                        )
                    )


                    if date_key in trend_map:

                        trend_map[date_key][
                            "project_count"
                        ] += 1


                        trend_map[date_key][
                            "risk_count"
                        ] += summary[
                            "risk_count"
                        ]


                        trend_map[date_key][
                            "high_risk_count"
                        ] += summary[
                            "high_count"
                        ]


                        trend_map[date_key][
                            "middle_risk_count"
                        ] += summary[
                            "middle_count"
                        ]


                        trend_map[date_key][
                            "low_risk_count"
                        ] += summary[
                            "low_count"
                        ]


                        trend_map[date_key][
                            "average_score_total"
                        ] += summary[
                            "score"
                        ]


                        trend_map[date_key][
                            "average_score_count"
                        ] += 1


                # ==================================
                # V2.1 风险等级分布统计
                # ==================================

                risk_distribution[
                    "high"
                ] += summary[
                    "high_count"
                ]


                risk_distribution[
                    "middle"
                ] += summary[
                    "middle_count"
                ]


                risk_distribution[
                    "low"
                ] += summary[
                    "low_count"
                ]


                # ==================================
                # V2.1 项目评分分布
                # ==================================

                current_score = summary[
                    "score"
                ]


                if current_score < 40:

                    score_distribution[
                        "0_39"
                    ] += 1


                elif current_score < 60:

                    score_distribution[
                        "40_59"
                    ] += 1


                elif current_score < 80:

                    score_distribution[
                        "60_79"
                    ] += 1


                else:

                    score_distribution[
                        "80_100"
                    ] += 1


                # ==================================
                # 总风险 / 总评分
                # ==================================

                total_risks += summary[
                    "risk_count"
                ]


                total_score += summary[
                    "score"
                ]


                # ==================================
                # 加入全部项目列表
                # ==================================

                all_projects.append({

                    "id":
                        item.id,

                    "filename":
                        item.filename,

                    "project_name":
                        item.project_name
                        or
                        item.filename,

                    "score":
                        summary["score"],

                    "score_level":
                        summary[
                            "score_level"
                        ],

                    "risk_count":
                        summary[
                            "risk_count"
                        ],

                    "high_count":
                        summary[
                            "high_count"
                        ],

                    "middle_count":
                        summary[
                            "middle_count"
                        ],

                    "low_count":
                        summary[
                            "low_count"
                        ],

                    "total_deduction":
                        summary[
                            "total_deduction"
                        ],

                    "status":
                        item.status,

                    "created_time":
                        (
                            str(
                                item.created_time
                            )
                            if item.created_time
                            else ""
                        )

                })


            # ==================================
        # 平均评分
        # ==================================

        average_score = round(
            total_score
            /
            total_projects,
            1
        )


        # ==================================
        # 高风险项目数量
        #
        # 高风险 + 极高风险都算
        # ==================================

        high_risk_projects = len([
            item
            for item in all_projects
            if item["score"] < 60
        ])





        # ==================================
        # 最近分析项目
        # 按ID倒序
        # ==================================

        recent_projects = sorted(

            all_projects,

            key=lambda x:
            x["id"],

            reverse=True

        )[:5]


        # ==================================
        # 重点关注项目
        #
        # 条件：
        # 1. score < 60
        # 或
        # 2. 至少1个高风险
        #
        # 排序：
        # 高风险越多越靠前
        # 总扣分越高越靠前
        # 评分越低越靠前
        # ==================================

        attention_projects = [

            item
            for item in all_projects

            if (
                item["score"] < 60
                or
                item["high_count"] > 0
            )

        ]


        attention_projects = sorted(

            attention_projects,

            key=lambda x: (

                -x["high_count"],

                -x["total_deduction"],

                x["score"]

            )

        )[:10]


        # ==================================
        # Dashboard V2.4
        # 当前周期平均评分
        # ==================================

        if current_period[
            "project_count"
        ] > 0:

            current_average_score = round(

                current_period[
                    "score_total"
                ]
                /
                current_period[
                    "project_count"
                ],

                1

            )

        else:

            current_average_score = 0


        # ==================================
        # 上一周期平均评分
        # ==================================

        if previous_period[
            "project_count"
        ] > 0:

            previous_average_score = round(

                previous_period[
                    "score_total"
                ]
                /
                previous_period[
                    "project_count"
                ],

                1

            )

        else:

            previous_average_score = 0


        # ==================================
        # 百分比变化计算
        # ==================================

        def calculate_change(
            current,
            previous
        ):

            if previous == 0:

                if current == 0:
                    return 0

                return 100


            return round(

                (
                    current
                    -
                    previous
                )
                /
                previous
                *
                100,

                1

            )


        # ==================================
        # Dashboard V2.4
        # 周期对比结果
        # ==================================

        period_comparison = {

            "days":
                days,


            # 项目分析量
            "current_projects":
                current_period[
                    "project_count"
                ],

            "previous_projects":
                previous_period[
                    "project_count"
                ],

            "project_change_percent":
                calculate_change(

                    current_period[
                        "project_count"
                    ],

                    previous_period[
                        "project_count"
                    ]

                ),


            # 高风险数量
            "current_high_risks":
                current_period[
                    "high_risk_count"
                ],

            "previous_high_risks":
                previous_period[
                    "high_risk_count"
                ],

            "high_risk_change_percent":
                calculate_change(

                    current_period[
                        "high_risk_count"
                    ],

                    previous_period[
                        "high_risk_count"
                    ]

                ),


            # 平均评分
            "current_average_score":
                current_average_score,

            "previous_average_score":
                previous_average_score,

            "average_score_change":
                round(

                    current_average_score
                    -
                    previous_average_score,

                    1

                )

        }


        # ==================================
        # V2.3 整理趋势
        # ==================================

        analysis_trend = []

        # ==================================
        # V2.3 整理最近7天趋势
        # ==================================

        analysis_trend = []


        for key in trend_map:

            trend_item = trend_map[key]


            if trend_item[
                "average_score_count"
            ] > 0:

                average_score_day = round(

                    trend_item[
                        "average_score_total"
                    ]
                    /
                    trend_item[
                        "average_score_count"
                    ],

                    1

                )

            else:

                average_score_day = 0


            analysis_trend.append({

                "date":
                    trend_item["date"],

                "project_count":
                    trend_item[
                        "project_count"
                    ],

                "risk_count":
                    trend_item[
                        "risk_count"
                    ],

                "high_risk_count":
                    trend_item[
                        "high_risk_count"
                    ],

                "middle_risk_count":
                    trend_item[
                        "middle_risk_count"
                    ],

                "low_risk_count":
                    trend_item[
                        "low_risk_count"
                    ],

                "average_score":
                    average_score_day

            })

        # ==================================
        # Dashboard V2.6
        # AI管理预警基础规则
        # ==================================

        management_alert = (
            build_dashboard_alerts(
                period_comparison,
                attention_projects
            )
        )


        # ==================================
        # 返回
        # ==================================

        return {

            "total_projects":
                total_projects,

            "high_risk_projects":
                high_risk_projects,

            "total_risks":
                total_risks,

            "average_score":
                average_score,

           # ==========================
           # Dashboard V2.1
           # ==========================

            "risk_distribution":
                risk_distribution,
            "score_distribution":
                score_distribution,

            "analysis_trend":
                analysis_trend,


            # ==========================
            # Dashboard V2.4
            # ==========================

            "period_comparison":
                period_comparison,

            "management_alert":
                management_alert,


            "recent_projects":
                recent_projects,

            "attention_projects":
                attention_projects



        }

    except Exception:

        raise

    finally:

        db.close()


@router.post("/dashboard/ai-summary")
def dashboard_ai_summary(
    data: dict
):

    db = SessionLocal()

    try:

        # ==================================
        # V2.5.3
        # 生成稳定的数据指纹
        # ==================================

        normalized_data = normalize_dashboard_ai_data(data)
        fingerprint = dashboard_ai_fingerprint(normalized_data)
        days = normalized_data["days"]


        print(
            "Dashboard AI缓存指纹:",
            fingerprint[:12]
        )


        # ==================================
        # 1. 查询数据库缓存
        # ==================================

        cache = db.query(
            DashboardAICache
        ).filter(

            DashboardAICache.fingerprint
            ==
            fingerprint

        ).first()


        # ==================================
        # 2. 命中缓存
        # ==================================

        if cache:

            print(
                "Dashboard AI摘要：数据库缓存命中"
            )


            try:
                summary = json.loads(cache.summary)
                if not isinstance(summary, dict):
                    raise ValueError("cached summary is not an object")
            except (TypeError, ValueError, json.JSONDecodeError):
                print("Dashboard AI摘要：损坏缓存已失效")
                db.delete(cache)
                db.commit()
                cache = None

            if cache:
                return {

                    "success": True,

                    "cached": True,

                    "summary": summary

                }


        # ==================================
        # 3. 未命中缓存
        # 调用 DeepSeek
        # ==================================

        print(
            "Dashboard AI摘要：数据库缓存未命中，调用AI"
        )


        result = analyze_dashboard_management(
            normalized_data
        )

        if not isinstance(result, dict):
            raise AIResponseFormatError("AI dashboard summary is not an object")


        # ==================================
        # 4. 保存缓存
        # ==================================

        new_cache = DashboardAICache(

            fingerprint=fingerprint,

            days=days,

            summary=json.dumps(
                result,
                ensure_ascii=False
            )

        )


        db.add(
            new_cache
        )

        db.commit()


        print(
            "Dashboard AI摘要：已保存数据库缓存"
        )


        # ==================================
        # 5. 返回
        # ==================================

        return {

            "success": True,

            "cached": False,

            "summary": result

        }


    except Exception as exc:

        db.rollback()


        print("Dashboard AI摘要错误:", type(exc).__name__)
        raise to_ai_http_exception(exc) from exc


    finally:

        db.close()
