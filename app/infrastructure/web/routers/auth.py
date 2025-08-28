from fastapi import APIRouter, status
router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register():
    return {"message": "Registration endpoint - To be implemented"}

@router.post("/login")
async def login():
    return {"message": "Login endpoint - To be implemented"}

@router.post("/refresh")
async def refresh_token():
    return {"message": "Refresh endpoint - To be implemented"}

@router.get("/profile")
async def get_profile():
    return {"message": "Profile endpoint - To be implemented"}
