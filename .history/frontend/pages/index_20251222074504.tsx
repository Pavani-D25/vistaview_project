import fs from "fs";
import path from "path";
import Head from "next/head";

type Props = {
  images: string[];
};

export default function Home({ images }: Props) {
  return (
    <>
      <Head>
        <title>VistaView Catalog</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <main className="container">
        <header className="header">
          <h1>VistaView Vendor Catalog</h1>
          <p>Images ingested from PDF (public/images)</p>
        </header>

        {images.length === 0 ? (
          <div className="empty">
            <p>No images found. Run the backend ingestion and ensure files are in /frontend/public/images.</p>
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
    </>
  );
}

export async function getServerSideProps() {
  const imagesDir = path.join(process.cwd(), "public", "images");
  let images: string[] = [];
  try {
    const files = await fs.promises.readdir(imagesDir);
    images = files
      .filter((f) => /\.(jpe?g|png|webp|gif)$/i.test(f))
      .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  } catch {
    // Directory missing or unreadable; return empty list
    images = [];
  }
  return { props: { images } };
}
