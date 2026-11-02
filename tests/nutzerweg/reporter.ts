import type { Reporter, TestCase, TestResult } from "@playwright/test/reporter";

const NOCH_NICHT = "[noch nicht gebaut] ";

// Je Weg eine Zeile: grün, rot oder noch nicht gebaut. Übersprungen heißt hier nie grün.
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
    } else {
      this.rot++;
      this.zeilen.push(`ROT               ${name}  (${result.error?.message?.split("\n")[0] ?? result.status})`);
    }
  }

  onError(error: { message?: string }) {
    this.rot++;
    this.zeilen.push(`ROT               ${error.message?.split("\n")[0] ?? "Fehler"}`);
  }

  onEnd() {
    console.log(`\nNutzerweg\n${this.zeilen.join("\n")}`);
    console.log(`Laufzeit: ${((Date.now() - this.start) / 1000).toFixed(1)} s`);
    if (this.rot > 0) process.exitCode = 1;
  }
}
