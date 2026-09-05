import ReactEChartsCore from "echarts-for-react/esm/core";
import * as echarts from "echarts/core";
import {
    BarChart,
    LineChart,
    PieChart
} from "echarts/charts";
import {
    GridComponent,
    LegendComponent,
    TooltipComponent
} from "echarts/components";
import {LabelLayout} from "echarts/features";
import {CanvasRenderer} from "echarts/renderers";


echarts.use([
    BarChart,
    LineChart,
    PieChart,
    GridComponent,
    LegendComponent,
    TooltipComponent,
    LabelLayout,
    CanvasRenderer
]);


export default function DashboardChart(props){
    return <ReactEChartsCore echarts={echarts} {...props} />;
}
