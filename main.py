#!/usr/bin/env python3
"""
The Circle of Life - Multi-process Ecosystem Simulation
"""

import multiprocessing as mp
import signal
import sys
import time
from config import Config
from env_process import env_process
from display_process import display_process
from predator_process import predator_process
from prey_process import prey_process

def cleanup(signum, frame):
    """Gestionnaire de signal pour nettoyage propre"""
    print("\n\n Arrêt de la simulation...")
    sys.exit(0)

def main():
    print("=" * 60)
    print(" THE CIRCLE OF LIFE - Simulation d'Écosystème")
    print("=" * 60)
    
    # Configuration
    config = Config()
    
    # Gestionnaire de signal pour Ctrl+C
    signal.signal(signal.SIGINT, cleanup)
    
    # Création des ressources partagées
    shared_memory = {
        'predator_count': mp.Value('i', 0),
        'prey_count': mp.Value('i', 0),
        'grass_count': mp.Value('i', config.INITIAL_GRASS),
        'population_lock': mp.Lock(),
        'drought_active': mp.Value('i', 0),  # 0 = False, 1 = True
        'env_pid': mp.Value('i', 0)
    }
    
    # File de messages pour display <-> env
    msg_queue = mp.Queue()
    
    # Démarrage du processus environnement
    print("\n Démarrage du processus environnement...")
    env_proc = mp.Process(
        target=env_process,
        args=(shared_memory, msg_queue, config),
        name="env"
    )
    env_proc.start()
    time.sleep(0.5)  # Attendre que l'environnement soit prêt
    
    # Démarrage du processus display
    print(" Démarrage du processus display...")
    display_proc = mp.Process(
        target=display_process,
        args=(msg_queue, config),
        name="display"
    )
    display_proc.start()
    time.sleep(0.5)
    
    # Démarrage des prédateurs initiaux
    print(f" Démarrage de {config.INITIAL_PREDATORS} prédateurs...")
    predator_procs = []
    for i in range(config.INITIAL_PREDATORS):
        p = mp.Process(
            target=predator_process,
            args=(i, shared_memory, config),
            name=f"predator_{i}"
        )
        p.start()
        predator_procs.append(p)
        time.sleep(0.1)
    
    # Démarrage des proies initiales
    print(f" Démarrage de {config.INITIAL_PREYS} proies...")
    prey_procs = []
    for i in range(config.INITIAL_PREYS):
        p = mp.Process(
            target=prey_process,
            args=(i, shared_memory, config),
            name=f"prey_{i}"
        )
        p.start()
        prey_procs.append(p)
        time.sleep(0.1)
    
    print("\n Simulation démarrée!")
    print(" Appuyez sur Ctrl+C pour arrêter\n")
    
    try:
        # Attendre que les processus se terminent
        env_proc.join()
        display_proc.join()
        
        for p in predator_procs :
            if p.is_alive():
                p.join(timeout=1)

        for prey in prey_procs :
            if prey.is_alive():
                prey.join(timeout=1)
                
    except KeyboardInterrupt:
        print("\n\n Arrêt demandé par l'utilisateur...")
    finally:
        # Nettoyage
        print(" Nettoyage des processus...")
        
        # Terminer tous les processus encore actifs
        for p in [env_proc, display_proc] + predator_procs + prey_procs:
            if p.is_alive():
                p.terminate()
                p.join(timeout=1)
                if p.is_alive():
                    p.kill()
        
        print(" Simulation terminée proprement")
        print("=" * 60)

if __name__ == "__main__":
    mp.set_start_method('spawn', force=True)
    main()
