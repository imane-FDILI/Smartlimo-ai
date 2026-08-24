import axios from "axios";
import { useState, useRef, useEffect } from "react";
import TripMap from "./TripMap";
import { Check, Edit, X, Send, MapPin, Calendar, Clock, Users, Briefcase, Car, DollarSign, Baby } from "lucide-react";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";

   const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function Chatbot({ onClose }) {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const [showVehicleButtons, setShowVehicleButtons] = useState(false);
  const [showConfirmButtons, setShowConfirmButtons] = useState(false);
  const [showDatePicker, setShowDatePicker] = useState(false);

  const messagesEndRef = useRef(null);

  // Vérification de l'expiration de la session
  const isSessionExpired = () => {
    const savedTimestamp = localStorage.getItem("smartlimo_timestamp");

    if (!savedTimestamp) return false;

    const maxAgeMs = 24 * 60 * 60 * 1000;

    return Date.now() - parseInt(savedTimestamp) > maxAgeMs;
  };
  const renderSummary = (text) => {
  const lines = text.split("\n").filter(l => l.startsWith("- "));
  const iconMap = {
    "Pickup": MapPin,
    "Destination": MapPin,
    "Date": Calendar,
    "Time": Clock,
    "Passengers": Users,
    "Luggage": Briefcase,
    "Vehicle": Car,
    "Estimated price": DollarSign,
    "Child seat": Baby,
  };
   return lines.map((line, i) => {
    const [label, ...rest] = line.replace("- ", "").split(": ");
    const value = rest.join(": ");
    const Icon = iconMap[label] || MapPin;
    return (
      <div key={i} className="summary-line">
        <Icon size={14} /> <strong>{label}:</strong> {value}
      </div>
    );
  });
};
  // Nettoyage de l'ancienne session
  if (isSessionExpired()) {
    localStorage.removeItem("smartlimo_conversation_id");
    localStorage.removeItem("smartlimo_messages");
    localStorage.removeItem("smartlimo_timestamp");
  }

  const [conversationId, setConversationId] = useState(
    () => localStorage.getItem("smartlimo_conversation_id") || null
  );

  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem("smartlimo_messages");

    return saved
      ? JSON.parse(saved)
      : [
          {
            sender: "bot",
            text:
              "Hello! Welcome to SmartLimo AI. I'm here to help you book your limousine in just a few messages. Where would you like to be picked up?",
          },
        ];
  });

  // Sauvegarde conversation ID
  useEffect(() => {
    if (conversationId) {
      localStorage.setItem(
        "smartlimo_conversation_id",
        conversationId
      );

      localStorage.setItem(
        "smartlimo_timestamp",
        Date.now().toString()
      );
    }
  }, [conversationId]);

  // Sauvegarde messages
  useEffect(() => {
    localStorage.setItem(
      "smartlimo_messages",
      JSON.stringify(messages)
    );
  }, [messages]);

  // Scroll automatique
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  // ==============================
  // ENVOYER MESSAGE
  // ==============================

  const sendMessage = async (textOverride) => {
    const textToSend = textOverride ?? input;

    if (!textToSend.trim() || isLoading) return;

    const userMessage = {
      sender: "user",
      text: textToSend,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    // Cacher les boutons après sélection
    setShowVehicleButtons(false);
    setShowConfirmButtons(false);
    setShowDatePicker(false);

    try {
      const response = await axios.post(`${API_URL}/chat/`, {
        message: userMessage.text,
        conversation_id: conversationId,
      });

      const data = response.data;

      setConversationId(data.conversation_id);

      const botMessage = {
        sender: "bot",
        text: data.reply,
        tripInfo: null,
      };

      // ==============================
      // CARTE
      // ==============================

      if (data.reply.includes("reservation summary")) {
        const pickupMatch =
          data.reply.match(/- Pickup: (.+)/);

        const dropoffMatch =
          data.reply.match(/- Destination: (.+)/);

        if (pickupMatch && dropoffMatch) {
          try {
            const routeResponse = await axios.get(
              `${API_URL}/route/`,
              {
                params: {
                  pickup: pickupMatch[1].trim(),
                  dropoff: dropoffMatch[1].trim(),
                },
              }
            );

            if (!routeResponse.data.error) {
              botMessage.tripInfo = routeResponse.data;
            }
          } catch (routeError) {
            console.log(
              "Route error:",
              routeError
            );
          }
        }
      }

      setMessages((prev) => [
        ...prev,
        botMessage,
      ]);

      // ==============================
      // DATE PICKER
      // ==============================

      if (
        data.reply.includes(
          "What date would you like to travel"
        )
      ) {
        setShowDatePicker(true);
      }

      // ==============================
      // VEHICULES
      // ==============================

      if (
        data.reply.includes(
          "What type of vehicle would you prefer"
        )
      ) {
        setShowVehicleButtons(true);
      }

      // ==============================
      // CONFIRMATION
      // ==============================

      if (
        data.reply.includes(
          "Would you like to confirm your reservation"
        )
      ) {
        setShowConfirmButtons(true);
      }
    } catch (error) {
      console.log("Error:", error);
      console.log("Response:", error.response);

      setMessages((prev) => [
        ...prev,
        {
          sender: "bot",
          text:
            "Sorry, I can't reach the server. Please try again.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // ==============================
  // ENTER
  // ==============================

  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      sendMessage();
    }
  };

  // ==============================
  // VEHICULE
  // ==============================

  const handleVehicleClick = (vehicle) => {
    sendMessage(vehicle);
  };

  // ==============================
  // CONFIRMATION
  // ==============================

  const handleConfirmClick = (answer) => {
    sendMessage(answer);
  };

  // ==============================
  // DATE
  // ==============================

  const handleDateSelect = (date) => {
    if (!date) return;

    const formatted = date.toLocaleDateString(
      "en-US",
      {
        year: "numeric",
        month: "long",
        day: "numeric",
      }
    );

    sendMessage(formatted);
  };

  // ==============================
  // INTERFACE
  // ==============================

  return (
    <div className="chatbot">

      {/* HEADER */}
      <div className="chatbot-header">
        <span>SmartLimo AI</span>

        <button
          className="close-button"
          onClick={onClose}
        >
          ✕
        </button>
      </div>

      {/* MESSAGES */}
      <div className="chatbot-messages">

        {messages.map((msg, index) => (
          <div
            key={index}
            className={`message ${msg.sender}`}
          >
            {msg.sender === "bot" && msg.text.includes("Here is your reservation summary") ? (
              <div>
                {msg.text.split("\n")[0]}
                {renderSummary(msg.text)}
              </div>
            ) : (
              msg.text.replace(/Available options: .+\n?/, "")
            )}

            {/* MAP */}
            {msg.tripInfo && (
              <TripMap
                pickupCoords={
                  msg.tripInfo.pickup_coords
                }
                dropoffCoords={
                  msg.tripInfo.dropoff_coords
                }
                distanceKm={
                  msg.tripInfo.distance_km
                }
                durationMin={
                  msg.tripInfo.duration_min
                }
                geometry={
                  msg.tripInfo.geometry
                }
              />
            )}
          </div>
        ))}

        {/* TYPING INDICATOR */}
        {isLoading && (
          <div className="typing-indicator">

            <span>
              SmartLimo AI is typing
            </span>

            <div className="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>

          </div>
        )}

        {/* VEHICLE BUTTONS */}
        {showVehicleButtons && (
          <div className="vehicle-buttons">
            {(() => {
              const lastBotMessage = messages.filter(m => m.sender === "bot").slice(-1)[0];
              const match = lastBotMessage?.text.match(/Available options: (.+)/);
              const options = match ? match[1].split(", ") : ["Sedan", "Executive SUV", "Premium SUV", "Transit VAN", "Sprinter VAN"];
              return options.map((vehicle) => (
                <button
                  key={vehicle}
                  className="vehicle-btn"
                  onClick={() => handleVehicleClick(vehicle)}
                >
                  {vehicle}
                </button>
              ));
            })()}
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* DATE PICKER */}
      {showDatePicker && (
        <div className="date-picker-container">

          <DatePicker
            selected={null}
            onChange={handleDateSelect}
            minDate={new Date()}
            inline
          />

        </div>
      )}

      {/* CONFIRMATION */}
      {showConfirmButtons && (
                <div className="confirm-buttons">
          <button
            className="confirm-btn-yes"
            onClick={() =>
              handleConfirmClick("yes")
            }
          >
            <Check size={16} />
            Confirm Reservation
          </button>
          <button
            className="confirm-btn-no"
            onClick={() =>
              handleConfirmClick("no")
            }
          >
            <Edit size={16} />
            Modify
          </button>
          <button
            className="confirm-btn-cancel"
            onClick={() =>
              handleConfirmClick("cancel my reservation")
            }
          >
            <X size={16} />
            Cancel
          </button>
        </div>
      )}

      {/* INPUT */}
      <div className="chatbot-input">

        <input
          type="text"
          placeholder="Type your message..."
          value={input}
          onChange={(e) =>
            setInput(e.target.value)
          }
          onKeyDown={handleKeyDown}
        />

        <button
          onClick={() => sendMessage()}
          className="send-button"
          disabled={isLoading}
        >
          <Send size={18} />
        </button>

      </div>

    </div>
  );
}

export default Chatbot;