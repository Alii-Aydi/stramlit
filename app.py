import datetime as dt
import pandas as pd
import streamlit as st
import plotly.express as px
from sqlalchemy import create_engine, text

# ── 1. Set Streamlit page config ───────────────────────────────────────────
st.set_page_config(page_title="Supply-Chain KPI Dashboard", layout="wide")

# ── 2. DB Engine ───────────────────────────────────────────────────────────
engine = create_engine(
    "mssql+pyodbc://DESKTOP-70UF714\\SQLEXPRESS/project4"
    "?driver=ODBC+Driver+17+for+SQL+Server"
    "&trusted_connection=yes"
)

def run_proc(proc_name: str, params=()):
    sql = f"EXEC {proc_name}" + (" " + ",".join("?" for _ in params) if params else "")
    return pd.read_sql(sql, engine, params=params)

# ── 3. Sidebar controls with 2013–2016 defaults ───────────────────────────
MIN_DATE = dt.date(2013, 1, 1)
MAX_DATE = dt.date(2016, 12, 31)
st.sidebar.header("Date Window")
start_date = st.sidebar.date_input("Start date", MIN_DATE, MIN_DATE, MAX_DATE)
end_date   = st.sidebar.date_input("End date",   MAX_DATE, MIN_DATE, MAX_DATE)
sd = dt.datetime.combine(start_date, dt.time.min)
ed = dt.datetime.combine(end_date,   dt.time.max)

# ── 4. Load KPI DataFrames ─────────────────────────────────────────────────
@st.cache_data(ttl=600)
def load_kpis(s, e):
    return {
        "sales_vs_pur":           run_proc("dbo.usp_KPI_SalesVsPurchases", (s, e)),
        "avg_margin_with_group":  run_proc("dbo.usp_KPI_AvgMarginPerProductWithGroup", (s, e)),
        "deal_cov":               run_proc("dbo.usp_KPI_DealCoverage", ()),
        "movement":               run_proc("dbo.usp_KPI_StockMovementVolume", (s, e)),
        "top_clients":            run_proc("dbo.usp_KPI_MostDiscountedClients", (10,)),
        "supplier_perf":          run_proc("dbo.usp_KPI_SupplierPerformance", ()),
        "promo_perf":             run_proc("dbo.usp_KPI_PromoPerformance", ()),
        "txn_dist":               run_proc("dbo.usp_KPI_TransactionDistribution", (s, e)),
        "gross":                  run_proc("dbo.usp_KPI_GrossProfit", ()),
        "cogs_vs_po":             run_proc("dbo.usp_KPI_COGSvsPurchases", ()),
        "promo_by_group":         run_proc("dbo.usp_KPI_PromoDealsByStockGroup", ()),
        "promo_by_buy":           run_proc("dbo.usp_KPI_PromoPerformanceByBuyingGroup", ()),
        "tax_variance":           run_proc("dbo.usp_KPI_SupposedTaxAmount", (s, e)),
        "sales_by_group":         run_proc("dbo.usp_KPI_SalesByStockGroup", (s, e)),
        "cust_seg":               run_proc("dbo.usp_KPI_CustomerSegmentSales", ()),
        "imbalance": run_proc("dbo.usp_KPI_ProductImbalance_SingleRow", (sd, ed, 10)),
    }

@st.cache_data(ttl=600)
def load_trend(s, e):
    sql = text("""
      WITH Sales AS (
        SELECT 
          DATEFROMPARTS(YEAR(LastEditedWhen), MONTH(LastEditedWhen), 1) AS Period,
          SUM(ExtendedPrice) AS Sales
        FROM dbo.SalesInvoiceLines
        WHERE LastEditedWhen BETWEEN :start AND :end
        GROUP BY YEAR(LastEditedWhen), MONTH(LastEditedWhen)
      ), Purchases AS (
        SELECT 
          DATEFROMPARTS(YEAR(LastReceiptDate), MONTH(LastReceiptDate), 1) AS Period,
          SUM(ExpectedUnitPricePerOuter * OrderedOuters) AS Purchases
        FROM dbo.PurchaseOrderLines
        WHERE LastReceiptDate BETWEEN :start AND :end
        GROUP BY YEAR(LastReceiptDate), MONTH(LastReceiptDate)
      )
      SELECT 
        COALESCE(s.Period, p.Period) AS Period,
        COALESCE(s.Sales, 0)       AS Sales,
        COALESCE(p.Purchases, 0)   AS Purchases
      FROM Sales s
      FULL OUTER JOIN Purchases p ON s.Period = p.Period
      ORDER BY Period;
    """)
    return pd.read_sql(sql, engine, params={"start": s, "end": e})

