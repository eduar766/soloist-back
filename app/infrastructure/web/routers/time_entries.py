from fastapi import APIRouter, status
router = APIRouter()

@router.get("/")
async def list_time_entries():
    return {"message": "List time entries - To be implemented"}

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_time_entry():
    return {"message": "Create time entry - To be implemented"}

@router.post("/timer/start", status_code=status.HTTP_201_CREATED)
async def start_timer():
    return {"message": "Start timer - To be implemented"}

@router.post("/timer/stop")
async def stop_timer():
    return {"message": "Stop timer - To be implemented"}
