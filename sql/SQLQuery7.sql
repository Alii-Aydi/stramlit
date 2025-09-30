SELECT *
INTO dbo.SalesInvoices
FROM WideWorldImporters.Sales.Invoices;

ALTER TABLE dbo.SalesInvoices
  ADD CONSTRAINT PK_SalesInvoices 
      PRIMARY KEY CLUSTERED (InvoiceID);

ALTER TABLE dbo.SalesInvoices
  ADD CONSTRAINT FK_SalesInvoices_Customers
      FOREIGN KEY (CustomerID)
      REFERENCES dbo.SalesCustomers(CustomerID);
