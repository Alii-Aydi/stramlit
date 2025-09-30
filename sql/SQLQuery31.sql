USE project4;
GO

CREATE OR ALTER PROCEDURE dbo.usp_KPI_GrossProfit
AS
BEGIN
  SET NOCOUNT ON;
  SELECT
    SUM(LineProfit)   AS TotalProfit,
    SUM(ExtendedPrice) AS TotalRevenue,
    (SUM(LineProfit)*1.0)/NULLIF(SUM(ExtendedPrice),0) AS GrossMarginPct
  FROM dbo.SalesInvoiceLines;
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_KPI_COGSvsPurchases
AS
BEGIN
  SET NOCOUNT ON;
  SELECT
    SUM(ExtendedPrice - LineProfit) AS COGS,
    (SELECT SUM(ExpectedUnitPricePerOuter*OrderedOuters) FROM dbo.PurchaseOrderLines) AS TotalPurchases
  FROM dbo.SalesInvoiceLines;
END;
GO

-- 2) Distinct deal counts per group
CREATE OR ALTER PROCEDURE dbo.usp_KPI_PromoDealsByStockGroup
AS
BEGIN
  SET NOCOUNT ON;

  SELECT
    grp.StockGroupID,
    grp.StockGroupName,
    COUNT(DISTINCT sd.SpecialDealID)    AS DealCount,
    /* union of item-level and group-level items */
    COUNT(DISTINCT COALESCE(sd.StockItemID, sisg2.StockItemID)) AS AffectedItems,
    AVG(sd.DiscountPercentage)         AS AvgDiscountPct
  FROM dbo.SalesSpecialDeals AS sd

  LEFT JOIN dbo.StockItemsStockGroups AS sisg
    ON sisg.StockItemID = sd.StockItemID

  JOIN dbo.WarehouseStockGroups AS grp
    ON grp.StockGroupID = COALESCE(sisg.StockGroupID, sd.StockGroupID)

  /* for AffectedItems union */
  LEFT JOIN dbo.StockItemsStockGroups AS sisg2
    ON sisg2.StockGroupID = grp.StockGroupID

  GROUP BY
    grp.StockGroupID,
    grp.StockGroupName
  ORDER BY
    DealCount DESC;
END;
GO

-- 3) Promo performance by BuyingGroup × StockGroup
CREATE OR ALTER PROCEDURE dbo.usp_KPI_PromoPerformanceByBuyingGroup
AS
BEGIN
  SET NOCOUNT ON;

  SELECT
    bg.BuyingGroupID,
    bg.BuyingGroupName,
    grp.StockGroupID,
    grp.StockGroupName,
    COUNT(DISTINCT sd.SpecialDealID)    AS DealCount,
    AVG(sd.DiscountPercentage)         AS AvgDiscountPct,
    SUM(COALESCE(il.ExtendedPrice, 0)) AS SalesDuringDeals,
    SUM(COALESCE(il.LineProfit,    0)) AS ProfitDuringDeals
  FROM dbo.SalesSpecialDeals AS sd
  JOIN dbo.SalesBuyingGroups       AS bg
    ON bg.BuyingGroupID = sd.BuyingGroupID

  LEFT JOIN dbo.StockItemsStockGroups AS sisg
    ON sisg.StockItemID = sd.StockItemID

  JOIN dbo.WarehouseStockGroups AS grp
    ON grp.StockGroupID = COALESCE(sisg.StockGroupID, sd.StockGroupID)

  LEFT JOIN dbo.StockItemsStockGroups AS sisg2
    ON sisg2.StockGroupID = grp.StockGroupID

  LEFT JOIN dbo.SalesInvoiceLines AS il
    ON il.StockItemID = sisg2.StockItemID

  GROUP BY
    bg.BuyingGroupID,
    bg.BuyingGroupName,
    grp.StockGroupID,
    grp.StockGroupName
  ORDER BY
    SalesDuringDeals DESC;
END;
GO


