import axios from "axios";
import { useState, useRef, useEffect } from "react";
import TripMap from "./TripMap";

const API_URL = "http://127.0.0.1:8000";

function Chatbot({ onClose }) {
  // Historique des messages affichés (bot + utilisateur), avec le message d'accueil initial
  const [messages, setMessages] = useState([
    { sender: "bot", text: "Hello!  Welcome to SmartLimo AI.I'm here to help you book your limousine in just a few messages.Where would you like to be picked up?" },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  // Id renvoyé par le backend pour garder le fil de la conversation entre chaque appel
  const [conversationId, setConversationId] = useState(null);
  // Données du trajet (coordonnées, distance, geometry) une fois le resume de reservation détecté
  const [tripInfo, setTripInfo] = useState(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll vers le dernier message à chaque nouveau message ou changement de statut de chargement
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_URL}/chat/`, {
        message: userMessage.text,
        conversation_id: conversationId,
      });
      setConversationId(response.data.conversation_id);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: response.data.reply },
      ]);

      // Si le bot affiche le resume de reservation -> on extrait pickup/destination
      // du texte de la réponse pour aller chercher le trajet (route) et l'afficher sur la carte
      const data = response.data;
      if (data.reply.includes("reservation summary")) {
        const pickupMatch = data.reply.match(/- Pickup: (.+)/);
        const dropoffMatch = data.reply.match(/- Destination: (.+)/);
        if (pickupMatch && dropoffMatch) {
          axios.get(`${API_URL}/route/`, {
            params: { pickup: pickupMatch[1].trim(), dropoff: dropoffMatch[1].trim() }
          }).then(res => {
            if (!res.data.error) setTripInfo(res.data);
          });
        }
      }
    } catch (error) {
      console.log(error);
      console.log(error.response);
      console.log(error.message);

      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "Sorry, I can't reach the server." },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // Envoi du message avec la touche Entrée
  const handleKeyDown = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  return (
    <div className="chatbot">
      <div className="chatbot-header">
        <span>SmartLimo AI</span>
        <button className="close-button" onClick={onClose}>✕</button>
      </div>

      <div className="chatbot-messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.sender}`}>
            {msg.text}
          </div>
        ))}
        {isLoading && <div className="message bot">...</div>}
        {/* Carte affichée uniquement une fois le trajet resolu depuis le resume de reservation */}
        {tripInfo && (
          <TripMap
            pickupCoords={tripInfo.pickup_coords}
            dropoffCoords={tripInfo.dropoff_coords}
            distanceKm={tripInfo.distance_km}
            durationMin={tripInfo.duration_min}
            geometry={tripInfo.geometry}
          />
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chatbot-input">
        <input
          type="text"
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button onClick={sendMessage}>Send</button>
      </div>
    </div>
  );
}

export default Chatbot;