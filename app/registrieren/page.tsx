import { registerAction } from "../../lib/auth/actions";
import { messageFor } from "../../lib/auth/messages";

export default async function RegisterPage({
  searchParams,
}: {
  searchParams: Promise<{ fehler?: string }>;
}) {
  const { fehler } = await searchParams;
  const message = messageFor(fehler);
  return (
    <main>
      <h1>Registrieren</h1>
      {message && <p role="alert">{message}</p>}
      <form action={registerAction}>
        <label>
          E-Mail <input name="email" type="email" autoComplete="email" required />
        </label>
        <label>
          Passwort (mindestens 8 Zeichen){" "}
          <input name="password" type="password" autoComplete="new-password" minLength={8} required />
        </label>
        <button type="submit">Registrieren</button>
      </form>
      <p>
        Schon registriert? <a href="/login">Anmelden</a>
      </p>
    </main>
  );
}
