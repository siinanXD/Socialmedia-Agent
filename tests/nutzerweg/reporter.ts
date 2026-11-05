import { stripVTControlCharacters } from "node:util";
import type { Reporter, TestCase, TestResult } from "@playwright/test/reporter";

const NOCH_NICHT = "[noch nicht gebaut] ";
const ohneFarbe = stripVTControlCharacters;

// Je Weg eine Zeile: grün, rot, nicht gespielt oder noch nicht gebaut. Übersprungen heißt hier nie grün.
export default class Nutzerweg implements Reporter {
  private zeilen: string[] = [];
  private rot = 0;
  private start = Date.now();

  onTestEnd(test: TestCase, result: TestResult) {
    const name = test.title.replace(NOCH_NICHT, "");
    if (test.title.startsWith(NOCH_NICHT)) {
      this.zeilen.push(`NOCH NICHT GEBAUT  ${name}`);
    } else if (result.status === "passed") {
      this.zeilen.push(`GRÜN              ${name}`);
    } else if (result.status === "skipped") {
      // Serieller Lauf: ein roter Vorgänger überspringt den Rest. Der Weg wurde nicht gespielt.
      this.rot++;
      this.zeilen.push(`NICHT GESPIELT     ${name}  (Vorgänger rot)`);
    } else {
      this.rot++;
      this.zeilen.push(`ROT               ${name}  (${ohneFarbe(result.error?.message ?? result.status).split("\n")[0]})`);
    }
  }

  onError(error: { message?: string }) {
    this.rot++;
    this.zeilen.push(`ROT               ${ohneFarbe(error.message ?? "Fehler").split("\n")[0]}`);
  }

  onEnd() {
    console.log(`\nNutzerweg\n${this.zeilen.join("\n")}`);
    console.log(`Laufzeit: ${((Date.now() - this.start) / 1000).toFixed(1)} s`);
    if (this.rot > 0) process.exitCode = 1;
  }
}
