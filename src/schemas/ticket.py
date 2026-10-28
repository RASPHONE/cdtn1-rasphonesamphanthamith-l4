from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class UnassignedTicketRead(BaseModel):
    ticket_id: int
    ticket_code: str
    center_id: int
    customer_name: str
    customer_phone: str
    serial_no: str
    issue_desc: str
    category_id: int
    category_name: str
    priority: str
    status: str
    technician_id: Optional[int]
    received_at: datetime
    due_date: datetime
    is_warranty: bool


class UnassignedTicketList(BaseModel):
    page: int
    page_size: int
    total: int
    items: List[UnassignedTicketRead]


class QualifiedTechnicianRead(BaseModel):
    technician_id: int
    technician_code: str
    ho_ten: str
    level: str
    proficiency: int
    workload: int


class AssignmentCreate(BaseModel):
    technician_id: int


class AssignmentUpdate(BaseModel):
    technician_id: int
    reason: str


class TicketAssignmentRead(BaseModel):
    ticket_id: int
    ticket_code: str
    center_id: int
    status: str
    technician_id: int
    log_id: int

class QualifiedTechnicianList(BaseModel):
    ticket_id: int
    items: List[QualifiedTechnicianRead]
