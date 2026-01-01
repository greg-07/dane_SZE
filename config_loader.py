"""
Centralny ładowacz konfiguracji dla systemu SZE.
Ładuje wszystkie pliki JSON z folderu config/ i udostępnia je reszcie systemu.
"""
import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Ścieżka do folderu z konfiguracją (względem lokalizacji tego pliku)
CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config')

# Globalny cache z załadowanymi konfiguracjami
_config_cache = {
    'energy_profiles': None,
    'cwu_schedule': None,
    'system_config': None,
    'user_corrections': None,
    'last_load_time': None
}

def _load_json_file(filename: str) -> Optional[Dict[str, Any]]:
    """Ładuje pojedynczy plik JSON i zwraca jako słownik."""
    filepath = os.path.join(CONFIG_DIR, filename)
    
    if not os.path.exists(filepath):
        logger.error(f"Plik konfiguracyjny nie istnieje: {filepath}")
        return None
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Załadowano konfigurację z: {filename}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Błąd parsowania JSON w pliku {filename}: {e}")
        return None
    except Exception as e:
        logger.error(f"Nieoczekiwany błąd przy ładowaniu {filename}: {e}")
        return None

def reload_all_configs() -> bool:
    """
    Przeładowuje wszystkie pliki konfiguracyjne z dysku.
    Zwraca True jeśli wszystkie pliki załadowano poprawnie.
    """
    logger.info("Przeładowywanie wszystkich konfiguracji...")
    
    global _config_cache
    
    # Próbuj załadować każdy plik
    energy_data = _load_json_file('energy_profiles.json')
    cwu_data = _load_json_file('cwu_schedule.json')
    system_data = _load_json_file('system_config.json')
    corrections_data = _load_json_file('user_corrections.json')
    
    # Sprawdź, które pliki załadowały się poprawnie
    success = True
    loaded_files = []
    
    if energy_data:
        _config_cache['energy_profiles'] = energy_data
        loaded_files.append('energy_profiles.json')
    else:
        success = False
        logger.warning("Nie udało się załadować energy_profiles.json")
    
    if cwu_data:
        _config_cache['cwu_schedule'] = cwu_data
        loaded_files.append('cwu_schedule.json')
    else:
        success = False
        logger.warning("Nie udało się załadować cwu_schedule.json")
    
    if system_data:
        _config_cache['system_config'] = system_data
        loaded_files.append('system_config.json')
    else:
        success = False
        logger.warning("Nie udało się załadować system_config.json")
    
    if corrections_data:
        _config_cache['user_corrections'] = corrections_data
        loaded_files.append('user_corrections.json')
    else:
        success = False
        logger.warning("Nie udało się załadować user_corrections.json")
    
    if loaded_files:
        _config_cache['last_load_time'] = datetime.now().isoformat()
        logger.info(f"Pomyślnie załadowano pliki: {', '.join(loaded_files)}")
    
    return success

def get_energy_profiles(day_type: str = None) -> Optional[Dict[str, Any]]:
    """
    Zwraca profile energetyczne.
    Jeśli podano day_type ('dzien_roboczy', 'sobota', 'niedziela_swieto'),
    zwraca tylko profil dla tego dnia.
    """
    if not _config_cache['energy_profiles']:
        reload_all_configs()
    
    data = _config_cache['energy_profiles']
    if not data:
        return None
    
    if day_type:
        # Zwróć konkretny profil dnia
        profiles = data.get('energy_profiles', {})
        return profiles.get(day_type)
    else:
        # Zwróć wszystkie profile
        return data

def get_cwu_schedule() -> Optional[Dict[str, Any]]:
    """Zwraca harmonogram CWU."""
    if not _config_cache['cwu_schedule']:
        reload_all_configs()
    
    return _config_cache['cwu_schedule']

def get_system_config() -> Optional[Dict[str, Any]]:
    """Zwraca konfigurację systemu (hardware, API, PV, kalendarz, taryfa)."""
    if not _config_cache['system_config']:
        reload_all_configs()
    
    return _config_cache['system_config']

def get_user_corrections() -> Optional[Dict[str, Any]]:
    """Zwraca korekty użytkownika i straty systemowe."""
    if not _config_cache['user_corrections']:
        reload_all_configs()
    
    return _config_cache['user_corrections']

def get_config_status() -> Dict[str, Any]:
    """Zwraca status wszystkich konfiguracji (przydatne do logowania/dashboardu)."""
    status = {
        'last_load_time': _config_cache['last_load_time'],
        'files_loaded': {
            'energy_profiles': _config_cache['energy_profiles'] is not None,
            'cwu_schedule': _config_cache['cwu_schedule'] is not None,
            'system_config': _config_cache['system_config'] is not None,
            'user_corrections': _config_cache['user_corrections'] is not None,
        }
    }
    return status

# Inicjalne ładowanie konfiguracji przy imporcie modułu
if __name__ != "__main__":
    logger.info("Inicjalizacja ładowacza konfiguracji SZE...")
    reload_all_configs()
