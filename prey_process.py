"""
Processus PREY - Simulation d'une proie individuelle
"""

import socket
import time
import json
import random

class Prey:
    """Représente une proie dans l'écosystème"""
    
    def __init__(self, prey_id, shared_memory, config):
        self.id = prey_id
        self.shared_mem = shared_memory
        self.config = config
        
        # Attributs de la proie
        self.energy = config.PREY_INITIAL_ENERGY
        self.state = 'passive'  # 'active' ou 'passive'
        self.alive = True
        
        # Socket pour communiquer avec env
        self.socket = None
        
    def connect_to_env(self):
        """Se connecte au processus environnement"""
        max_retries = 5
        for attempt in range(max_retries):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.config.SOCKET_HOST, self.config.SOCKET_PORT))
                # Envoyer message JOIN
                self.send_message({
                    'type': 'JOIN',
                    'entity': 'prey',
                    'id': self.id
                })
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                else:
                    print(f" Proie {self.id}: Impossible de se connecter")
                    return False
        return False
    
    def send_message(self, msg):
        """Envoie un message au processus env"""
        if self.socket:
            try:
                data = json.dumps(msg) + '\n'
                self.socket.sendall(data.encode('utf-8'))
            except Exception as e:
                print(f" Proie {self.id}: Erreur envoi message: {e}")
    
    def update_state(self):
        """Met à jour l'état (actif/passif) selon l'énergie"""
        if self.energy < self.config.PREY_HUNGER_THRESHOLD:
            if self.state != 'active':
                self.state = 'active'
                # print(f" Proie {self.id}: ACTIVE (énergie: {self.energy:.1f})")
        elif self.energy > self.config.PREY_HUNGER_THRESHOLD + 20:
            if self.state != 'passive':
                self.state = 'passive'
                # print(f" Proie {self.id}: PASSIVE (énergie: {self.energy:.1f})")
    
    def try_to_feed(self):
        """Tente de se nourrir d'herbe"""
        if self.state == 'active':
            with self.shared_mem['population_lock']:
                if self.shared_mem['grass_count'].value > 0:
                    # Manger de l'herbe
                    self.shared_mem['grass_count'].value -= 1
                    self.energy += self.config.PREY_ENERGY_GAIN
                    # print(f" Proie {self.id}: A mangé de l'herbe! (énergie: {self.energy:.1f})")
                    
                    self.send_message({
                        'type': 'FEED',
                        'entity': 'prey',
                        'id': self.id,
                        'target': 'grass'
                    })
                    return True
        return False
    
    def try_to_reproduce(self):
        """Tente de se reproduire si énergie suffisante"""
        if self.energy > self.config.PREY_REPRODUCTION_THRESHOLD:
            # Probabilité de reproduction
            if random.random() < 0.4:  # 40% de chance
                self.energy -= self.config.PREY_REPRODUCTION_COST
                # print(f" Proie {self.id}: Reproduction! (énergie: {self.energy:.1f})")
                
                self.send_message({
                    'type': 'REPRODUCE',
                    'entity': 'prey',
                    'id': self.id
                })
                return True
        return False
    
    def live(self):
        """Boucle de vie de la proie"""
        if not self.connect_to_env():
            return
        
        # print(f" Proie {self.id} née avec {self.energy:.1f} d'énergie")
        
        while self.alive and self.energy > 0:
            # Diminution de l'énergie
            self.energy -= self.config.PREY_ENERGY_DECAY
            
            # Mise à jour de l'état
            self.update_state()
            
            # Tentative de se nourrir
            self.try_to_feed()
            
            # Tentative de reproduction
            self.try_to_reproduce()
            
            # Vérifier la mort
            if self.energy <= 0:
                self.alive = False
                break
            
            # Attendre le prochain cycle
            time.sleep(self.config.SIMULATION_TICK)
        
        # Mort de la proie
        # print(f" Proie {self.id} est morte")
        self.send_message({
            'type': 'DEATH',
            'entity': 'prey',
            'id': self.id
        })
        
        # Fermer le socket
        if self.socket:
            self.socket.close()

def prey_process(prey_id, shared_memory, config):
    """Point d'entrée du processus proie"""
    prey = Prey(prey_id, shared_memory, config)
    prey.live()
