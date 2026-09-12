from datetime import date
from math import ceil
from typing import Annotated

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import func, or_, select

from taskflow.api.dependencies import CurrentUser, DbSession, OwnedProject
from taskflow.models.project import Project
from taskflow.models.task import Task, TaskStatus
from taskflow.schemas.common import Page
from taskflow.schemas.project import (
    ProjectCreate,
    ProjectRead,
    ProjectStats,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: DbSession,
    current_user: CurrentUser,
) -> Project:
    project = Project(
        name=payload.name.strip(),
        description=payload.description,
        owner_id=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=Page[ProjectRead])
def list_projects(
    db: DbSession,
    current_user: CurrentUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(max_length=100)] = None,
) -> Page[ProjectRead]:
    filters = [Project.owner_id == current_user.id]
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(or_(Project.name.ilike(pattern), Project.description.ilike(pattern)))

    total = db.scalar(select(func.count(Project.id)).where(*filters)) or 0
    projects = list(
        db.scalars(
            select(Project)
            .where(*filters)
            .order_by(Project.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return Page(
        items=projects,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project: OwnedProject) -> Project:
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    payload: ProjectUpdate,
    project: OwnedProject,
    db: DbSession,
) -> Project:
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        updates["name"] = updates["name"].strip()
    for field, value in updates.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project: OwnedProject, db: DbSession) -> Response:
    db.delete(project)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/stats", response_model=ProjectStats)
def get_project_stats(project: OwnedProject, db: DbSession) -> ProjectStats:
    rows = db.execute(
        select(Task.status, func.count(Task.id))
        .where(Task.project_id == project.id)
        .group_by(Task.status)
    ).all()
    counts = {task_status.value: 0 for task_status in TaskStatus}
    for task_status, count in rows:
        counts[task_status.value] = count

    total = sum(counts.values())
    overdue = (
        db.scalar(
            select(func.count(Task.id)).where(
                Task.project_id == project.id,
                Task.due_date < date.today(),
                Task.status.not_in([TaskStatus.DONE, TaskStatus.CANCELLED]),
            )
        )
        or 0
    )
    return ProjectStats(
        total=total,
        todo=counts[TaskStatus.TODO.value],
        in_progress=counts[TaskStatus.IN_PROGRESS.value],
        done=counts[TaskStatus.DONE.value],
        cancelled=counts[TaskStatus.CANCELLED.value],
        overdue=overdue,
        completion_rate=round(counts[TaskStatus.DONE.value] / total * 100, 2) if total else 0.0,
    )
