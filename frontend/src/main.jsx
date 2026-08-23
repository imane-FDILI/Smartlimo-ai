// SmartLimo AI - Point d'entrée du frontend
//
// Monte le composant racine <App /> dans l'élément HTML #root
// (voir frontend/index.html). C'est le tout premier fichier JavaScript
// exécuté par Vite au chargement de la page.

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// StrictMode active des vérifications supplémentaires en développement
// (détection d'effets de bord non idempotents, API dépréciées...) : il
// n'a aucun effet en production et ne modifie pas le rendu final.
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
