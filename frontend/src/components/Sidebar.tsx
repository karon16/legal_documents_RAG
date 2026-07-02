import React from 'react';
import { Plus, MessageSquare, Search, FileText, BarChart2, Clock } from 'lucide-react';

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span style={{ color: "var(--color-secondary)", fontSize: "24px" }}>⚖️</span>
        JusticeCongo
      </div>
      <div className="brand-sub">Conseiller Juridique IA</div>
      
      <button className="send-btn" style={{ width: "100%", height: "40px", borderRadius: "8px", marginBottom: "28px", fontSize: "14px", fontWeight: "500", gap: "8px" }}>
        <Plus size={18} />
        Nouvelle question
      </button>

      <div className="nav-section">
        <div className="nav-title">Menu</div>
        <div className="nav-item active">
          <MessageSquare size={18} />
          Questions
        </div>
        <div className="nav-item">
          <Search size={18} />
          Rechercher
        </div>
        <div className="nav-item">
          <FileText size={18} />
          Textes de loi
        </div>
        <div className="nav-item">
          <BarChart2 size={18} />
          Statistiques
        </div>
      </div>

      <div className="nav-section">
        <div className="nav-title">Historique</div>
        <div style={{ fontSize: "11px", color: "var(--color-neutral-dark)", marginLeft: "12px", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>Aujourd'hui</div>
        <div className="nav-item history">
          <Clock size={14} />
          Droits de succession...
        </div>
        
        <div style={{ fontSize: "11px", color: "var(--color-neutral-dark)", marginLeft: "12px", marginTop: "16px", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: 600 }}>Hier</div>
        <div className="nav-item history">
          <Clock size={14} />
          Procédure de licenciement...
        </div>
      </div>

      <div className="user-profile">
        <div className="avatar">U</div>
        <div className="user-info">
          <div className="user-name">Utilisateur</div>
          <div className="user-plan">Standard Plan</div>
        </div>
      </div>
    </aside>
  );
}
