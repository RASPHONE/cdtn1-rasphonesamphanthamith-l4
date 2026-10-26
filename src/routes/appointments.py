from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from src.repositories.appointment_repository import PostgresAppointmentRepository
from src.repositories.ticket_repository import PostgresTicketRepository
from src.schemas.appointment import (
    AppointmentCreate,
    AppointmentList,
    AppointmentRead,
    AppointmentUpdate,
)
from src.security import get_current_center_id
from src.services.appointment_service import AppointmentService

router = APIRouter(prefix="/api/appointments", tags=["appointments"])


def get_appointment_service() -> AppointmentService:
    return AppointmentService(
        appointment_repository=PostgresAppointmentRepository(),
        ticket_repository=PostgresTicketRepository(),
    )


@router.get("", response_model=AppointmentList)
def list_appointments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    technician_id: Optional[int] = None,
    ticket_id: Optional[int] = None,
    ngay_hen: Optional[date] = None,
    trang_thai: Optional[str] = None,
    include_deleted: bool = False,
    center_id: int = Depends(get_current_center_id),
    service: AppointmentService = Depends(get_appointment_service),
):
    return service.list_appointments(
        center_id=center_id,
        page=page,
        page_size=page_size,
        technician_id=technician_id,
        ticket_id=ticket_id,
        ngay_hen=ngay_hen,
        trang_thai=trang_thai,
        include_deleted=include_deleted,
    )


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment(
    appointment_id: int,
    include_deleted: bool = False,
    center_id: int = Depends(get_current_center_id),
    service: AppointmentService = Depends(get_appointment_service),
):
    return service.get_appointment(
        center_id=center_id,
        appointment_id=appointment_id,
        include_deleted=include_deleted,
    )


@router.post("", response_model=AppointmentRead, status_code=201)
def create_appointment(
    payload: AppointmentCreate,
    center_id: int = Depends(get_current_center_id),
    service: AppointmentService = Depends(get_appointment_service),
):
    return service.create_appointment(
        center_id=center_id,
        payload=payload,
    )


@router.patch("/{appointment_id}", response_model=AppointmentRead)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    center_id: int = Depends(get_current_center_id),
    service: AppointmentService = Depends(get_appointment_service),
):
    return service.update_appointment(
        center_id=center_id,
        appointment_id=appointment_id,
        payload=payload,
    )


@router.delete("/{appointment_id}")
def delete_appointment(
    appointment_id: int,
    center_id: int = Depends(get_current_center_id),
    service: AppointmentService = Depends(get_appointment_service),
):
    return service.soft_delete_appointment(
        center_id=center_id,
        appointment_id=appointment_id,
    )
