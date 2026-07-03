import type { BBox, FlightDelta, WsUpdateMessage } from "../types/flight";

type Listener = (flights: FlightDelta[], ts: number) => void;

function wsUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws/telemetry`;
}

export class TelemetryWebSocket {
  private ws: WebSocket | null = null;
  private bbox: BBox = [39, -76, 42, -72];
  private listeners = new Set<Listener>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private statusListeners = new Set<(connected: boolean) => void>();

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  onStatus(listener: (connected: boolean) => void): () => void {
    this.statusListeners.add(listener);
    return () => this.statusListeners.delete(listener);
  }

  setBbox(bbox: BBox): void {
    this.bbox = bbox;
    this.sendSubscribe();
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.ws = new WebSocket(wsUrl());
    this.ws.onopen = () => {
      this.notifyStatus(true);
      this.sendSubscribe();
    };
    this.ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data as string) as WsUpdateMessage;
        if (msg.type === "update" && Array.isArray(msg.flights)) {
          for (const l of this.listeners) l(msg.flights, msg.ts);
        }
      } catch {
        /* ignore malformed */
      }
    };
    this.ws.onclose = () => {
      this.notifyStatus(false);
      this.scheduleReconnect();
    };
    this.ws.onerror = () => this.ws?.close();
  }

  disconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this.ws?.close();
    this.ws = null;
    this.notifyStatus(false);
  }

  private sendSubscribe(): void {
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    this.ws.send(
      JSON.stringify({ type: "subscribe", bbox: this.bbox }),
    );
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, 3000);
  }

  private notifyStatus(ok: boolean): void {
    for (const l of this.statusListeners) l(ok);
  }
}

export const telemetryWs = new TelemetryWebSocket();
