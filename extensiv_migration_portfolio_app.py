import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Extensiv Migration Portfolio", page_icon="📦", layout="wide")

# ---------------- CONFIG ----------------
DEFAULT_DATA_FILE = "Fresh_Migration_Reconciliation_Oct05_2026.csv"

# ---------------- HELPERS ----------------
def clean_text(v):
    if pd.isna(v):
        return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan", "none", "<na>", "nat"} else s

def safe_num(v):
    try:
        if pd.isna(v): return 0
        return float(v)
    except:
        return 0

def first_existing(df, names):
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lookup:
            return lookup[n.lower()]
    return None

def col_series(df, names, default=""):
    c = first_existing(df, names)
    if c:
        return df[c]
    return pd.Series([default] * len(df), index=df.index)

def normalize_status(v):
    s = clean_text(v).lower()
    if "transition" in s or "both" in s:
        return "Transition / Both"
    if "extensiv" in s and ("live" in s or "native" in s):
        return "Extensiv Live"
    if "camelot" in s or "wms" in s:
        return "Camelot Live"
    if "review" in s or "unknown" in s or not s:
        return "Needs Review"
    if "migrat" in s:
        return "Extensiv Live"
    return clean_text(v)

def derive_region(warehouse):
    w = clean_text(warehouse).lower()
    west = ["burnaby","meadow","chts","surrey","tsawwassen","blundell","calgary","rockyview","aldergrove","tilbury","riverside"]
    east = ["brampton","royal","pickering","toronto","windsor"]
    if any(x in w for x in west): return "West"
    if any(x in w for x in east): return "East"
    return "Unknown"

def truthy(v):
    return clean_text(v).lower() in {"yes","y","true","1","x","live","active"}

def load_data(uploaded=None):
    if uploaded is not None:
        return pd.read_csv(uploaded, low_memory=False)
    candidates = [
        Path(__file__).parent / DEFAULT_DATA_FILE,
        Path.cwd() / DEFAULT_DATA_FILE,
    ]
    for p in candidates:
        if p.exists():
            return pd.read_csv(p, low_memory=False)
    return None

def prep(raw):
    df = raw.copy()
    # Flexible mapping: works even if the reconciliation headers vary slightly.
    df["Account"] = col_series(df, ["Account","Customer","Customer Name","Client","Client Name"]).map(clean_text)
    df["Client Code"] = col_series(df, ["Client Code","Code","ID","Customer Code"]).map(clean_text)
    df["Warehouse"] = col_series(df, ["Warehouse","Facility","Location"]).map(clean_text)
    reg = col_series(df, ["Region"]).map(clean_text)
    df["Region"] = [r if r else derive_region(w) for r,w in zip(reg,df["Warehouse"])]

    status_raw = col_series(df, ["Verified Current System","Migration Status","Current System","Status","Reconciled Status"]).map(clean_text)
    df["Portfolio Status"] = status_raw.map(normalize_status)

    df["CSR"] = col_series(df, ["CSR","Detected CSR / Primary User","Created By","Primary CSR"]).map(clean_text)
    df["Complexity"] = col_series(df, ["Complexity","Complexity Type","Complexity Level"]).map(clean_text)
    df.loc[df["Complexity"]=="","Complexity"] = "Unknown / Not Assigned"

    df["Plan Notes"] = col_series(df, ["Plan Notes","Notes","Notes / Blocker","Blocker"]).map(clean_text)
    df["Planned Go-Live"] = col_series(df, ["Planned Go-Live","Planned Go Live","Planned Go-Live Date"]).map(clean_text)
    df["Actual Go-Live"] = col_series(df, ["Actual Go-Live","Actual Go Live","Actual Go Live Date"]).map(clean_text)
    df["Extensiv Evidence"] = col_series(df, ["Extensiv Evidence","Extensiv Billing Evidence","Extensiv Inventory Evidence"]).map(clean_text)
    df["Camelot Evidence"] = col_series(df, ["Camelot Evidence","Camelot Recent Activity","WMS Evidence"]).map(clean_text)
    df["Last Camelot Activity"] = col_series(df, ["Last Camelot Activity","Last WMS Activity","Last WMS Shipment/Receipt"]).map(clean_text)
    df["Conflict"] = col_series(df, ["Conflict Flag","Conflict / Review","Review Flag"]).map(clean_text)

    # Preserve evidence columns when present
    inv_col = first_existing(df, ["Extensiv Inventory Evidence","Has Inventory","Inventory Evidence"])
    bill_col = first_existing(df, ["Extensiv Billing Evidence","Billing Evidence"])
    df["Inventory Evidence"] = df[inv_col].map(clean_text) if inv_col else ""
    df["Billing Evidence"] = df[bill_col].map(clean_text) if bill_col else ""

    # Data quality / management attention
    df["Attention"] = ""
    both = df["Portfolio Status"].eq("Transition / Both")
    review = df["Portfolio Status"].eq("Needs Review")
    no_csr = df["CSR"].eq("")
    no_wh = df["Warehouse"].eq("")
    high_complex = df["Complexity"].str.contains("high|complex|edi|api", case=False, na=False)
    camelot = df["Portfolio Status"].eq("Camelot Live")

    df.loc[both, "Attention"] = "Active/evidenced in both systems"
    df.loc[review, "Attention"] = "System status needs review"
    df.loc[(df["Attention"]=="") & no_csr, "Attention"] = "CSR not assigned / not evidenced"
    df.loc[(df["Attention"]=="") & no_wh, "Attention"] = "Warehouse not assigned"
    df.loc[(df["Attention"]=="") & high_complex & camelot, "Attention"] = "Complex account remains on Camelot"
    df.loc[(df["Attention"]=="") & df["Conflict"].ne(""), "Attention"] = "Source conflict requires review"

    return df

