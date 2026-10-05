import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.express as px

st.set_page_config(page_title="18 Wheels | Extensiv Migration Portfolio", page_icon="📦", layout="wide")

DATA = Path(__file__).parent / "data" / "migration_portfolio.csv"
AS_OF = "October 5, 2026"

@st.cache_data
def load_data():
    return pd.read_csv(DATA, low_memory=False).fillna("")

df = load_data()

def options(s):
    return sorted([str(x).strip() for x in s.unique() if str(x).strip()])

def pct(a,b):
    return (a/b*100) if b else 0

st.markdown("""
<style>
.block-container{padding-top:1.25rem;padding-bottom:3rem}
div[data-testid="stMetric"]{border:1px solid rgba(128,128,128,.22);border-radius:12px;padding:12px}
[data-testid="stSidebar"]{min-width:300px}
</style>
""", unsafe_allow_html=True)

st.title("18 Wheels Extensiv Migration Portfolio")
st.caption(f"Executive & BOD dashboard • Data as of {AS_OF} • Operational evidence + migration-plan chronology")

with st.sidebar:
    st.subheader("Portfolio Filters")
    st.caption("Type a few letters in Client Search to jump to a customer.")
    labels = ["All Clients"] + sorted([
        (str(r["Customer"]) + (" | " + str(r["Client Code"]) if str(r["Client Code"]).strip() else ""))
        for _,r in df.iterrows() if str(r["Customer"]).strip()
    ])
    selected = st.selectbox("🔎 Client Search", labels)
    scope = st.radio("Scope", ["Managed Migration Portfolio","All Reconciled Accounts"], index=0)
    regions = st.multiselect("Region", options(df["Region"]))
    warehouses = st.multiselect("Warehouse", options(df["Plan Warehouse"]))
    statuses = st.multiselect("Current System / Status", options(df["Portfolio Status"]))
    csrs = st.multiselect("CSR", options(df["Plan CSR"]))
    complexities = st.multiselect("Complexity", options(df["Complexity"]))

f = df.copy()
if scope == "Managed Migration Portfolio":
    f = f[f["Managed Portfolio"]=="Yes"]
if selected != "All Clients":
    name = selected.split(" | ")[0]
    f = f[f["Customer"]==name]
if regions: f=f[f["Region"].isin(regions)]
if warehouses: f=f[f["Plan Warehouse"].isin(warehouses)]
if statuses: f=f[f["Portfolio Status"].isin(statuses)]
if csrs: f=f[f["Plan CSR"].isin(csrs)]
if complexities: f=f[f["Complexity"].astype(str).isin(complexities)]

# KPI
ext_live = int((f["Portfolio Status"]=="Extensiv Live").sum())
cam_live = int((f["Portfolio Status"]=="Camelot Live").sum())
both = int((f["Portfolio Status"]=="Transition / Both").sum())
review = int((f["Portfolio Status"]=="Needs Review").sum())
den = ext_live + cam_live + both
adoption = pct(ext_live + both, den)

a,b,c,d1,e,fm = st.columns(6)
a.metric("Portfolio Accounts", len(f))
b.metric("Extensiv Live", ext_live)
c.metric("Camelot Live", cam_live)
d1.metric("Transition / Both", both)
e.metric("Needs Review", review)
fm.metric("Extensiv Adoption", f"{adoption:.1f}%")

tabs=st.tabs(["Executive View","Migration Portfolio","Warehouse & Region","Complexity & CSR","Management Attention","Client Profile","Data"])

with tabs[0]:
    st.subheader("Transition Stats — Exec Baseline Oct 1")
    st.caption("This is Dave's Oct 1 Exec/BOD baseline, kept as a benchmark. It is not recalculated from historical transactions.")
    baseline=pd.DataFrame([
        {"Region":"West","% Live Extensiv":"54%","# On Extensiv":88,"# On Camelot":74,"Q4 to Extensiv":30},
        {"Region":"East","% Live Extensiv":"85%","# On Extensiv":83,"# On Camelot":15,"Q4 to Extensiv":10},
    ])
    st.dataframe(baseline,use_container_width=True,hide_index=True)

    c1,c2=st.columns([1,1.2])
    with c1:
        st.subheader("Current Managed Portfolio")
        vc=f["Portfolio Status"].value_counts().reindex(
            ["Extensiv Live","Camelot Live","Transition / Both","Needs Review"],fill_value=0
        ).reset_index()
        vc.columns=["Status","Customers"]
        fig=px.pie(vc,names="Status",values="Customers",hole=.62)
        fig.update_traces(textinfo="percent+value",textposition="inside")
        fig.update_layout(height=390,margin=dict(l=10,r=10,t=10,b=10),legend_orientation="h")
        st.plotly_chart(fig,use_container_width=True)
    with c2:
        st.subheader("Executive Analysis")
        managed=f[f["Managed Portfolio"]=="Yes"] if "Managed Portfolio" in f.columns else f
        att=int((managed["Management Attention"].astype(str).str.strip()!="").sum())
        high=int(managed["Complexity"].astype(str).str.contains("3|heavy|high",case=False,regex=True).sum())
        edi=int(pd.to_numeric(managed["Camelot EDI Tx 12M"],errors="coerce").fillna(0).gt(0).sum())
        st.write(
            f"Current evidence identifies **{ext_live + both}** accounts with Extensiv presence/live status "
            f"and **{cam_live + both}** with Camelot presence in the selected scope. "
            f"**{both}** accounts have evidence requiring cutover monitoring and **{review}** remain unresolved."
        )
        st.write(
            f"Portfolio risk indicators: **{high}** high/heavy-complexity records, "
            f"**{edi}** accounts with Camelot EDI activity in the supplied period, and "
            f"**{att}** records with a management-attention note."
        )
        st.info("Historical Camelot activity before a customer's go-live does not classify the customer as currently on Camelot.")