kpis  = load_kpis(sd, ed)
trend = load_trend(sd, ed)

# ── 5. Fix AvgMargin dtype so nlargest works ───────────────────────────────
kpis["avg_margin_with_group"]["AvgMargin"] = pd.to_numeric(
    kpis["avg_margin_with_group"]["AvgMargin"], errors="coerce"
)

# ── 6. Helper to safely extract a single value ─────────────────────────────
def get_first(df, col, default=0):
    return df[col].iloc[0] if col in df.columns and not df.empty and pd.notna(df[col].iloc[0]) else default

# ── 7. Extract headline metrics ────────────────────────────────────────────
sales     = get_first(kpis["sales_vs_pur"], "TotalSales")
purch     = get_first(kpis["sales_vs_pur"], "TotalPurchases")
profit    = get_first(kpis["gross"], "TotalProfit")
margin    = get_first(kpis["gross"], "GrossMarginPct")
cogs      = get_first(kpis["cogs_vs_po"], "COGS")
total_txn = int(kpis["txn_dist"]["TxnCount"].sum() or 0)
mov       = get_first(kpis["movement"], "TotalMovementVolume")
cov       = get_first(kpis["deal_cov"], "DealCoveragePercent")
deals     = int(get_first(kpis["promo_perf"], "ActiveDeals"))
avg_disc  = get_first(kpis["promo_perf"], "AvgDiscountPct") / 100.0
max_disc  = get_first(kpis["promo_perf"], "MaxDiscountPct") / 100.0

# ── 8. Headline metrics display ────────────────────────────────────────────
st.title("📊 Optimisation de la chaîne d’approvisionnement")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Sales",     f"${sales:,.2f}")
c2.metric("Total Profit",    f"${profit:,.2f}")
c3.metric("Gross Margin",    f"{margin:.1%}")
c4.metric("Total Purchases", f"${purch:,.2f}")

# ── 9. Cost & inventory metrics ───────────────────────────────────────────
c5, c6, c7 = st.columns(3)
c5.metric("COGS",               f"${cogs:,.2f}")
c6.metric("Total Transactions", f"{total_txn:,}")
c7.metric("Stock Movement Vol.",f"{mov:,}")

# ── 10. Performance & promotions metrics ──────────────────────────────────
p1, p2, p3, p4 = st.columns(4)
p1.metric("Deal Coverage",  f"{cov:.1f}%")
p2.metric("Active Deals",   f"{deals}")
p3.metric("Avg Discount %", f"{avg_disc:.1%}")
p4.metric("Max Discount %", f"{max_disc:.1%}")

# ── 11. Top-discounted clients ─────────────────────────────────────────────
st.subheader("🏷️ Top 10 Most-Discounted Clients")
st.table(kpis["top_clients"])

# ── 12. Section Tabs ────────────────────────────────────────────────────────
tabs = st.tabs([
    "📊 Sales vs Purchases Trend",
    "📈 Margin by Product",
    "🚚 Supplier Performance",
    "🛒 Sales by Stock Group",
    "📊 Customer Segments",
    "🔄 Transaction Mix",
    "🎯 Promo by Stock Group",
    "👥 Promo by Buying Group",
    "💲 Tax Analysis",
    "📦 Imbalance",
])

# Trend chart
with tabs[0]:
    st.subheader("Monthly Sales vs Purchases")
    trend["Period"] = pd.to_datetime(trend["Period"])
    fig = px.line(trend, x="Period", y=["Sales","Purchases"],
                  labels={"value":"Amount ($)", "Period":"Month"})
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(trend.style.format({"Sales":"${:,.2f}", "Purchases":"${:,.2f}"}))

