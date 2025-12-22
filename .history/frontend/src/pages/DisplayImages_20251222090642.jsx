import { useEffect, useState } from "react";

export default function DisplayImages() {
  const [images, setImages] = useState([]);
  const [collages, setCollages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("images"); // "images" | "collages"
  const [error, setError] = useState("");

  useEffect(() => {
    document.title = "VistaView Images";
    const load = async () => {
      setLoading(true);
      setError("");
      // Try backend API first
      try {
        const res = await fetch("/api/media");
        if (res.ok) {
          const data = await res.json();
          setImages(Array.isArray(data.images) ? data.images : []);
          setCollages(Array.isArray(data.collages) ? data.collages : []);
          setLoading(false);
          return;
        }
      } catch {
        /* ...no-op... */
      }
      // Fallback to static manifests in /public
      try {
        const [iRes, cRes] = await Promise.allSettled([
          fetch("/images/index.json"),
          fetch("/collages/index.json"),
        ]);
        const iJson =
          iRes.status === "fulfilled" && iRes.value.ok ? await iRes.value.json() : [];
        const cJson =
          cRes.status === "fulfilled" && cRes.value.ok ? await cRes.value.json() : [];
        setImages(Array.isArray(iJson) ? iJson : []);
        setCollages(Array.isArray(cJson) ? cJson : []);
      } catch (e) {
        setError("Unable to load media list. Provide /api/media or index.json manifests.");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const list = tab === "images" ? images : collages;
  const base = tab === "images" ? "/images/" : "/collages/";

  return (
    <main className="container">
      <header className="header">
        <h1>Ingested {tab === "images" ? "Images" : "Collages"}</h1>
        <p>From /public/{tab === "images" ? "images" : "collages"}</p>
        <div className="tabs">
          <button
            className={tab === "images" ? "active" : ""}
            onClick={() => setTab("images")}
          >
            Images
          </button>
          <button
            className={tab === "collages" ? "active" : ""}
            onClick={() => setTab("collages")}
          >
            Collages
          </button>
        </div>
      </header>

      {loading ? (
        <div className="empty">Loading...</div>
      ) : list.length === 0 ? (
        <div className="empty">
          {error || `No ${tab} found. Run ingestion to populate /frontend/public/${tab}.`}
        </div>
      ) : (
        <section className="grid">
          {list.map((name) => (
            <figure key={name} className="card">
              <img
                src={`${base}${encodeURIComponent(name)}`}
                alt={name}
                loading="lazy"
              />
              <figcaption title={name}>{name}</figcaption>
            </figure>
          ))}
        </section>
      )}

      <style>{`
        :root {
          --bg: #0b0c10;
          --fg: #e5e7eb;
          --muted: #9ca3af;
          --card: #111827;
          --accent: #2563eb;
        }
        * { box-sizing: border-box; }
        .container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 24px;
          color: var(--fg);
          background: var(--bg);
          min-height: 100vh;
        }
        .header { margin-bottom: 16px; display:flex; align-items:center; gap:16px; }
        .header h1 { margin: 0; font-size: 22px; }
        .header p { margin: 0; color: var(--muted); font-size: 14px; }
        .tabs { margin-left:auto; display:flex; gap:8px; }
        .tabs button {
          background: transparent;
          color: var(--fg);
          border: 1px solid #1f2937;
          border-radius: 8px;
          padding: 6px 10px;
          cursor: pointer;
        }
        .tabs button.active {
          border-color: var(--accent);
          color: var(--accent);
        }
        .empty { padding: 40px 0; color: var(--muted); text-align: center; }
        .grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
          gap: 12px;
        }
        .card {
          margin: 0;
          background: var(--card);
          border: 1px solid #1f2937;
          border-radius: 10px;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        .card img {
          width: 100%;
          height: 220px;
          object-fit: contain;
          background: #0f172a;
        }
        .card figcaption {
          padding: 8px 10px;
          border-top: 1px solid #1f2937;
          font-size: 12px;
          color: var(--muted);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      `}</style>
    </main>
  );
}