# ---------------- STYLE ----------------
st.markdown("""
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 3rem;}
div[data-testid="stMetric"] {border:1px solid rgba(128,128,128,.22); border-radius:12px; padding:12px 14px;}
.small-note {color:#777; font-size:.86rem;}
.section {font-size:1.18rem; font-weight:700; margin-top:.5rem;}
</style>
""", unsafe_allow_html=True)

# ---------------- DATA ----------------
with st.sidebar:
    st.header("Migration Portfolio")
    uploaded = st.file_uploader("Load fresh reconciliation CSV", type=["csv"])
    st.caption("If no file is uploaded, the app reads " + DEFAULT_DATA_FILE + " from the same folder as app.py.")

raw = load_data(uploaded)
if raw is None:
    st.error(f"Data file not found. Put `{DEFAULT_DATA_FILE}` beside app.py or upload it from the sidebar.")
    st.stop()

df = prep(raw)

# ---------------- SIDEBAR FILTERS ----------------
def opts(s):
    return sorted([x for x in s.fillna("").astype(str).str.strip().unique() if x and x.lower() != "nan"])

with st.sidebar:
    st.divider()
    # Streamlit selectbox has type-ahead: typing 2-3 letters jumps/matches.
    client_labels = ["All Clients"] + sorted(
        [f"{r['Account']}  |  {r['Client Code']}" if r["Client Code"] else r["Account"]
         for _,r in df[df["Account"].ne("")].drop_duplicates(["Account","Client Code"]).iterrows()]
    )
    selected_client = st.selectbox("🔎 Client Search (type a few letters)", client_labels, index=0)

    regions = st.multiselect("Region", opts(df["Region"]))
    warehouses = st.multiselect("Warehouse", opts(df["Warehouse"]))
    statuses = st.multiselect("Portfolio Status", opts(df["Portfolio Status"]))
    complexities = st.multiselect("Complexity", opts(df["Complexity"]))
    csrs = st.multiselect("CSR", opts(df["CSR"]))

f = df.copy()
if selected_client != "All Clients":
    # exact label match
    label_series = f.apply(lambda r: f"{r['Account']}  |  {r['Client Code']}" if r["Client Code"] else r["Account"], axis=1)
    f = f[label_series.eq(selected_client)]
if regions: f = f[f["Region"].isin(regions)]
if warehouses: f = f[f["Warehouse"].isin(warehouses)]
if statuses: f = f[f["Portfolio Status"].isin(statuses)]
if complexities: f = f[f["Complexity"].isin(complexities)]
if csrs: f = f[f["CSR"].isin(csrs)]

# ---------------- HEADER ----------------
st.title("Extensiv Migration Portfolio")
st.caption("Executive & BOD view • operational evidence first • planning data used as reference, not as proof of live status")

