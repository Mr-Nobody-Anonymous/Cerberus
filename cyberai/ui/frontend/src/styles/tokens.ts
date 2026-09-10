/**
 * CERBERUS design tokens — dark cyber-command-center theme.
 * Spec §11: dark theme, #080b10 base, cyan/blue-violet accents.
 */

export const colors = {
  // Surfaces
  bg0: "#080b10", // app background
  bg1: "#0d1117", // panel background
  bg2: "#131923", // raised surface / cards
  bg3: "#1a2230", // hover / active surface
  border: "#1f2937",
  borderBright: "#2d3a4d",

  // Text
  text: "#d5dde8",
  textDim: "#8b98a9",
  textFaint: "#5c6878",

  // Accents
  cyan: "#22d3ee",
  blue: "#3b82f6",
  violet: "#8b5cf6",
  green: "#34d399",
  yellow: "#fbbf24",
  red: "#f87171",
  orange: "#fb923c",

  // Status
  statusOnline: "#34d399",
  statusWarn: "#fbbf24",
  statusError: "#f87171",
  statusBlocked: "#f87171",
} as const;

export const fonts = {
  ui: "'Segoe UI', system-ui, -apple-system, sans-serif",
  mono: "'Cascadia Code', 'Fira Code', 'JetBrains Mono', Consolas, monospace",
} as const;

export const radii = { sm: "4px", md: "8px", lg: "12px" } as const;

export const shadows = {
  panel: "0 1px 3px rgba(0,0,0,0.4)",
  overlay: "0 8px 32px rgba(0,0,0,0.6)",
} as const;

/** CSS custom properties injected once at app start. */
export const cssVariables = `
:root {
  --cb-bg0: ${colors.bg0};
  --cb-bg1: ${colors.bg1};
  --cb-bg2: ${colors.bg2};
  --cb-bg3: ${colors.bg3};
  --cb-border: ${colors.border};
  --cb-border-bright: ${colors.borderBright};
  --cb-text: ${colors.text};
  --cb-text-dim: ${colors.textDim};
  --cb-text-faint: ${colors.textFaint};
  --cb-cyan: ${colors.cyan};
  --cb-blue: ${colors.blue};
  --cb-violet: ${colors.violet};
  --cb-green: ${colors.green};
  --cb-yellow: ${colors.yellow};
  --cb-red: ${colors.red};
  --cb-orange: ${colors.orange};
  --cb-font-ui: ${fonts.ui};
  --cb-font-mono: ${fonts.mono};
  --cb-radius-sm: ${radii.sm};
  --cb-radius-md: ${radii.md};
  --cb-radius-lg: ${radii.lg};
  --cb-shadow-panel: ${shadows.panel};
  --cb-shadow-overlay: ${shadows.overlay};
}
`;
