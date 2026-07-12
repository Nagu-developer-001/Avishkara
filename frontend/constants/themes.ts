export const THEME_IDS = [
  "broadcast-sports",
  "olympic-minimal",
] as const;

export type ThemeId = (typeof THEME_IDS)[number];

export const THEMES: Array<{
  id: ThemeId;
  name: string;
  shortName: string;
  description: string;
  swatches: [string, string, string];
}> = [
  {
    id: "broadcast-sports",
    name: "Broadcast Sports Analytics",
    shortName: "Dark",
    description: "Dark control-room interface with electric cyan and restrained sports red.",
    swatches: ["#050b16", "#00d4ff", "#ff3b30"],
  },
  {
    id: "olympic-minimal",
    name: "Olympic Minimal",
    shortName: "Light",
    description: "Clean light mode with charcoal, white, and restrained gold.",
    swatches: ["#f7f5ef", "#c59a2e", "#18202a"],
  },
];
