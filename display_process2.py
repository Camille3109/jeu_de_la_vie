import multiprocessing as mp
import time
import sys
import os
import signal
import select
from config import Config
from env_process import env_process
from predator_process import predator_process
from prey_process import prey_process

class DisplayManager:
    """Gestionnaire de l'affichage de la simulation"""
    def __init__(self, config):
        self.config = config
        self.cmd_queue = mp.Queue()  # Pour envoyer des ordres à ENV
        self.data_queue = mp.Queue() # Pour recevoir les données de ENV
        self.processes = []
        self.running = True
    
    def start_simulation(self):

        # Démarrer ENV
        env_proc = mp.Process(target=env_process, args=(self.cmd_queue, self.data_queue, self.config))
        env_proc.start()
        self.processes.append(env_proc)
        time.sleep(0.5)
        env_pid = env_proc.pid
        return env_pid

    # On arrête la simulation 
    def stop_simulation(self):
        if not self.running:
            return
        print("\nArrêt de la simulation...")
        self.cmd_queue.put({'type': 'SHUTDOWN'})
        for p in self.processes:
            if p.is_alive():
                p.join(timeout=0.5)
        self.running = False

    # Gère les entrées de l'utilisateur dans le terminal : IA
    def handle_input(self, env_pid):
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline().strip().lower()
            if line == 'q':
                return "QUIT"
            elif line == 's':
                self.trigger_drought(env_pid)
        return None

    # Gère le déclenchement d'une sécheresse
    def trigger_drought(self, env_pid):
        try:
            if env_pid > 0:
                os.kill(env_pid, signal.SIGUSR1)
                print("\n[EVENT] Sécheresse déclenchée !")
        except Exception as e:
            print(f"Erreur signal: {e}")

    # La boucle principale qui contrôle la simulation 
    def run_main_loop(self):
        print("\n" + "="*70)
        print(" THE CIRCLE OF LIFE - Simulation Lancée")
        print(" Commandes: [q] Quitter | [s] Sécheresse")
        print("="*70 + "\n")

        nb_predateurs = input("Entrez le nombre de prédateurs : ")
        nb_proies = input("Entrez le nombre de proies : ")
        nb_herbe = input("Entrez la quantité d'herbe : ")

        
        # on initialise la quantité d'herbe indiquée par l'utilisateur
        self.cmd_queue.put({'type': 'GET_HERBE', 'value': int(nb_herbe)})
        self.cmd_queue.put({'type': 'GET_PREY', 'value': int(nb_proies)})
        self.cmd_queue.put({'type': 'GET_PREDATOR', 'value': int(nb_predateurs)})
        
        env_pid = self.start_simulation()


        try:
            while self.running:
                # On demande le statut à ENV via la queue
                self.cmd_queue.put({'type': 'GET_STATUS'})
                
                # On lit la réponse (IA)
                status = None
                start_wait = time.time()
                while time.time() - start_wait < 0.2:
                    if not self.data_queue.empty():
                        msg = self.data_queue.get()
                        if isinstance(msg, dict) and 'predators' in msg:
                            status = msg
                            break
                
                # 3. Affichage
                if status:
                    self.print_status_line(status)

                # 4. Gérer le clavier
                if self.handle_input(env_pid) == "QUIT":
                    break
                
                time.sleep(self.config.DISPLAY_UPDATE_INTERVAL) # on attend pendant un temps défini avant de relancer une boucle
        
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_simulation()

    def print_status_line(self, status):
        
        total_pop = status['predators'] + status['preys']
        health = " STABLE"
        if status['predators'] == 0:
            health = " EXTINCTION PRÉDATEURS"
        elif status['preys'] == 0:
            health = " EXTINCTION PROIES"
        elif total_pop < 10:
            health = " CRITIQUE"
        
        print(f"\r Tick: {status.get('tick', 0):6d} | " # les 6d, 3d servent à bien aligner ce qu'on affiche
              f"Preds: {status['predators']:3d} | "
              f"Proies: {status['preys']:3d} | "
              f"Herbe: {status['grass']:4d} | "
              f"Sécheresse: {'OUI' if status['drought_active'] else 'NON'} | "
              f"{health:15s}", end='', flush=True) # flush permet d'afficher les données au fur à mesure qu'elles arrivent
        
        

        if status["predators"] == 0 and status["preys"] == 0 :
            self.stop_simulation()
        elif status.get('tick', 0) >= 800 and health == " STABLE":
            self.stop_simulation()

if __name__ == "__main__":
    # Configuration
    my_config = Config()
    
    # Lancement
    controller = DisplayManager(my_config)
    controller.run_main_loop()