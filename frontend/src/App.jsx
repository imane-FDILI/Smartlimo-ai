import { useState } from "react";
import Chatbot from "./Chatbot";
import chatIcon from "./assets/chat-icon.png";
import "./App.css";

function App() {
  const [isChatOpen, setIsChatOpen] = useState(false);

  return (
    <div className="app">
      {/* Texte central */}
      <div className="intro">
        <h1 className="title"> SmartLimo AI</h1>
        <p className="subtitle">
          Assistant conversationnel intelligent : réservez votre limousine,
          obtenez une estimation de prix et suivez votre chauffeur simplement
          en discutant.
        </p>
      </div>

      {/* Icône flottante : toujours visible, ouvre/ferme le chat */}
      <button
        className="chat-button"
        onClick={() => setIsChatOpen(!isChatOpen)}
      >
        <img src={chatIcon} alt="Chat" className="chat-icon" />
      </button>

      {/* Fenêtre du chatbot, au-dessus de l'icône */}
      {isChatOpen && <Chatbot onClose={() => setIsChatOpen(false)} />}
    </div>
  );
}

export default App;