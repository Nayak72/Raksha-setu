/**
 * MQTT Client panel — subscribe to topics and display real-time messages.
 */
import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Wifi,
  WifiOff,
  Send,
  ChevronDown,
  ChevronUp,
  Circle,
} from 'lucide-react';
import { useMqtt } from '../hooks/useMqtt';

const DEFAULT_TOPICS = [
  'alerts/#',
  'raksha/dispatch/#',
  'raksha/shelters/#',
  'raksha/system/#',
];

export default function MqttClientPanel() {
  const { isConnected, messages, connect, disconnect, subscribe } = useMqtt();
  const [brokerUrl, setBrokerUrl] = useState(import.meta.env.VITE_MQTT_WS_URL || 'ws://10.2.1.183:9001/mqtt');
  const [newTopic, setNewTopic] = useState('');
  const [subscribedTopics, setSubscribedTopics] = useState<string[]>([]);
  const [expandedMsg, setExpandedMsg] = useState<number | null>(null);
  const [topicFilter, setTopicFilter] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-subscribe to default topics on connect
  useEffect(() => {
    if (isConnected && subscribedTopics.length === 0) {
      DEFAULT_TOPICS.forEach((topic) => {
        subscribe(topic);
      });
      setSubscribedTopics(DEFAULT_TOPICS);
    }
  }, [isConnected, subscribedTopics.length, subscribe]);

  const handleConnect = () => {
    if (isConnected) {
      disconnect();
      setSubscribedTopics([]);
    } else {
      connect(brokerUrl);
    }
  };

  const handleSubscribe = () => {
    if (newTopic.trim() && isConnected) {
      subscribe(newTopic.trim());
      setSubscribedTopics((prev) => [...prev, newTopic.trim()]);
      setNewTopic('');
    }
  };

  const filteredMessages = topicFilter
    ? messages.filter((m) => m.topic.includes(topicFilter))
    : messages;

  const getTopicColor = (topic: string): string => {
    if (topic.includes('alert')) return 'text-danger-400';
    if (topic.includes('dispatch')) return 'text-safe-400';
    if (topic.includes('shelter')) return 'text-raksha-400';
    if (topic.includes('system')) return 'text-warning-400';
    return 'text-surface-300';
  };

  return (
    <div className="flex flex-col h-full" id="mqtt-client-panel">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {isConnected ? (
            <Wifi className="text-safe-400" size={20} />
          ) : (
            <WifiOff className="text-surface-500" size={20} />
          )}
          <h2 className="text-lg font-bold text-white">MQTT Client</h2>
          <span className={isConnected ? 'status-safe' : 'status-critical'}>
            <Circle size={6} fill="currentColor" />
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Connection */}
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={brokerUrl}
          onChange={(e) => setBrokerUrl(e.target.value)}
          placeholder="ws://test.mosquitto.org:8080/mqtt"
          className="input-field text-sm flex-1"
          disabled={isConnected}
          id="mqtt-broker-url"
        />
        <button
          onClick={handleConnect}
          className={`px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
            isConnected
              ? 'bg-danger-600/20 text-danger-400 border border-danger-500/30 hover:bg-danger-600/30'
              : 'btn-primary'
          }`}
          id="mqtt-connect-btn"
        >
          {isConnected ? 'Disconnect' : 'Connect'}
        </button>
      </div>

      {/* Subscribe */}
      {isConnected && (
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={newTopic}
            onChange={(e) => setNewTopic(e.target.value)}
            placeholder="Topic to subscribe..."
            className="input-field text-sm flex-1"
            onKeyDown={(e) => e.key === 'Enter' && handleSubscribe()}
            id="mqtt-topic-input"
          />
          <button onClick={handleSubscribe} className="btn-primary px-3" id="mqtt-subscribe-btn">
            <Send size={14} />
          </button>
        </div>
      )}

      {/* Subscribed topics */}
      {subscribedTopics.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {subscribedTopics.map((topic) => (
            <span
              key={topic}
              className="px-2 py-1 rounded-md bg-raksha-500/10 text-raksha-400 text-[10px] font-mono border border-raksha-500/20"
            >
              {topic}
            </span>
          ))}
        </div>
      )}

      {/* Filter */}
      <div className="flex gap-2 mb-3">
        <input
          type="text"
          value={topicFilter}
          onChange={(e) => setTopicFilter(e.target.value)}
          placeholder="Filter by topic..."
          className="input-field text-xs flex-1 py-1.5"
          id="mqtt-filter-input"
        />
        <span className="text-xs text-surface-500 self-center whitespace-nowrap">
          {filteredMessages.length} msgs
        </span>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-1.5 pr-1">
        <AnimatePresence mode="popLayout">
          {filteredMessages.slice(0, 50).map((msg, idx) => {
            const isExpanded = expandedMsg === idx;
            return (
              <motion.div
                key={`${msg.topic}-${msg.timestamp.getTime()}-${idx}`}
                layout
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="rounded-lg bg-surface-800/40 border border-surface-700/30 p-2.5 cursor-pointer hover:border-surface-600/40 transition-all"
                onClick={() => setExpandedMsg(isExpanded ? null : idx)}
              >
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-mono font-bold ${getTopicColor(msg.topic)}`}>
                    {msg.topic}
                  </span>
                  <span className="text-[9px] text-surface-500 ml-auto font-mono">
                    {msg.timestamp.toLocaleTimeString()}
                  </span>
                  {isExpanded ? (
                    <ChevronUp size={10} className="text-surface-500" />
                  ) : (
                    <ChevronDown size={10} className="text-surface-500" />
                  )}
                </div>

                {!isExpanded && (
                  <p className="text-xs text-surface-300 mt-1 truncate font-mono">
                    {msg.payload.slice(0, 80)}
                    {msg.payload.length > 80 ? '...' : ''}
                  </p>
                )}

                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <pre className="mt-2 p-2 rounded-lg bg-surface-900/60 text-xs text-surface-300 font-mono overflow-x-auto whitespace-pre-wrap break-all">
                        {msg.parsed
                          ? JSON.stringify(msg.parsed, null, 2)
                          : msg.payload}
                      </pre>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {filteredMessages.length === 0 && (
          <div className="text-center py-8 text-surface-500">
            <Wifi size={24} className="mx-auto mb-2 opacity-30" />
            <p className="text-xs">
              {isConnected ? 'Waiting for messages...' : 'Connect to see messages'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
