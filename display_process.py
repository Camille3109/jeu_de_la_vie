"""
Processus DISPLAY - Interface utilisateur pour observer et contrôler la simulation
"""

import time
import sys
import os


class DisplayManager:
    """Gestionnaire de l'affichage de la simulation"""
    
    def __init__(self, msg_queue, config):
        self.msg_queue = msg_queue
        self.config = config
        self.running = True
        self.last_status = {}
        
    def get_status(self):
        """Demande le statut au processus env"""
        try:
            self.msg_queue.put({'type': 'GET_STATUS'})
            # Attendre la réponse (avec timeout)
            start_time = time.time()
            while time.time() - start_time < 2.0:
                if not self.msg_queue.empty():
                    status = self.msg_queue.get()
                    if isinstance(status, dict) and 'predators' in status:
                        self.last_status = status
                        return status
                time.sleep(0.01)
        except Exception as e:
            print(f" Erreur get_status: {e}")
        return self.last_status
    
    def display_simple(self):
        print("\n" + "="*70)
        print(" THE CIRCLE OF LIFE - Simulation en cours")
        print("="*70)
        print("\n Commandes: [q] Quitter | [d] Déclencher sécheresse")
        print("-"*70)
        
        while self.running:
            status = self.get_status()
            
            if status:
                # Calcul de la santé de l'écosystème
                total_pop = status['predators'] + status['preys']
                health = " STABLE"
                if status['predators'] == 0:
                    health = " EXTINCTION PRÉDATEURS"
                elif status['preys'] == 0:
                    health = " EXTINCTION PROIES"
                elif total_pop < 10:
                    health = " CRITIQUE"
                
                drought_str = "  SÉCHERESSE" if status.get('drought', False) else "  Normal"
                
                # Affichage (efface la ligne précédente)
                print(f"\r Tick: {status.get('tick', 0):6d} | "
                      f" Prédateurs: {status['predators']:3d} | "
                      f" Proies: {status['preys']:3d} | "
                      f" Herbe: {status['grass']:4d} | "
                      f"{drought_str:15s} | "
                      f"{health:20s}", end='', flush=True)
            
            time.sleep(self.config.DISPLAY_UPDATE_INTERVAL)
    
    
    
    def run(self):
        """Lance l'affichage"""
        print(" Démarrage du display...")
        time.sleep(1)  # Attendre que env soit prêt
        self.display_simple()
        
        print("\n\n Display arrêté")

def display_process(msg_queue, config):
    """Point d'entrée du processus display"""
    display = DisplayManager(msg_queue, config)
    display.run()
