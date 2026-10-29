import type { NextConfig } from "next";

const config: NextConfig = {
  // Next würde sonst beim Start die versionierte AGENTS.md verändern.
  agentRules: false,
};

export default config;
