from fastapi import APIRouter, status
router = APIRouter()

@router.get("/")
async def list_projects():
    return {"message": "List projects - To be implemented"}

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_project():
    return {"message": "Create project - To be implemented"}

@router.get("/{project_id}")
async def get_project(project_id: int):
    return {"message": f"Get project {project_id} - To be implemented"}

@router.put("/{project_id}")
async def update_project(project_id: int):
    return {"message": f"Update project {project_id} - To be implemented"}
