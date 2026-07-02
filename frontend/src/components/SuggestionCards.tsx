import React from 'react';
import { Home, Store, Users } from 'lucide-react';

export default function SuggestionCards() {
  return (
    <div className="suggestions-grid">
      <div className="suggestion-card">
        <div className="card-icon">
          <Home size={18} />
        </div>
        <div className="card-title">Droits du locataire</div>
        <div className="card-desc">Informations sur les baux et expulsions</div>
      </div>
      
      <div className="suggestion-card">
        <div className="card-icon gold">
          <Store size={18} />
        </div>
        <div className="card-title">Créer une entreprise</div>
        <div className="card-desc">Guide sur le registre du commerce</div>
      </div>

      <div className="suggestion-card">
        <div className="card-icon">
          <Users size={18} />
        </div>
        <div className="card-title">Code de la Famille</div>
        <div className="card-desc">Questions sur le mariage et l'héritage</div>
      </div>
    </div>
  );
}
