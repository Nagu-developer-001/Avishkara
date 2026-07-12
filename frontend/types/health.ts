export type BackendHealth = {
  status: "healthy";
  service: "Avishkara API";
};

export type BackendStatus =
  | { available: true; health: BackendHealth }
  | { available: false };
