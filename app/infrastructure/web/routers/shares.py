from fastapi import APIRouter, status
router = APIRouter()

@router.get("/")
async def list_shares():
    return {"message": "List shares - To be implemented"}

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_share():
    return {"message": "Create share - To be implemented"}

@router.get("/{token}")
async def get_shared_content(token: str):
    return {"message": f"Get shared content for token {token} - To be implemented"}

@router.delete("/{share_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_share(share_id: int):
    return None