total = len(f)
ext_live = int((f["Portfolio Status"]=="Extensiv Live").sum())
camelot_live = int((f["Portfolio Status"]=="Camelot Live").sum())
transition = int((f["Portfolio Status"]=="Transition / Both").sum())
review = int((f["Portfolio Status"]=="Needs Review").sum())
den = ext_live + camelot_live + transition
adoption = ((ext_live + transition) / den * 100) if den else 0

k1,k2,k3,k4,k5,k6 = st.columns(6)
k1.metric("Portfolio", f"{total:,}")
k2.metric("Extensiv Live", f"{ext_live:,}")
k3.metric("Camelot Live", f"{camelot_live:,}")
k4.metric("Transition / Both", f"{transition:,}")
k5.metric("Needs Review", f"{review:,}")
k6.metric("Extensiv Adoption", f"{adoption:.1f}%")

tabs = st.tabs(["Executive Portfolio","Region & Warehouse","Complexity & CSR","Management Attention","Client Profile","Master Data"])

# ---------------- EXECUTIVE ----------------
with tabs[0]:
    c1,c2 = st.columns([1,1.35])
    with c1:
        st.subheader("Migration Portfolio")
        status_order = ["Extensiv Live","Camelot Live","Transition / Both","Needs Review"]
        counts = f["Portfolio Status"].value_counts().reindex(status_order, fill_value=0).reset_index()
        counts.columns = ["Status","Customers"]
        fig = px.pie(counts, names="Status", values="Customers", hole=.62)
        fig.update_traces(textposition="inside", textinfo="percent+value")
        fig.update_layout(height=390, margin=dict(l=10,r=10,t=20,b=10), legend_orientation="h")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("Transition Stats")
        reg = f[f["Region"].isin(["West","East"])].groupby("Region")["Portfolio Status"].value_counts().unstack(fill_value=0)
        rows=[]
        for region in ["West","East"]:
            rr = reg.loc[region] if region in reg.index else pd.Series(dtype=float)
            e=int(rr.get("Extensiv Live",0)); c=int(rr.get("Camelot Live",0)); t=int(rr.get("Transition / Both",0))
            d=e+c+t
            rows.append({"Region":region,"% Live Extensiv":round((e+t)/d*100,1) if d else 0,
                         "# On Extensiv":e+t,"# On Camelot":c+t,"Transition / Both":t})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.info("“On Extensiv” and “On Camelot” include Transition/Both because those customers have evidence in both systems. Adoption excludes Needs Review.")

        st.subheader("Executive Brief")
        top_attention = int((f["Attention"]!="").sum())
        west = next((x for x in rows if x["Region"]=="West"), None)
        east = next((x for x in rows if x["Region"]=="East"), None)
        brief = (
            f"{ext_live + transition:,} customers have current Extensiv evidence across the filtered portfolio; "
            f"{camelot_live + transition:,} have current Camelot/WMS evidence. "
            f"{transition:,} customers require transition monitoring because they appear in both systems, and "
            f"{review:,} require status review. "
        )
        if west and east:
            brief += f"Verified Extensiv adoption is {west['% Live Extensiv']:.1f}% in West and {east['% Live Extensiv']:.1f}% in East. "
        brief += f"{top_attention:,} records currently have at least one management-attention flag."
        st.write(brief)

# ---------------- REGION / WH ----------------
with tabs[1]:
    st.subheader("Regional Migration Portfolio")
    r = f.groupby(["Region","Portfolio Status"]).size().reset_index(name="Customers")
    fig = px.bar(r, x="Region", y="Customers", color="Portfolio Status", barmode="stack", text_auto=True)
    fig.update_layout(height=390)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Warehouse Portfolio")
    w = f.copy()
    w.loc[w["Warehouse"]=="","Warehouse"]="Unknown"
    wagg = w.groupby(["Warehouse","Portfolio Status"]).size().reset_index(name="Customers")
    fig2 = px.bar(wagg, y="Warehouse", x="Customers", color="Portfolio Status", orientation="h", barmode="stack")
    fig2.update_layout(height=max(420, 32*w["Warehouse"].nunique()), yaxis={"categoryorder":"total ascending"})
    st.plotly_chart(fig2, use_container_width=True)

