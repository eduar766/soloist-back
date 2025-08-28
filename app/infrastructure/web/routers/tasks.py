from fastapi import APIRouter, status
router = APIRouter()

@router.get("/")
async def list_tasks():
    return {"message": "List tasks - To be implemented"}

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_task():
    return {"message": "Create task - To be implemented"}

@router.get("/{task_id}")
async def get_task(task_id: int):
    return {"message": f"Get task {task_id} - To be implemented"}

@router.put("/{task_id}")
async def update_task(task_id: int):
    return {"message": f"Update task {task_id} - To be implemented"}
