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
