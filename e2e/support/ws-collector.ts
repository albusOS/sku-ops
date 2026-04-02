import { API_BASE_URL } from "./api-client";

const WS_ORIGIN = API_BASE_URL.replace(/^http/, "ws");

/**
 * Connects to the domainevent WebSocket and records all received events.
 */
export class WSEventCollector {
  private ws: WebSocket | null = null;
  private events: unknown[] = [];
  private resolvers: Array<{ type: string; resolve: (ev: unknown) => void }> = [];

  async connect(token: string): Promise<void> {
    return new Promise<void>((resolve, reject) => {
      this.ws = new WebSocket(`${WS_ORIGIN}/api/beta/shared/ws?token=${token}`);
      this.ws.onopen = () => resolve();
      this.ws.onerror = (err) => reject(err);
      this.ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data as string) as { type?: string };
          if (data.type === "ping") return;
          this.events.push(data);
          for (let i = this.resolvers.length - 1; i >= 0; i--) {
            if (this.resolvers[i].type === data.type) {
              this.resolvers[i].resolve(data);
              this.resolvers.splice(i, 1);
            }
          }
        } catch {
          // ignore non-JSON
        }
      };
    });
  }

  async waitFor(type: string, timeoutMs = 5000): Promise<unknown> {
    const existing = this.events.find((e) => (e as { type?: string }).type === type);
    if (existing) return existing;
    return new Promise<unknown>((resolve, reject) => {
      const entry = { type, resolve };
      this.resolvers.push(entry);
      setTimeout(() => {
        const idx = this.resolvers.indexOf(entry);
        if (idx !== -1) {
          this.resolvers.splice(idx, 1);
          reject(new Error(`Timed out waiting for WS event "${type}" after ${timeoutMs}ms`));
        }
      }, timeoutMs);
    });
  }

  allOfType(type: string): unknown[] {
    return this.events.filter((e) => (e as { type?: string }).type === type);
  }

  clear(): void {
    this.events = [];
  }

  close(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.resolvers = [];
  }
}
