from fastapi import APIRouter, Depends
from utils.deps import get_current_user

router = APIRouter(prefix="/test", tags=["test"], dependencies=[Depends(get_current_user)])


@router.get("/list")
async def list_items():
    return {"msg": "success"}


@router.post("/create")
async def create_item():
    return {"msg": "success"}


@router.put("/update/{id}")
async def update_item(id: int):
    return {"msg": "success"}


@router.delete("/delete/{id}")
async def delete_item(id: int):
    return {"msg": "success"}
