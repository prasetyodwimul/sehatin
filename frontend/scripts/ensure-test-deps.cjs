const { spawnSync } = require("node:child_process");

function dependenciesAreUsable() {
  try {
    require.resolve("vitest/vitest.mjs");
    // Rollup uses a platform-specific optional dependency. Requiring it catches
    // copied node_modules folders from a different OS/CPU before Vitest starts.
    require("rollup");
    return true;
  } catch (error) {
    const message = error && error.message ? error.message : String(error);
    console.log("[pretest] Local test dependencies need refresh:", message.split("\n")[0]);
    return false;
  }
}

if (!dependenciesAreUsable()) {
  console.log("[pretest] Rebuilding node_modules from package-lock.json for this machine...");
  const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm";
  const result = spawnSync(
    npmCommand,
    ["ci", "--include=optional", "--no-audit", "--no-fund"],
    { stdio: "inherit", shell: false }
  );
  if (result.error) {
    console.error("[pretest] npm ci could not start:", result.error.message);
    process.exit(1);
  }
  if (result.status !== 0) {
    console.error("[pretest] npm ci failed. Check internet/proxy access, then rerun npm run test.");
    process.exit(result.status || 1);
  }
  if (!dependenciesAreUsable()) {
    console.error("[pretest] Dependencies are still unusable after npm ci.");
    process.exit(1);
  }
}

console.log("[pretest] Vitest/Rollup dependencies are ready for this platform.");
