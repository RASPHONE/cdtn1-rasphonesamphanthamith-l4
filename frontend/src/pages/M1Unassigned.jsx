import { useState, useEffect } from "react";
import { apiRequest } from "../api";

export default function M1Unassigned({ onSelectTicket }) {
    const [tickets, setTickets] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const fetchTickets = async () => {
        setLoading(true); setError("");
        try {
            const data = await apiRequest("/api/tickets/unassigned");
            setTickets(data.items);
        } catch (err) { setError(err.message); }
        finally { setLoading(false); }
    };

    useEffect(() => { fetchTickets(); }, []);

    return (
        <div className="p-6">
        <h2 className="text-2xl font-bold mb-4">M1: Phiếu bảo hành chưa phân công</h2>

        {/* State: Loading */}
        {loading && <div className="text-center py-10 text-blue-600">Đang tải dữ liệu...</div>}

        {/* State: Error */}
        {!loading && error && (
            <div className="bg-red-50 text-red-600 p-4 rounded border border-red-200">
            <p className="font-semibold">Lỗi: {error}</p>
            <button onClick={fetchTickets} className="mt-2 px-3 py-1 bg-red-600 text-white rounded text-sm">Thử lại</button>
            </div>
        )}

        {/* State: Empty */}
        {!loading && !error && tickets.length === 0 && (
            <div className="text-center py-10 text-gray-500 bg-white rounded border">Không có phiếu nào cần phân công.</div>
        )}

        {/* State: Data */}
        {!loading && !error && tickets.length > 0 && (
            <div className="bg-white rounded shadow overflow-x-auto">
            <table className="w-full text-left">
            <thead className="bg-gray-100">
            <tr>
            <th className="p-3">Mã phiếu</th>
            <th className="p-3">Khách hàng</th>
            <th className="p-3">Hạng mục</th>
            <th className="p-3">Độ ưu tiên</th>
            <th className="p-3">Hành động</th>
            </tr>
            </thead>
            <tbody>
            {tickets.map((t) => (
                <tr key={t.ticket_id} className="border-t hover:bg-gray-50">
                <td className="p-3">{t.ticket_code}</td>
                <td className="p-3">{t.customer_name}</td>
                <td className="p-3">{t.category_name}</td>
                <td className="p-3"><span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs">{t.priority}</span></td>
                <td className="p-3">
                <button onClick={() => onSelectTicket(t.ticket_id)} className="text-blue-600 hover:underline font-medium">Phân công</button>
                </td>
                </tr>
            ))}
            </tbody>
            </table>
            </div>
        )}
        </div>
    );
}
