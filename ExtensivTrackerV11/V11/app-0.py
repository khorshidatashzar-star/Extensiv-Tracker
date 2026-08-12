
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import re

st.set_page_config(
    page_title="Extensiv Migration Tracker",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE = Path(__file__).parent
MASTER_FILE = BASE / "Go_Live_East_West_CSR.xlsx"
EXTENSIV_CSV = BASE / "all extensive client- and invoiced client.csv"

# ---------- Visual styling ----------
st.markdown("""
<style>
    .block-container {padding-top: 1.4rem; padding-bottom: 3rem;}
    [data-testid="stMetricValue"] {font-size: 1.55rem;}
    .status-row {display:flex; gap:10px; flex-wrap:wrap; margin:.2rem 0 1rem 0;}
    .pill {display:inline-block; padding:7px 12px; border-radius:999px; font-weight:700; font-size:.85rem;}
    .p-green {background:#dcfce7; color:#166534;}
    .p-blue {background:#dbeafe; color:#1e40af;}
    .p-orange {background:#ffedd5; color:#9a3412;}
    .p-red {background:#fee2e2; color:#991b1b;}
    .p-gray {background:#f1f5f9; color:#475569;}
    .journey {display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin:8px 0 18px 0;}
    .node {padding:10px 14px; border-radius:10px; border:1px solid #d1d5db; font-weight:700; background:#fff;}
    .done {background:#dcfce7; border-color:#86efac; color:#166534;}
    .current {background:#dbeafe; border-color:#93c5fd; color:#1e40af;}
    .future {background:#ffedd5; border-color:#fdba74; color:#9a3412;}
    .arrow {font-weight:800; color:#94a3b8;}
    .section-title {font-size:1.05rem; font-weight:800; margin:.5rem 0 .5rem 0;}
    .small-muted {color:#64748b; font-size:.88rem;}
</style>
""", unsafe_allow_html=True)

# ---------- Data ----------
@st.cache_data
def load_data():
    if not MASTER_FILE.exists():
        st.error(f"Missing data file: {MASTER_FILE.name}")
        st.stop()

    xls = pd.ExcelFile(MASTER_FILE)
    sheets = {str(s).strip().lower(): s for s in xls.sheet_names}

    def find_sheet(names):
        for n in names:
            if n in xls.sheet_names:
                return n
            if n.strip().lower() in sheets:
                return sheets[n.strip().lower()]
        return None

    def read(names, header=0, expected=None):
        s = find_sheet(names)
        if not s:
            return pd.DataFrame(columns=expected or [])
        try:
            return pd.read_excel(xls, sheet_name=s, header=header)
        except Exception:
            return pd.DataFrame(columns=expected or [])

    migrated = read(
        ["Go Live East-West", "Go Live"],
        header=3,
        expected=["Customer","WMS System Today","Warehouse","Region","ID #","CSR Name (by Region)",
                  "Customer Complexity","EDI Heavy","First Transaction Date (by Region)",
                  "Regional CSR (Latest Order)","Regional First Transaction Date",
                  "Matched Extensiv Customer","Actual Go Live Date (In Extensiv)"]
    )
    move = read(
        ["Warehouse move", "Camelot"],
        header=2,
        expected=["Customer","WMS System Today","Warehouse","Region","ID #","CSR Name (by Region)",
                  "Customer Complexity","EDI Heavy","Last WMS Transaction Date"]
    )
    future = read(
        ["Future migration Plan", "Future Migration Plan"],
        header=0,
        expected=["Complexity","Customer","WMS Client Code","CSR from Latest WMS Transaction",
                  "User ID","Last WMS Transaction Date","Last Document","Warehouse","Created By EDI?"]
    )
    onboard = read(
        ["NEw Onboarded-Extensiv","New Onboarded-Extensiv","New Onboarded"],
        header=0,
        expected=["Client Name","Onboarding Date","Planned Warehouse","Matched Extensiv Customer",
                  "CSR (Latest Order Created By)","First Transaction Date","First Transaction Type",
                  "First Transaction Warehouse","Last Transaction Date","Last Transaction Type",
                  "Last Transaction Warehouse","Latest Order Date","Latest Order Transaction ID",
                  "Latest Order Warehouse","Match Confidence"]
    )

    # Remove blank rows.
    for df, col in [(migrated,"Customer"), (move,"Customer"), (future,"Customer"), (onboard,"Client Name")]:
        if col in df.columns:
            df.dropna(subset=[col], inplace=True)

    try:
        ext = pd.read_csv(EXTENSIV_CSV, encoding="cp1252")
    except Exception:
        ext = pd.DataFrame()

    return migrated, move, future, onboard, ext, xls.sheet_names

def clean(v):
    if v is None or pd.isna(v):
        return ""
    s = str(v).strip()
    return "" if s.lower() in {"nan","none"} else s

def norm(v):
    s = clean(v).lower()
    s = re.sub(r"\s+"," ",s)
    return s

def first_nonblank(values):
    for v in values:
        x = clean(v)
        if x:
            return x
    return ""

def unique_join(values):
    vals=[]
    for v in values:
        x=clean(v)
        if x and x not in vals:
            vals.append(x)
    return " / ".join(vals)


# ---------- Authoritative CSR list ----------
# Generated by matching Extensiv "Created By" names to Camelot Users (User ID -> Full Name).
# Support/admin/system/EDI actors are excluded. Display names use first + last name only.
AUTHORIZED_CSR_NAMES = ['Amritha Sunny', 'Amy Wang', 'Ankit Pahwa', 'Anna Atashzar', 'Aoi Takigashira', 'Casper Chen', 'Cihan Karayazi', 'Daisy Wong', 'Dallas Luscombe', 'Dharmin Patel', 'Dhruv Sawhney', 'Dhruvil Shah', 'Domini Domini', 'Ehsan Mokhtari', 'Gurjeet Kaur', 'Hira Paul', 'Holly Tidd', 'Hugo Tsai', 'Idy Lee', 'Igor Moisseev', 'Jaeeun Lee', 'Jamie Wong', 'Jasdeep Kaur', 'Jeremy Anderson', 'Joel Macdonald', 'Karla Buenrostro', 'Karthik Vishwanath', 'Kartik Sharma', 'Kate Tran', 'Kelben Zhang', 'Komalpreet Kaur', 'Lily Chan', 'Miho Kasahara', 'Mohammed Ali', 'Morvarid Valizadeh', 'Nesha Bissoon', 'Nihar Patel', 'Parisa Farhand', 'Preeti Srivastava', 'Priya Sagar', 'Ramandeep Kaur', 'Ria Keating', 'Samrat Rana', 'Soha Sabounchi', 'Sufyan Siddiqui', 'Tim Zhang', 'Trevor Large', 'Venkteshwar Venkteshwar', 'Vickie Cao', 'Yang Wang']

CSR_SOURCE_ALIASES = {
    "damini damini": "Domini Domini",
    "dharmin petel": "Dharmin Patel",
    "dhruvilkumar shah": "Dhruvil Shah",
    "joel mcdonald": "Joel Macdonald",
    "casper chen": "Casper Chen",
    "jamie tin yan wong": "Jamie Wong",
    "karla herrera buenrostro": "Karla Buenrostro",
    "nihar bharat patel": "Nihar Patel",
    "hira lal paul": "Hira Paul",
    "mohammed mujahed ali": "Mohammed Ali",
}

def canonical_csr(value):
    s = clean(value)
    if not s:
        return ""

    key = norm(s)

    # Exact source aliases from Camelot/Extensiv matching.
    if key in CSR_SOURCE_ALIASES:
        return CSR_SOURCE_ALIASES[key]

    # Direct match to the authoritative names.
    for name in AUTHORIZED_CSR_NAMES:
        if norm(name) == key:
            return name

    # For descriptive text, accept a CSR only if an authoritative full name is literally present.
    for name in AUTHORIZED_CSR_NAMES:
        if norm(name) and norm(name) in key:
            return name

    # Not in the approved CSR list => do not show it as a CSR.
    return ""

def canonicalize_csr_series(df, column):
    if column in df.columns:
        df[column] = df[column].map(canonical_csr)

def fmt_date(v):
    if v is None or pd.isna(v) or clean(v)=="":
        return "—"
    try:
        return pd.to_datetime(v).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return clean(v)


def is_note_row(value):
    """Return True for explanatory rows that are not actual client names."""
    s = norm(value)
    if not s:
        return True
    note_phrases = [
        "all these right now are in wms camelot system",
        "complexity 2 customers 2nd to transition",
        "complexity 3 customers 3rd to transition",
        "calgary moving to rockyview",
        "active means",
        "1-lite",
        "2-medium",
        "3-heavy",
        "code in wms is",
        "code in extensiv",
        "already migrated",
        "we have one",
    ]
    return any(p in s for p in note_phrases)

migrated, move, future, onboard, ext, source_sheets = load_data()

# Remove technical Excel/index columns. They are never useful in the dashboard.
for _df in [migrated, move, future, onboard, ext]:
    _drop = [c for c in _df.columns if str(c).strip().lower().startswith("unnamed:")]
    if _drop:
        _df.drop(columns=_drop, inplace=True, errors="ignore")


# Remove explanatory / note rows that may exist inside the Excel tabs.
if "Customer" in migrated.columns:
    migrated = migrated[~migrated["Customer"].map(is_note_row)].copy()
if "Customer" in move.columns:
    move = move[~move["Customer"].map(is_note_row)].copy()
if "Customer" in future.columns:
    future = future[~future["Customer"].map(is_note_row)].copy()
if "Client Name" in onboard.columns:
    onboard = onboard[~onboard["Client Name"].map(is_note_row)].copy()


# Standardize CSR names across all source tabs before building search/filter lists.
for _df, _col in [
    (migrated, "CSR Name (by Region)"),
    (migrated, "Regional CSR (Latest Order)"),
    (move, "CSR Name (by Region)"),
    (move, "Regional CSR (Latest Order)"),
    (future, "CSR from Latest WMS Transaction"),
    (onboard, "CSR (Latest Order Created By)"),
]:
    canonicalize_csr_series(_df, _col)

def rows_for(df, main_col, selected, alt_col=None):
    if main_col not in df.columns:
        return df.iloc[0:0].copy()
    mask = df[main_col].astype(str).map(norm).eq(norm(selected))
    if alt_col and alt_col in df.columns:
        mask = mask | df[alt_col].astype(str).map(norm).eq(norm(selected))
    return df[mask].copy()

# ---------- Unified search index ----------
client_names=[]
for df,col in [(migrated,"Customer"),(move,"Customer"),(future,"Customer"),(onboard,"Client Name")]:
    if col in df.columns:
        client_names += [clean(x) for x in df[col].dropna().tolist() if clean(x)]
client_names = sorted(
    {x for x in client_names if x and not is_note_row(x)},
    key=str.lower
)

csr_names = sorted(AUTHORIZED_CSR_NAMES, key=str.lower)

# ---------- Header ----------
st.title("📦 Extensiv Migration Tracker")
st.caption("V11 — management view: migration, CSR, warehouse, region and key dates only")
page = st.radio(
    "Page",
    ["Client Explorer", "EDI Clients"],
    horizontal=True,
    label_visibility="collapsed",
)

if page == "EDI Clients":
    st.subheader("EDI Clients")
    st.caption("EDI customers are kept on this separate page instead of being repeated throughout the dashboard.")

    edi_rows = []

    if "Created By EDI?" in future.columns:
        for _, r in future.iterrows():
            if norm(r.get("Created By EDI?")) == "yes":
                edi_rows.append({
                    "Client": clean(r.get("Customer")),
                    "System / Stage": "Camelot / Future Migration",
                    "CSR": canonical_csr(r.get("CSR from Latest WMS Transaction")),
                    "Warehouse": clean(r.get("Warehouse")),
                    "Complexity": clean(r.get("Complexity")),
                    "Last WMS Transaction": r.get("Last WMS Transaction Date"),
                })

    if "EDI Heavy" in migrated.columns:
        for _, r in migrated.iterrows():
            if norm(r.get("EDI Heavy")) in {"yes", "y", "true", "1"}:
                edi_rows.append({
                    "Client": clean(r.get("Customer")),
                    "System / Stage": "Migrated from Camelot",
                    "CSR": canonical_csr(r.get("CSR Name (by Region)")),
                    "Warehouse": clean(r.get("Warehouse")),
                    "Complexity": clean(r.get("Customer Complexity")),
                    "Last WMS Transaction": None,
                })

    edi_df = pd.DataFrame(edi_rows)
    if not edi_df.empty:
        edi_df = edi_df.drop_duplicates(subset=["Client", "System / Stage", "Warehouse"])
        edi_df["Last WMS Transaction"] = pd.to_datetime(edi_df["Last WMS Transaction"], errors="coerce")
        st.metric("EDI clients", edi_df["Client"].nunique())
        st.dataframe(edi_df, hide_index=True, use_container_width=True)
    else:
        st.info("No EDI clients were found in the supplied files.")
    st.stop()

st.caption("Search a client or CSR. Type a few letters and choose from the suggested matches.")

search1, search2, search3 = st.columns([2.2, 1.5, 1])
with search1:
    selected_client = st.selectbox(
        "Search client",
        options=[""] + client_names,
        index=0,
        placeholder="Start typing a client name…",
    )
with search2:
    selected_csr = st.selectbox(
        "Filter by CSR",
        options=["All CSRs"] + csr_names,
        index=0,
        placeholder="Start typing a CSR name…",
    )
with search3:
    view = st.selectbox("View", ["All", "Extensiv", "Camelot / Future", "Directly onboarded to Extensiv"])

# ---------- Executive overview ----------
future_count = future["Customer"].nunique() if "Customer" in future.columns else 0
migrated_count = migrated["Customer"].nunique() if "Customer" in migrated.columns else 0
new_count = onboard["Client Name"].nunique() if "Client Name" in onboard.columns else 0
edi_future = int((future.get("Created By EDI?", pd.Series(dtype=str)).astype(str).str.lower()=="yes").sum())
scope = migrated_count + future_count
progress = (migrated_count / scope * 100) if scope else 0

k1,k2,k3,k4 = st.columns(4)
k1.metric("Migration complete", f"{progress:.0f}%")
k2.metric("Migrated to Extensiv", migrated_count)
k3.metric("Planned / Future", future_count)
k4.metric("New onboarding", new_count)

# ---------- Simple colored status chart ----------
status_df = pd.DataFrame({
    "Status":["Migrated to Extensiv","Camelot","New onboarding"],
    "Clients":[migrated_count,future_count,new_count],
})
st.markdown('<div class="section-title">Migration portfolio</div>', unsafe_allow_html=True)
st.bar_chart(status_df.set_index("Status"), horizontal=True, color="#4F81BD")

# ---------- Future migration visual ----------
if not future.empty and "Complexity" in future.columns:
    future_chart = future.copy()
    future_chart["Complexity"] = future_chart["Complexity"].astype(str).str.strip()
    future_chart = future_chart[
        future_chart["Complexity"].str.lower().isin(["complexity 1","complexity 2","complexity 3"])
    ]
    mix = future_chart.groupby("Complexity")["Customer"].nunique().reset_index(name="Clients")
    st.markdown('<div class="section-title">What is coming next</div>', unsafe_allow_html=True)
    c1,c2 = st.columns([1.5,1])
    with c1:
        st.bar_chart(mix.set_index("Complexity"), horizontal=True)
    with c2:
        st.markdown(
            '<div class="status-row">'
            f'<span class="pill p-green">Extensiv active: {migrated_count}</span>'
            f'<span class="pill p-orange">Future migration: {future_count}</span>'
            f'<span class="pill p-blue">New onboarding: {new_count}</span>'
            f'<span class="pill p-red">EDI future: {edi_future}</span>'
            '</div>',
            unsafe_allow_html=True
        )
        st.caption("Orange = customers still planned for Camelot → Extensiv transition.")

# ---------- CSR filter mode ----------
if selected_csr != "All CSRs" and not selected_client:
    st.divider()
    st.subheader(f"Clients owned / recently handled by {selected_csr}")

    hits=[]
    def add_hits(df, client_col, csr_cols, source):
        if client_col not in df.columns:
            return
        for _,r in df.iterrows():
            if any(norm(canonical_csr(r.get(c))) == norm(selected_csr) for c in csr_cols if c in df.columns):
                hits.append({
                    "Client": clean(r.get(client_col)),
                    "Source": source,
                    "Warehouse": clean(r.get("Warehouse") or r.get("Planned Warehouse")),
                    "Region": clean(r.get("Region")),
                })
    add_hits(migrated,"Customer",["CSR Name (by Region)","Regional CSR (Latest Order)"],"Migrated from Camelot")
    add_hits(move,"Customer",["CSR Name (by Region)"],"Camelot")
    add_hits(future,"Customer",["CSR from Latest WMS Transaction"],"Camelot")
    add_hits(onboard,"Client Name",["CSR (Latest Order Created By)"],"Directly onboarded to Extensiv")

    if hits:
        hit_df=pd.DataFrame(hits).drop_duplicates()
        st.dataframe(hit_df, hide_index=True, use_container_width=True)
    else:
        st.info("No client found for this CSR in the supplied workbook.")
    st.stop()

if not selected_client:
    st.info("Choose a client above to open its profile. The Client and CSR boxes are searchable — type a few letters and pick the suggestion.")
    st.stop()

# ---------- Client profile ----------
m = rows_for(migrated,"Customer",selected_client,"Matched Extensiv Customer")
w = rows_for(move,"Customer",selected_client,"Matched Extensiv Customer")
f = rows_for(future,"Customer",selected_client)
n = rows_for(onboard,"Client Name",selected_client,"Matched Extensiv Customer")

# View filtering
if view=="Extensiv" and m.empty:
    st.warning("This client does not have a migrated Extensiv row in the supplied workbook.")
if view=="Camelot / Future" and f.empty and w.empty:
    st.warning("This client does not have a current Camelot / Future Migration row.")
if view=="Directly onboarded to Extensiv" and n.empty:
    st.warning("This client is not listed in New Onboarding.")

# Determine primary status
has_migrated = not m.empty and any("extensiv" in norm(x) or "exstensiv" in norm(x) for x in m.get("WMS System Today",[]))
has_future = not f.empty or any("camelot" in norm(x) for x in w.get("WMS System Today",[]))
has_new = not n.empty

if has_migrated:
    status="Extensiv"
    pill="p-green"
elif has_future:
    status="Camelot / Future Migration"
    pill="p-orange"
elif has_new:
    status="Directly onboarded to Extensiv"
    pill="p-blue"
else:
    status="Unknown"
    pill="p-gray"

regions=[]
warehouses=[]
csrs=[]
complexities=[]
edi=[]

for df in [m,w]:
    if "Region" in df.columns: regions += df["Region"].tolist()
    if "Warehouse" in df.columns: warehouses += df["Warehouse"].tolist()
    if "CSR Name (by Region)" in df.columns: csrs += df["CSR Name (by Region)"].tolist()
    if "Regional CSR (Latest Order)" in df.columns: csrs += df["Regional CSR (Latest Order)"].tolist()
    if "Customer Complexity" in df.columns: complexities += df["Customer Complexity"].tolist()
    if "EDI Heavy" in df.columns: edi += df["EDI Heavy"].tolist()

if not f.empty:
    if "Warehouse" in f.columns: warehouses += f["Warehouse"].tolist()
    if "CSR from Latest WMS Transaction" in f.columns: csrs += f["CSR from Latest WMS Transaction"].tolist()
    if "Complexity" in f.columns: complexities += f["Complexity"].tolist()
    if "Created By EDI?" in f.columns: edi += f["Created By EDI?"].tolist()

if not n.empty:
    if "Planned Warehouse" in n.columns: warehouses += n["Planned Warehouse"].tolist()
    if "CSR (Latest Order Created By)" in n.columns: csrs += n["CSR (Latest Order Created By)"].tolist()

st.divider()
st.subheader(selected_client)

st.markdown(
    f'<div class="status-row"><span class="pill {pill}">{status}</span>'
    + (f'<span class="pill p-gray">{unique_join(regions)}</span>' if unique_join(regions) else '')
    + (f'<span class="pill p-red">EDI: {unique_join(edi)}</span>' if unique_join(edi) else '')
    + '</div>',
    unsafe_allow_html=True
)

# Six easy-to-read cards
a,b,c,d = st.columns(4)
a.metric("Warehouse", unique_join(warehouses) or "—")
b.metric("CSR", unique_join(csrs) or "—")
c.metric("Region", unique_join([region_from_warehouse(x) for x in warehouses]) or unique_join(regions) or "—")
d.metric("Complexity", unique_join(complexities) or "—")

# ---------- Journey diagram ----------
first_dates=[]
last_dates=[]
go_live=[]
if "First Transaction Date (by Region)" in m.columns: first_dates += m["First Transaction Date (by Region)"].dropna().tolist()
if "Regional First Transaction Date" in m.columns: first_dates += m["Regional First Transaction Date"].dropna().tolist()
if "First Transaction Date" in n.columns: first_dates += n["First Transaction Date"].dropna().tolist()
if "Last Transaction Date" in n.columns: last_dates += n["Last Transaction Date"].dropna().tolist()
if "Last WMS Transaction Date" in f.columns: last_dates += f["Last WMS Transaction Date"].dropna().tolist()
if "Last WMS Transaction Date" in w.columns: last_dates += w["Last WMS Transaction Date"].dropna().tolist()
if "Actual Go Live Date (In Extensiv)" in m.columns: go_live += [clean(x) for x in m["Actual Go Live Date (In Extensiv)"].tolist() if clean(x)]


def region_from_warehouse(value):
    """Business region derived from warehouse/location, not from raw Region text."""
    s = norm(value)
    if not s:
        return ""

    # National accounts remain National when the warehouse itself is National.
    if "national" in s:
        return "National"

    east_terms = [
        "brampton", "8470", "royal", "2510", "mississauga", "pickering",
        "ontario", " on", "toronto"
    ]
    west_terms = [
        "meadow", "8335", "burnaby", "7185", "blundell", "16160",
        "aldergrove", "290189", "town", "rockyview", "calgary",
        "chts", "2929", "surrey", "tsawwassen", "3995", "delta",
        "tilbury", "riverside", "bc", "alberta", " ab"
    ]

    if any(t in s for t in east_terms):
        return "East"
    if any(t in s for t in west_terms):
        return "West"
    return ""

def safe_datetime_min(values):
    if values is None:
        return None
    parsed = pd.to_datetime(pd.Series(list(values) if isinstance(values, (list, tuple, set, pd.Series)) else [values]), errors="coerce").dropna()
    return parsed.min() if not parsed.empty else None

def safe_datetime_max(values):
    if values is None:
        return None
    parsed = pd.to_datetime(pd.Series(list(values) if isinstance(values, (list, tuple, set, pd.Series)) else [values]), errors="coerce").dropna()
    return parsed.max() if not parsed.empty else None

first_tx = safe_datetime_min(first_dates)
last_tx = safe_datetime_max(last_dates) if last_dates else None

st.markdown('<div class="section-title">Client journey</div>', unsafe_allow_html=True)
if has_migrated:
    journey = (
        '<div class="journey">'
        '<span class="node done">Camelot / Setup</span><span class="arrow">→</span>'
        '<span class="node done">Extensiv Ready</span><span class="arrow">→</span>'
        f'<span class="node done">First Transaction<br><small>{fmt_date(first_tx)}</small></span><span class="arrow">→</span>'
        f'<span class="node current">Active in Extensiv<br><small>{unique_join(go_live) or "Go-live recorded"}</small></span>'
        '</div>'
    )
elif has_future:
    journey = (
        '<div class="journey">'
        '<span class="node done">Camelot Active</span><span class="arrow">→</span>'
        '<span class="node current">Migration Planning</span><span class="arrow">→</span>'
        '<span class="node future">Extensiv Setup</span><span class="arrow">→</span>'
        '<span class="node future">First Extensiv Transaction</span>'
        '</div>'
    )
else:
    journey = (
        '<div class="journey">'
        '<span class="node done">New Client</span><span class="arrow">→</span>'
        '<span class="node done">Extensiv Setup</span><span class="arrow">→</span>'
        f'<span class="node current">Transaction Activity<br><small>{fmt_date(first_tx)}</small></span>'
        '</div>'
    )
st.markdown(journey, unsafe_allow_html=True)

# ---------- Key facts, one screen ----------
ids=[]
if "ID #" in m.columns: ids += m["ID #"].tolist()
if "ID #" in w.columns: ids += w["ID #"].tolist()
if "WMS Client Code" in f.columns: ids += f["WMS Client Code"].tolist()

matched=[]
if "Matched Extensiv Customer" in m.columns: matched += m["Matched Extensiv Customer"].tolist()
if "Matched Extensiv Customer" in n.columns: matched += n["Matched Extensiv Customer"].tolist()

latest_ext_order = None
if not n.empty and "Latest Order Date" in n.columns:
    _vals = pd.to_datetime(n["Latest Order Date"], errors="coerce").dropna()
    if not _vals.empty:
        latest_ext_order = _vals.max()

last_wms_doc = unique_join(f["Last Document"].tolist()) if (not f.empty and "Last Document" in f.columns) else ""

left,right = st.columns(2)

with left:
    st.markdown("#### Transaction snapshot")
    st.markdown(
        f"""
        <div style="border:1px solid #e2e8f0;border-radius:12px;padding:16px;background:#ffffff;">
          <div style="margin-bottom:12px;"><b>First transaction</b><br>{fmt_date(first_tx)}</div>
          <div style="margin-bottom:12px;"><b>Last known transaction</b><br>{fmt_date(last_tx)}</div>
          <div style="margin-bottom:12px;"><b>Latest Extensiv order</b><br>{fmt_date(latest_ext_order)}</div>
          <div><b>Last WMS document</b><br>{last_wms_doc or "—"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right:
    st.markdown("#### Account snapshot")
    st.markdown(
        f"""
        <div style="border:1px solid #e2e8f0;border-radius:12px;padding:16px;background:#ffffff;">
          <div style="margin-bottom:12px;"><b>Client / WMS code</b><br>{unique_join(ids) or "—"}</div>
          <div style="margin-bottom:12px;"><b>Matched Extensiv name</b><br>{unique_join(matched) or "—"}</div>
          <div><b>Go-live</b><br>{unique_join(go_live) or "—"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------- Only one details expander ----------
st.divider()
st.subheader("Migration summary")

# Determine the business status and the few dates needed for migration management.
if not m.empty:
    migration_status = "Migrated to Extensiv"
elif not n.empty:
    migration_status = "Directly onboarded to Extensiv"
elif not f.empty or not w.empty:
    migration_status = "Camelot / Planned Migration"
else:
    migration_status = "Extensiv"

planned_dates = []
actual_dates = []

for _df in [m, w, f]:
    if not _df.empty:
        for _c in ["Planned Go-Live Date (Extensiv)", "Planned Go Live Date (Extensiv)", "Planned Go-Live Date"]:
            if _c in _df.columns:
                planned_dates += _df[_c].tolist()
        for _c in ["Actual Go Live Date (In Extensiv)", "Actual Go-Live Date (In Extensiv)", "Actual Go Live Date"]:
            if _c in _df.columns:
                actual_dates += _df[_c].tolist()

planned_migration = safe_datetime_min(planned_dates)
actual_migration = safe_datetime_min(actual_dates)

# Region is a business result of warehouse location.
business_region = unique_join([region_from_warehouse(x) for x in warehouses]) or unique_join(regions) or "—"

summary_rows = [
    {"Information": "Migration status", "Value": migration_status},
    {"Information": "Warehouse", "Value": unique_join(warehouses) or "—"},
    {"Information": "Region", "Value": business_region},
    {"Information": "CSR", "Value": unique_join(csrs) or "—"},
    {"Information": "First Extensiv transaction", "Value": show_date(first_tx) if "show_date" in globals() else (first_tx.strftime("%Y-%m-%d") if first_tx is not None and not pd.isna(first_tx) else "—")},
]

if migration_status == "Migrated to Extensiv":
    summary_rows.append({
        "Information": "Actual migration / go-live",
        "Value": actual_migration.strftime("%Y-%m-%d") if actual_migration is not None and not pd.isna(actual_migration) else "—",
    })
elif migration_status == "Camelot / Planned Migration":
    summary_rows.append({
        "Information": "Planned migration to Extensiv",
        "Value": planned_migration.strftime("%Y-%m-%d") if planned_migration is not None and not pd.isna(planned_migration) else "—",
    })

st.dataframe(
    pd.DataFrame(summary_rows),
    hide_index=True,
    use_container_width=True,
    column_config={
        "Information": st.column_config.TextColumn(""),
        "Value": st.column_config.TextColumn(""),
    },
)

st.caption("Management view only — raw Excel columns, row numbers, technical matching fields, WMS document numbers and EDI details are intentionally hidden.")

