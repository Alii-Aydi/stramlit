USE project4;
GO

-- 1. Speed up filtering/join on SalesInvoiceLines by LastEditedWhen & StockItemID
CREATE NONCLUSTERED INDEX IX_SIL_LastEditedWhen_StockItemID
ON dbo.SalesInvoiceLines(LastEditedWhen)
INCLUDE(StockItemID, LineProfit, Quantity, ExtendedPrice);

-- 2. Speed up receipt & transaction scans by type + key fields
CREATE NONCLUSTERED INDEX IX_SIT_ByType_Date
ON dbo.StockItemTransactions(TransactionTypeID, TransactionOccurredWhen)
INCLUDE(StockItemID, SupplierID, CustomerID, Quantity);

-- 4. Cover lookups in ApplicationTransactionTypes
CREATE UNIQUE INDEX IX_TT_Name ON dbo.ApplicationTransactionTypes(TransactionTypeName);

GO
