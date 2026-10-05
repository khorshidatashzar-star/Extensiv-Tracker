import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Extensiv Migration Portfolio", page_icon="📦", layout="wide")

# ---------------- CONFIG ----------------
DEFAULT_DATA_FILE = "migration_portfolio.csv"

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

def load_data():
    data_path = Path(__file__).resolve().parent / DEFAULT_DATA_FILE
    if data_path.exists():
        return pd.read_csv(data_path, low_memory=False)
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
