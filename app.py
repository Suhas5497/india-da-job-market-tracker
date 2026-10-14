"""India Data Analyst Job Market Tracker - Streamlit dashboard."""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent
GOLD, BLUE = "#bf8a2a", "#4a8ee6"           # validated: CVD dE 25+, contrast >= 3:1 on dark surface
SURFACE, INK, MUTED, GRID = "#0f1424", "#e8ecf3", "#9aa3b5", "#232a3d"

st.set_page_config(page_title="India DA Job Market Tracker", page_icon="📊", layout="wide")
st.markdown(f"""<style>
.stApp {{background:{SURFACE}; color:{INK};}}
.kpi {{background:#151b2e;border:1px solid {GRID};border-radius:10px;padding:16px 18px;}}
.kpi .v {{font-size:2.1rem;font-weight:700;color:{INK};line-height:1.1}}
.kpi .l {{font-size:.86rem;color:{MUTED};margin-top:4px}}
.kpi .s {{font-size:.75rem;color:{MUTED};opacity:.8;margin-top:2px}}
</style>""", unsafe_allow_html=True)


@st.cache_data
def load():
    d = pd.read_csv(ROOT / "data/processed/jobs.csv")
    d["fresher_friendly"] = (d.seniority != "Senior") & (
        d.seniority.isin(["Intern", "Junior"]) | (d.min_years <= 1) | (d.says_fresher & d.min_years.isna()))
    return d


def layout(fig, h=360):
    fig.update_layout(height=h, paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, font=dict(color=INK, size=13),
                      margin=dict(l=10, r=20, t=10, b=10), bargap=0.25, bargroupgap=0.08,
                      legend=dict(orientation="h", y=1.08, x=0, font=dict(color=MUTED)),
                      hoverlabel=dict(bgcolor="#151b2e", font_color=INK))
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, color=MUTED)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", color=MUTED)
    return fig


def kpi(col, value, label, sub=""):
    col.markdown(f'<div class="kpi"><div class="v">{value}</div><div class="l">{label}</div>'
                 f'<div class="s">{sub}</div></div>', unsafe_allow_html=True)


df_all = load()
span = f"{df_all.date_added.min()} to {df_all.date_added.max()}"

st.title("India Data Analyst Job Market Tracker")
st.caption(f"What Indian employers actually ask of analysts, and how many roles are really open to freshers. "
           f"Snapshot: {len(df_all)} analyst postings, {span}.")

# ---- filters (one row) ----
f1, f2, f3 = st.columns([2, 2, 1])
roles = f1.multiselect("Role family", sorted(df_all.role_family.unique()),
                       default=["Data Analyst", "Business Analyst", "Product Analyst"])
cities = f2.multiselect("City", df_all.city.value_counts().index.tolist(), placeholder="All cities")
fresher_only = f3.toggle("Fresher-friendly only", value=False)
df = df_all[df_all.role_family.isin(roles)] if roles else df_all
if cities:
    df = df[df.city.isin(cities)]
view = df[df.fresher_friendly] if fresher_only else df
if view.empty:
    st.warning("No postings match these filters.")
    st.stop()

# ---- KPI row ----
fr = df[df.fresher_friendly]
stated = df.min_years.notna().sum()
sal = fr[(fr.salary_lpa_low.notna()) & (fr.seniority != "Intern")]
k1, k2, k3, k4 = st.columns(4)
kpi(k1, f"{len(df):,}", "analyst postings in view")
kpi(k2, f"{100 * len(fr) / len(df):.1f}%", "are fresher-friendly", f"{len(fr)} postings")
kpi(k3, f"{100 * (df.min_years <= 1).sum() / max(stated, 1):.1f}%", "ask for 0-1 years",
    f"of {stated} postings that state a number")
kpi(k4, f"₹{((sal.salary_lpa_low + sal.salary_lpa_high) / 2).median():.1f} L" if len(sal) else "n/a",
    "median fresher salary (annual)", f"only {len(sal)} postings publish one" if len(sal) else "none published")
st.write("")

# ---- skills: fresher-friendly vs all ----
st.subheader("Skills employers mention")
skill_cols = [c for c in df.columns if c.startswith("skill_") and c != "skill_Communication"]
share_all = (df[skill_cols].mean() * 100).rename(lambda c: c[6:])
share_fr = (fr[skill_cols].mean() * 100).rename(lambda c: c[6:]) if len(fr) else share_all * 0
order = share_all.sort_values().index[-12:]
fig = go.Figure()
fig.add_bar(y=order, x=share_all[order], orientation="h", name=f"All postings (n={len(df)})", marker_color=BLUE,
            hovertemplate="%{y}: %{x:.1f}% of all postings<extra></extra>")
