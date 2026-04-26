/**
 * Full-page MQTT client view.
 */
import MqttClientPanel from '../components/MqttClientPanel';

export default function MqttPage() {
  return (
    <div className="h-[calc(100vh-4rem)] animate-fade-in" id="mqtt-page">
      <div className="glass-panel p-5 h-full">
        <MqttClientPanel />
      </div>
    </div>
  );
}
