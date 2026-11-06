import { UploadForm } from "../../../components/upload-form";
import { requireUser } from "../../../lib/auth/session";
import { SECTIONS } from "../../../lib/studio/sections";
import { createClient } from "../../../lib/supabase/server";
import { listAssets, type AssetRow } from "../../../lib/uploads/store";

const leer = SECTIONS.find((s) => s.href === "/mediathek")!.leer;
const mb = (bytes: number) => `${(bytes / 1024 / 1024).toLocaleString("de-DE", { maximumFractionDigits: 1 })} MB`;

export default async function Page() {
  await requireUser();
  let assets: AssetRow[] | null;
  try {
    assets = await listAssets(await createClient());
  } catch {
    assets = null;
  }
  return (
    <>
      <h1>Mediathek</h1>
      <UploadForm />
      {assets === null ? (
        <p role="alert" className="profile-message error">
          Die Medien konnten gerade nicht geladen werden.
        </p>
      ) : assets.length === 0 ? (
        <section className="empty" aria-labelledby="leer-titel">
          <h2 id="leer-titel">{leer.titel}</h2>
          <p>{leer.text}</p>
        </section>
      ) : (
        <section aria-labelledby="medien-titel">
          <h2 id="medien-titel">Deine Medien</h2>
          <ul className="medien">
            {assets.map((a) => (
              <li key={a.id}>
                <strong>{a.original_filename}</strong> · {mb(a.size_bytes)} ·{" "}
                {new Date(a.created_at).toLocaleDateString("de-DE")}
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
