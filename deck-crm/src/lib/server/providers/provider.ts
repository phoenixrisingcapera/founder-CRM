export interface ProviderResult {
  text: string;
}

export interface AIProvider {
  complete(input: { system: string; user: string }): Promise<ProviderResult>;
}
