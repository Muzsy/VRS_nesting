const _raw: string =
  (import.meta.env.VITE_DXF_PREFLIGHT_ENABLED as string | undefined) ?? "1";

export const DXF_PREFLIGHT_ENABLED: boolean = !["0", "false", "no", "off"].includes(
  _raw.trim().toLowerCase(),
);
