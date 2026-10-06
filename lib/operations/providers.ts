export type ProviderHealth = {
  healthy: boolean;
  checkedAt: string;
  detail: string;
};

export type ProviderCapability = {
  provider: string;
  capability: "telephony" | "speech_to_text" | "text_to_speech" | "sms" | "forensic_analysis" | "lpr" | "biometric_verification";
  mode: "mock" | "live";
};

export type VoiceProviderAdapter = {
  capabilities(): ProviderCapability[];
  verifyWebhook(signature: string, body: string): boolean;
  health(): Promise<ProviderHealth>;
  startOutboundCall(input: { destination: string; disclosure: string }): Promise<{ providerRequestId: string }>;
};

export type MessagingProviderAdapter = {
  capabilities(): ProviderCapability[];
  health(): Promise<ProviderHealth>;
  sendAuthorizedSms(input: { destination: string; body: string; authorizationId: string }): Promise<{ providerMessageId: string }>;
};

/**
 * Deliberately inert adapters. They establish stable business interfaces without
 * selecting, licensing, billing, or activating a vendor.
 */
export const mockVoiceProvider: VoiceProviderAdapter = {
  capabilities: () => [
    { provider: "mock", capability: "telephony", mode: "mock" },
    { provider: "mock", capability: "speech_to_text", mode: "mock" },
    { provider: "mock", capability: "text_to_speech", mode: "mock" },
  ],
  verifyWebhook: () => false,
  health: async () => ({ healthy: true, checkedAt: new Date().toISOString(), detail: "Synthetic mock adapter; no live provider connected." }),
  startOutboundCall: async () => ({ providerRequestId: "mock-disabled" }),
};

export const mockMessagingProvider: MessagingProviderAdapter = {
  capabilities: () => [{ provider: "mock", capability: "sms", mode: "mock" }],
  health: async () => ({ healthy: true, checkedAt: new Date().toISOString(), detail: "Synthetic mock adapter; no live provider connected." }),
  sendAuthorizedSms: async () => ({ providerMessageId: "mock-disabled" }),
};
