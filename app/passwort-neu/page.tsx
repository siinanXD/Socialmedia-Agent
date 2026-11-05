import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { setNewPasswordAction } from "../../lib/auth/password-reset";
import { RECOVERY_COOKIE } from "../../lib/auth/recovery";
import { AuthIntro } from "../../components/auth-intro";
import { SubmitButton } from "../../components/submit-button";
import { messageFor } from "../../lib/auth/messages";
import { createClient } from "../../lib/supabase/server";

export default async function NewPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ fehler?: string }>;
}) {
  // Nur mit Recovery-Markierung aus dem Auth-Callback und gültiger Session (proxy.ts lässt die Route offen).
  const cookieStore = await cookies();
  if (!cookieStore.get(RECOVERY_COOKIE)) redirect("/login");
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getUser();
  if (error || !data.user) redirect("/login");

  const message = messageFor((await searchParams).fehler);
  return (
    <main className="auth">
      <AuthIntro />
      <h1>Neues Passwort</h1>
      {message && <p role="alert">{message}</p>}
      <form action={setNewPasswordAction}>
        <label>
          Neues Passwort (mindestens 8 Zeichen){" "}
          <input name="password" type="password" autoComplete="new-password" minLength={8} required />
        </label>
        <label>
          Passwort wiederholen{" "}
          <input name="confirm" type="password" autoComplete="new-password" minLength={8} required />
        </label>
        <SubmitButton label="Passwort speichern" pendingLabel="Wird gespeichert …" />
      </form>
    </main>
  );
}