# Margin by Product (with Group)
with tabs[1]:
    df_mg = kpis["avg_margin_with_group"].nlargest(10, "AvgMargin")
    st.subheader("Average Margin per Product (Top 10)")
    fig = px.bar(
        df_mg,
        x="StockItemName",
        y="AvgMargin",
        color="StockGroupName",
        labels={
          "StockItemName":"Product",
          "AvgMargin":"Avg Margin",
          "StockGroupName":"Product Group"
        }
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_mg)

# Supplier Performance
with tabs[2]:
    df_sup = kpis["supplier_perf"].nlargest(20, "TotalQtyReceived")
    st.subheader("Top Suppliers by Quantity Received")
    st.plotly_chart(px.bar(df_sup, x="SupplierName", y="TotalQtyReceived"), use_container_width=True)
    st.dataframe(df_sup)

# Sales by Stock Group
with tabs[3]:
    df_sbg = kpis["sales_by_group"]
    st.subheader("Units Sold & Profit by Stock Group")
    st.plotly_chart(px.bar(df_sbg, x="StockGroupName", y=["TotalUnitsSold","TotalProfit"], barmode="group"), use_container_width=True)
    st.dataframe(df_sbg)

# Customer Segments
with tabs[4]:
    df_cs = kpis["cust_seg"]
    st.subheader("Quantity Shipped by Customer Category")
    st.plotly_chart(px.bar(df_cs, x="CustomerCategoryName", y="TotalQtyShipped"), use_container_width=True)
    st.dataframe(df_cs)

# Transaction Mix
with tabs[5]:
    df_tx = kpis["txn_dist"]
    st.subheader("Transaction Type Distribution")
    st.plotly_chart(px.pie(df_tx, names="TransactionTypeName", values="TxnCount"), use_container_width=True)
    st.dataframe(df_tx)

# Promo by Stock Group
with tabs[6]:
    df_ps = kpis["promo_by_group"]
    st.subheader("Deals by Stock Group")
    if df_ps.empty:
        st.warning("⚠️ No deals by stock group—verify your mapping.")
    else:
        st.plotly_chart(px.bar(df_ps, x="StockGroupName", y="DealCount"), use_container_width=True)
        st.dataframe(df_ps)

# Promo by Buying Group
with tabs[7]:
    df_pb = kpis["promo_by_buy"]
    st.subheader("Deals by Buying Group")
    if df_pb.empty:
        st.warning("⚠️ No deals by buying group—verify your mapping.")
    else:
        st.plotly_chart(px.bar(df_pb, x="BuyingGroupName", y="DealCount"), use_container_width=True)
        st.dataframe(df_pb)

# Tax Analysis
with tabs[8]:
    df_tv = kpis["tax_variance"]
    df_agg = df_tv.groupby("TaxRate", as_index=False).agg(
        ExpectedTax=("ExpectedTaxAmount","sum"),
        RecordedTax=("RecordedTaxAmount","sum")
    )
    st.subheader("Expected vs Recorded Tax by Rate")
    fig2 = px.bar(df_agg, x="TaxRate", y=["ExpectedTax","RecordedTax"], barmode="group")
    st.plotly_chart(fig2, use_container_width=True)
    st.dataframe(df_agg.style.format({"ExpectedTax":"${:,.2f}","RecordedTax":"${:,.2f}"}))
    
with tabs[9]:
    df_im = kpis["imbalance"]
    st.subheader("Top 10 Products by Purchase–Sales Buildup")
    st.plotly_chart(
        px.bar(df_im,
               x="StockItemName",
               y="NetBuildUp",
               color="StockGroupNames",
               hover_data=["SupplierName","QtyPurchased","QtySold","PurchaseToSalesRatio"]),
        use_container_width=True
    )
    st.dataframe(df_im.style.format({
        "QtyPurchased":"{:,}",
        "QtySold":"{:,}",
        "NetBuildUp":"{:,}",
        "PurchaseToSalesRatio":".2f"
    }))


st.caption("⟡ Powered by SQL Server + Streamlit + Plotly (© 2025)")
