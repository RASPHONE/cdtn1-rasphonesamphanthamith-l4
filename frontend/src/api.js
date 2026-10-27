const API_URL = "http://localhost:8000";

export async function apiRequest(endpoint, options = {}) {
    const token = localStorage.getItem("token");
    const headers = {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
    };

    const response = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers,
    });

    if (response.status === 401) {
        localStorage.removeItem("token");
        window.location.reload();
        throw new Error("Phiên đăng nhập hết hạn hoặc không hợp lệ.");
    }

    if (response.status === 204) return null;

    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.message || "Đã xảy ra lỗi không xác định.");
    }
    return data;
}
