USE project4;
GO

/* ────────────────────────────────────────────────────────────────────
   1. Total Sales vs Purchases (line‑level dates only)
─────────────────────────────────────────────────────────────────────*/
IF OBJECT_ID('dbo.usp_KPI_SalesVsPurchases', 'P') IS NOT NULL
    DROP PROCEDURE dbo.usp_KPI_SalesVsPurchases;
GO
CREATE PROCEDURE dbo.usp_KPI_SalesVsPurchases
    @StartDate DATETIME = NULL,
    @EndDate   DATETIME = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
      /* sales from invoice lines, filter on LastEditedWhen */
      (SELECT SUM(ExtendedPrice)
       FROM dbo.SalesInvoiceLines
       WHERE (@StartDate IS NULL OR LastEditedWhen >= @StartDate)
         AND (@EndDate   IS NULL OR LastEditedWhen <= @EndDate)
      ) AS TotalSales,
      /* purchases from PO lines, filter on LastReceiptDate */
      (SELECT SUM(ExpectedUnitPricePerOuter * OrderedOuters)
       FROM dbo.PurchaseOrderLines
       WHERE (@StartDate IS NULL OR LastReceiptDate >= @StartDate)
         AND (@EndDate   IS NULL OR LastReceiptDate <= @EndDate)
      ) AS TotalPurchases;
END
GO

/* ────────────────────────────────────────────────────────────────────
   2. Average Margin per Product (line‑level dates only)
─────────────────────────────────────────────────────────────────────*/
CREATE OR ALTER PROCEDURE dbo.usp_KPI_AvgMarginPerProductWithGroup
    @StartDate DATETIME = NULL,
    @EndDate   DATETIME = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
      si.StockItemID,
      si.StockItemName,
      sg.StockGroupID,
      sg.StockGroupName,
      AVG(il.LineProfit)           AS AvgMargin,
      COUNT(DISTINCT il.InvoiceID) AS InvoiceCount,
      SUM(il.LineProfit)           AS TotalProfit,
      SUM(il.ExtendedPrice)        AS TotalRevenue,
      ROUND(
        SUM(il.LineProfit)*1.0
        / NULLIF(SUM(il.ExtendedPrice),0)
        * 100,2
      )                           AS MarginPct
    FROM dbo.SalesInvoiceLines AS il
    JOIN dbo.WarehouseStockItem AS si
      ON si.StockItemID = il.StockItemID
    LEFT JOIN dbo.StockItemsStockGroups AS sisg
      ON sisg.StockItemID = si.StockItemID
    LEFT JOIN dbo.WarehouseStockGroups AS sg
      ON sg.StockGroupID = sisg.StockGroupID
    WHERE (@StartDate IS NULL OR il.LastEditedWhen >= @StartDate)
      AND (@EndDate   IS NULL OR il.LastEditedWhen <= @EndDate)
    GROUP BY
      si.StockItemID,
      si.StockItemName,
      sg.StockGroupID,
      sg.StockGroupName
    ORDER BY AvgMargin DESC;
END;
GO

/* ────────────────────────────────────────────────────────────────────
   3. Deal Coverage → % of stock groups with at least one deal
─────────────────────────────────────────────────────────────────────*/
IF OBJECT_ID('dbo.usp_KPI_DealCoverage','P') IS NOT NULL
  DROP PROCEDURE dbo.usp_KPI_DealCoverage;
GO
CREATE PROCEDURE dbo.usp_KPI_DealCoverage
AS
BEGIN
  SET NOCOUNT ON;

  DECLARE 
    @TotalGroups    INT = (SELECT COUNT(*) FROM dbo.WarehouseStockGroups),
    @GroupsWithDeals INT = (
      SELECT COUNT(DISTINCT StockGroupID)
      FROM dbo.SalesSpecialDeals
      WHERE StockGroupID IS NOT NULL
    );

  SELECT
    @GroupsWithDeals              AS GroupsWithDeals,
    @TotalGroups                  AS TotalGroups,
    CAST(@GroupsWithDeals AS FLOAT)
      / NULLIF(@TotalGroups,0) * 100 
      AS DealCoveragePercent;
END;
GO

/* ────────────────────────────────────────────────────────────────────
   5. Stock Movement Volume (filter on TransactionOccurredWhen)
─────────────────────────────────────────────────────────────────────*/
IF OBJECT_ID('dbo.usp_KPI_StockMovementVolume', 'P') IS NOT NULL
    DROP PROCEDURE dbo.usp_KPI_StockMovementVolume;
GO
CREATE PROCEDURE dbo.usp_KPI_StockMovementVolume
    @StartDate DATETIME = NULL,
    @EndDate   DATETIME = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
      SUM(Quantity) AS TotalMovementVolume
    FROM dbo.StockItemTransactions
    WHERE (@StartDate IS NULL OR TransactionOccurredWhen >= @StartDate)
      AND (@EndDate   IS NULL OR TransactionOccurredWhen <= @EndDate);
END
GO

/* ────────────────────────────────────────────────────────────────────
   6. Most‑Discounted “Clients” → top N BuyingGroups by % discount
─────────────────────────────────────────────────────────────────────*/
IF OBJECT_ID('dbo.usp_KPI_MostDiscountedClients','P') IS NOT NULL
  DROP PROCEDURE dbo.usp_KPI_MostDiscountedClients;
GO
CREATE PROCEDURE dbo.usp_KPI_MostDiscountedClients
  @TopN INT = 10
AS
BEGIN
  SET NOCOUNT ON;

  SELECT TOP(@TopN)
    bg.BuyingGroupName       AS ClientGroup,
    SUM(sd.DiscountPercentage) AS TotalDiscountPct,
    COUNT(*)                   AS DealCount
  FROM dbo.SalesSpecialDeals AS sd
  JOIN dbo.SalesBuyingGroups AS bg
    ON bg.BuyingGroupID = sd.BuyingGroupID
  WHERE sd.DiscountPercentage IS NOT NULL
  GROUP BY
    bg.BuyingGroupName
  ORDER BY
    SUM(sd.DiscountPercentage) DESC;
END;
GO
