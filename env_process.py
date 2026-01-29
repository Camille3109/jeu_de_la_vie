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
    
    def __init__(self,cmd_queue, data_queue, config):
        self.shared_mem =  {
            'predator_count': mp.Value('i', 0),
            'prey_count': mp.Value('i', 0),
            'grass_count': mp.Value('i', 0),
            'count_lock': mp.Lock(),# populations : lock pour accéder à la shared memory
            'grass_lock': mp.Lock(), # herbe
            'state_lock': mp.Lock(), # shutdown / epidemy 
            'shutdown': mp.Value('i', 0), # pour arrêter les proies et prédateurs plus propremement 
            'epidemy_active': mp.Value('i', 0)
        }
        self.cmd_queue = cmd_queue
        self.data_queue = data_queue
        self.config = config
        self.running = True
        self.drought_active = False
        self.tick_count = 0
        self.drought_end_tick = 0
        self.epidemy_end_tick = 0
        self.epidemy_dem = False
        self.processes = []
        
        # Socket serveur
        self.server_socket = None
        self.clients = []
        
        # Statistiques
        self.total_births = 0
        self.total_deaths = 0
    
    def setup_socket(self):
        """Configure le socket serveur pour recevoir les messages"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Autorise la réutilisation de l’adresse et du port du socket immédiatement après sa fermeture
        self.server_socket.bind((self.config.SOCKET_HOST, self.config.SOCKET_PORT))
        self.server_socket.listen(10)
        self.server_socket.settimeout(0.5)  # Non-bloquant
    
    def handle_socket_connections(self): # IA
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
                    line, buffer = buffer.split('\n', 1) # on récup ligne par ligne dans le buffer (IA)
                    if line.strip(): # si la ligne n'est pas vide (IA)
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
            
            # Un predateur ou une proie est ajouté suite à sa création
            if msg_type == 'JOIN':
                entity = msg.get('entity')
                with self.shared_mem['count_lock']:
                    if entity == 'predator':
                        self.shared_mem['predator_count'].value += 1
                    elif entity == 'prey' :
                        self.shared_mem['prey_count'].value += 1
            
            # Un predateur ou une proie est enlevé suite à sa mort
            elif msg_type == 'DEATH':
                entity = msg.get('entity')
                with self.shared_mem['count_lock']:
                    if entity == 'predator':
                        self.shared_mem['predator_count'].value = max(0, self.shared_mem['predator_count'].value - 1)
                    elif entity == 'prey':
                        self.shared_mem['prey_count'].value = max(0, self.shared_mem['prey_count'].value - 1)
                self.total_deaths += 1
            
            # Un predateur ou une proie est ajouté suite à une reproduction
            elif msg_type == 'REPRODUCE':
                entity = msg.get('entity')
                with self.shared_mem['count_lock']:
                    nb_preys = self.shared_mem['prey_count'].value
                    nb_preds =  self.shared_mem['predator_count'].value
                # Vérification : on ne reproduit pas une espèce éteinte
                if entity == 'predator' and 0 < nb_preds < self.config.MAX_PREDATORS:
                    # Lancer nouveau processus prédateur avec un id inutilisé
                    new_id = self.tick_count * 1000 + random.randint(0, 999)
                    p = mp.Process(
                        target=predator_process_wrapper,
                        args=(new_id, self.shared_mem, self.config),
                        name=f"predator_{new_id}"
                    )
                    p.start()
                    self.total_births += 1
                elif entity == 'prey' and 0 < nb_preys < self.config.MAX_PREYS:
                    # Lancer nouveau processus prédateur avec un id inutilisé
                    new_id = self.tick_count * 1000 + random.randint(0, 999)
                    p = mp.Process(
                        target=prey_process_wrapper,
                        args=(new_id, self.shared_mem, self.config),
                        name=f"prey_{new_id}"
                    )
                    p.start()
                    self.total_births += 1
            
            elif msg_type == 'FEED' : # On s'en occupe dans predator et prey
                pass
                
                
        except Exception as e:
            print(f" Erreur process_message: {e}")
    
    def handle_message_queue(self):
        """Traite les messages de la file (depuis display)"""
        while not self.cmd_queue.empty():
            try:
                msg = self.cmd_queue.get_nowait()
                cmd_type = msg.get('type')
                
                if cmd_type == 'GET_HERBE': # on initialise la quantité d'herbe au départ
                    with self.shared_mem['grass_lock']:
                        self.shared_mem['grass_count'].value = msg["value"]

                elif cmd_type == 'GET_PREY': # on initialise la quantité de proies au départ
                    with self.shared_mem['count_lock']:
                        self.shared_mem['prey_count'].value = msg["value"]

                elif cmd_type == 'GET_PREDATOR': # on initialise la quantité de prédateurs au départ
                    with self.shared_mem['count_lock']:
                        self.shared_mem['predator_count'].value = msg["value"]

                elif cmd_type == 'GET_STATUS': # on récupère l'état des paramètres pour les transmettre au display
                    with self.shared_mem['count_lock'], self.shared_mem['grass_lock'], self.shared_mem['state_lock']:
                        status = {
                            'predators': self.shared_mem['predator_count'].value,
                            'preys': self.shared_mem['prey_count'].value,
                            'grass': int(self.shared_mem['grass_count'].value),
                            'tick': self.tick_count,
                            'births': self.total_births,
                            'deaths': self.total_deaths,
                            'drought_active': bool(self.drought_active),
                            'epidemy_active': bool(self.shared_mem['epidemy_active'].value)
                        }
                    self.data_queue.put(status)
                        
                
                elif cmd_type == 'SHUTDOWN': # On stoppe la simulation
                    self.running = False
                    with self.shared_mem['state_lock']:
                        self.shared_mem['shutdown'].value = 1
                    for p in self.processes:
                        if p.is_alive():
                            p.join(timeout=0.5)
                
                
            except Exception as e:
                print(f" Erreur message queue: {e}")

    def handle_signal(self, sig, frame):
        if sig == signal.SIGUSR1: # si on reçoit un signal, on déclenche une sécheresse
            self.trigger_drought()
        if sig == signal.SIGUSR2 : # si on reçoit un signal, on déclenche une épidémie
            self.epidemy_dem = True
    
    def update_grass(self):
        """Met à jour la croissance de l'herbe"""
        if not self.drought_active:
            with self.shared_mem['grass_lock']:
                current = self.shared_mem['grass_count'].value
                new_value = min(current + self.config.GRASS_GROWTH_RATE, self.config.GRASS_MAX)
                self.shared_mem['grass_count'].value = int(new_value)  # Convertir en int
        else : # Si la sécheresse est active
            with self.shared_mem['grass_lock']:
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
        duration = random.randint(self.config.DROUGHT_MIN_DURATION, self.config.DROUGHT_MAX_DURATION)
        self.drought_end_tick = self.tick_count + duration
        print(f"\n 🌞​ SÉCHERESSE déclenchée (durée: {duration} ticks)")

    def end_drought(self):
        """Termine une sécheresse"""
        self.drought_active = False
        print(f"\n 🌧️​ SÉCHERESSE terminée")


    def check_epidemy(self):
        with self.shared_mem['state_lock']:
            if not self.shared_mem['epidemy_active'].value: 
                if random.random() < self.config.EPIDEMY_PROBABILITY:
                    self.trigger_epidemy()


    def trigger_epidemy(self):
        """Démarre une émidémie
        On le fait sans verrou car :
        - Seul le processus ENV possède le droit d'écrire 
          dans 'epidemy_active'. Il y écrit à seulement 2 endroits, et séquentiellement. 
          Il n'y a donc pas de danger d'écriture simultanée.
        - Ca garantit que le déclenchement de l'événement ne bloque pas les nombreux 
          processus qui lisent cette valeur, ce qui créait des bugs auparavant"""
        self.shared_mem['epidemy_active'].value = 1
        duree = random.randint(
            self.config.EPIDEMY_MIN_DURATION,
            self.config.EPIDEMY_MAX_DURATION
        )
        self.epidemy_end_tick = self.tick_count + duree
        print(f"\n 🦠 ÉPIDÉMIE déclenchée pour {duree} ticks !")


    def update_epidemy(self):
        """Termine une épidémie"""
        with self.shared_mem['state_lock']:
            if self.shared_mem['epidemy_active'].value:
                if self.tick_count >= self.epidemy_end_tick:
                    self.shared_mem['epidemy_active'].value = 0
                    print(f"\n 💊​ ÉPIDÉMIE terminée")


    
    
    def run(self):
        """Boucle principale de l'environnement"""

        try:
            self.setup_socket()
            
            # Thread pour gérer les connexions socket
            socket_thread = Thread(target=self.handle_socket_connections, daemon=True)
            socket_thread.start()
            
            print("Démarrage...")
            print("\n")

            signal.signal(signal.SIGUSR1, self.handle_signal)
            signal.signal(signal.SIGUSR2, self.handle_signal)

            self.handle_message_queue()

            # On récup le nb de prédateurs et proies
            with self.shared_mem["count_lock"] : 
                nb_predateurs = self.shared_mem["predator_count"].value
                nb_proies = self.shared_mem["prey_count"].value
            
                self.shared_mem["predator_count"].value = 0
                self.shared_mem["prey_count"].value = 0

            # Démarrer nb_predateurs prédateurs
            for i in range(nb_predateurs):
                p = mp.Process(target=predator_process_wrapper, args=(i, self.shared_mem, self.config))
                p.start()
                self.processes.append(p)
            
            time.sleep(0.5)
                
            # Démarrer nb_proies proies
            for i in range(nb_proies):
                p = mp.Process(target=prey_process_wrapper, args=(i, self.shared_mem, self.config))
                p.start()
                self.processes.append(p)

            time.sleep(0.5)
            
            while self.running:
                self.tick_count += 1
                
                # Traiter la file de messages
                self.handle_message_queue()
                
                # Mettre à jour l'herbe
                self.update_grass()
                
                # Gérer les sécheresses
                self.check_drought()

                # Gérer les épidémies
                if self.epidemy_dem : 
                    self.trigger_epidemy()
                    self.epidemy_dem = False
                self.check_epidemy()
                self.update_epidemy()
                
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


def env_process(cmd_queue, data_queue, config):
    """Point d'entrée du processus environnement"""
    env = EnvironmentManager(cmd_queue, data_queue, config)
    env.run()
