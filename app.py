import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px

st.set_page_config(
    page_title="18 Wheels | Extensiv Migration Portfolio",
    page_icon="📦",
    layout="wide"
)

DATA_FILE = Path(__file__).resolve().parent / "migration_portfolio.csv"

def clean(v):
    if pd.isna(v):
        return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan", "none", "<na>", "nat"} else s

def first_col(df, names):
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for n in names:
        if n.lower() in lookup:
            return lookup[n.lower()]
    return None

def series(df, names, default=""):
    c = first_col(df, names)
    if c is None:
        return pd.Series([default] * len(df), index=df.index)
    return df[c]

def normalize_status(v):
    s = clean(v).lower()
    if "transition" in s or "both" in s:
        return "Transition / Both"
    if "extensiv" in s:
        return "Extensiv Live"
    if "camelot" in s or s == "wms" or "wms live" in s:
        return "Camelot Live"
    if "review" in s or "unknown" in s or not s:
        return "Needs Review"
    return clean(v)

def derive_region(warehouse):
    w = clean(warehouse).lower()
    west = ["burnaby", "meadow", "chts", "surrey", "tsawwassen", "blundell",
            "calgary", "rockyview", "aldergrove", "tilbury", "riverside"]
    east = ["brampton", "royal", "pickering", "toronto", "windsor"]
    if any(x in w for x in west):
        return "West"
    if any(x in w for x in east):
        return "East"
    return "Unknown"

@st.cache_data
def load_data():
    return pd.read_csv(DATA_FILE, low_memory=False)

def prep(raw):
    df = raw.copy()

    df["Account"] = series(
        df, ["Account", "Customer", "Customer Name", "Client", "Client Name"]
    ).map(clean)

    df["Client Code"] = series(
        df, ["Client Code", "Code", "ID", "Customer Code"]
    ).map(clean)

    df["Warehouse"] = series(
        df, ["Warehouse", "Facility", "Location"]
    ).map(clean)

    supplied_region = series(df, ["Region"]).map(clean)
    df["Region"] = [
        r if r else derive_region(w)
        for r, w in zip(supplied_region, df["Warehouse"])
    ]

    raw_status = series(
        df,
        ["Portfolio Status", "Verified Current System", "Migration Status",
         "Current System", "Status", "Reconciled Status"]
    ).map(clean)
    df["Portfolio Status"] = raw_status.map(normalize_status)

    df["CSR"] = series(
        df, ["CSR", "Plan CSR", "Detected CSR / Primary User", "Primary CSR"]
    ).map(clean)
    df.loc[df["CSR"] == "", "CSR"] = "Not Assigned"

    df["Complexity"] = series(
        df, ["Complexity", "Complexity Type", "Complexity Level"]
    ).map(clean)
    df.loc[df["Complexity"] == "", "Complexity"] = "Unknown / Not Assigned"

    df["Planned Go-Live"] = series(
        df, ["Planned Go-Live", "Planned Go Live", "Planned Go-Live Date"]
    ).map(clean)

    df["Actual Go-Live"] = series(
        df, ["Actual Go-Live", "Actual Go Live", "Listed Actual Go-Live",
             "Actual Go Live Date"]
    ).map(clean)

    df["Plan Notes"] = series(
        df, ["Plan Notes", "Notes / Blocker", "Blocker"]
    ).map(clean)

    df["Last Camelot Activity"] = series(
        df, ["Last Camelot Activity", "Last WMS Activity",
             "Last WMS Shipment/Receipt"]
    ).map(clean)

    df["Extensiv Inventory"] = series(
        df, ["Extensiv Inventory", "Extensiv Inventory Evidence"]
    ).map(clean)

    df["Extensiv Billing"] = series(
        df, ["Extensiv Billing", "Extensiv Billing Evidence"]
    ).map(clean)

    df["Camelot Recent Activity"] = series(
        df, ["Camelot Recent Activity", "Camelot Evidence", "WMS Evidence"]
    ).map(clean)

    df["Management Attention"] = series(
        df, ["Management Attention", "Conflict / Review", "Conflict Flag", "Review Flag"]
    ).map(clean)

    df["Scope"] = series(
        df, ["Managed Portfolio", "Scope", "Portfolio Scope"]
    ).map(clean)

    return df

st.title("📦 18 Wheels Extensiv Migration Portfolio")
st.caption("Executive / BOD migration dashboard • Data as of October 5, 2026")

if not DATA_FILE.exists():
    st.error(
        "migration_portfolio.csv was not found. Put migration_portfolio.csv "
        "in the same GitHub folder as app.py."
    )
    st.stop()

try:
    raw = load_data()
    df = prep(raw)
except Exception as e:
    st.error("The CSV was found, but the dashboard could not read it.")
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("migration_portfolio.csv is empty.")
    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.header("Portfolio Filters")

search = st.sidebar.text_input(
    "Client search",
    placeholder="Type client name or code..."
).strip().lower()

