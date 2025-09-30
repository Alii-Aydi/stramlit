import os
from dotenv import load_dotenv
import datetime as dt
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_extras.colored_header import colored_header
from streamlit_extras.dataframe_explorer import dataframe_explorer
from sqlalchemy import create_engine, text
import humanize
import pyodbc
print(pyodbc.drivers())


# ── 1. Enhanced Page Configuration ─────────────────────────────────────────
st.set_page_config(
    page_title="Supply Chain Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 2. Custom CSS for Enhanced Styling ────────────────────────────────────
st.markdown("""
<style>
    /* Main container styling */
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    
    /* Metric card enhancements */
    .metric-container {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border-left: 4px solid #2a5298;
        margin-bottom: 1rem;
    }
    
    /* Section headers */
    .section-header {
        background: linear-gradient(90deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    
    /* Dashboard sections */
    .dashboard-section {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        border: 1px solid #e9ecef;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #0000;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        border: 1px solid #dee2e6;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #2a5298;
        color: white;
    }
    
    /* Custom warning and info boxes */
    .custom-warning {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .custom-info {
        background: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

load_dotenv()

# ── 3. Database Engine Setup ───────────────────────────────────────────────
server = os.environ["AZURE_SQL_SERVER"]
database = os.environ["AZURE_SQL_DATABASE"]
username = os.environ["AZURE_SQL_USERNAME"]
password = os.environ["AZURE_SQL_PASSWORD"]
driver = os.environ["AZURE_SQL_DRIVER"].replace(" ", "+")

# SQLAlchemy URL format for Azure SQL
connection_string = f"mssql+pyodbc://{username}:{password}@{server}:1433/{database}?driver={driver}&Encrypt=yes&TrustServerCertificate=no"

engine = create_engine(connection_string)


def run_proc(proc_name: str, params=()):
    sql = f"EXEC {proc_name}" + \
        (" " + ",".join("?" for _ in params) if params else "")
    return pd.read_sql(sql, engine, params=params)


# ── 4. Enhanced Sidebar with Better Organization ───────────────────────────
with st.sidebar:
    st.markdown("### 🔧 Dashboard Controls")

    # Date range selection with improved styling
    MIN_DATE = dt.date(2013, 1, 1)
    MAX_DATE = dt.date(2016, 12, 31)

    st.markdown("#### 📅 Date Range Filter")
    date_col1, date_col2 = st.columns(2)

    with date_col1:
        start_date = st.date_input(
            "Start Date",
            MIN_DATE,
            MIN_DATE,
            MAX_DATE,
            help="Select the start date for analysis"
        )

    with date_col2:
        end_date = st.date_input(
            "End Date",
            MAX_DATE,
            MIN_DATE,
            MAX_DATE,
            help="Select the end date for analysis"
        )

    # Date range validation
    if start_date > end_date:
        st.error("❌ Start date must be before end date")
        st.stop()

    # Convert dates for SQL queries
    sd = dt.datetime.combine(start_date, dt.time.min)
    ed = dt.datetime.combine(end_date, dt.time.max)

    # Dashboard refresh controls
    st.markdown("#### 🔄 Data Refresh")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

   

    # Info panel
    st.markdown("#### ℹ️ Dashboard Info")
    selected_days = (end_date - start_date).days + 1
    st.info(f"**Analysis Period**: {selected_days} days")

    

# ── 5. Enhanced Data Loading Functions ─────────────────────────────────────


@st.cache_data(ttl=600)
def load_kpis(s, e):
    with st.spinner("Loading KPI data..."):
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
            "imbalance":              run_proc("dbo.usp_KPI_ProductImbalance_SingleRow", (sd, ed, 10)),
        }


@st.cache_data(ttl=600)
def load_trend(s, e):
    with st.spinner("Loading trend data..."):
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


# Load data
kpis = load_kpis(sd, ed)
trend = load_trend(sd, ed)

# ── 6. Data Processing ──────────────────────────────────────────────────────
kpis["avg_margin_with_group"]["AvgMargin"] = pd.to_numeric(
    kpis["avg_margin_with_group"]["AvgMargin"], errors="coerce"
)


def get_first(df, col, default=0):
    return df[col].iloc[0] if col in df.columns and not df.empty and pd.notna(df[col].iloc[0]) else default


def format_number(n):
    return humanize.intword(n, format="%.1f").replace(' million', 'M').replace(' billion', 'B').replace(' thousand', 'K')




# ── 8. Key Performance Indicators Section ──────────────────────────────────
colored_header(
    label="📈 Key Performance Indicators",
    description="Primary business metrics and performance indicators",
    color_name="blue-70"
)

# Extract metrics
sales = get_first(kpis["sales_vs_pur"], "TotalSales")
purch = get_first(kpis["sales_vs_pur"], "TotalPurchases")
profit = get_first(kpis["gross"], "TotalProfit")
margin = get_first(kpis["gross"], "GrossMarginPct")
cogs = get_first(kpis["cogs_vs_po"], "COGS")
total_txn = int(kpis["txn_dist"]["TxnCount"].sum() or 0)
mov = get_first(kpis["movement"], "TotalMovementVolume")
cov = get_first(kpis["deal_cov"], "DealCoveragePercent")
deals = int(get_first(kpis["promo_perf"], "ActiveDeals"))
avg_disc = get_first(kpis["promo_perf"], "AvgDiscountPct") / 100.0
max_disc = get_first(kpis["promo_perf"], "MaxDiscountPct") / 100.0

# Financial Performance Metrics
st.markdown("#### 💰 Financial Performance")
fin_col1, fin_col2, fin_col3, fin_col4 = st.columns(4)

with fin_col1:
    st.metric(
        label="💵 Total Sales",
        value=format_number(sales),
        delta=f"{(sales/purch-1)*100:.1f}% vs Purchases" if purch > 0 else None,
        help="Total revenue generated from sales"
    )

with fin_col2:
    st.metric(
        label="💸 Total Purchases",
        value=format_number(purch),
        delta=f"{(purch/sales)*100:.1f}% of Sales" if sales > 0 else None,
        help="Total amount spent on purchases"
    )

with fin_col3:
    st.metric(
        label="💰 Gross Profit",
        value=format_number(profit),
        delta=f"{margin:.1f}% Margin",
        help="Total profit after cost of goods sold"
    )

with fin_col4:
    st.metric(
        label="📊 Gross Margin",
        value=f"{margin:.1f}%",
        delta="On avg sale",
        help="Profit as percentage of sales"
    )

# Operational Metrics
st.markdown("#### 🏭 Operational Performance")
op_col1, op_col2, op_col3 = st.columns(3)

with op_col1:
    st.metric(
        label="🔄 COGS",
        value=format_number(cogs),
        delta=f"{(cogs/sales)*100:.1f}% of Sales" if sales > 0 else None,
        help="Cost of goods sold"
    )

with op_col2:
    st.metric(
        label="📊 Total Transactions",
        value=format_number(total_txn),
        delta=f"${sales/total_txn:,.0f} avg/txn" if total_txn > 0 else None,
        help="Total number of transactions processed"
    )

with op_col3:
    st.metric(
        label="📦 Stock Movement",
        value=format_number(mov),
        delta="Units moved",
        help="Total volume of stock movement"
    )

# Sales & Promotion Metrics
st.markdown("#### 🎯 Sales & Promotions")
promo_col1, promo_col2, promo_col3, promo_col4 = st.columns(4)

with promo_col1:
    st.metric(
        label="📈 Deal Coverage",
        value=f"{cov:.1f}%",
        delta="Of Products",
        help="Percentage of products covered by deals"
    )

with promo_col2:
    st.metric(
        label="🎁 Active Deals",
        value=f"{deals:,}",
        delta="Current promotions",
        help="Number of currently active promotional deals"
    )

with promo_col3:
    st.metric(
        label="💳 Avg Discount",
        value=f"{avg_disc:.1%}",
        delta="Per transaction",
        help="Average discount percentage applied"
    )

with promo_col4:
    st.metric(
        label="🎊 Max Discount",
        value=f"{max_disc:.1%}",
        delta="Highest applied",
        help="Maximum discount percentage available"
    )

# Style the metrics
style_metric_cards(
    background_color="#0000",
    border_left_color="#2a5298",
    border_color="#e9ecef",
    box_shadow="0 2px 10px rgba(0,0,0,0.1)"
)

# ── 9. Top Discounted Clients Section ──────────────────────────────────────
st.markdown("---")
colored_header(
    label="🏷️ Top Discounted Clients",
    description="Customers receiving the highest discount rates",
    color_name="green-70"
)

# Enhanced client table with better formatting
if not kpis["top_clients"].empty:
    # Create enhanced table with styling
    client_df = kpis["top_clients"].copy()

    # Add rank column
    client_df.insert(0, 'Rank', range(1, len(client_df) + 1))

    # Format columns if they exist
    if 'TotalDiscountAmount' in client_df.columns:
        client_df['TotalDiscountAmount'] = client_df['TotalDiscountAmount'].apply(
            lambda x: f"${x:,.2f}")
    if 'AvgDiscountPct' in client_df.columns:
        client_df['AvgDiscountPct'] = client_df['AvgDiscountPct'].apply(
            lambda x: f"{x:.1f}%")

    st.dataframe(
        client_df,
        use_container_width=True,
        
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", width="small"),
            "CustomerName": st.column_config.TextColumn("Customer Name", width="large"),
            "TotalDiscountAmount": st.column_config.TextColumn("Total Discount", width="medium"),
            "AvgDiscountPct": st.column_config.TextColumn("Avg Discount %", width="medium"),
        }
    )
else:
    st.info("No client discount data available for the selected period.")

# ── 10. Enhanced Tabbed Analytics Section ──────────────────────────────────
st.markdown("---")
colored_header(
    label="📊 Detailed Analytics",
    description="In-depth analysis across different business dimensions",
    color_name="red-70"
)

# Create tabs with better organization
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Trends & Performance",
    "💰 Financial Analysis",
    "🏭 Operations & Supply",
    "🎯 Marketing & Promotions",
    "📊 Advanced Analytics"
])

# ── Tab 1: Trends & Performance ────────────────────────────────────────────
with tab1:
    # Sales vs Purchases Trend
    st.subheader("📈 Monthly Sales vs Purchases Trend")

    if not trend.empty:
        trend["Period"] = pd.to_datetime(trend["Period"]).dt.date

        # Create enhanced trend chart
        fig_trend = go.Figure()

        fig_trend.add_trace(go.Scatter(
            x=trend["Period"],
            y=trend["Sales"],
            mode='lines+markers',
            name='Sales',
            line=dict(color='#28a745', width=3),
            marker=dict(size=8),
            hovertemplate='<b>Sales</b><br>Date: %{x}<br>Amount: $%{y:,.0f}<extra></extra>'
        ))

        fig_trend.add_trace(go.Scatter(
            x=trend["Period"],
            y=trend["Purchases"],
            mode='lines+markers',
            name='Purchases',
            line=dict(color='#dc3545', width=3),
            marker=dict(size=8),
            hovertemplate='<b>Purchases</b><br>Date: %{x}<br>Amount: $%{y:,.0f}<extra></extra>'
        ))

        fig_trend.update_layout(
            title="Monthly Sales vs Purchases Comparison",
            xaxis_title="Month",
            yaxis_title="Amount ($)",
            hovermode='x unified',
            template='plotly_white',
            height=500,
            showlegend=True,
            legend=dict(x=0.02, y=0.98)
        )

        st.plotly_chart(fig_trend, use_container_width=True)

        # Summary statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Avg Monthly Sales", f"${trend['Sales'].mean():,.0f}")
        with col2:
            st.metric("📊 Avg Monthly Purchases",
                      f"${trend['Purchases'].mean():,.0f}")
        with col3:
            net_flow = trend['Sales'].sum() - trend['Purchases'].sum()
            st.metric("💰 Net Cash Flow", f"${net_flow:,.0f}")

        # Detailed trend data
        with st.expander("📋 View Detailed Trend Data"):
            st.dataframe(
                trend.style.format({
                    "Sales": "${:,.2f}",
                    "Purchases": "${:,.2f}"
                }),
                use_container_width=True
            )

    # Customer Segments
    st.subheader("👥 Customer Segment Performance")
    df_cs = kpis["cust_seg"]

    if not df_cs.empty:
        fig_cs = px.bar(
            df_cs,
            x="CustomerCategoryName",
            y="TotalQtyShipped",
            color="CustomerCategoryName",
            title="Quantity Shipped by Customer Category",
            labels={"TotalQtyShipped": "Total Quantity Shipped",
                    "CustomerCategoryName": "Customer Category"}
        )
        fig_cs.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_cs, use_container_width=True)

        with st.expander("📊 Customer Segment Details"):
            st.dataframe(df_cs, use_container_width=True)
    else:
        st.info("No customer segment data available.")

# ── Tab 2: Financial Analysis ──────────────────────────────────────────────
with tab2:
    # Sales by Stock Group
    st.subheader("📊 Sales Performance by Product Group")
    df_sbg = kpis["sales_by_group"]

    if not df_sbg.empty:
        fig_sbg = px.bar(
            df_sbg,
            x="StockGroupName",
            y=["TotalUnitsSold", "TotalProfit"],
            barmode="group",
            title="Units Sold vs Profit by Stock Group",
            labels={"value": "Amount", "variable": "Metric"}
        )
        fig_sbg.update_layout(height=500)
        st.plotly_chart(fig_sbg, use_container_width=True)

        with st.expander("📈 Sales by Group Details"):
            st.dataframe(df_sbg, use_container_width=True)

    # Margin Analysis
    st.subheader("💹 Product Margin Analysis")
    df_mg = kpis["avg_margin_with_group"].nlargest(10, "AvgMargin")

    if not df_mg.empty:
        fig_mg = px.bar(
            df_mg,
            x="StockItemName",
            y="AvgMargin",
            color="StockGroupName",
            title="Top 10 Products by Average Margin",
            labels={
                "StockItemName": "Product",
                "AvgMargin": "Average Margin ($)",
                "StockGroupName": "Product Group"
            }
        )
        fig_mg.update_layout(height=500)
        st.plotly_chart(fig_mg, use_container_width=True)

        with st.expander("💰 Margin Details"):
            st.dataframe(df_mg, use_container_width=True)

    # Tax Analysis
    st.subheader("💳 Tax Analysis")
    df_tv = kpis["tax_variance"]

    if not df_tv.empty:
        df_agg = df_tv.groupby("TaxRate", as_index=False).agg(
            ExpectedTax=("ExpectedTaxAmount", "sum"),
            RecordedTax=("RecordedTaxAmount", "sum")
        )

        fig_tax = px.bar(
            df_agg,
            x="TaxRate",
            y=["ExpectedTax", "RecordedTax"],
            barmode="group",
            title="Expected vs Recorded Tax by Rate",
            labels={"value": "Tax Amount ($)", "variable": "Tax Type"}
        )
        fig_tax.update_layout(height=400)
        st.plotly_chart(fig_tax, use_container_width=True)

        with st.expander("📊 Tax Details"):
            st.dataframe(
                df_agg.style.format({
                    "ExpectedTax": "${:,.2f}",
                    "RecordedTax": "${:,.2f}"
                }),
                use_container_width=True
            )

# ── Tab 3: Operations & Supply ─────────────────────────────────────────────
with tab3:
    # Supplier Performance
    st.subheader("🚚 Supplier Performance Analysis")
    df_sup = kpis["supplier_perf"].nlargest(20, "TotalQtyReceived")

    if not df_sup.empty:
        fig_sup = px.bar(
            df_sup.head(10),
            x="SupplierName",
            y="TotalQtyReceived",
            color="TotalQtyReceived",
            title="Top 10 Suppliers by Quantity Received",
            labels={"TotalQtyReceived": "Total Quantity Received"}
        )
        fig_sup.update_layout(height=500, showlegend=False)
        st.plotly_chart(fig_sup, use_container_width=True)

        with st.expander("📦 All Supplier Details"):
            st.dataframe(df_sup, use_container_width=True)

    # Transaction Distribution
    st.subheader("🔄 Transaction Type Distribution")
    df_tx = kpis["txn_dist"]

    if not df_tx.empty:
        fig_tx = px.pie(
            df_tx,
            names="TransactionTypeName",
            values="TxnCount",
            title="Distribution of Transaction Types",
            hole=0.4  # Donut chart
        )
        fig_tx.update_layout(height=500)
        st.plotly_chart(fig_tx, use_container_width=True)

        with st.expander("📊 Transaction Details"):
            st.dataframe(df_tx, use_container_width=True)

# ── Tab 4: Marketing & Promotions ──────────────────────────────────────────
with tab4:
    # Promo by Stock Group
    st.subheader("🎯 Promotional Deals by Stock Group")
    df_ps = kpis["promo_by_group"]

    if not df_ps.empty:
        fig_ps = px.bar(
            df_ps,
            x="StockGroupName",
            y="DealCount",
            color="DealCount",
            title="Number of Deals by Stock Group",
            labels={"DealCount": "Number of Deals",
                    "StockGroupName": "Stock Group"}
        )
        fig_ps.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_ps, use_container_width=True)

        with st.expander("📊 Stock Group Deal Details"):
            st.dataframe(df_ps, use_container_width=True)
    else:
        st.markdown("""
        <div class="custom-warning">
            <h4>⚠️ No Promotional Data Available</h4>
            <p>No deals by stock group found. This might indicate:</p>
            <ul>
                <li>No promotional campaigns during the selected period</li>
                <li>Data mapping issues between promotions and stock groups</li>
                <li>Promotional data not properly recorded</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    # Promo by Buying Group
    st.subheader("👥 Promotional Deals by Buying Group")
    df_pb = kpis["promo_by_buy"]

    if not df_pb.empty:
        fig_pb = px.bar(
            df_pb,
            x="BuyingGroupName",
            y="DealCount",
            color="DealCount",
            title="Number of Deals by Buying Group",
            labels={"DealCount": "Number of Deals",
                    "BuyingGroupName": "Buying Group"}
        )
        fig_pb.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_pb, use_container_width=True)

        with st.expander("📊 Buying Group Deal Details"):
            st.dataframe(df_pb, use_container_width=True)
    else:
        st.markdown("""
        <div class="custom-warning">
            <h4>⚠️ No Buying Group Data Available</h4>
            <p>No deals by buying group found. Please verify data mapping between promotions and buying groups.</p>
        </div>
        """, unsafe_allow_html=True)

# ── Tab 5: Advanced Analytics ──────────────────────────────────────────────
with tab5:
    # Product Imbalance Analysis
    st.subheader("📦 Product Inventory Imbalance Analysis")
    df_im = kpis["imbalance"]

    if not df_im.empty:
        fig_im = px.bar(
            df_im,
            x="StockItemName",
            y="NetBuildUp",
            color="StockGroupNames",
            title="Top 10 Products by Purchase-Sales Buildup",
            labels={
                "NetBuildUp": "Net Build Up (Units)",
                "StockItemName": "Product Name",
                "StockGroupNames": "Product Group"
            },
            hover_data=["SupplierName", "QtyPurchased",
                        "QtySold", "PurchaseToSalesRatio"]
        )
        fig_im.update_layout(height=500, xaxis_tickangle=-45)
        st.plotly_chart(fig_im, use_container_width=True)

        # Key insights
        col1, col2, col3 = st.columns(3)
        with col1:
            total_buildup = df_im["NetBuildUp"].sum()
            st.metric("📊 Total Net Buildup", f"{total_buildup:,} units")

        with col2:
            avg_ratio = df_im["PurchaseToSalesRatio"].mean()
            st.metric("📈 Avg Purchase/Sales Ratio", f"{avg_ratio:.2f}")

        with col3:
            critical_items = len(df_im[df_im["PurchaseToSalesRatio"] > 2])
            st.metric("⚠️ Critical Items", f"{critical_items}")

        # Detailed analysis
        with st.expander("📋 Detailed Imbalance Analysis"):
            st.markdown("**Products with highest inventory buildup:**")
            st.dataframe(
                df_im.style.format({
                    "QtyPurchased": "{:,}",
                    "QtySold": "{:,}",
                    "NetBuildUp": "{:,}",
                    "PurchaseToSalesRatio": "{:.2f}"
                }),
                use_container_width=True
            )

            # Risk assessment
            high_risk = df_im[df_im["PurchaseToSalesRatio"] > 3]
            if not high_risk.empty:
                st.markdown("**🚨 High Risk Products (Ratio > 3):**")
                st.dataframe(high_risk[["StockItemName", "SupplierName",
                             "PurchaseToSalesRatio"]], use_container_width=True)
    else:
        st.info("No product imbalance data available for the selected period.")

    # Additional Analytics Section
    st.subheader("🔍 Additional Performance Metrics")

    # Create performance summary
    perf_col1, perf_col2 = st.columns(2)

    with perf_col1:
        st.markdown("##### 📊 Financial Health")

        # Calculate key ratios
        if sales > 0 and purch > 0:
            profit_margin = (profit / sales) * 100
            turnover_ratio = sales / purch

            health_metrics = pd.DataFrame({
                'Metric': ['Profit Margin', 'Sales/Purchase Ratio', 'COGS Ratio', 'Deal Coverage'],
                'Value': [f'{profit_margin:.1f}%', f'{turnover_ratio:.2f}', f'{(cogs/sales)*100:.1f}%', f'{cov:.1f}%'],
                'Status': [
                    '✅ Good' if profit_margin > 20 else '⚠️ Monitor' if profit_margin > 10 else '❌ Poor',
                    '✅ Good' if turnover_ratio > 1.2 else '⚠️ Monitor' if turnover_ratio > 1.0 else '❌ Poor',
                    '✅ Good' if (
                        cogs/sales)*100 < 60 else '⚠️ Monitor' if (cogs/sales)*100 < 80 else '❌ Poor',
                    '✅ Good' if cov > 80 else '⚠️ Monitor' if cov > 60 else '❌ Poor'
                ]
            })

            st.dataframe(health_metrics, use_container_width=True,
                         hide_index=True)

    with perf_col2:
        st.markdown("##### 🎯 Operational Efficiency")

        # Operational metrics
        if total_txn > 0:
            avg_txn_value = sales / total_txn

            ops_metrics = pd.DataFrame({
                'Metric': ['Avg Transaction Value', 'Active Deals', 'Stock Movement', 'Avg Discount'],
                'Value': [f'${avg_txn_value:,.0f}', f'{deals:,}', f'{mov:,}', f'{avg_disc:.1f}%'],
                'Trend': ['📈', '🎯', '🔄', '💳']
            })

            st.dataframe(ops_metrics, use_container_width=True,
                         hide_index=True)

# ── 11. Executive Summary Section ──────────────────────────────────────────
st.markdown("---")
colored_header(
    label="📋 Executive Summary",
    description="Key insights and recommendations based on current data",
    color_name="violet-70"
)

# Generate insights
insights_col1, insights_col2 = st.columns(2)

with insights_col1:
    st.markdown("#### 🎯 Key Insights")

    insights = []

    # Financial insights
    if margin > 25:
        insights.append(
            "✅ Strong gross margin indicates healthy pricing strategy")
    elif margin > 15:
        insights.append("⚠️ Moderate margin - consider cost optimization")
    else:
        insights.append("❌ Low margin - urgent pricing/cost review needed")

    # Sales insights
    if sales > purch * 1.3:
        insights.append("✅ Strong sales performance vs purchases")
    elif sales > purch:
        insights.append(
            "⚠️ Sales slightly above purchases - monitor inventory")
    else:
        insights.append("❌ Sales below purchases - inventory buildup risk")

    # Deal coverage insights
    if cov > 80:
        insights.append("✅ Excellent deal coverage across product range")
    elif cov > 60:
        insights.append("⚠️ Good deal coverage - expand to more products")
    else:
        insights.append(
            "❌ Low deal coverage - missing promotion opportunities")

    # Display insights
    for insight in insights:
        st.markdown(f"• {insight}")

with insights_col2:
    st.markdown("#### 💡 Recommendations")

    recommendations = []

    # Based on margin
    if margin < 20:
        recommendations.append(
            "🎯 Focus on high-margin products and pricing optimization")

    # Based on deal coverage
    if cov < 70:
        recommendations.append(
            "📈 Expand promotional programs to improve deal coverage")

    # Based on inventory
    if not df_im.empty and df_im["PurchaseToSalesRatio"].mean() > 2:
        recommendations.append(
            "📦 Review inventory management - potential overstock issues")

    # Based on discounts
    if avg_disc > 0.15:
        recommendations.append(
            "💰 Analyze discount strategy - high average discount rates")

    # Default recommendations
    if not recommendations:
        recommendations.extend([
            "📊 Continue monitoring key performance indicators",
            "🔄 Maintain current operational efficiency",
            "🎯 Explore new growth opportunities"
        ])

    # Display recommendations
    for rec in recommendations:
        st.markdown(f"• {rec}")



# ── 13. Data Export Options ────────────────────────────────────────────────
with st.expander("📥 Export Data"):
    st.markdown("#### Download Options")

    export_col1, export_col2, export_col3 = st.columns(3)

    with export_col1:
        if st.button("📊 Export KPI Summary"):
            # Create summary DataFrame
            summary_data = {
                'Metric': ['Total Sales', 'Total Purchases', 'Gross Profit', 'Gross Margin', 'COGS', 'Total Transactions'],
                'Value': [sales, purch, profit, margin, cogs, total_txn]
            }
            summary_df = pd.DataFrame(summary_data)

            csv = summary_df.to_csv(index=False)
            st.download_button(
                label="💾 Download CSV",
                data=csv,
                file_name=f"kpi_summary_{start_date}_to_{end_date}.csv",
                mime="text/csv"
            )

    with export_col2:
        if st.button("📈 Export Trend Data"):
            if not trend.empty:
                csv = trend.to_csv(index=False)
                st.download_button(
                    label="💾 Download CSV",
                    data=csv,
                    file_name=f"sales_trend_{start_date}_to_{end_date}.csv",
                    mime="text/csv"
                )

    with export_col3:
        if st.button("🏷️ Export Client Data"):
            if not kpis["top_clients"].empty:
                csv = kpis["top_clients"].to_csv(index=False)
                st.download_button(
                    label="💾 Download CSV",
                    data=csv,
                    file_name=f"top_clients_{start_date}_to_{end_date}.csv",
                    mime="text/csv"
                )

# ── 14. Debug Information (Optional) ───────────────────────────────────────
if st.checkbox("🔧 Show Debug Information"):
    st.markdown("#### Debug Information")
    debug_col1, debug_col2 = st.columns(2)

    with debug_col1:
        st.markdown("##### Data Loading Status")
        st.write(f"• KPI data loaded: {len(kpis)} datasets")
        st.write(f"• Trend data points: {len(trend)}")
        st.write(f"• Date range: {(end_date - start_date).days + 1} days")

    with debug_col2:
        st.markdown("##### System Information")
        st.write(f"• Dashboard loaded at: {dt.datetime.now()}")
        st.write(f"• Cache TTL: 600 seconds")
        st.write(f"• Database engine: SQL Server")
