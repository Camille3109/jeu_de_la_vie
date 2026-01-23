"""
Configuration centralisée pour la simulation
"""

# Générée par IA

class Config:

    # Populations initiales
    INITIAL_PREDATORS = 5
    INITIAL_PREYS = 15
    INITIAL_GRASS = 100
    
    # Seuils d'énergie
    PREDATOR_HUNGER_THRESHOLD = 75  # H pour prédateurs
    PREY_HUNGER_THRESHOLD = 70      # H pour proies
    PREDATOR_REPRODUCTION_THRESHOLD = 120  # R pour prédateurs
    PREY_REPRODUCTION_THRESHOLD = 100      # R pour proies
    
    # Énergie
    PREDATOR_INITIAL_ENERGY = 100.0
    PREY_INITIAL_ENERGY = 95.0
    PREDATOR_ENERGY_DECAY = 0.5  # Perte par tick
    PREY_ENERGY_DECAY = 0.3
    PREDATOR_ENERGY_GAIN = 46.0    # Gain en mangeant une proie
    PREY_ENERGY_GAIN = 40.0        # Gain en mangeant de l'herbe
    
    # Reproduction
    PREDATOR_REPRODUCTION_COST = 60.0
    PREY_REPRODUCTION_COST = 50.0
    
    # Environnement
    GRASS_GROWTH_RATE = 2.0      # Herbe ajoutée par tick
    GRASS_MAX = 500              # Maximum d'herbe
    GRASS_DECREASE_RATE = 1.0
    
    # Sécheresse
    DROUGHT_PROBABILITY = 0.005  # Probabilité par tick
    DROUGHT_MIN_DURATION = 50    # Ticks minimum
    DROUGHT_MAX_DURATION = 150   # Ticks maximum
    
    # Communication
    SOCKET_HOST = 'localhost'
    SOCKET_PORT = 9999
    
    # Timing
    SIMULATION_TICK = 0.1        # Secondes entre chaque tick
    DISPLAY_UPDATE_INTERVAL = 1.0  # Secondes entre mises à jour display
    
    # Limites
    MAX_PREDATORS = 100
    MAX_PREYS = 200
    
    def __init__(self):
        """Initialisation avec possibilité de charger depuis fichier"""
        pass
    