with tabs[1]:
    st.subheader("Migration Portfolio")
    g=f.groupby(["Region","Portfolio Status"]).size().reset_index(name="Customers")
    fig=px.bar(g,x="Region",y="Customers",color="Portfolio Status",barmode="stack",text_auto=True)
    fig.update_layout(height=420)
    st.plotly_chart(fig,use_container_width=True)
    st.caption("Use the Scope selector to separate the managed migration plan from discovery-only accounts found in operational extracts.")

with tabs[2]:
    st.subheader("Warehouse Portfolio")
    w=f.copy()
    w["Warehouse Display"]=w["Plan Warehouse"].replace("","Unknown")
    wg=w.groupby(["Warehouse Display","Portfolio Status"]).size().reset_index(name="Customers")
    fig=px.bar(wg,y="Warehouse Display",x="Customers",color="Portfolio Status",orientation="h",barmode="stack")
    fig.update_layout(height=max(420,30*w["Warehouse Display"].nunique()),yaxis={"categoryorder":"total ascending"})
    st.plotly_chart(fig,use_container_width=True)

with tabs[3]:
    c1,c2=st.columns(2)
    with c1:
        st.subheader("Complexity")
        x=f["Complexity"].astype(str).replace({"":"Unknown","nan":"Unknown"})
        x=x.value_counts().reset_index(); x.columns=["Complexity","Customers"]
        fig=px.pie(x,names="Complexity",values="Customers",hole=.5)
        fig.update_layout(height=390)
        st.plotly_chart(fig,use_container_width=True)
        st.caption("Complexity comes only from the supplied migration planning source; missing values remain Unknown.")
    with c2:
        st.subheader("CSR Portfolio")
        x=f.copy(); x["CSR Display"]=x["Plan CSR"].replace("","Unassigned")
        top=x["CSR Display"].value_counts().head(15).index
        x=x[x["CSR Display"].isin(top)].groupby(["CSR Display","Portfolio Status"]).size().reset_index(name="Customers")
        fig=px.bar(x,y="CSR Display",x="Customers",color="Portfolio Status",orientation="h",barmode="stack")
        fig.update_layout(height=500,yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(fig,use_container_width=True)

with tabs[4]:
    st.subheader("Management Attention")
    x=f[f["Management Attention"].astype(str).str.strip()!=""].copy()
    if x.empty:
        st.success("No attention flags in the current filter.")
    else:
        cnt=x["Management Attention"].value_counts().reset_index()
        cnt.columns=["Attention","Customers"]
        fig=px.bar(cnt,y="Attention",x="Customers",orientation="h",text_auto=True)
        fig.update_layout(height=max(320,55*len(cnt)))
        st.plotly_chart(fig,use_container_width=True)
        st.dataframe(x[["Customer","Client Code","Region","Plan Warehouse","Portfolio Status","Plan CSR","Complexity",
                        "Listed Actual Go-Live","Camelot Last Activity","Management Attention"]],
                     use_container_width=True,hide_index=True)

with tabs[5]:
    if selected=="All Clients":
        st.info("Choose a customer from Client Search in the sidebar. You can type a few letters to find it.")
    elif f.empty:
        st.warning("The selected client is hidden by another active filter.")
    else:
        r=f.iloc[0]
        st.subheader(r["Customer"])
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Current Status",r["Portfolio Status"])
        c2.metric("Region",r["Region"] or "Unknown")
        c3.metric("Warehouse",r["Plan Warehouse"] or "Unknown")
        c4.metric("CSR",r["Plan CSR"] or "Unassigned")
        l,rcol=st.columns(2)
        with l:
            st.markdown("#### Migration Plan")
            st.write("**Client Code:**",r["Client Code"] or "—")
            st.write("**Complexity:**",r["Complexity"] or "Unknown")
            st.write("**Plan System Today:**",r["Plan System Today"] or "—")
            st.write("**Planned Go-Live:**",r["Planned Go-Live"] or "—")
            st.write("**Listed Actual Go-Live:**",r["Listed Actual Go-Live"] or "—")
            st.write("**Plan Notes:**",r["Plan Notes"] or "—")
        with rcol:
            st.markdown("#### Operational Evidence")
            st.write("**Extensiv Inventory:**",r["Extensiv Inventory"])
            st.write("**Extensiv Billing:**",r["Extensiv Billing"])
            st.write("**Extensiv Facilities:**",r["Extensiv Facilities"] or "—")
            st.write("**Camelot Recent Activity:**",r["Camelot Recent Activity"])
            st.write("**Camelot Last Activity:**",r["Camelot Last Activity"] or "—")
            st.write("**Camelot EDI Tx 12M:**",r["Camelot EDI Tx 12M"])
        if r["Management Attention"]:
            st.warning(r["Management Attention"])

with tabs[6]:
    st.subheader("Auditable Portfolio Data")
    cols=["Customer","Client Code","Region","Plan Warehouse","Portfolio Status","Managed Portfolio",
          "Extensiv Inventory","Extensiv Billing","Extensiv Facilities","Camelot Recent Activity","Camelot Last Activity",
          "Plan System Today","Planned Go-Live","Listed Actual Go-Live","Plan CSR","Complexity","Plan Notes","Management Attention"]
    st.dataframe(f[cols],use_container_width=True,hide_index=True,height=620)
    st.download_button("Download filtered CSV",f[cols].to_csv(index=False).encode("utf-8"),
                       "migration_portfolio_filtered.csv","text/csv")

st.divider()
st.caption("Classification rule: actual/direct/current Extensiv evidence establishes Extensiv live; historical Camelot activity before go-live does not create a Both status. Both is reserved for Camelot activity demonstrably after the listed go-live.")
