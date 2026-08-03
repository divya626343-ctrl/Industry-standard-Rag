// Local dev default. In Docker, this exact file gets regenerated at container
// startup by docker/entrypoint.sh using envsubst, reading VITE_API_URL from the
// container's actual runtime environment (see Dockerfile + compose "environment:").
window.__ENV__ = {
  VITE_API_URL: "https://urban-journey-x5gxqr5xqp9j2p45v-8000.app.github.dev",
};
