USE project4;
GO

-- 1) Import PurchaseOrders and PurchaseOrderLines from the WWI database
SELECT *
INTO dbo.PurchaseOrders
FROM WideWorldImporters.Purchasing.PurchaseOrders;
GO

-- 2) Add primary keys
ALTER TABLE dbo.PurchaseOrders
ADD CONSTRAINT PK_PurchaseOrders
  PRIMARY KEY CLUSTERED (PurchaseOrderID);
GO

-- PurchaseOrders → Suppliers
ALTER TABLE dbo.PurchaseOrders
ADD CONSTRAINT FK_POrders_To_Suppliers
  FOREIGN KEY (SupplierID) 
    REFERENCES dbo.PurchasingSuppliers (SupplierID);
GO

-- PurchaseOrders → DeliveryMethods
ALTER TABLE dbo.PurchaseOrders
ADD CONSTRAINT FK_POrders_To_DeliveryMethods
  FOREIGN KEY (DeliveryMethodID) 
    REFERENCES dbo.ApplicationDeliveryMethods (DeliveryMethodID);
GO

-- PurchaseOrders → ContactPerson
ALTER TABLE dbo.PurchaseOrders
ADD CONSTRAINT FK_POrders_To_ContactPerson
  FOREIGN KEY (ContactPersonID) 
    REFERENCES dbo.ApplicationPeople (PersonID);
GO

-- PurchaseOrders → AuthorisedPerson
ALTER TABLE dbo.PurchaseOrders
ADD CONSTRAINT FK_POrders_To_AuthorisedPerson
  FOREIGN KEY (AuthorisedPersonID) 
    REFERENCES dbo.ApplicationPeople (PersonID);
GO

-- PurchaseOrderLines → PurchaseOrders
ALTER TABLE dbo.PurchaseOrderLines
ADD CONSTRAINT FK_POLines_To_POrders
  FOREIGN KEY (PurchaseOrderID) 
    REFERENCES dbo.PurchaseOrders (PurchaseOrderID);
GO