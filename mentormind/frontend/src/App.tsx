import { useEffect, useState } from "react";
import { apiGet } from "./api";

export default function App() {
  const [status, setStatus] = useState("đang kiểm tra...");

  useEffect(() => {
    apiGet<{ status: string }>("/health")
      .then((r) => setStatus(r.status))
      .catch(() => setStatus("không kết nối được API"));
  }, []);

  return (
    <main>
      <h1>MentorMind</h1>
      <p>Trạng thái API: {status}</p>
    </main>
  );
}
