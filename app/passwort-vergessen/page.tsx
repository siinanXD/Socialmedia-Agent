import { requestResetAction } from "../../lib/auth/password-reset";
import { AuthIntro } from "../../components/auth-intro";
import { SubmitButton } from "../../components/submit-button";
import { messageFor } from "../../lib/auth/messages";

export default async function ForgotPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ fehler?: string; hinweis?: string }>;
}) {
  const { fehler, hinweis } = await searchParams;
  const message = messageFor(fehler) ?? messageFor(hinweis);
  return (
    <main className="auth">
      <AuthIntro />
      <h1>Passwort vergessen</h1>
      {message && <p role="alert">{message}</p>}
      <form action={requestResetAction}>
        <label>
          E-Mail <input name="email" type="email" autoComplete="email" required />
        </label>
        <SubmitButton label="Link anfordern" pendingLabel="Wird gesendet …" />
      </form>
      <p>
        <a href="/login">Zurück zur Anmeldung</a>
      </p>
    </main>
  );
}
