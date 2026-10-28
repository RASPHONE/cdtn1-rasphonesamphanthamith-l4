from datetime import date, time, timedelta


def auth_header(client, username="manager1", password="manager123"):
    response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )

    assert response.status_code == 200

    token = response.json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "up"}


def test_login_success(client):
    response = client.post(
        "/api/auth/login",
        json={
            "username": "manager1",
            "password": "manager123",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["token_type"] == "bearer"
    assert body["role"] == "CENTER_MANAGER"
    assert body["center_id"] == 1
    assert "access_token" in body


def test_login_invalid_credentials(client):
    response = client.post(
        "/api/auth/login",
        json={
            "username": "manager1",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"] == "invalid_credentials"


def test_protected_endpoint_requires_token(client):
    response = client.get("/api/tickets/unassigned")

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"


def test_protected_endpoint_rejects_invalid_token(client):
    response = client.get(
        "/api/tickets/unassigned",
        headers={
            "Authorization": "Bearer invalid-token",
        },
    )

    assert response.status_code == 401
    assert response.json()["error"] == "unauthorized"


def test_appointment_crud_flow(client):
    headers = auth_header(client)

    tomorrow = date.today() + timedelta(days=1)

    payload = {
        "ticket_id": 103,
        "loai": "GIAO_MAY",
        "ngay_hen": tomorrow.isoformat(),
        "gio_bat_dau": "09:00",
        "gio_ket_thuc": "10:00",
    }

    create_response = client.post(
        "/api/appointments",
        json=payload,
        headers=headers,
    )

    assert create_response.status_code == 201

    appointment = create_response.json()
    appointment_id = appointment["appointment_id"]

    assert appointment["ticket_id"] == 103
    assert appointment["technician_id"] == 1
    assert appointment["center_id"] == 1
    assert appointment["trang_thai"] == "DA_XAC_NHAN"
    assert appointment["is_deleted"] is False

    conflict_response = client.post(
        "/api/appointments",
        json=payload,
        headers=headers,
    )

    assert conflict_response.status_code == 409
    assert conflict_response.json()["error"] == "appointment_conflict"
    assert conflict_response.json()["conflicts"][0]["appointment_id"] == appointment_id

    list_response = client.get(
        "/api/appointments",
        headers=headers,
    )

    assert list_response.status_code == 200

    list_body = list_response.json()

    assert any(
        item["appointment_id"] == appointment_id
        for item in list_body["items"]
    )

    detail_response = client.get(
        f"/api/appointments/{appointment_id}",
        headers=headers,
    )

    assert detail_response.status_code == 200
    assert detail_response.json()["appointment_id"] == appointment_id

    update_response = client.patch(
        f"/api/appointments/{appointment_id}",
        json={
            "gio_bat_dau": "13:00",
            "gio_ket_thuc": "14:00",
        },
        headers=headers,
    )

    assert update_response.status_code == 200
    assert update_response.json()["gio_bat_dau"] == "13:00:00"
    assert update_response.json()["gio_ket_thuc"] == "14:00:00"

    delete_response = client.delete(
        f"/api/appointments/{appointment_id}",
        headers=headers,
    )

    assert delete_response.status_code == 200

    delete_body = delete_response.json()

    assert delete_body["appointment_id"] == appointment_id
    assert delete_body["is_deleted"] is True

    list_after_delete_response = client.get(
        "/api/appointments",
        headers=headers,
    )

    assert list_after_delete_response.status_code == 200

    list_after_delete_body = list_after_delete_response.json()

    assert all(
        item["appointment_id"] != appointment_id
        for item in list_after_delete_body["items"]
    )


def test_create_appointment_in_past_fails(client):
    headers = auth_header(client)

    yesterday = date.today() - timedelta(days=1)

    payload = {
        "ticket_id": 103,
        "loai": "GIAO_MAY",
        "ngay_hen": yesterday.isoformat(),
        "gio_bat_dau": "09:00",
        "gio_ket_thuc": "10:00",
    }

    response = client.post(
        "/api/appointments",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["error"] == "appointment_in_past"


def test_create_appointment_for_unassigned_ticket_fails(client):
    headers = auth_header(client)

    tomorrow = date.today() + timedelta(days=1)

    payload = {
        "ticket_id": 101,
        "loai": "GIAO_MAY",
        "ngay_hen": tomorrow.isoformat(),
        "gio_bat_dau": "09:00",
        "gio_ket_thuc": "10:00",
    }

    response = client.post(
        "/api/appointments",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["error"] == "ticket_not_assignable"


def test_create_appointment_cross_center_fails(client):
    headers = auth_header(client, username="manager1")

    tomorrow = date.today() + timedelta(days=1)

    payload = {
        "ticket_id": 201,
        "loai": "GIAO_MAY",
        "ngay_hen": tomorrow.isoformat(),
        "gio_bat_dau": "09:00",
        "gio_ket_thuc": "10:00",
    }

    response = client.post(
        "/api/appointments",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["error"] == "cross_center_access"


def test_technician_skill_crud_flow(client):
    headers = auth_header(client)

    list_response = client.get(
        "/api/technicians/1/skills",
        headers=headers,
    )

    assert list_response.status_code == 200

    existing_skills = list_response.json()

    assert any(skill["category_id"] == 1 for skill in existing_skills)

    duplicate_response = client.post(
        "/api/technicians/1/skills",
        json={
            "category_id": 1,
            "proficiency": 3,
        },
        headers=headers,
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error"] == "skill_already_exists"

    invalid_proficiency_response = client.post(
        "/api/technicians/1/skills",
        json={
            "category_id": 4,
            "proficiency": 6,
        },
        headers=headers,
    )

    assert invalid_proficiency_response.status_code == 422
    assert invalid_proficiency_response.json()["error"] == "proficiency_out_of_range"

    inactive_category_response = client.post(
        "/api/technicians/1/skills",
        json={
            "category_id": 7,
            "proficiency": 3,
        },
        headers=headers,
    )

    assert inactive_category_response.status_code == 422
    assert inactive_category_response.json()["error"] == "category_inactive"

    create_response = client.post(
        "/api/technicians/1/skills",
        json={
            "category_id": 4,
            "proficiency": 3,
        },
        headers=headers,
    )

    assert create_response.status_code == 201

    created_skill = create_response.json()

    assert created_skill["technician_id"] == 1
    assert created_skill["category_id"] == 4
    assert created_skill["proficiency"] == 3

    detail_response = client.get(
        "/api/technicians/1/skills/4",
        headers=headers,
    )

    assert detail_response.status_code == 200
    assert detail_response.json()["proficiency"] == 3

    update_response = client.patch(
        "/api/technicians/1/skills/4",
        json={
            "proficiency": 5,
        },
        headers=headers,
    )

    assert update_response.status_code == 200
    assert update_response.json()["proficiency"] == 5

    delete_response = client.delete(
        "/api/technicians/1/skills/4",
        headers=headers,
    )

    assert delete_response.status_code == 204

    deleted_detail_response = client.get(
        "/api/technicians/1/skills/4",
        headers=headers,
    )

    assert deleted_detail_response.status_code == 404
    assert deleted_detail_response.json()["error"] == "skill_not_found"


def test_technician_skill_cross_center_fails(client):
    headers = auth_header(client, username="manager1")

    response = client.get(
        "/api/technicians/3/skills",
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["error"] == "cross_center_access"


def test_unassigned_ticket_list_center_scoping(client):
    manager1_headers = auth_header(client, username="manager1")
    manager2_headers = auth_header(client, username="manager2")

    manager1_response = client.get(
        "/api/tickets/unassigned",
        headers=manager1_headers,
    )

    assert manager1_response.status_code == 200

    manager1_ticket_ids = [
        item["ticket_id"]
        for item in manager1_response.json()["items"]
    ]

    assert 101 in manager1_ticket_ids
    assert 201 not in manager1_ticket_ids

    manager2_response = client.get(
        "/api/tickets/unassigned",
        headers=manager2_headers,
    )

    assert manager2_response.status_code == 200

    manager2_ticket_ids = [
        item["ticket_id"]
        for item in manager2_response.json()["items"]
    ]

    assert 201 in manager2_ticket_ids
    assert 101 not in manager2_ticket_ids


def test_ticket_assignment_flow(client):
    headers = auth_header(client)

    qualified_response = client.get(
        "/api/tickets/101/qualified-technicians",
        headers=headers,
    )

    assert qualified_response.status_code == 200

    qualified_data = qualified_response.json()
    assert qualified_data["ticket_id"] == 101
    qualified_technicians = qualified_data["items"]

    assert len(qualified_technicians) >= 1

    assign_response = client.post(
        "/api/tickets/101/assignment",
        json={
            "technician_id": 1,
        },
        headers=headers,
    )

    assert assign_response.status_code == 200

    assigned_ticket = assign_response.json()

    assert assigned_ticket["ticket_id"] == 101
    assert assigned_ticket["status"] == "DA_PHAN_CONG"
    assert assigned_ticket["technician_id"] == 1

    unassigned_after_response = client.get(
        "/api/tickets/unassigned",
        headers=headers,
    )

    assert unassigned_after_response.status_code == 200

    unassigned_ids = [
        item["ticket_id"]
        for item in unassigned_after_response.json()["items"]
    ]

    assert 101 not in unassigned_ids

    reassign_response = client.patch(
        "/api/tickets/101/assignment",
        json={
            "technician_id": 2,
            "reason": "Rebalance workload",
        },
        headers=headers,
    )

    assert reassign_response.status_code == 200
    assert reassign_response.json()["technician_id"] == 2

    reassign_without_reason_response = client.patch(
        "/api/tickets/101/assignment",
        json={
            "technician_id": 1,
            "reason": "   ",
        },
        headers=headers,
    )

    assert reassign_without_reason_response.status_code == 422
    assert reassign_without_reason_response.json()["error"] == "reason_required"


def test_assign_cross_center_technician_fails(client):
    headers = auth_header(client)

    response = client.post(
        "/api/tickets/101/assignment",
        json={
            "technician_id": 3,
        },
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["error"] == "technician_not_qualified"


def test_qualified_technicians_cross_center_fails(client):
    headers = auth_header(client, username="manager1")

    response = client.get(
        "/api/tickets/201/qualified-technicians",
        headers=headers,
    )

    assert response.status_code == 403
    assert response.json()["error"] == "cross_center_access"


def make_token(role, center_id=1, user_id=9):
    """Token for a role that has no demo login (used to check QT-15 masking)."""
    import jwt

    from src.config import get_settings

    payload = {"sub": "test", "user_id": user_id, "role": role, "center_id": center_id}
    token = jwt.encode(payload, get_settings().jwt_secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


def test_reassign_with_missing_reason_field_returns_422(client):
    # Teacher feedback / API contract §4: a missing reason is a QT-07 violation (422),
    # not a malformed request (400).
    headers = auth_header(client)

    response = client.patch(
        "/api/tickets/103/assignment",
        json={"technician_id": 2},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["error"] == "reason_required"


def test_conflict_precheck_endpoint(client):
    headers = auth_header(client)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    client.post(
        "/api/appointments",
        json={"ticket_id": 103, "loai": "NHAN_MAY", "ngay_hen": tomorrow,
              "gio_bat_dau": "14:00", "gio_ket_thuc": "15:00"},
        headers=headers,
    )

    busy = client.get(
        "/api/appointments/conflicts",
        params={"technician_id": 1, "ngay_hen": tomorrow,
                "gio_bat_dau": "14:30", "gio_ket_thuc": "15:30"},
        headers=headers,
    )
    free = client.get(
        "/api/appointments/conflicts",
        params={"technician_id": 1, "ngay_hen": tomorrow,
                "gio_bat_dau": "15:00", "gio_ket_thuc": "16:00"},
        headers=headers,
    )

    assert busy.status_code == 200
    assert len(busy.json()["conflicts"]) == 1
    assert free.json() == {"conflicts": []}


def test_invalid_filter_value_returns_400(client):
    headers = auth_header(client)

    response = client.get("/api/tickets/unassigned?priority=URGENT", headers=headers)

    assert response.status_code == 400
    assert response.json()["error"] == "bad_request"
    assert response.json()["details"][0]["field"] == "priority"


def test_ticket_detail_and_cross_center(client):
    headers = auth_header(client)

    own = client.get("/api/tickets/103", headers=headers)
    other = client.get("/api/tickets/201", headers=headers)

    assert own.status_code == 200
    assert own.json()["ticket_code"] == "PB-1-00103"
    assert own.json()["customer_phone"] == "0900000103"
    assert other.status_code == 403


def test_non_manager_role_sees_masked_phone(client):
    response = client.get("/api/tickets/unassigned", headers=make_token("TECHNICIAN"))

    assert response.status_code == 200
    assert response.json()["items"][0]["customer_phone"] == "090****101"


def test_issue_categories_lists_active_only(client):
    headers = auth_header(client)

    response = client.get("/api/issue-categories", headers=headers)

    assert response.status_code == 200
    assert [c["category_name"] for c in response.json()] == ["MAN_HINH", "PHAN_MEM"]


def test_database_down_returns_503_not_raw_error(client):
    from src.db import DatabaseUnavailableError
    from src.main import app
    from src.routes.tickets import get_ticket_assignment_service

    class DownService:
        def list_unassigned_tickets(self, **kwargs):
            raise DatabaseUnavailableError("connection refused")

    headers = auth_header(client)
    app.dependency_overrides[get_ticket_assignment_service] = lambda: DownService()

    response = client.get("/api/tickets/unassigned", headers=headers)

    assert response.status_code == 503
    assert response.json()["error"] == "database_unavailable"
    assert "connection refused" not in response.text
