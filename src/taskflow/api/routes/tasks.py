from math import ceil
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select

from taskflow.api.dependencies import CurrentUser, DbSession, OwnedProject
from taskflow.models.project import Project
from taskflow.models.task import Task, TaskPriority, TaskStatus
from taskflow.schemas.common import Page
from taskflow.schemas.task import TaskCreate, TaskRead, TaskUpdate

project_tasks_router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])
task_router = APIRouter(prefix="/tasks", tags=["tasks"])


@project_tasks_router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    project: OwnedProject,
    db: DbSession,
) -> Task:
    task = Task(
        **payload.model_dump(),
        project_id=project.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@project_tasks_router.get("", response_model=Page[TaskRead])
def list_tasks(
    project: OwnedProject,
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: TaskPriority | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> Page[TaskRead]:
    filters = [Task.project_id == project.id]
    if task_status is not None:
        filters.append(Task.status == task_status)
    if priority is not None:
        filters.append(Task.priority == priority)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(Task.title.ilike(pattern), Task.description.ilike(pattern)))

    total = db.scalar(select(func.count(Task.id)).where(*filters)) or 0
    tasks = list(
        db.scalars(
            select(Task)
            .where(*filters)
            .order_by(Task.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return Page(
        items=tasks,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


def get_owned_task(task_id: int, db: DbSession, current_user: CurrentUser) -> Task:
    task = db.scalar(
        select(Task)
        .join(Project)
        .where(Task.id == task_id, Project.owner_id == current_user.id)
    )
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@task_router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, db: DbSession, current_user: CurrentUser) -> Task:
    return get_owned_task(task_id, db, current_user)


@task_router.patch("/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Task:
    task = get_owned_task(task_id, db, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@task_router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: DbSession, current_user: CurrentUser) -> Response:
    task = get_owned_task(task_id, db, current_user)
    db.delete(task)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
