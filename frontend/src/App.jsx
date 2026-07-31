// SmartLimo AI - Composant racine de l'application
//
// Affiche la page d'accueil (titre + description) ainsi que le bouton
// flottant qui ouvre/ferme la fenêtre de chat (composant Chatbot). C'est
// le seul endroit où l'état "le chat est-il ouvert ?" est géré : le
// Chatbot lui-même n'est monté dans le DOM que lorsque isChatOpen est vrai.

import { useState } from "react";
import Chatbot from "./Chatbot";
import "./App.css";

function App() {
  // isChatOpen : contrôle l'affichage de la fenêtre de chat. Le composant
  // <Chatbot /> n'existe pas du tout tant que isChatOpen est false (voir
  // le rendu conditionnel plus bas), ce qui réinitialise complètement la
  // conversation React à chaque fermeture/réouverture (mais pas côté
  // backend, où la session est conservée via conversation_id).
  const [isChatOpen, setIsChatOpen] = useState(false);

  return (
    <div className="app">
      {/* Texte central */}
      <div className="intro">
        <h1 className="title"> SmartLimo AI</h1>
        <p className="subtitle">
          Intelligent conversational assistant for booking your limousine, getting instant fare estimates, and tracking your chauffeur through natural conversation.
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
      {/* Rendu conditionnel : le composant Chatbot n'est créé que si
          isChatOpen est vrai. On lui passe onClose pour qu'il puisse
          lui-même déclencher sa fermeture (ex: bouton "X" dans son en-tête). */}
      {isChatOpen && <Chatbot onClose={() => setIsChatOpen(false)} />}
    </div>
  );
}

export default App;
