import { useState } from "react";
import Chatbot from "./Chatbot";
import "./App.css";

function App() {
  const [isChatOpen, setIsChatOpen] = useState(false);

  return (
    <div className="app">
      {/* Texte central */}
      <div className="intro">
        <h1 className="title"> SmartLimo AI</h1>
        <p className="subtitle">
          Intelligent conversational assistant for booking your limousine,<b>getting instant fare estimates,</b>  and tracking your chauffeur through natural conversation.
        </p>
      </div>

      {/* Icône flottante : toujours visible, ouvre/ferme le chat */}
      <button
        className="chat-launcher"
        onClick={() => setIsChatOpen(!isChatOpen)}
      >
        <img src="/launcher-van.png" alt="SmartLimo" className="launcher-van" />
        <div className="launcher-text">
          <span className="launcher-question"><strong>Ask SmartLimo</strong></span>
          <span className="launcher-cta"><strong>Get Instant Quote</strong></span>
        </div>
      </button>

      {/* Fenêtre du chatbot, au-dessus de l'icône */}
      {isChatOpen && <Chatbot onClose={() => setIsChatOpen(false)} />}
    </div>
  );
}

export default App;