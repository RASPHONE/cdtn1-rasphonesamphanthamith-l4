import { useState, useEffect } from "react";
import { apiRequest } from "../api";

export default function M2Assignment({ ticketId, onBack }) {
    const [techs, setTechs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [success, setSuccess] = useState("");

    const fetchTechs = async () => {
        setLoading(true); setError(""); setSuccess("");
        try {
            const data = await apiRequest(`/api/tickets/${ticketId}/qualified-technicians`);
            setTechs(data);
        } catch (err) { setError(err.message); }
        finally { setLoading(false); }
    };

    const handleAssign = async (techId) => {
        setError(""); setSuccess("");
        try {
            await apiRequest(`/api/tickets/${ticketId}/assignment`, {
                method: "POST",
                body: JSON.stringify({ technician_id: techId }),
            });
            setSuccess("Phân công thành công! Đang quay lại danh sách...");
            setTimeout(onBack, 1500);
        } catch (err) { setError(err.message); }
    };

    useEffect(() => { fetchTechs(); }, [ticketId]);

    return (
        <div className="p-6">
        <button onClick={onBack} className="mb-4 text-blue-600 hover:underline">&larr; Quay lại M1</button>
        <h2 className="text-2xl font-bold mb-4">M2: Phân công KTV cho phiếu #{ticketId}</h2>

        {loading && <div className="text-center py-10 text-blue-600">Đang tải danh sách KTV đủ điều kiện...</div>}

        {error && (
            <div className="bg-red-50 text-red-600 p-4 rounded border border-red-200 mb-4">
            <p className="font-semibold">Lỗi: {error}</p>
            <button onClick={fetchTechs} className="mt-2 px-3 py-1 bg-red-600 text-white rounded text-sm">Thử lại</button>
            </div>
        )}

        {success && <div className="bg-green-50 text-green-700 p-4 rounded border border-green-200 mb-4">{success}</div>}

        {!loading && !error && techs.length === 0 && (
            <div className="text-center py-10 text-gray-500 bg-white rounded border">Không có KTV nào đủ điều kiện (Proficiency ≥ 3) cho hạng mục này.</div>
        )}

        {!loading && techs.length > 0 && (
            <div className="bg-white rounded shadow overflow-x-auto">
            <table className="w-full text-left">
            <thead className="bg-gray-100">
            <tr>
            <th className="p-3">Mã KTV</th>
            <th className="p-3">Họ tên</th>
            <th className="p-3">Tay nghề (Proficiency)</th>
            <th className="p-3">Workload hiện tại</th>
            <th className="p-3">Hành động</th>
            </tr>
            </thead>
            <tbody>
            {techs.map((t) => (
                <tr key={t.technician_id} className="border-t hover:bg-gray-50">
                <td className="p-3">{t.technician_code}</td>
                <td className="p-3">{t.ho_ten}</td>
                <td className="p-3"><span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">{t.proficiency}</span></td>
                <td className="p-3">{t.workload} phiếu</td>
                <td className="p-3">
                <button onClick={() => handleAssign(t.technician_id)} className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-sm">Chọn phân công</button>
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
