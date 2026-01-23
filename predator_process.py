"""
Processus PREDATOR - Simulation d'un prédateur individuel
"""

import socket
import time
import json
import random

class Predator:
    """Représente un prédateur dans l'écosystème"""
    
    def __init__(self, predator_id, shared_memory, config):
        self.id = predator_id 
        self.shared_mem = shared_memory
        self.config = config
        
        # Attributs du prédateur
        self.energy = config.PREDATOR_INITIAL_ENERGY
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
                    'entity': 'predator',
                    'id': self.id
                })
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                else:
                    print(f" Prédateur {self.id}: Impossible de se connecter")
                    return False
        return False
    
    def send_message(self, msg):
        """Envoie un message au processus env"""
        if self.socket:
            try:
                data = json.dumps(msg) + '\n' # on utilise cette fonction car msg est un dico, elle transforme en string
                self.socket.sendall(data.encode('utf-8'))
            except Exception as e:
                print(f" Prédateur {self.id}: Erreur envoi message: {e}")
    
    def update_state(self):
        """Met à jour l'état (actif/passif) selon l'énergie"""
        if self.energy < self.config.PREDATOR_HUNGER_THRESHOLD:
            if self.state != 'active':
                self.state = 'active'
        elif self.energy > self.config.PREDATOR_HUNGER_THRESHOLD + 20:
            if self.state != 'passive':
                self.state = 'passive'
    
    def try_to_feed(self):
        """Tentative pour se nourrir d'une proie"""
        if self.state == 'active':
            with self.shared_mem['population_lock']:
                if self.shared_mem['prey_count'].value > 0:
                    # Chance de capturer une proie
                    if random.random() < 0.7: 
                            self.shared_mem['prey_count'].value -= 1
                            self.energy += self.config.PREDATOR_ENERGY_GAIN
                        
                            self.send_message({
                                'type': 'FEED',
                                'entity': 'predator',
                                'id': self.id,
                                'target': 'prey'
                            })
                            return True
        return False
    
    def try_to_reproduce(self):
        """Tentative de se reproduire si énergie suffisante"""
        if self.energy > self.config.PREDATOR_REPRODUCTION_THRESHOLD:
            # Probabilité de reproduction
            if random.random() < 0.3: 
                self.energy -= self.config.PREDATOR_REPRODUCTION_COST
                
                self.send_message({
                    'type': 'REPRODUCE',
                    'entity': 'predator',
                    'id': self.id
                })
                return True
        return False
    
    def live(self):
        """Boucle de vie du prédateur"""
        if not self.connect_to_env():
            return
        
        while self.alive and self.energy > 0 and not self.shared_mem['shutdown'].value :
            # Diminution de l'énergie
            self.energy -= self.config.PREDATOR_ENERGY_DECAY
            
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
        
        # Mort du prédateur

        self.send_message({
            'type': 'DEATH',
            'entity': 'predator',
            'id': self.id
        })
        
        # Fermer le socket
        if self.socket:
            self.socket.close()

def predator_process(predator_id, shared_memory, config):

    predator = Predator(predator_id, shared_memory, config)
    predator.live()