fig.add_bar(y=order, x=share_fr[order], orientation="h", name=f"Fresher-friendly (n={len(fr)})", marker_color=GOLD,
            hovertemplate="%{y}: %{x:.1f}% of fresher-friendly postings<extra></extra>")
fig.update_traces(marker_line_width=0)
fig.update_layout(legend_traceorder="reversed")
st.plotly_chart(layout(fig, 470).update_xaxes(ticksuffix="%", title=None), width='stretch')
st.caption("Share of postings whose description mentions each skill. 'Communication / stakeholder' is excluded "
           "because it appears in most postings and drowns out the rest.")

c1, c2 = st.columns(2)
# ---- experience asked ----
with c1:
    st.subheader("Experience asked")
    b = pd.cut(df.min_years.dropna(), [-1, 1, 2, 4, 7, 99], labels=["0-1 yrs", "2 yrs", "3-4 yrs", "5-7 yrs", "8+ yrs"])
    vc = b.value_counts().sort_index()
    fig = go.Figure(go.Bar(x=vc.index.astype(str), y=vc.values, marker_color=BLUE, marker_line_width=0,
                           text=[f"{100 * v / vc.sum():.0f}%" for v in vc.values], textposition="outside",
                           textfont_color=MUTED, hovertemplate="%{x}: %{y} postings<extra></extra>"))
    fig = layout(fig, 340)
    fig.update_xaxes(gridcolor="rgba(0,0,0,0)")
    fig.update_yaxes(gridcolor=GRID, title="postings")
    st.plotly_chart(fig, width='stretch')
    st.caption(f"First experience requirement stated in the posting; {stated} of {len(df)} postings state one.")

# ---- cities ----
with c2:
    st.subheader("Where the fresher roles are")
    cs = df.groupby("city").agg(postings=("job_id", "size"), fresher=("fresher_friendly", "sum"))
    cs = cs[cs.postings >= 10].sort_values("postings").tail(10)
    cs["pct"] = 100 * cs.fresher / cs.postings
    fig = go.Figure(go.Bar(y=cs.index, x=cs.pct, orientation="h", marker_color=GOLD, marker_line_width=0,
                           text=[f"{p:.0f}%  ({int(f)} of {int(n)})" for p, f, n in zip(cs.pct, cs.fresher, cs.postings)],
                           textposition="outside", textfont_color=MUTED,
                           hovertemplate="%{y}: %{x:.1f}% fresher-friendly<extra></extra>"))
    fig = layout(fig, 340)
    fig.update_xaxes(ticksuffix="%", range=[0, max(30, cs.pct.max() * 1.6)])
    st.plotly_chart(fig, width='stretch')
    st.caption("Share of each city's postings that are fresher-friendly (cities with 10+ postings). "
               "'Unspecified' = postings with no city, mostly hybrid/remote.")

# ---- table ----
st.subheader("The postings")
show = view[["date_added", "title", "company", "city", "role_family", "seniority", "min_years",
             "salary_text", "url"]].sort_values("date_added", ascending=False)
st.dataframe(show, width='stretch', hide_index=True,
             column_config={"url": st.column_config.LinkColumn("link", display_text="open"),
                            "min_years": st.column_config.NumberColumn("yrs asked", format="%d")})
st.download_button("Download this view (CSV)", show.to_csv(index=False), "india_da_jobs.csv")

with st.expander("Method and limits"):
    st.markdown("""
- **Source:** a public job-listings index (mostly LinkedIn postings) for India, titles matching data, business,
  BI, MIS, product analyst or analytics roles. Finance-operations, QA, security, recruiting and trainer roles are excluded.
- **Fresher-friendly:** not a senior title AND (intern/junior title, OR first stated requirement is 0-1 years,
  OR the posting says fresher/entry level and gives no number).
- **Skills** are keyword matches on the description, so a skill counts when it is mentioned, required or preferred.
- **Salary** is only shown where the posting publishes one, which is a small, non-random subset.
- Full job descriptions are not stored or republished: only derived fields and the original link.
- One weekly snapshot so far; the tracker is designed to append a new week each run.
""")
st.caption("Built by Suhas Dhamapurkar · SQL (DuckDB) + Python + Streamlit")
