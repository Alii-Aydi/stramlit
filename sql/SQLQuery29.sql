USE project4;
GO

/*──────────────────────────────────────────────────────────────────────
  1. Supplier Performance
──────────────────────────────────────────────────────────────────────*/
CREATE OR ALTER PROCEDURE dbo.usp_KPI_SupplierPerformance
AS
BEGIN
  SET NOCOUNT ON;

  ;WITH Receipts AS (
    SELECT
      sit.SupplierID,
      sit.TransactionOccurredWhen AS ReceiptDate,
      sit.Quantity
    FROM dbo.StockItemTransactions sit
    JOIN dbo.ApplicationTransactionTypes tt
      ON tt.TransactionTypeID = sit.TransactionTypeID
    WHERE
      tt.TransactionTypeName = 'Stock Receipt'
      AND sit.SupplierID IS NOT NULL
  ),
  Numbered AS (
    SELECT
      SupplierID,
      Quantity,
      ReceiptDate,
      LAG(ReceiptDate) OVER(
        PARTITION BY SupplierID ORDER BY ReceiptDate
      ) AS PrevReceipt
    FROM Receipts
  )
  SELECT
    s.SupplierID,
    sp.SupplierName,
    COUNT(*)                         AS ReceiptEvents,
    SUM(s.Quantity)                 AS TotalQtyReceived,
    AVG(DATEDIFF(day, s.PrevReceipt, s.ReceiptDate)) AS AvgDaysBetweenReceipts
  FROM Numbered s
  JOIN dbo.PurchasingSuppliers sp
    ON sp.SupplierID = s.SupplierID
  GROUP BY
    s.SupplierID,
    sp.SupplierName
  ORDER BY TotalQtyReceived DESC;
END;
GO


/*──────────────────────────────────────────────────────────────────────
  2. Promotions Impact
──────────────────────────────────────────────────────────────────────*/
-- 1) Overall promo performance (deals + sales/profit)
CREATE OR ALTER PROCEDURE dbo.usp_KPI_PromoPerformance
AS
BEGIN
  SET NOCOUNT ON;

  SELECT
    grp.StockGroupID,
    grp.StockGroupName,
    COUNT(DISTINCT sd.SpecialDealID) AS ActiveDeals,
    AVG(sd.DiscountPercentage)      AS AvgDiscountPct,
    MAX(sd.DiscountPercentage)      AS MaxDiscountPct,
    SUM(COALESCE(il.ExtendedPrice, 0)) AS SalesDuringDeals,
    SUM(COALESCE(il.LineProfit,    0)) AS ProfitDuringDeals
  FROM dbo.SalesSpecialDeals AS sd

  /* map item-level deals to groups */
  LEFT JOIN dbo.StockItemsStockGroups AS sisg
    ON sisg.StockItemID = sd.StockItemID

  /* determine group: bridge if present, else deal’s own GroupID */
  JOIN dbo.WarehouseStockGroups AS grp
    ON grp.StockGroupID = COALESCE(sisg.StockGroupID, sd.StockGroupID)

  /* pull every sale for any item in that group */
  LEFT JOIN dbo.StockItemsStockGroups AS sisg2
    ON sisg2.StockGroupID = grp.StockGroupID
  LEFT JOIN dbo.SalesInvoiceLines       AS il
    ON il.StockItemID = sisg2.StockItemID

  GROUP BY
    grp.StockGroupID,
    grp.StockGroupName
  ORDER BY
    ActiveDeals DESC;
END;
GO


/*──────────────────────────────────────────────────────────────────────
  3. Customer Segment Behaviour
──────────────────────────────────────────────────────────────────────*/
IF OBJECT_ID('dbo.usp_KPI_CustomerSegmentSales','P') IS NOT NULL
  DROP PROCEDURE dbo.usp_KPI_CustomerSegmentSales;
GO

CREATE PROCEDURE dbo.usp_KPI_CustomerSegmentSales
AS
BEGIN
  SET NOCOUNT ON;

  SELECT
    cc.CustomerCategoryName,
    COUNT(DISTINCT sit.CustomerID)    AS Customers,
    COUNT(*)                          AS ShipmentEvents,
    SUM(ABS(sit.Quantity))            AS TotalQtyShipped
  FROM dbo.StockItemTransactions sit
  JOIN dbo.SalesCustomers c
    ON c.CustomerID = sit.CustomerID
  JOIN dbo.SalesCustomersCategories cc
    ON cc.CustomerCategoryID = c.CustomerCategoryID
  WHERE sit.CustomerID IS NOT NULL
    AND sit.TransactionTypeID = 10    -- Stock Issue
  GROUP BY cc.CustomerCategoryName
  ORDER BY TotalQtyShipped DESC;
