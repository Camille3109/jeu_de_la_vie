"""
Processus ENV - Gestion de l'environnement et des populations
"""

import socket
import signal
import time
import json
import random
import os
import multiprocessing as mp
from threading import Thread
from predator_process import predator_process as predator_process_wrapper
from prey_process import prey_process as prey_process_wrapper

class EnvironmentManager:
    """Gestionnaire de l'environnement de simulation"""
    
    def __init__(self, shared_memory, cmd_queue, data_queue, config):
        self.shared_mem = shared_memory
        self.cmd_queue = cmd_queue
        self.data_queue = data_queue
        self.config = config
        self.running = True
        self.drought_active = False
        self.tick_count = 0
        self.drought_end_tick = 0
        
        # Socket serveur
        self.server_socket = None
        self.clients = []
        
        # Statistiques
        self.total_births = 0
        self.total_deaths = 0
        
    def setup_socket(self):
        """Configure le socket serveur pour recevoir les messages"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.config.SOCKET_HOST, self.config.SOCKET_PORT))
        self.server_socket.listen(10)
        self.server_socket.settimeout(0.5)  # Non-bloquant
        print(f" Socket serveur démarré sur {self.config.SOCKET_HOST}:{self.config.SOCKET_PORT}")
    
    def handle_socket_connections(self):
        """Thread pour gérer les connexions socket"""
        while self.running:
            try:
                client, addr = self.server_socket.accept()
                self.clients.append(client)
                # Thread pour gérer ce client
                t = Thread(target=self.handle_client, args=(client,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f" Erreur socket: {e}")
                break
    
    def handle_client(self, client):
        """Gère les messages d'un client"""
        buffer = ""
        try:
            while self.running:
                data = client.recv(1024).decode('utf-8')
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        self.process_message(json.loads(line))
        except Exception as e:
            pass
        finally:
            try:
                client.close()
            except:
                pass
            if client in self.clients:
                self.clients.remove(client)
    
    def process_message(self, msg):
        """Traite un message reçu via socket"""
        try:
            msg_type = msg.get('type')
            
            if msg_type == 'JOIN':
                entity = msg.get('entity')
                entity_id = msg.get('id')
                with self.shared_mem['population_lock']:
                    if entity == 'predator':
                        self.shared_mem['predator_count'].value += 1
                    elif entity == 'prey':
                        self.shared_mem['prey_count'].value += 1
            
            elif msg_type == 'DEATH':
                entity = msg.get('entity')
                with self.shared_mem['population_lock']:
                    if entity == 'predator':
                        self.shared_mem['predator_count'].value = max(0, self.shared_mem['predator_count'].value - 1)
                    elif entity == 'prey':
                        self.shared_mem['prey_count'].value = max(0, self.shared_mem['prey_count'].value - 1)
                self.total_deaths += 1
            
            elif msg_type == 'REPRODUCE':
                entity = msg.get('entity')
                with self.shared_mem['population_lock']:
                    if entity == 'predator' and self.shared_mem['predator_count'].value < self.config.MAX_PREDATORS:
                        # Lancer nouveau processus prédateur
                        new_id = self.tick_count * 1000 + random.randint(0, 999)
                        p = mp.Process(
                            target=predator_process_wrapper,
                            args=(new_id, self.shared_mem, self.config),
                            name=f"predator_{new_id}"
                        )
                        p.start()
                        self.total_births += 1
                    elif entity == 'prey' and self.shared_mem['prey_count'].value < self.config.MAX_PREYS:
                        new_id = self.tick_count * 1000 + random.randint(0, 999)
                        p = mp.Process(
                            target=prey_process_wrapper,
                            args=(new_id, self.shared_mem, self.config),
                            name=f"prey_{new_id}"
                        )
                        p.start()
                        self.total_births += 1
            
            elif msg_type == 'FEED' :
                pass
                
                
        except Exception as e:
            print(f" Erreur process_message: {e}")
    
    def handle_message_queue(self):
        """Traite les messages de la file (depuis display)"""
        while not self.cmd_queue.empty():
            try:
                msg = self.cmd_queue.get_nowait()
                cmd_type = msg.get('type')
                
                if cmd_type == 'GET_STATUS':
                    with self.shared_mem['population_lock']:
                        status = {
                            'predators': self.shared_mem['predator_count'].value,
                            'preys': self.shared_mem['prey_count'].value,
                            'grass': int(self.shared_mem['grass_count'].value),
                            'tick': self.tick_count,
                            'births': self.total_births,
                            'deaths': self.total_deaths,
                            'drought_active': bool(self.shared_mem['drought_active'].value)
                        }
                    self.data_queue.put(status)
                
                elif cmd_type == 'MODIFY_PARAMS':
                    param = msg.get('param')
                    value = msg.get('value')
                    self.config.update_parameter(param, value)
                        
                
                elif cmd_type == 'SHUTDOWN':
                    self.running = False
                
                
            except Exception as e:
                print(f" Erreur message queue: {e}")

    def handle_signal(self, sig, frame):
        if sig == signal.SIGUSR1:
            self.trigger_drought()
    
    def update_grass(self):
        """Met à jour la croissance de l'herbe"""
        if not self.drought_active:
            with self.shared_mem['population_lock']:
                current = self.shared_mem['grass_count'].value
                new_value = min(current + self.config.GRASS_GROWTH_RATE, self.config.GRASS_MAX)
                self.shared_mem['grass_count'].value = int(new_value)  # Convertir en int
        else : 
            with self.shared_mem['population_lock']:
                current = self.shared_mem['grass_count'].value
                new_value = max(current - self.config.GRASS_DECREASE_RATE, 0)
                self.shared_mem['grass_count'].value = int(new_value)  # Convertir en int

    
    def check_drought(self):
        """Vérifie et gère les sécheresses"""
        if not self.drought_active:
            # Démarrer sécheresse aléatoirement
            if random.random() < self.config.DROUGHT_PROBABILITY:
                self.trigger_drought()
        else:
            # Vérifier fin de sécheresse
            if self.tick_count >= self.drought_end_tick:
                self.end_drought()
    
    def trigger_drought(self):
        """Déclenche une sécheresse"""
        self.drought_active = True
        self.shared_mem['drought_active'].value = 1
        duration = random.randint(self.config.DROUGHT_MIN_DURATION, self.config.DROUGHT_MAX_DURATION)
        self.drought_end_tick = self.tick_count + duration
        print(f"  SÉCHERESSE déclenchée (durée: {duration} ticks)")

    
    def end_drought(self):
        """Termine une sécheresse"""
        self.drought_active = False
        self.shared_mem['drought_active'].value = 0
        print(f"  SÉCHERESSE terminée")
    
    def run(self):
        """Boucle principale de l'environnement"""

        self.shared_mem['env_pid'].value = os.getpid()
        try:
            self.setup_socket()
            
            # Thread pour gérer les connexions socket
            socket_thread = Thread(target=self.handle_socket_connections, daemon=True)
            socket_thread.start()
            
            print(" Environnement actif")

            signal.signal(signal.SIGUSR1, self.handle_signal)
            
            while self.running:
                self.tick_count += 1
                
                # Traiter la file de messages
                self.handle_message_queue()
                
                # Mettre à jour l'herbe
                self.update_grass()
                
                # Gérer les sécheresses
                self.check_drought()
                
                # Attendre le prochain tick
                time.sleep(self.config.SIMULATION_TICK)
        
        except Exception as e:
            print(f" Erreur dans ENV: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Nettoyage
            if self.server_socket:
                self.server_socket.close()


def env_process(shared_memory, cmd_queue, data_queue, config):
    """Point d'entrée du processus environnement"""
    env = EnvironmentManager(shared_memory, cmd_queue, data_queue, config)
    env.run()
