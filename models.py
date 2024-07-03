from dataclasses import dataclass
from typing import List, Optional

import duckdb
from pydantic import BaseModel


@dataclass
class InvoiceDenormalized:
    CompanyId: int
    ReturnedInvoiceId: int
    returnedMessageItemId: int
    returnedDocumentId: int
    ReturnedMessageItemFileName: str
    OriginalMessageItemId: str
    ReturnedMessageId: int
    ReturnedMessageCreatedTime: str
    VendorName: str
    VendorNumber: str
    InfinxInvoiceNumber: str
    InfinxInvoiceAmount: float
    InfinxInvoiceDate: str
    InfinxVendorNumber: str
    InfinxPurchaseOrder: str
    SalesOrderNumber: str
    SalesOrderDate: Optional[dict]
    DueDate: str
    SalesTaxPercent: float
    SalesTaxAmount: float
    MiscCharges: float
    DeliveryDate: Optional[dict]
    ShipDate: Optional[dict]
    ShippingCharges: float
    PurchaseOrderNum: str
    PurchaseOrderLineNum: str
    SupplierPartNum: str
    ItemDescription: str
    UnitOfMeasure: str
    UnitPrice: float
    Quantity: float
    LineItemNetTotal: float
    TaxPercent: float
    TaxAmount: float
    LineItemTotal: float
    MiscAmount: float
    MiscInfo: str
    MiscInfoXML: Optional[dict]
    ContactType: int
    ContactType_US: str
    ContactName: str
    ContactAddress1: str
    ContactAddress2: str
    ContactCity: str
    ContactState: str

    @staticmethod
    def get_column_names():
        return [
            field.name for field in InvoiceDenormalized.__dataclass_fields__.values()
        ]

    @staticmethod
    def from_db_cursor(cursor: duckdb.DuckDBPyConnection):
        columns = [
            col[0]
            for col in cursor.description  # pyright: ignore[reportOptionalIterable]
        ]
        while True:
            rows = cursor.fetchmany(256)
            if not rows:
                break
            for row in rows:
                row_dict = dict(zip(columns, row))
                invoice = InvoiceDenormalized(**row_dict)
                yield invoice


@dataclass
class InvoiceLineItem:
    LineItemTotal: float
    LineItemNetTotal: Optional[float] = None
    UnitPrice: Optional[float] = None
    Quantity: float = 1.0
    ItemDescription: str = ""
    UnitOfMeasure: str = ""
    SupplierPartNum: str = ""

    def __post_init__(self):
        self.ItemDescription = self.ItemDescription.upper()
        if self.UnitPrice is None:
            self.UnitPrice = self.LineItemTotal
        if self.LineItemNetTotal is None:
            self.LineItemNetTotal = self.LineItemTotal

    def to_dict(self):
        return self.__dict__


