import axios from "axios";
import { useState, useRef, useEffect } from "react";
import TripMap from "./TripMap";

const API_URL = "http://127.0.0.1:8000";

function Chatbot({ onClose }) {
  const [messages, setMessages] = useState([
    { sender: "bot", text: "Hello!  Welcome to SmartLimo AI.I'm here to help you book your limousine in just a few messages.Where would you like to be picked up?" },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const messagesEndRef = useRef(null);
  const [showVehicleButtons, setShowVehicleButtons] = useState(false);
  const [showConfirmButtons, setShowConfirmButtons] = useState(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const sendMessage = async (textOverride) => {
    const textToSend = textOverride ?? input;
    if (!textToSend.trim() || isLoading) return;

    const userMessage = { sender: "user", text: textToSend };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await axios.post(`${API_URL}/chat/`, {
        message: userMessage.text,
        conversation_id: conversationId,
      });
      setConversationId(response.data.conversation_id);

      const data = response.data;
      // Le message du bot est cree ici, avec un champ tripInfo initialement vide.
      // Il sera rempli JUSTE APRES si un resume est detecte, AVANT d'etre
      // ajoute a la liste des messages -> la carte reste ainsi rattachee
      // a CE message precis, a sa place dans l'historique, meme si
      // d'autres messages sont ajoutes ensuite.
      const botMessage = { sender: "bot", text: data.reply, tripInfo: null };

      if (data.reply.includes("reservation summary")) {
        const pickupMatch = data.reply.match(/- Pickup: (.+)/);
        const dropoffMatch = data.reply.match(/- Destination: (.+)/);
        if (pickupMatch && dropoffMatch) {
          try {
            const res = await axios.get(`${API_URL}/route/`, {
              params: { pickup: pickupMatch[1].trim(), dropoff: dropoffMatch[1].trim() }
            });
            if (!res.data.error) {
              botMessage.tripInfo = res.data;
            }
          } catch (routeError) {
            console.log(routeError);
          }
        }
      }

      setMessages((prev) => [...prev, botMessage]);
      setShowVehicleButtons(data.reply.includes("What type of vehicle would you prefer"));
      setShowConfirmButtons(data.reply.includes("Would you like to confirm your reservation"));
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

  const handleKeyDown = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  const handleVehicleClick = (vehicle) => {
    setShowVehicleButtons(false);
    sendMessage(vehicle);
  };
  const handleConfirmClick = (answer) => {
  setShowConfirmButtons(false);
  sendMessage(answer);
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
            {/* La carte s'affiche ici, DANS le message concerne, si tripInfo
                a ete rempli pour CE message precis lors de sa creation. */}
            {msg.tripInfo && (
              <TripMap
                pickupCoords={msg.tripInfo.pickup_coords}
                dropoffCoords={msg.tripInfo.dropoff_coords}
                distanceKm={msg.tripInfo.distance_km}
                durationMin={msg.tripInfo.duration_min}
                geometry={msg.tripInfo.geometry}
              />
            )}
          </div>
        ))}
        {isLoading && <div className="message bot">...</div>}

        {showVehicleButtons && (
          <div className="vehicle-buttons">
            {["Sedan", "Executive SUV", "Premium SUV", "Transit VAN", "Sprinter VAN", "No Preference"].map((v) => (
              <button key={v} className="vehicle-btn" onClick={() => handleVehicleClick(v)}>
                {v}
              </button>
            ))}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      {showConfirmButtons && (
        <div className="confirm-buttons">
          <button className="confirm-btn-yes" onClick={() => handleConfirmClick("yes")}>
            ✓ Confirmer la réservation
          </button>
          <button className="confirm-btn-no" onClick={() => handleConfirmClick("no")}>
            Modifier
          </button>
        </div>
      )}

      <div className="chatbot-input">
        <input
          type="text"
          placeholder="Type your message..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button onClick={() => sendMessage()}>Send</button>
      </div>
    </div>
  );
}

export default Chatbot;