region_options = sorted([x for x in df["Region"].dropna().unique() if clean(x)])
region = st.sidebar.multiselect("Region", region_options)

warehouse_options = sorted([x for x in df["Warehouse"].dropna().unique() if clean(x)])
warehouse = st.sidebar.multiselect("Warehouse", warehouse_options)

status_order = ["Extensiv Live", "Camelot Live", "Transition / Both", "Needs Review"]
status_options = [x for x in status_order if x in set(df["Portfolio Status"])]
status = st.sidebar.multiselect("Current System / Status", status_options)

csr_options = sorted([x for x in df["CSR"].dropna().unique() if clean(x)])
csr = st.sidebar.multiselect("CSR", csr_options)

complexity_options = sorted([x for x in df["Complexity"].dropna().unique() if clean(x)])
complexity = st.sidebar.multiselect("Complexity", complexity_options)

f = df.copy()

if search:
    mask = (
        f["Account"].str.lower().str.contains(search, na=False, regex=False)
        | f["Client Code"].str.lower().str.contains(search, na=False, regex=False)
    )
    f = f[mask]

if region:
    f = f[f["Region"].isin(region)]
if warehouse:
    f = f[f["Warehouse"].isin(warehouse)]
if status:
    f = f[f["Portfolio Status"].isin(status)]
if csr:
    f = f[f["CSR"].isin(csr)]
if complexity:
    f = f[f["Complexity"].isin(complexity)]

# ---------------- KPIs ----------------
total = len(f)
ext_live = int((f["Portfolio Status"] == "Extensiv Live").sum())
cam_live = int((f["Portfolio Status"] == "Camelot Live").sum())
both = int((f["Portfolio Status"] == "Transition / Both").sum())
review = int((f["Portfolio Status"] == "Needs Review").sum())
adoption_den = ext_live + cam_live + both
adoption = (ext_live / adoption_den * 100) if adoption_den else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Accounts", f"{total:,}")
c2.metric("Extensiv Live", f"{ext_live:,}")
c3.metric("Camelot Live", f"{cam_live:,}")
c4.metric("Transition / Both", f"{both:,}")
c5.metric("Needs Review", f"{review:,}")
c6.metric("Extensiv Adoption", f"{adoption:.1f}%")

tabs = st.tabs([
    "Executive View",
    "Migration Portfolio",
    "Warehouse & Region",
    "Complexity & CSR",
    "Management Attention",
    "Client Profile",
    "Data"
])

