from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from src.repositories.technician_repository import PostgresTechnicianRepository
from src.repositories.technician_skill_repository import (
    PostgresTechnicianSkillRepository,
)
from src.repositories.ticket_repository import PostgresTicketRepository
from src.repositories.ticket_status_log_repository import (
    PostgresTicketStatusLogRepository,
)
from src.repositories.transaction import postgres_transaction
from src.schemas.ticket import (
    AssignmentCreate,
    AssignmentUpdate,
    QualifiedTechnicianList,
    TicketAssignmentRead,
    TicketDetailRead,
    UnassignedTicketList,
)
from src.security import get_current_center_id, get_current_role, get_current_user_id
from src.services.ticket_assignment_service import TicketAssignmentService

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

Priority = Literal["CAO", "TRUNG_BINH", "THAP"]


def get_ticket_assignment_service() -> TicketAssignmentService:
    return TicketAssignmentService(
        ticket_repository=PostgresTicketRepository(),
        technician_repository=PostgresTechnicianRepository(),
        technician_skill_repository=PostgresTechnicianSkillRepository(),
        status_log_repository=PostgresTicketStatusLogRepository(),
        transaction=postgres_transaction,
    )


@router.get("/unassigned", response_model=UnassignedTicketList)
def list_unassigned_tickets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = Query(None, ge=1),
    priority: Optional[Priority] = None,
    center_id: int = Depends(get_current_center_id),
    role: str = Depends(get_current_role),
    service: TicketAssignmentService = Depends(get_ticket_assignment_service),
):
    return service.list_unassigned_tickets(
        center_id=center_id,
        role=role,
        category_id=category_id,
        priority=priority,
        page=page,
        page_size=page_size,
    )


@router.get("/{ticket_id}", response_model=TicketDetailRead)
def get_ticket(
    ticket_id: int,
    center_id: int = Depends(get_current_center_id),
    role: str = Depends(get_current_role),
    service: TicketAssignmentService = Depends(get_ticket_assignment_service),
):
    return service.get_ticket(center_id=center_id, ticket_id=ticket_id, role=role)


@router.get(
    "/{ticket_id}/qualified-technicians",
    response_model=QualifiedTechnicianList,
)
def list_qualified_technicians(
    ticket_id: int,
    center_id: int = Depends(get_current_center_id),
    service: TicketAssignmentService = Depends(get_ticket_assignment_service),
):
    return service.list_qualified_technicians(
        center_id=center_id,
        ticket_id=ticket_id,
    )


@router.post(
    "/{ticket_id}/assignment",
    response_model=TicketAssignmentRead,
)
def assign_technician(
    ticket_id: int,
    payload: AssignmentCreate,
    center_id: int = Depends(get_current_center_id),
    user_id: int = Depends(get_current_user_id),
    service: TicketAssignmentService = Depends(get_ticket_assignment_service),
):
    return service.assign_technician(
        center_id=center_id,
        ticket_id=ticket_id,
        payload=payload,
        changed_by=user_id,
    )


@router.patch(
    "/{ticket_id}/assignment",
    response_model=TicketAssignmentRead,
)
def reassign_technician(
    ticket_id: int,
    payload: AssignmentUpdate,
    center_id: int = Depends(get_current_center_id),
    user_id: int = Depends(get_current_user_id),
    service: TicketAssignmentService = Depends(get_ticket_assignment_service),
):
    return service.reassign_technician(
        center_id=center_id,
        ticket_id=ticket_id,
        payload=payload,
        changed_by=user_id,
    )
