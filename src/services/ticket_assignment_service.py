from typing import Any, Dict, List

from src.db import get_connection
from src.errors import AppError
from src.schemas.ticket import AssignmentCreate, AssignmentUpdate


class TicketAssignmentService:
    CLOSED_TICKET_STATUSES = {"HOAN_TAT", "DA_DONG", "DA_HUY"}

    def __init__(
        self,
        ticket_repository,
        technician_repository,
        technician_skill_repository,
        status_log_repository,
    ):
        self.ticket_repo = ticket_repository
        self.technician_repo = technician_repository
        self.skill_repo = technician_skill_repository
        self.status_log_repo = status_log_repository

    def list_unassigned_tickets(
        self,
        *,
        center_id: int,
        category_id: int | None = None,
        priority: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        items, total = self.ticket_repo.list_unassigned(
            center_id=center_id,
            category_id=category_id,
            priority=priority,
            page=page,
            page_size=page_size,
        )

        return {
            "page": page,
            "page_size": page_size,
            "total": total,
            "items": items,
        }

    def list_qualified_technicians(
        self,
        *,
        center_id: int,
        ticket_id: int,
    ) -> Dict[str, Any]:
        ticket = self._get_active_ticket_for_center(
            center_id=center_id,
            ticket_id=ticket_id,
        )

        items = self.technician_repo.list_qualified_for_category(
            center_id=ticket["center_id"],
            category_id=ticket["category_id"],
        )

        return {
            "ticket_id": ticket_id,
            "items": items,
        }

    def assign_technician(
        self,
        *,
        center_id: int,
        ticket_id: int,
        payload: AssignmentCreate,
        changed_by: int,
    ) -> Dict[str, Any]:
        ticket = self._get_active_ticket_for_center(
            center_id=center_id,
            ticket_id=ticket_id,
        )

        if ticket["status"] != "MOI" or ticket["technician_id"] is not None:
            raise AppError(
                "ticket_not_assignable",
                "This ticket is not eligible for first-time assignment.",
            )

        technician = self._get_qualified_technician(
            ticket=ticket,
            technician_id=payload.technician_id,
        )

        # NFR5: ticket update + status log insert in ONE transaction.
        with get_connection() as conn:
            updated_ticket = self.ticket_repo.assign_technician(
                ticket_id,
                technician["technician_id"],
                "DA_PHAN_CONG",
                conn=conn,
            )
            log_id = self.status_log_repo.create(
                ticket_id=ticket_id,
                from_status="MOI",
                to_status="DA_PHAN_CONG",
                changed_by=changed_by,
                note=None,
                conn=conn,
            )

        if not updated_ticket:
            raise AppError(
                "ticket_not_found",
                "Ticket not found.",
            )

        updated_ticket["log_id"] = log_id
        return updated_ticket

    def reassign_technician(
        self,
        *,
        center_id: int,
        ticket_id: int,
        payload: AssignmentUpdate,
        changed_by: int,
    ) -> Dict[str, Any]:
        ticket = self._get_active_ticket_for_center(
            center_id=center_id,
            ticket_id=ticket_id,
        )

        if ticket["technician_id"] is None or ticket["status"] == "MOI":
            raise AppError(
                "ticket_not_assignable",
                "This ticket is not currently assigned.",
            )

        reason = payload.reason.strip()

        if len(reason) < 5 or len(reason) > 255:
            raise AppError(
                "reason_required",
                "Reassignment reason must be between 5 and 255 characters.",
            )

        technician = self._get_qualified_technician(
            ticket=ticket,
            technician_id=payload.technician_id,
        )

        # NFR5: ticket update + status log insert in ONE transaction.
        with get_connection() as conn:
            updated_ticket = self.ticket_repo.update_technician(
                ticket_id,
                technician["technician_id"],
                conn=conn,
            )
            log_id = self.status_log_repo.create(
                ticket_id=ticket_id,
                from_status=ticket["status"],
                to_status=ticket["status"],
                changed_by=changed_by,
                note=reason,
                conn=conn,
            )

        if not updated_ticket:
            raise AppError(
                "ticket_not_found",
                "Ticket not found.",
            )

        updated_ticket["log_id"] = log_id
        return updated_ticket

    def _get_active_ticket_for_center(
        self,
        *,
        center_id: int,
        ticket_id: int,
    ) -> Dict[str, Any]:
        ticket = self.ticket_repo.get_by_id(ticket_id)

        if not ticket or ticket["is_deleted"]:
            raise AppError(
                "ticket_not_found",
                "Ticket not found.",
            )

        if ticket["center_id"] != center_id:
            raise AppError(
                "cross_center_access",
                "You cannot access another center's ticket.",
            )

        if not ticket["is_warranty"]:
            raise AppError(
                "ticket_not_assignable",
                "Only warranty tickets can use this assignment flow.",
            )

        if ticket["status"] in self.CLOSED_TICKET_STATUSES:
            raise AppError(
                "ticket_not_assignable",
                "Closed tickets cannot be assigned or reassigned.",
            )

        return ticket

    def _get_qualified_technician(
        self,
        *,
        ticket: Dict[str, Any],
        technician_id: int,
    ) -> Dict[str, Any]:
        technician = self.technician_repo.get_by_id(technician_id)

        if not technician:
            raise AppError(
                "technician_not_found",
                "Technician not found.",
            )

        if not technician["is_active"]:
            raise AppError(
                "technician_not_qualified",
                "Technician is not active.",
            )

        if technician["center_id"] != ticket["center_id"]:
            raise AppError(
                "technician_not_qualified",
                "Technician belongs to another center.",
            )

        skill = self.skill_repo.get_skill(
            technician_id=technician_id,
            category_id=ticket["category_id"],
        )

        if not skill or skill["proficiency"] < 3:
            raise AppError(
                "technician_not_qualified",
                "Technician does not have sufficient proficiency for this category.",
            )

        return technician
