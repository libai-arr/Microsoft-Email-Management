from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.group import Group
from app.models.mailbox import Mailbox
from app.schemas.group import GroupCreate, GroupUpdate, GroupResponse

router = APIRouter()


@router.get("", response_model=list[GroupResponse])
async def list_groups(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Group, func.count(Mailbox.id).label("mailbox_count"))
        .outerjoin(Mailbox, Group.id == Mailbox.group_id)
        .group_by(Group.id)
        .order_by(Group.created_at)
    )
    rows = (await db.execute(stmt)).all()
    return [
        GroupResponse(
            id=g.id,
            name=g.name,
            description=g.description,
            created_at=g.created_at,
            mailbox_count=count,
        )
        for g, count in rows
    ]


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(body: GroupCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Group).where(Group.name == body.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="分组名称已存在")

    group = Group(name=body.name, description=body.description)
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        mailbox_count=0,
    )


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: UUID, body: GroupUpdate, db: AsyncSession = Depends(get_db)
):
    group = await db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")

    if body.name is not None:
        group.name = body.name
    if body.description is not None:
        group.description = body.description

    await db.commit()
    await db.refresh(group)

    count_stmt = select(func.count(Mailbox.id)).where(Mailbox.group_id == group_id)
    count = (await db.execute(count_stmt)).scalar() or 0

    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        mailbox_count=count,
    )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(group_id: UUID, db: AsyncSession = Depends(get_db)):
    group = await db.get(Group, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="分组不存在")

    await db.delete(group)
    await db.commit()
