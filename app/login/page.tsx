import { loginAction } from "../../lib/auth/actions";
import { AuthIntro } from "../../components/auth-intro";
import { SubmitButton } from "../../components/submit-button";
import { messageFor } from "../../lib/auth/messages";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ fehler?: string; hinweis?: string }>;
}) {
  const { fehler, hinweis } = await searchParams;
  const message = messageFor(fehler) ?? messageFor(hinweis);
  return (
    <main className="auth">
      <AuthIntro />
      <h1>Anmelden</h1>
      {message && <p role="alert">{message}</p>}
      <form action={loginAction}>
        <label>
          E-Mail <input name="email" type="email" autoComplete="email" required />
        </label>
        <label>
          Passwort <input name="password" type="password" autoComplete="current-password" required />
        </label>
        <SubmitButton label="Anmelden" pendingLabel="Anmeldung läuft …" />
      </form>
      <p>
        <a href="/passwort-vergessen">Passwort vergessen?</a>
      </p>
      <p>
        Noch kein Konto? <a href="/registrieren">Registrieren</a>
      </p>
    </main>
  );
}
