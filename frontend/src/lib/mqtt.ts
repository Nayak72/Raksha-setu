/**
 * MQTT client for browser using mqtt.js.
 * Connects to Mosquitto over WebSocket.
 */
import mqtt, { MqttClient, IClientOptions } from 'mqtt';

export type MqttMessage = {
  topic: string;
  payload: string;
  timestamp: Date;
  parsed?: Record<string, unknown>;
};

type MqttEventHandler = (msg: MqttMessage) => void;

class MqttService {
  private client: MqttClient | null = null;
  private handlers: Map<string, Set<MqttEventHandler>> = new Map();
  private _isConnected = false;
  private _messages: MqttMessage[] = [];
  private readonly MAX_MESSAGES = 200;

  get isConnected(): boolean {
    return this._isConnected;
  }

  get messages(): MqttMessage[] {
    return [...this._messages];
  }

  connect(brokerUrl?: string): void {
    const url = brokerUrl || import.meta.env.VITE_MQTT_WS_URL || 'ws://localhost:9001';

    const options: IClientOptions = {
      clientId: `raksha-dashboard-${Math.random().toString(16).slice(2, 8)}`,
      clean: true,
      connectTimeout: 5000,
      reconnectPeriod: 3000,
    };

    try {
      this.client = mqtt.connect(url, options);

      this.client.on('connect', () => {
        this._isConnected = true;
        console.log('[MQTT] Connected to broker');
      });

      this.client.on('message', (topic: string, message: Buffer) => {
        const payload = message.toString();
        let parsed: Record<string, unknown> | undefined;

        try {
          parsed = JSON.parse(payload);
        } catch {
          // Not JSON
        }

        const msg: MqttMessage = {
          topic,
          payload,
          timestamp: new Date(),
          parsed,
        };

        this._messages.unshift(msg);
        if (this._messages.length > this.MAX_MESSAGES) {
          this._messages = this._messages.slice(0, this.MAX_MESSAGES);
        }

        // Dispatch to topic handlers
        const topicHandlers = this.handlers.get(topic);
        if (topicHandlers) {
          topicHandlers.forEach((handler) => handler(msg));
        }

        // Dispatch to wildcard handlers
        const wildcardHandlers = this.handlers.get('#');
        if (wildcardHandlers) {
          wildcardHandlers.forEach((handler) => handler(msg));
        }
      });

      this.client.on('error', (err) => {
        console.error('[MQTT] Error:', err);
      });

      this.client.on('close', () => {
        this._isConnected = false;
        console.log('[MQTT] Disconnected');
      });

      this.client.on('reconnect', () => {
        console.log('[MQTT] Reconnecting...');
      });
    } catch (err) {
      console.error('[MQTT] Connection failed:', err);
    }
  }

  subscribe(topic: string, handler?: MqttEventHandler): void {
    if (this.client && this._isConnected) {
      this.client.subscribe(topic, { qos: 1 }, (err) => {
        if (err) {
          console.error(`[MQTT] Subscribe error for ${topic}:`, err);
        } else {
          console.log(`[MQTT] Subscribed to ${topic}`);
        }
      });
    }

    if (handler) {
      if (!this.handlers.has(topic)) {
        this.handlers.set(topic, new Set());
      }
      this.handlers.get(topic)!.add(handler);
    }
  }

  unsubscribe(topic: string, handler?: MqttEventHandler): void {
    if (this.client && this._isConnected) {
      this.client.unsubscribe(topic);
    }

    if (handler) {
      const topicHandlers = this.handlers.get(topic);
      if (topicHandlers) {
        topicHandlers.delete(handler);
      }
    }
  }

  onMessage(handler: MqttEventHandler): () => void {
    this.subscribe('#', handler);
    return () => this.unsubscribe('#', handler);
  }

  disconnect(): void {
    if (this.client) {
      this.client.end();
      this.client = null;
      this._isConnected = false;
    }
  }
}

export const mqttService = new MqttService();
