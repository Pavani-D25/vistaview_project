import Head from "next/head";

export default function DisplayImages({ images }) {
  return (
    <>
      <Head>
        <title>VistaView Images</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <main className="container">
        <header className="header">
          <h1>Ingested Images</h1>
          <p>From /public/images</p>
        </header>

        {images.length === 0 ? (
          <div className="empty">
            No images found. Run the ingestion and ensure files are in /frontend/public/images.
          </div>
        ) : (
          <section className="grid">
            {images.map((name) => (
              <figure key={name} className="card">
                <img
                  src={`/images/${encodeURIComponent(name)}`}
                  alt={name}
                  loading="lazy"
                />
                <figcaption title={name}>{name}</figcaption>
              </figure>
            ))}
          </section>
        )}
      </main>

      <style jsx>{`
        :root {
          --bg: #0b0c10;
          --fg: #e5e7eb;
          --muted: #9ca3af;
          --card: #111827;
        }
        * { box-sizing: border-box; }
        body, html, #__next { height: 100%; }
        .container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 24px;
          color: var(--fg);
          background: var(--bg);
          min-height: 100vh;
        }
        .header { margin-bottom: 16px; }
        .header h1 { margin: 0 0 4px 0; font-size: 22px; }
        .header p { margin: 0; color: var(--muted); font-size: 14px; }
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
    </>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export async function getServerSideProps() {
  const fs = await import("fs");
  const path = await import("path");

  const imagesDir = path.join(process.cwd(), "public", "images");
  let images = [];
  try {
    const files = await fs.promises.readdir(imagesDir);
    images = files
      .filter((f) => /\.(jpe?g|png|webp|gif)$/i.test(f))
      .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  } catch {
    images = [];
  }
  return { props: { images } };
}