# ---------------- COMPLEXITY / CSR ----------------
with tabs[2]:
    a,b = st.columns(2)
    with a:
        st.subheader("Complexity Portfolio")
        comp = f["Complexity"].replace("", "Unknown / Not Assigned").value_counts().reset_index()
        comp.columns=["Complexity","Customers"]
        fig = px.pie(comp, names="Complexity", values="Customers", hole=.5)
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Complexity is displayed only when supported by the new reconciliation/planning source. Unknown is not inferred.")
    with b:
        st.subheader("CSR Workload")
        csr = f.copy()
        csr.loc[csr["CSR"]=="","CSR"]="Unassigned / Not Evidenced"
        csragg = csr.groupby(["CSR","Portfolio Status"]).size().reset_index(name="Customers")
        top = csr.groupby("CSR").size().sort_values(ascending=False).head(15).index
        csragg = csragg[csragg["CSR"].isin(top)]
        fig = px.bar(csragg, y="CSR", x="Customers", color="Portfolio Status", orientation="h", barmode="stack")
        fig.update_layout(height=500, yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(fig, use_container_width=True)

# ---------------- ATTENTION ----------------
with tabs[3]:
    st.subheader("Management Attention")
    att = f[f["Attention"].ne("")].copy()
    if att.empty:
        st.success("No management-attention flags in the current filter.")
    else:
        ac = att["Attention"].value_counts().reset_index()
        ac.columns=["Attention","Customers"]
        fig = px.bar(ac, x="Customers", y="Attention", orientation="h", text_auto=True)
        fig.update_layout(height=max(330,55*len(ac)), yaxis={"categoryorder":"total ascending"})
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(att[["Account","Client Code","Region","Warehouse","Portfolio Status","Complexity","CSR","Attention","Plan Notes"]],
                     use_container_width=True, hide_index=True)

# ---------------- CLIENT PROFILE ----------------
with tabs[4]:
    if selected_client == "All Clients":
        st.info("Use Client Search in the left sidebar. Type a few letters of the customer name or client code and select the match.")
    elif f.empty:
        st.warning("The selected client is excluded by another active sidebar filter.")
    else:
        r=f.iloc[0]
        st.subheader(r["Account"] or "Client")
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Current Portfolio Status", r["Portfolio Status"])
        c2.metric("Region", r["Region"] or "Unknown")
        c3.metric("Warehouse", r["Warehouse"] or "Unknown")
        c4.metric("CSR", r["CSR"] or "Not evidenced")

        left,right=st.columns(2)
        with left:
            st.markdown("#### Migration & Planning")
            st.write("**Client Code:**", r["Client Code"] or "—")
            st.write("**Complexity:**", r["Complexity"] or "Unknown / Not Assigned")
            st.write("**Planned Go-Live:**", r["Planned Go-Live"] or "—")
            st.write("**Actual Go-Live:**", r["Actual Go-Live"] or "—")
            st.write("**Plan Notes:**", r["Plan Notes"] or "—")
        with right:
            st.markdown("#### Operational Evidence")
            st.write("**Extensiv Evidence:**", r["Extensiv Evidence"] or "—")
            st.write("**Inventory Evidence:**", r["Inventory Evidence"] or "—")
            st.write("**Billing Evidence:**", r["Billing Evidence"] or "—")
            st.write("**Camelot Evidence:**", r["Camelot Evidence"] or "—")
            st.write("**Last Camelot Activity:**", r["Last Camelot Activity"] or "—")
            st.write("**Attention:**", r["Attention"] or "None")
        if r["Plan Notes"]:
            st.caption("Plan Notes are reference/planning information. They do not override operational evidence.")

# ---------------- MASTER ----------------
with tabs[5]:
    st.subheader("Auditable Master")
    display_cols = ["Account","Client Code","Region","Warehouse","Portfolio Status","Complexity","CSR",
                    "Planned Go-Live","Actual Go-Live","Extensiv Evidence","Camelot Evidence","Attention","Plan Notes"]
    st.dataframe(f[display_cols], use_container_width=True, hide_index=True, height=600)
    csv = f[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered portfolio CSV", csv, "migration_portfolio_filtered.csv", "text/csv")

st.divider()
st.caption(f"Loaded {len(df):,} portfolio records • Dashboard generated from the fresh reconciliation source only.")
