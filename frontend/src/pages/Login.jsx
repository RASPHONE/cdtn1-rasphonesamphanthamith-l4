import { useState } from "react";
import { apiRequest } from "../api";

export default function Login({ onLogin }) {
    const [username, setUsername] = useState("manager1");
    const [password, setPassword] = useState("manager123");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError("");
        try {
            const data = await apiRequest("/api/auth/login", {
                method: "POST",
                body: JSON.stringify({ username, password }),
            });
            localStorage.setItem("token", data.access_token);
            onLogin(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="flex items-center justify-center min-h-screen">
        <form onSubmit={handleSubmit} className="bg-white p-8 rounded shadow-md w-96">
        <h2 className="text-2xl font-bold mb-6 text-center">Đăng nhập Center Manager</h2>
        {error && <div className="bg-red-100 text-red-700 p-2 rounded mb-4 text-sm">{error}</div>}
        <div className="mb-4">
        <label className="block text-sm font-medium mb-1">Username</label>
        <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} className="w-full border p-2 rounded" />
        </div>
        <div className="mb-6">
        <label className="block text-sm font-medium mb-1">Password</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="w-full border p-2 rounded" />
        </div>
        <button type="submit" disabled={loading} className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50">
        {loading ? "Đang xử lý..." : "Đăng nhập"}
        </button>
        </form>
        </div>
    );
}
