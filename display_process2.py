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
        self.msg_queue = mp.Queue()
        self.shared_memory = {
            'predator_count': mp.Value('i', 0),
            'prey_count': mp.Value('i', 0),
            'grass_count': mp.Value('i', config.INITIAL_GRASS),
            'population_lock': mp.Lock(),
            'drought_active': mp.Value('i', 0),
            'env_pid': mp.Value('i', 0)
        }
        self.processes = []
        self.running = True
    
    def start_simulation(self):
        # 1. Démarrer ENV
        env_proc = mp.Process(target=env_process, args=(self.shared_memory, self.msg_queue, self.config))
        env_proc.start()
        self.processes.append(env_proc)
        
        # 2. Démarrer Prédateurs
        for i in range(self.config.INITIAL_PREDATORS):
            p = mp.Process(target=predator_process, args=(i, self.shared_memory, self.config))
            p.start()
            self.processes.append(p)
            
        # 3. Démarrer Proies
        for i in range(self.config.INITIAL_PREYS):
            p = mp.Process(target=prey_process, args=(i, self.shared_memory, self.config))
            p.start()
            self.processes.append(p)

    def stop_simulation(self):
        print("\nArêt de la simulation...")
        self.msg_queue.put({'type': 'SHUTDOWN'})
        for p in self.processes:
            if p.is_alive():
                p.terminate()
                p.join(timeout=0.5)
        self.running = False

    def handle_input(self):
        """Gère les entrées clavier sur le processus principal"""
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            line = sys.stdin.readline().strip().lower()
            if line == 'q':
                return "QUIT"
            elif line == 'd':
                self.trigger_drought()
        return None

    def trigger_drought(self):
        try:
            env_pid = self.shared_memory['env_pid'].value
            if env_pid > 0:
                os.kill(env_pid, signal.SIGUSR1)
                print("\n[EVENT] Sécheresse déclenchée !")
        except Exception as e:
            print(f"Erreur signal: {e}")

    def run_main_loop(self):
        """Boucle d'affichage et de contrôle principale"""
        print("\n" + "="*70)
        print(" THE CIRCLE OF LIFE - Simulation Lancée")
        print(" Commandes: [q] Quitter | [d] Sécheresse")
        print("="*70 + "\n")

        try:
            while self.running:
                # 1. Demander le statut à ENV via la queue
                self.msg_queue.put({'type': 'GET_STATUS'})
                
                # 2. Lire la réponse (non-bloquant)
                status = None
                start_wait = time.time()
                while time.time() - start_wait < 0.2:
                    if not self.msg_queue.empty():
                        msg = self.msg_queue.get()
                        if isinstance(msg, dict) and 'predators' in msg:
                            status = msg
                            break
                
                # 3. Affichage
                if status:
                    self._print_status_line(status)

                # 4. Gérer le clavier
                if self.handle_input() == "QUIT":
                    break
                
                time.sleep(self.config.DISPLAY_UPDATE_INTERVAL)
        
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_simulation()

    def _print_status_line(self, status):
        health = "STABLE"
        if status['predators'] == 0: health = "EXT. PREDATEURS"
        elif status['preys'] == 0: health = "EXT. PROIES"
        
        print(f"\r Tick: {status.get('tick', 0):6d} | "
              f"Preds: {status['predators']:3d} | "
              f"Proies: {status['preys']:3d} | "
              f"Herbe: {status['grass']:4d} | "
              f"Sécheresse: {'OUI' if status['drought_active'] else 'NON'} | "
              f"{health:15s}", end='', flush=True)

if __name__ == "__main__":
    # Configuration
    mp.set_start_method('spawn', force=True)
    my_config = Config()
    
    # Lancement
    controller = DisplayManager(my_config)
    controller.start_simulation()
    controller.run_main_loop()