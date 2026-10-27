import { useState, useEffect } from "react";
import Login from "./pages/Login";
import M1Unassigned from "./pages/M1Unassigned";
import M2Assignment from "./pages/M2Assignment";
import M3Appointments from "./pages/M3Appointments";

function App() {
  const [user, setUser] = useState(null);
  const [currentPage, setCurrentPage] = useState("m1");
  const [selectedTicketId, setSelectedTicketId] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      setUser({ token }); // Simplification for prototype
    }
  }, []);

  if (!user) {
    return <Login onLogin={setUser} />;
  }

  const handleSelectTicket = (id) => {
    setSelectedTicketId(id);
    setCurrentPage("m2");
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    setUser(null);
  };

  return (
    <div className="min-h-screen flex flex-col">
    <header className="bg-blue-800 text-white p-4 flex justify-between items-center shadow">
    <h1 className="text-xl font-bold">Mekong Mobile L4 - Center Manager</h1>
    <div className="flex gap-4 items-center">
    <nav className="flex gap-4">
    <button onClick={() => setCurrentPage("m1")} className={`hover:underline ${currentPage === "m1" ? "font-bold" : ""}`}>M1: Phân công</button>
    <button onClick={() => setCurrentPage("m3")} className={`hover:underline ${currentPage === "m3" ? "font-bold" : ""}`}>M3: Lịch hẹn</button>
    </nav>
    <button onClick={handleLogout} className="bg-red-600 px-3 py-1 rounded text-sm hover:bg-red-700">Đăng xuất</button>
    </div>
    </header>

    <main className="flex-grow bg-gray-50">
    {currentPage === "m1" && <M1Unassigned onSelectTicket={handleSelectTicket} />}
    {currentPage === "m2" && selectedTicketId && <M2Assignment ticketId={selectedTicketId} onBack={() => setCurrentPage("m1")} />}
    {currentPage === "m3" && <M3Appointments />}
    </main>
    </div>
  );
}

export default App;
