import { useState, useEffect } from "react";
import { apiRequest } from "../api";

export default function M3Appointments() {
    const [appointments, setAppointments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    // Form states
    const [ticketId, setTicketId] = useState("103"); // Seeded assigned ticket
    const [loai, setLoai] = useState("GIAO_MAY");
    const [ngayHen, setNgayHen] = useState("");
    const [batDau, setBatDau] = useState("09:00");
    const [ketThuc, setKetThuc] = useState("10:00");
    const [formMsg, setFormMsg] = useState({ type: "", text: "" });

    const fetchAppointments = async () => {
        setLoading(true); setError("");
        try {
            const data = await apiRequest("/api/appointments");
            setAppointments(data.items);
        } catch (err) { setError(err.message); }
        finally { setLoading(false); }
    };

    const handleCreate = async (e) => {
        e.preventDefault();
        setFormMsg({ type: "", text: "" });
        try {
            await apiRequest("/api/appointments", {
                method: "POST",
                body: JSON.stringify({
                    ticket_id: parseInt(ticketId),
                                     loai,
                                     ngay_hen: ngayHen,
                                     gio_bat_dau: batDau,
                                     gio_ket_thuc: ketThuc,
                }),
            });
            setFormMsg({ type: "success", text: "Tạo lịch hẹn thành công!" });
            fetchAppointments();
        } catch (err) {
            setFormMsg({ type: "error", text: err.message });
        }
    };

    useEffect(() => { fetchAppointments(); }, []);

    return (
        <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-1 bg-white p-6 rounded shadow h-fit">
        <h3 className="text-lg font-bold mb-4">Tạo lịch hẹn mới</h3>
        <form onSubmit={handleCreate} className="space-y-4">
        <div>
        <label className="block text-sm font-medium mb-1">Ticket ID (Đã phân công)</label>
        <input type="number" value={ticketId} onChange={(e) => setTicketId(e.target.value)} className="w-full border p-2 rounded" required />
        </div>
        <div>
        <label className="block text-sm font-medium mb-1">Loại</label>
        <select value={loai} onChange={(e) => setLoai(e.target.value)} className="w-full border p-2 rounded">
        <option value="GIAO_MAY">Giao máy</option>
        <option value="NHAN_MAY">Nhận máy</option>
        </select>
        </div>
        <div>
        <label className="block text-sm font-medium mb-1">Ngày hẹn</label>
        <input type="date" value={ngayHen} onChange={(e) => setNgayHen(e.target.value)} className="w-full border p-2 rounded" required />
        </div>
        <div className="grid grid-cols-2 gap-2">
        <div>
        <label className="block text-sm font-medium mb-1">Bắt đầu</label>
        <input type="time" value={batDau} onChange={(e) => setBatDau(e.target.value)} className="w-full border p-2 rounded" required />
        </div>
        <div>
        <label className="block text-sm font-medium mb-1">Kết thúc</label>
        <input type="time" value={ketThuc} onChange={(e) => setKetThuc(e.target.value)} className="w-full border p-2 rounded" required />
        </div>
        </div>
        <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">Tạo lịch</button>

        {formMsg.text && (
            <div className={`p-2 rounded text-sm ${formMsg.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            {formMsg.text}
            </div>
        )}
        </form>
        </div>

        <div className="md:col-span-2">
        <h2 className="text-2xl font-bold mb-4">M3: Danh sách lịch hẹn</h2>

        {loading && <div className="text-center py-10 text-blue-600">Đang tải...</div>}

        {!loading && error && (
            <div className="bg-red-50 text-red-600 p-4 rounded border border-red-200">
            <p className="font-semibold">Lỗi: {error}</p>
            <button onClick={fetchAppointments} className="mt-2 px-3 py-1 bg-red-600 text-white rounded text-sm">Thử lại</button>
            </div>
        )}

        {!loading && !error && appointments.length === 0 && (
            <div className="text-center py-10 text-gray-500 bg-white rounded border">Chưa có lịch hẹn nào.</div>
        )}

        {!loading && !error && appointments.length > 0 && (
            <div className="bg-white rounded shadow overflow-x-auto">
            <table className="w-full text-left">
            <thead className="bg-gray-100">
            <tr>
            <th className="p-3">ID</th>
            <th className="p-3">Ticket</th>
            <th className="p-3">Loại</th>
            <th className="p-3">Thời gian</th>
            <th className="p-3">Trạng thái</th>
            </tr>
            </thead>
            <tbody>
            {appointments.map((a) => (
                <tr key={a.appointment_id} className="border-t hover:bg-gray-50">
                <td className="p-3">{a.appointment_id}</td>
                <td className="p-3">{a.ticket_id}</td>
                <td className="p-3">{a.loai}</td>
                <td className="p-3">{a.ngay_hen} {a.gio_bat_dau?.substring(0,5)}-{a.gio_ket_thuc?.substring(0,5)}</td>
                <td className="p-3"><span className="px-2 py-1 bg-gray-200 rounded text-xs">{a.trang_thai}</span></td>
                </tr>
            ))}
            </tbody>
            </table>
            </div>
        )}
        </div>
        </div>
    );
}
