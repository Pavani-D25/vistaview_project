import { useState, useRef } from "react";
import { Link } from "react-router-dom";

const BACKEND_URL =
  (typeof import.meta !== "undefined" &&
    import.meta.env &&
    import.meta.env.VITE_BACKEND_URL) ||
  "http://localhost:8000";

export default function InputPage() {
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [status, setStatus] = useState("");
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef(null);

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f && f.type === "application/pdf") {
      setFile(f);
      setStatus(`Selected: ${f.name}`);
    } else {
      setStatus("Please drop a single PDF file.");
    }
  };

  const onUpload = async () => {
    if (!file) {
      setStatus("Select a PDF first.");
      return;
    }
    setUploading(true);
    setStatus("Uploading...");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch(`${BACKEND_URL}/api/upload`, {
        method: "POST",
        body: fd,
      });
      if (!res.ok) throw new Error(`Upload failed (${res.status})`);
      const json = await res.json().catch(() => ({}));
      setStatus(json.message || "Upload complete. Run ingestion if required.");
    } catch (e) {
      setStatus(`Error: ${e.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <main className="container">
      <header className="header">
        <h1>Upload Catalog PDF</h1>
        <p>Drag and drop a PDF, or choose a file.</p>
      </header>

      <div
        className={`dropzone ${dragOver ? "over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
      >
        <div className="hint">
          {file ? file.name : "Drop PDF here or click to select"}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f && f.type === "application/pdf") {
              setFile(f);
              setStatus(`Selected: ${f.name}`);
            } else {
              setStatus("Please choose a PDF file.");
            }
          }}
        />
      </div>

      <div className="actions">
        <button disabled={!file || uploading} onClick={onUpload}>
          {uploading ? "Uploading..." : "Send to Backend"}
        </button>
        <Link className="link" to="/images" aria-label="View images">
          View Images
        </Link>
      </div>

      <div className="status">{status}</div>

      <style>{`
        :root {
          --bg: #0b0c10;
          --fg: #e5e7eb;
          --muted: #9ca3af;
          --card: #111827;
          --accent: #2563eb;
          --accentDim: #1e40af;
        }
        * { box-sizing: border-box; }
        .container {
          max-width: 800px;
          margin: 0 auto;
          padding: 24px;
          color: var(--fg);
          background: var(--bg);
          min-height: 100vh;
        }
        .header { margin-bottom: 12px; }
        .header h1 { margin: 0 0 4px 0; font-size: 22px; }
        .header p { margin: 0; color: var(--muted); font-size: 14px; }
        .dropzone {
          margin-top: 16px;
          border: 2px dashed #334155;
          border-radius: 12px;
          min-height: 160px;
          display: grid;
          place-items: center;
          background: var(--card);
          cursor: pointer;
          transition: border-color .2s ease;
        }
        .dropzone.over { border-color: var(--accent); }
        .hint { color: var(--muted); }
        .actions {
          margin-top: 16px;
          display: flex;
          gap: 10px;
          align-items: center;
        }
        button {
          background: var(--accent);
          border: none;
          color: white;
          border-radius: 8px;
          padding: 8px 12px;
          cursor: pointer;
        }
        button[disabled] { background: #334155; cursor: not-allowed; }
        .link { color: var(--accent); text-decoration: none; }
        .link:hover { color: var(--accentDim); }
        .status { margin-top: 10px; color: var(--muted); min-height: 20px; }
      `}</style>
    </main>
  );
}
