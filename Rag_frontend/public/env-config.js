// TEMPORARY: pinned to the current Codespaces forwarded URL for live debugging.
// Revert to "http://localhost:8000" (or back to a template-driven value) once
// local dev / the Docker entrypoint flow is confirmed working again.
//
// NOTE: Codespaces forwarded URLs are tied to a specific Codespace instance --
// if you rebuild/recreate the Codespace (not just restart it), this subdomain
// WILL change and this value will need updating again.
window.__ENV__ = {
  VITE_API_URL: "https://urban-journey-x5gxqr5xqp9j2p45v-8000.app.github.dev",
};
