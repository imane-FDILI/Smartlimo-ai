import axios from "axios";
import { useState, useRef, useEffect } from "react";

const API_URL = "http://127.0.0.1:8000";

function Chatbot({ onClose }) {
  const [messages, setMessages] = useState([
    { sender: "bot", text: "Hello!  Welcome to SmartLimo AI.I'm here to help you book your limousine in just a few messages.Where would you like to be picked up?" },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const messagesEndRef = useRef(null);

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