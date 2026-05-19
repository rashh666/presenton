export const getHeader = (personaKey?: string | null, paletteOverride?: string | null) => {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
  };
  if (personaKey) headers["x-persona"] = personaKey;
  if (paletteOverride) headers["x-palette-override"] = paletteOverride;
  return headers;
};

/** Read both session-scoped overrides from localStorage. */
export const getSessionHeaders = () => {
  if (typeof window === "undefined") return {};
  const persona = localStorage.getItem("selectedPersona") || undefined;
  const palette = localStorage.getItem("paletteOverride") || undefined;
  return { persona: persona || null, palette: palette || null };
};

export const getHeaderForFormData = () => {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
  };
};
