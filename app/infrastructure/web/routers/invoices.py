from fastapi import APIRouter, status
router = APIRouter()

@router.get("/")
async def list_invoices():
    return {"message": "List invoices - To be implemented"}

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_invoice():
    return {"message": "Create invoice - To be implemented"}

@router.get("/{invoice_id}")
async def get_invoice(invoice_id: int):
    return {"message": f"Get invoice {invoice_id} - To be implemented"}

@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf(invoice_id: int):
    return {"message": f"Generate PDF for invoice {invoice_id} - To be implemented"}
