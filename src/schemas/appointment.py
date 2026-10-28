from datetime import date, time
from typing import List, Literal, Optional

from pydantic import BaseModel

AppointmentType = Literal["GIAO_MAY", "NHAN_MAY", "KIEM_TRA_TAI_CHO"]
AppointmentStatus = Literal["DA_DAT", "DA_XAC_NHAN", "HOAN_TAT", "KHACH_HUY", "KHACH_KHONG_DEN"]


class AppointmentCreate(BaseModel):
    ticket_id: int
    loai: AppointmentType
    ngay_hen: date
    gio_bat_dau: time
    gio_ket_thuc: time


class AppointmentUpdate(BaseModel):
    loai: Optional[AppointmentType] = None
    # v0.2: only confirmation is allowed; cancellation statuses are deferred (US10).
    trang_thai: Optional[Literal["DA_XAC_NHAN"]] = None
    ngay_hen: Optional[date] = None
    gio_bat_dau: Optional[time] = None
    gio_ket_thuc: Optional[time] = None


class AppointmentRead(BaseModel):
    appointment_id: int
    ticket_id: int
    ticket_code: Optional[str] = None
    technician_id: int
    technician_ho_ten: Optional[str] = None
    center_id: int
    loai: str
    trang_thai: str
    ngay_hen: date
    gio_bat_dau: time
    gio_ket_thuc: time
    is_deleted: bool


class AppointmentList(BaseModel):
    page: int
    page_size: int
    total: int
    items: List[AppointmentRead]


class AppointmentDeleted(BaseModel):
    appointment_id: int
    is_deleted: bool


class AppointmentConflict(BaseModel):
    appointment_id: int
    ticket_id: int
    ngay_hen: date
    gio_bat_dau: time
    gio_ket_thuc: time
    trang_thai: str


class AppointmentConflictList(BaseModel):
    conflicts: List[AppointmentConflict]
