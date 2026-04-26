/**
 * Hook for MQTT client state in React.
 */
import { useState, useEffect, useCallback } from 'react';
import { mqttService, MqttMessage } from '../lib/mqtt';

export function useMqtt(autoConnect = false) {
  const [isConnected, setIsConnected] = useState(mqttService.isConnected);
  const [messages, setMessages] = useState<MqttMessage[]>([]);

  useEffect(() => {
    if (autoConnect && !mqttService.isConnected) {
      mqttService.connect();
    }

    const interval = setInterval(() => {
      setIsConnected(mqttService.isConnected);
      setMessages(mqttService.messages);
    }, 500);

    const unsub = mqttService.onMessage(() => {
      setMessages(mqttService.messages);
    });

    return () => {
      clearInterval(interval);
      unsub();
    };
  }, [autoConnect]);

  const connect = useCallback((url?: string) => {
    mqttService.connect(url);
  }, []);

  const disconnect = useCallback(() => {
    mqttService.disconnect();
    setIsConnected(false);
  }, []);

  const subscribe = useCallback((topic: string) => {
    mqttService.subscribe(topic);
  }, []);

  return { isConnected, messages, connect, disconnect, subscribe };
}
