#!/usr/bin/env python3
"""
Script de test pour la simulation Circle of Life
Teste différents scénarios et configurations
"""

import multiprocessing as mp
import time
import sys
from config import Config
from env_process import env_process
from display_process import display_process
from predator_process import predator_process
from prey_process import prey_process

def test_scenario(name, config_modifications, duration=30):
    """
    Teste un scénario spécifique
    
    Args:
        name: Nom du scénario
        config_modifications: Dict de modifications à appliquer à la config
        duration: Durée du test en secondes
    """
    print(f"\n{'='*70}")
    print(f" TEST: {name}")
    print(f"{'='*70}\n")
    
    # Configuration
    config = Config()
    for key, value in config_modifications.items():
        setattr(config, key, value)
    
    # Afficher la configuration
    print("Configuration:")
    for key, value in config_modifications.items():
        print(f"  - {key}: {value}")
    print()
    
    # Ressources partagées
    shared_memory = {
        'predator_count': mp.Value('i', 0),
        'prey_count': mp.Value('i', 0),
        'grass_count': mp.Value('i', config.INITIAL_GRASS),
        'population_lock': mp.Lock(),
        'drought_active': mp.Value('i', 0),
        'env_pid': mp.Value('i', 0)
    }
    
    msg_queue = mp.Queue()
    
    # Démarrer ENV
    env_proc = mp.Process(target=env_process, args=(shared_memory, msg_queue, config))
    env_proc.start()
    time.sleep(0.5)

    display_proc = mp.Process(
    target=display_process,
    args=(msg_queue, config, shared_memory),
    daemon=True)
    display_proc.start()
    time.sleep(0.5)
    
    # Démarrer prédateurs
    predator_procs = []
    for i in range(config.INITIAL_PREDATORS):
        p = mp.Process(target=predator_process, args=(i, shared_memory, config))
        p.start()
        predator_procs.append(p)
        time.sleep(0.05)
    
    # Démarrer proies
    prey_procs = []
    for i in range(config.INITIAL_PREYS):
        p = mp.Process(target=prey_process, args=(i, shared_memory, config))
        p.start()
        prey_procs.append(p)
        time.sleep(0.05)
    
    # Observer pendant la durée spécifiée
    start_time = time.time()
    observations = []
    
    print("Observation en cours...")
    while time.time() - start_time < duration:
        # Demander le statut
        msg_queue.put({'type': 'GET_STATUS'})
        time.sleep(0.1)
        
        if not msg_queue.empty():
            status = msg_queue.get()
            if isinstance(status, dict) and 'predators' in status:
                observations.append(status)
                print(f"\r  {int(time.time() - start_time):3d}s | "
                      f" {status['predators']:3d} | "
                      f" {status['preys']:3d} | "
                      f" {status['grass']:4d}", end='', flush=True)
        
        time.sleep(1)
    
    print("\n")
    
    # Arrêter la simulation
    msg_queue.put({'type': 'SHUTDOWN'})
    time.sleep(1)
    
    # Terminer tous les processus
    for p in [env_proc] + predator_procs + prey_procs:
        if p.is_alive():
            p.terminate()
            p.join(timeout=1)
    
    # Analyser les résultats
    if observations:
        print("\n Résultats:")
        print(f"  Observations: {len(observations)}")
        print(f"  Prédateurs - Min: {min(o['predators'] for o in observations)} "
              f"Max: {max(o['predators'] for o in observations)} "
              f"Final: {observations[-1]['predators']}")
        print(f"  Proies - Min: {min(o['preys'] for o in observations)} "
              f"Max: {max(o['preys'] for o in observations)} "
              f"Final: {observations[-1]['preys']}")
        print(f"  Herbe - Min: {int(min(o['grass'] for o in observations))} "
              f"Max: {int(max(o['grass'] for o in observations))} "
              f"Final: {int(observations[-1]['grass'])}")
        
        # Déterminer le résultat
        final = observations[-1]
        if final['predators'] == 0:
            result = " ÉCHEC - Extinction des prédateurs"
        elif final['preys'] == 0:
            result = " ÉCHEC - Extinction des proies"
        elif final['predators'] + final['preys'] < 5:
            result = "  CRITIQUE - Population très faible"
        else:
            result = " SUCCÈS - Écosystème stable"
        
        print(f"\n  Résultat: {result}")
    
    return observations

def main():
    print("="*70)
    print(" SUITE DE TESTS - The Circle of Life")
    print("="*70)
    
    mp.set_start_method('spawn', force=True)
    
    # Test 1: Configuration par défaut
    test_scenario(
        "Scénario Standard",
        {
            'INITIAL_PREDATORS': 5,
            'INITIAL_PREYS': 15,
            'INITIAL_GRASS': 100,
        },
        duration=30
    )
    
    # Test 2: Beaucoup de prédateurs
    test_scenario(
        "Surpopulation de Prédateurs",
        {
            'INITIAL_PREDATORS': 15,
            'INITIAL_PREYS': 10,
            'INITIAL_GRASS': 100,
            'PREDATOR_ENERGY_DECAY': 0.3,  # Prédateurs moins affamés
        },
        duration=25
    )
    
    # Test 3: Peu de ressources
    test_scenario(
        "Ressources Limitées",
        {
            'INITIAL_PREDATORS': 5,
            'INITIAL_PREYS': 20,
            'INITIAL_GRASS': 30,
            'GRASS_GROWTH_RATE': 0.5,
        },
        duration=25
    )
    
    # Test 4: Reproduction rapide
    test_scenario(
        "Reproduction Accélérée",
        {
            'INITIAL_PREDATORS': 2,
            'INITIAL_PREYS': 5,
            'INITIAL_GRASS': 150,
            'PREDATOR_REPRODUCTION_THRESHOLD': 80,
            'PREY_REPRODUCTION_THRESHOLD': 70,
        },
        duration=25
    )
    
    # Test 5: Environnement hostile
    test_scenario(
        "Environnement Hostile",
        {
            'INITIAL_PREDATORS': 3,
            'INITIAL_PREYS': 10,
            'INITIAL_GRASS': 50,
            'PREDATOR_ENERGY_DECAY': 0.8,
            'PREY_ENERGY_DECAY': 0.5,
            'GRASS_GROWTH_RATE': 1.0,
        },
        duration=25
    )
    
    print("\n" + "="*70)
    print(" Tous les tests sont terminés!")
    print("="*70)

if __name__ == "__main__":
    main()
