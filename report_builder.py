from jinja2 import Template
from datetime import datetime

TEMPLATE_WITH_IMAGES = """# Environmental Assessment Brief — {{ city }} ({{ parameter.upper() }})
**Period:** {{ start }} to {{ end }}  
**Source:** OpenAQ (v3)

## Executive Summary
- Average {{ parameter }}: **{{ kpis.mean }} µg/m³** (median **{{ kpis.median }}**, p95 **{{ kpis.p95 }}**)
- Days above threshold ({{ who }} µg/m³): **{{ kpis.days_exceed }}/{{ kpis.days_total }}** (**{{ kpis.exceed_pct }}%**)
- 90-day rolling trend vs prior 90 days: **{{ trend }}**

Overall, levels were {{ summary_word }} relative to the selected guideline.

## Baseline & Data
Data pulled from OpenAQ for *{{ city }}* between **{{ start }}** and **{{ end }}**. Values are daily means across selected sensors.

## Key Findings
- Exceedance rate: **{{ kpis.exceed_pct }}%** of days
- Peaks/seasonality visible in rolling chart
- Locations with highest readings may warrant targeted mitigations

## Recommended Mitigations (generic)
- Dust control and transport emissions management
- Targeted hotspot monitoring; public alerts on high-pollution days

## Charts
![Daily Mean](../charts/{{ report_name }}_timeseries.png)

![{{ window }}-day Rolling Mean](../charts/{{ report_name }}_rolling{{ window }}.png)

## Appendix
- Parameter: **{{ parameter }}**
- WHO threshold: **{{ who }} µg/m³**
- Generated on: {{ now }}
"""

TEMPLATE_NO_IMAGES = """# Environmental Assessment Brief — {{ city }} ({{ parameter.upper() }})
**Period:** {{ start }} to {{ end }}  
**Source:** OpenAQ (v3)

## Executive Summary
- Average {{ parameter }}: **{{ kpis.mean }} µg/m³** (median **{{ kpis.median }}**, p95 **{{ kpis.p95 }}**)
- Days above threshold ({{ who }} µg/m³): **{{ kpis.days_exceed }}/{{ kpis.days_total }}** (**{{ kpis.exceed_pct }}%**)
- 90-day rolling trend vs prior 90 days: **{{ trend }}**

Overall, levels were {{ summary_word }} relative to the selected guideline. Charts are displayed in the app above.

## Baseline & Data
Data pulled from OpenAQ for *{{ city }}* between **{{ start }}** and **{{ end }}**. Values are daily means across selected sensors.

## Key Findings
- Exceedance rate: **{{ kpis.exceed_pct }}%** of days
- Peaks/seasonality visible in rolling chart
- Locations with highest readings may warrant targeted mitigations

## Recommended Mitigations (generic)
- Dust control and transport emissions management
- Targeted hotspot monitoring; public alerts on high-pollution days

## Appendix
- Parameter: **{{ parameter }}**
- WHO threshold: **{{ who }} µg/m³**
- Generated on: {{ now }}
"""

def render_markdown(city: str, parameter: str, start: str, end: str,
                    kpis: dict, who: float, report_name: str,
                    window: int = 30, include_images: bool = True) -> str:
    trend = f"{kpis['trend_pct_90d']}%" if kpis.get("trend_pct_90d") is not None else "N/A"
    summary_word = "elevated" if (kpis.get("exceed_pct") or 0) >= 10 else "moderate"
    tpl = TEMPLATE_WITH_IMAGES if include_images else TEMPLATE_NO_IMAGES
    return Template(tpl).render(
        city=city, parameter=parameter, start=start, end=end, kpis=kpis, who=who,
        trend=trend, report_name=report_name, window=window,
        now=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), summary_word=summary_word
    )