@dataclass
class Invoice:
    CompanyId: int
    ReturnedInvoiceId: int
    returnedMessageItemId: int
    returnedDocumentId: int
    ReturnedMessageItemFileName: str
    OriginalMessageItemId: str
    ReturnedMessageId: int
    ReturnedMessageCreatedTime: str
    VendorName: str
    VendorNumber: str
    InfinxInvoiceNumber: str
    InfinxInvoiceAmount: float
    InfinxInvoiceDate: str
    InfinxVendorNumber: str
    InfinxPurchaseOrder: str
    SalesOrderNumber: str
    SalesOrderDate: Optional[dict]
    DueDate: str
    SalesTaxPercent: float
    SalesTaxAmount: float
    MiscCharges: float
    DeliveryDate: Optional[dict]
    ShipDate: Optional[dict]
    ShippingCharges: float
    PurchaseOrderNum: str
    PurchaseOrderLineNum: str
    TaxPercent: float
    TaxAmount: float
    MiscAmount: float
    MiscInfo: str
    MiscInfoXML: Optional[dict]
    ContactType: int
    ContactType_US: str
    ContactName: str
    ContactAddress1: str
    ContactAddress2: str
    ContactCity: str
    ContactState: str

    file_path: Optional[str]
    line_items: List[InvoiceLineItem]

    def to_dict(self) -> dict:
        return {**self.__dict__, "line_items": [l.to_dict() for l in self.line_items]}

    def to_extracted(self) -> "ExtractedInvoice":
        return ExtractedInvoice(
            InvoiceHeaderInfo=InvoiceHeaderInfo(
                SalesTaxAmount=self.SalesTaxAmount,
                ShippingCharges=self.ShippingCharges,
                InvoiceNumber=self.InfinxInvoiceNumber,
                InvoiceAmount=self.InfinxInvoiceAmount,
                InvoiceDate=self.InfinxInvoiceDate,
                PurchaseOrder=self.InfinxPurchaseOrder,
                VendorContactInfo=VendorContactInfo(
                    ContactName=self.ContactName,
                    ContactAddress1=self.ContactAddress1,
                    ContactAddress2=self.ContactAddress2,
                    ContactCity=self.ContactCity,
                    ContactState=self.ContactState,
                ),
            ),
            InvoiceLineItems=self.line_items,
        )

    @staticmethod
    def from_denormalized(
        data: List[InvoiceDenormalized], file_path: Optional[str] = None
    ) -> "Invoice":
        if not data:
            raise ValueError("The data list is empty")

        first_item = data[0]
        line_items = [
            InvoiceLineItem(
                ItemDescription=item.ItemDescription,
                UnitOfMeasure=item.UnitOfMeasure,
                UnitPrice=item.UnitPrice,
                Quantity=item.Quantity,
                LineItemNetTotal=item.LineItemNetTotal,
                LineItemTotal=item.LineItemTotal,
                SupplierPartNum=item.SupplierPartNum,
            )
            for item in data
            if item.ContactType != 5
        ]

        return Invoice(
            CompanyId=first_item.CompanyId,
            ReturnedInvoiceId=first_item.ReturnedInvoiceId,
            returnedMessageItemId=first_item.returnedMessageItemId,
            returnedDocumentId=first_item.returnedDocumentId,
            ReturnedMessageItemFileName=first_item.ReturnedMessageItemFileName,
            OriginalMessageItemId=first_item.OriginalMessageItemId,
            ReturnedMessageId=first_item.ReturnedMessageId,
            ReturnedMessageCreatedTime=first_item.ReturnedMessageCreatedTime,
            VendorName=first_item.VendorName,
            VendorNumber=first_item.VendorNumber,
            InfinxInvoiceNumber=first_item.InfinxInvoiceNumber,
            InfinxInvoiceAmount=first_item.InfinxInvoiceAmount,
            InfinxInvoiceDate=first_item.InfinxInvoiceDate,
            InfinxVendorNumber=first_item.InfinxVendorNumber,
            InfinxPurchaseOrder=first_item.InfinxPurchaseOrder,
            SalesOrderNumber=first_item.SalesOrderNumber,
            SalesOrderDate=first_item.SalesOrderDate,
            DueDate=first_item.DueDate,
            SalesTaxPercent=first_item.SalesTaxPercent,
            SalesTaxAmount=first_item.SalesTaxAmount,
            MiscCharges=first_item.MiscCharges,
            DeliveryDate=first_item.DeliveryDate,
            ShipDate=first_item.ShipDate,
            ShippingCharges=first_item.ShippingCharges,
            PurchaseOrderNum=first_item.PurchaseOrderNum,
            PurchaseOrderLineNum=first_item.PurchaseOrderLineNum,
            TaxPercent=first_item.TaxPercent,
            TaxAmount=first_item.TaxAmount,
            MiscAmount=first_item.MiscAmount,
            MiscInfo=first_item.MiscInfo,
            MiscInfoXML=first_item.MiscInfoXML,
            ContactType=first_item.ContactType,
            ContactType_US=first_item.ContactType_US,
            ContactName=first_item.ContactName,
            ContactAddress1=first_item.ContactAddress1,
            ContactAddress2=first_item.ContactAddress2,
            ContactCity=first_item.ContactCity,
            ContactState=first_item.ContactState,
            line_items=line_items,
            file_path=file_path,
        )


@dataclass
class VendorContactInfo:
    ContactName: str = ""
    ContactAddress1: str = ""
    ContactAddress2: str = ""
    ContactCity: str = ""
    ContactState: str = ""


@dataclass
class InvoiceHeaderInfo:
    InvoiceNumber: str
    InvoiceAmount: float
    InvoiceDate: str
    VendorContactInfo: VendorContactInfo
    PurchaseOrder: str = ""
    SalesTaxAmount: float = 0.0
    ShippingCharges: float = 0.0


class ExtractedInvoice(BaseModel):
    InvoiceHeaderInfo: InvoiceHeaderInfo
    InvoiceLineItems: List[InvoiceLineItem]
