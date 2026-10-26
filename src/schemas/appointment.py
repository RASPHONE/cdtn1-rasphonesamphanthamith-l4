from datetime import date, time
from typing import List, Literal, Optional

from pydantic import BaseModel


class AppointmentCreate(BaseModel):
    ticket_id: int
    loai: Literal["GIAO_MAY", "NHAN_MAY", "KIEM_TRA_TAI_CHO"]
    ngay_hen: date
    gio_bat_dau: time
    gio_ket_thuc: time


class AppointmentUpdate(BaseModel):
    loai: Optional[Literal["GIAO_MAY", "NHAN_MAY", "KIEM_TRA_TAI_CHO"]] = None
    trang_thai: Optional[
        Literal[
            "DA_DAT",
            "DA_XAC_NHAN",
            "HOAN_TAT",
            "KHACH_HUY",
            "KHACH_KHONG_DEN",
        ]
    ] = None
    ngay_hen: Optional[date] = None
    gio_bat_dau: Optional[time] = None
    gio_ket_thuc: Optional[time] = None


class AppointmentRead(BaseModel):
    appointment_id: int
    ticket_id: int
    technician_id: int
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
