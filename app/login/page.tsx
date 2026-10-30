import { loginAction } from "../../lib/auth/actions";
import { messageFor } from "../../lib/auth/messages";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ fehler?: string; hinweis?: string }>;
}) {
  const { fehler, hinweis } = await searchParams;
  const message = messageFor(fehler) ?? messageFor(hinweis);
  return (
    <main>
      <h1>Anmelden</h1>
      {message && <p role="alert">{message}</p>}
      <form action={loginAction}>
        <label>
          E-Mail <input name="email" type="email" autoComplete="email" required />
        </label>
        <label>
          Passwort <input name="password" type="password" autoComplete="current-password" required />
        </label>
        <button type="submit">Anmelden</button>
      </form>
      <p>
        Noch kein Konto? <a href="/registrieren">Registrieren</a>
      </p>
    </main>
  );
}