# ---------------- EXECUTIVE ----------------
with tabs[0]:
    st.subheader("Executive Migration Snapshot")

    left, right = st.columns([1.05, 1])

    with left:
        st.markdown("#### Oct 1 Executive/BOD Benchmark")
        benchmark = pd.DataFrame({
            "Region": ["West", "East"],
            "Extensiv Adoption": ["54%", "85%"],
            "On Extensiv": [88, 83],
            "On Camelot": [74, 15],
            "Q4 to Extensiv": [30, 10],
        })
        st.dataframe(benchmark, hide_index=True, use_container_width=True)
        st.caption(
            "Benchmark from the Oct 1 Transition Stats report. "
            "It is shown for comparison and is not recalculated from historical transactions."
        )

    with right:
        counts = (
            f["Portfolio Status"]
            .value_counts()
            .rename_axis("Status")
            .reset_index(name="Accounts")
        )
        if not counts.empty:
            fig = px.pie(
                counts,
                names="Status",
                values="Accounts",
                hole=0.58,
                title="Current Reconciled Portfolio"
            )
            fig.update_traces(textinfo="percent+value", textposition="inside")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Executive Analysis")
    a1, a2, a3 = st.columns(3)
    a1.info(f"**{ext_live:,}** accounts in the filtered view are classified Extensiv Live.")
    a2.info(f"**{cam_live:,}** accounts remain classified Camelot Live.")
    a3.info(f"**{both + review:,}** accounts need transition/review attention.")

    region_status = (
        f.groupby(["Region", "Portfolio Status"], dropna=False)
        .size()
        .reset_index(name="Accounts")
    )
    if not region_status.empty:
        fig = px.bar(
            region_status,
            x="Region",
            y="Accounts",
            color="Portfolio Status",
            barmode="stack",
            title="Portfolio by Region"
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------------- PORTFOLIO ----------------
with tabs[1]:
    st.subheader("Migration Portfolio")
    cols = [
        "Account", "Client Code", "Portfolio Status", "Region", "Warehouse",
        "CSR", "Complexity", "Planned Go-Live", "Actual Go-Live"
    ]
    st.dataframe(f[cols], hide_index=True, use_container_width=True, height=600)

# ---------------- WAREHOUSE ----------------
with tabs[2]:
    st.subheader("Warehouse & Region")

    wh = (
        f.assign(Warehouse=f["Warehouse"].replace("", "Unknown"))
        .groupby(["Warehouse", "Portfolio Status"])
        .size()
        .reset_index(name="Accounts")
    )
    if not wh.empty:
        fig = px.bar(
            wh,
            x="Warehouse",
            y="Accounts",
            color="Portfolio Status",
            barmode="stack",
            title="Migration Status by Warehouse"
        )
        st.plotly_chart(fig, use_container_width=True)

    reg = (
        f.assign(Region=f["Region"].replace("", "Unknown"))
        .groupby(["Region", "Portfolio Status"])
        .size()
        .reset_index(name="Accounts")
    )
    st.dataframe(reg, hide_index=True, use_container_width=True)

# ---------------- COMPLEXITY / CSR ----------------
with tabs[3]:
    st.subheader("Complexity & CSR")
    left, right = st.columns(2)

    with left:
        comp = (
            f["Complexity"]
            .replace("", "Unknown / Not Assigned")
            .value_counts()
            .reset_index()
        )
        comp.columns = ["Complexity", "Accounts"]
        if not comp.empty:
            fig = px.pie(
                comp,
                names="Complexity",
                values="Accounts",
                hole=0.45,
                title="Portfolio Complexity"
            )
            st.plotly_chart(fig, use_container_width=True)

    with right:
        csr_load = (
            f["CSR"]
            .replace("", "Not Assigned")
            .value_counts()
            .head(20)
            .reset_index()
        )
        csr_load.columns = ["CSR", "Accounts"]
        if not csr_load.empty:
            fig = px.bar(
                csr_load,
                x="Accounts",
                y="CSR",
                orientation="h",
                title="CSR Portfolio Workload"
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)

# ---------------- ATTENTION ----------------
with tabs[4]:
    st.subheader("Management Attention")

    attention_mask = (
        f["Portfolio Status"].isin(["Transition / Both", "Needs Review"])
        | f["Management Attention"].astype(str).str.strip().ne("")
    )
    att = f[attention_mask].copy()

    if att.empty:
        st.success("No accounts in the current filtered view are flagged for management attention.")
    else:
        show = [
            "Account", "Client Code", "Portfolio Status", "Region", "Warehouse",
            "CSR", "Complexity", "Management Attention", "Last Camelot Activity",
            "Actual Go-Live", "Plan Notes"
        ]
        st.dataframe(att[show], hide_index=True, use_container_width=True, height=550)

# ---------------- CLIENT PROFILE ----------------
with tabs[5]:
    st.subheader("Client Profile")

    choices = (
        f[["Account", "Client Code"]]
        .drop_duplicates()
        .sort_values(["Account", "Client Code"])
    )
    labels = [
        f"{r['Account']} ({r['Client Code']})" if r["Client Code"] else r["Account"]
        for _, r in choices.iterrows()
    ]

    if labels:
        selected = st.selectbox(
            "Search / select a client",
            labels,
            index=None,
            placeholder="Type 2–3 letters to search..."
        )
        if selected:
            idx = labels.index(selected)
            acct = choices.iloc[idx]["Account"]
            code = choices.iloc[idx]["Client Code"]

            p = f[(f["Account"] == acct) & (f["Client Code"] == code)]
            if p.empty:
                p = f[f["Account"] == acct]
            r = p.iloc[0]

            x1, x2, x3, x4 = st.columns(4)
            x1.metric("Current Status", r["Portfolio Status"] or "Unknown")
            x2.metric("Region", r["Region"] or "Unknown")
            x3.metric("Warehouse", r["Warehouse"] or "Unknown")
            x4.metric("Complexity", r["Complexity"] or "Unknown")

            profile = pd.DataFrame({
                "Field": [
                    "Account", "Client Code", "CSR", "Planned Go-Live",
                    "Actual Go-Live", "Extensiv Inventory", "Extensiv Billing",
                    "Camelot Recent Activity", "Last Camelot Activity",
                    "Management Attention", "Plan Notes"
                ],
                "Value": [
                    r["Account"], r["Client Code"], r["CSR"], r["Planned Go-Live"],
                    r["Actual Go-Live"], r["Extensiv Inventory"], r["Extensiv Billing"],
                    r["Camelot Recent Activity"], r["Last Camelot Activity"],
                    r["Management Attention"], r["Plan Notes"]
                ]
            })
            st.dataframe(profile, hide_index=True, use_container_width=True)
    else:
        st.info("No clients match the current filters.")

# ---------------- DATA ----------------
with tabs[6]:
    st.subheader("Auditable Reconciled Data")
    st.caption(f"Showing {len(f):,} of {len(df):,} rows.")
    st.dataframe(f, hide_index=True, use_container_width=True, height=650)

st.divider()
st.caption(
    "Classification principle: historical Camelot activity before an Extensiv go-live "
    "does not by itself classify an account as Both. Transition/Both should represent "
    "demonstrable post-cutover Camelot activity or an explicit transition condition."
)