/* ── Invoice-level variance so rounding errors surface ───────────── */
CREATE OR ALTER PROCEDURE dbo.usp_KPI_SupposedTaxAmount
  @StartDate DATETIME = NULL,
  @EndDate   DATETIME = NULL
AS
BEGIN
  SET NOCOUNT ON;

  SELECT
    il.InvoiceLineID,
    il.InvoiceID,
    il.ExtendedPrice     AS LineTotalWithTax,
    il.TaxRate,
    il.TaxAmount         AS RecordedTaxAmount,
    -- back-calculate expected tax from the stored line total:
    ROUND(
      il.ExtendedPrice
      * (il.TaxRate / (100.0 + il.TaxRate))
    ,2)                  AS ExpectedTaxAmount,
    il.TaxAmount
      - ROUND(
          il.ExtendedPrice
          * (il.TaxRate / (100.0 + il.TaxRate))
        ,2)
      AS TaxVariance
  FROM dbo.SalesInvoiceLines il
  WHERE (@StartDate IS NULL OR il.LastEditedWhen >= @StartDate)
    AND (@EndDate   IS NULL OR il.LastEditedWhen <= @EndDate);
END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_KPI_SalesByStockGroup
  @StartDate DATETIME = NULL,
  @EndDate   DATETIME = NULL,
  @CountryID INT      = NULL
AS
BEGIN
  SET NOCOUNT ON;

  ;WITH SalesLines AS (
    -- Pull only the invoice‐lines in your date window, with Customer
    SELECT
      il.StockItemID,
      il.Quantity,
      il.LineProfit,
      il.ExtendedPrice,
      si.CustomerID
    FROM dbo.SalesInvoiceLines AS il
    LEFT JOIN dbo.SalesInvoices AS si
      ON si.InvoiceID = il.InvoiceID
    WHERE 
      (@StartDate IS NULL OR il.LastEditedWhen >= @StartDate)
      AND (@EndDate   IS NULL OR il.LastEditedWhen <= @EndDate)
  ),
  SalesWithGroups AS (
    -- Map each sale into its stock‐group, falling back to sd.StockGroupID if needed
    SELECT
      COALESCE(sisg.StockGroupID, sg0.StockGroupID) AS StockGroupID,
      sl.Quantity,
      sl.LineProfit,
      sl.ExtendedPrice,
      sl.CustomerID
    FROM SalesLines AS sl
    LEFT JOIN dbo.StockItemsStockGroups AS sisg
      ON sisg.StockItemID = sl.StockItemID
    LEFT JOIN dbo.WarehouseStockGroups AS sg0
      ON sg0.StockGroupID = sisg.StockGroupID
  )
  SELECT
    sg.StockGroupID,
    sg.StockGroupName,
    cn.CountryName,
    SUM(swg.Quantity)      AS TotalUnitsSold,
    SUM(swg.LineProfit)    AS TotalProfit,
    SUM(swg.ExtendedPrice) AS TotalRevenue,
  
    ROUND(
      SUM(swg.LineProfit)*1.0 
      / NULLIF(SUM(swg.ExtendedPrice),0) 
      * 100,2
    )                      AS GrossMarginPct
  FROM SalesWithGroups AS swg
  JOIN dbo.WarehouseStockGroups AS sg
    ON sg.StockGroupID = swg.StockGroupID
  LEFT JOIN dbo.SalesCustomers AS sc
    ON sc.CustomerID = swg.CustomerID
  LEFT JOIN dbo.ApplicationCities AS city
    ON city.CityID = sc.DeliveryCityID
  LEFT JOIN dbo.ApplicationStatesProvinces AS sp
    ON sp.StateProvinceID = city.StateProvinceID
  LEFT JOIN dbo.ApplicationCountries AS cn
    ON cn.CountryID = sp.CountryID
  WHERE (@CountryID IS NULL OR cn.CountryID = @CountryID)
  GROUP BY
    sg.StockGroupID,
    sg.StockGroupName,
    cn.CountryName
  ORDER BY
    TotalUnitsSold DESC;
END;
GO