END;
GO


/*──────────────────────────────────────────────────────────────────────
  4. Transaction Type Distribution
     – minor: filter by date uses our new index
──────────────────────────────────────────────────────────────────────*/
CREATE OR ALTER PROCEDURE dbo.usp_KPI_TransactionDistribution
  @StartDate DATETIME = NULL,
  @EndDate   DATETIME = NULL
AS
BEGIN
  SET NOCOUNT ON;

  SELECT
    tt.TransactionTypeName,
    COUNT(*)                        AS TxnCount,
    COUNT(*)*100.0/SUM(COUNT(*)) OVER() AS PctShare
  FROM dbo.StockItemTransactions sit
  JOIN dbo.ApplicationTransactionTypes tt
    ON tt.TransactionTypeID = sit.TransactionTypeID
  WHERE
    (@StartDate IS NULL OR sit.TransactionOccurredWhen >= @StartDate)
    AND (@EndDate   IS NULL OR sit.TransactionOccurredWhen <= @EndDate)
  GROUP BY tt.TransactionTypeName
  ORDER BY TxnCount DESC;
END;
GO



CREATE OR ALTER PROCEDURE dbo.usp_KPI_ProductImbalance_SingleRow
    @StartDate DATETIME = NULL,
    @EndDate   DATETIME = NULL,
    @TopN      INT      = 10
AS
BEGIN
  SET NOCOUNT ON;

  ;WITH
  Sales AS (
    SELECT StockItemID, SUM(Quantity) AS QtySold
    FROM dbo.SalesInvoiceLines
    WHERE (@StartDate IS NULL OR LastEditedWhen >= @StartDate)
      AND (@EndDate   IS NULL OR LastEditedWhen <= @EndDate)
    GROUP BY StockItemID
  ),
  Purch AS (
    SELECT 
      pol.StockItemID,
      po.SupplierID,
      SUM(pol.OrderedOuters) AS QtyPurchased
    FROM dbo.PurchaseOrderLines pol
    JOIN dbo.PurchaseOrders po
      ON po.PurchaseOrderID = pol.PurchaseOrderID
    WHERE (@StartDate IS NULL OR pol.LastReceiptDate >= @StartDate)
      AND (@EndDate   IS NULL OR pol.LastReceiptDate <= @EndDate)
    GROUP BY pol.StockItemID, po.SupplierID
  ),
  Imb AS (
    SELECT
      pur.StockItemID,
      pur.SupplierID,
      COALESCE(pur.QtyPurchased,0) AS QtyPurchased,
      COALESCE(sal.QtySold,0)       AS QtySold,
      COALESCE(pur.QtyPurchased,0) - COALESCE(sal.QtySold,0) AS NetBuildUp,
      CASE 
        WHEN COALESCE(sal.QtySold,0)=0 THEN NULL
        ELSE CAST(pur.QtyPurchased AS FLOAT)/sal.QtySold 
      END AS PurchaseToSalesRatio
    FROM Purch pur
    LEFT JOIN Sales sal
      ON sal.StockItemID = pur.StockItemID
  )
  SELECT TOP(@TopN)
    i.StockItemID,
    si.StockItemName,
    STRING_AGG(sg.StockGroupName, ', ') 
      WITHIN GROUP (ORDER BY sg.StockGroupName) 
      AS StockGroupNames,
    i.SupplierID,
    sup.SupplierName,
    i.QtyPurchased,
    i.QtySold,
    i.NetBuildUp,
    i.PurchaseToSalesRatio
  FROM Imb i
  JOIN dbo.WarehouseStockItem     si
    ON si.StockItemID = i.StockItemID
  JOIN dbo.PurchasingSuppliers     sup
    ON sup.SupplierID = i.SupplierID
  LEFT JOIN dbo.StockItemsStockGroups sisg
    ON sisg.StockItemID = i.StockItemID
  LEFT JOIN dbo.WarehouseStockGroups   sg
    ON sg.StockGroupID = sisg.StockGroupID
  GROUP BY
    i.StockItemID,
    si.StockItemName,
    i.SupplierID,
    sup.SupplierName,
    i.QtyPurchased,
    i.QtySold,
    i.NetBuildUp,
    i.PurchaseToSalesRatio
  ORDER BY
    NetBuildUp DESC;
END;
GO

