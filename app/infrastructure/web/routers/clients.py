from fastapi import APIRouter, status
router = APIRouter()

@router.get("/")
async def list_clients():
    return {"message": "List clients - To be implemented"}

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_client():
    return {"message": "Create client - To be implemented"}

@router.get("/{client_id}")
async def get_client(client_id: int):
    return {"message": f"Get client {client_id} - To be implemented"}

@router.put("/{client_id}")
async def update_client(client_id: int):
    return {"message": f"Update client {client_id} - To be implemented"}

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(client_id: int):
    return None
