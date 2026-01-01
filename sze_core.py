"""
Główna logika Systemu Zarządzania Energią - WERSJA Z CONFIG_LOADER
"""
import logging
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
import json

# UWAGA: Import z config.py, który znajduje się w głównym folderze (sze_system/)
#from config import config
# Import naszego nowego ładowacza konfiguracji
from core.config_loader import (
    get_energy_profiles,
    get_cwu_schedule,
    get_system_config,
    get_user_corrections,
    get_config_status
)

logger = logging.getLogger(__name__)

class SystemManager:
    """Główny manager systemu SZE - działający na plikach JSON zamiast Excela"""

    def __init__(self):
        self.system_status = {}
        self.config_data = {}  # Będzie przechowywać wszystkie dane z config_loader
        self.last_update = None

        # Inicjalizacja - ładujemy dane z plików JSON
        self._load_config_data()
        self._update_system_status()
        self.cwu_boiler_enabled = True
        self.heaters_locked = True
        logger.info("System SZE (wersja JSON) zainicjalizowany")

    def _load_config_data(self):
        """Ładuje wszystkie dane z plików konfiguracyjnych JSON"""
        try:
            self.config_data = {
                'energy_profiles': get_energy_profiles(),
                'cwu_schedule': get_cwu_schedule(),
                'system_config': get_system_config(),
                'user_corrections': get_user_corrections(),
                'config_status': get_config_status()
            }
            
            # Logowanie informacji o załadowanych danych
            energy_profiles = self.config_data.get('energy_profiles', {})
            if energy_profiles:
                profiles = energy_profiles.get('energy_profiles', {})
                logger.info(f"Załadowano profile energetyczne dla: {list(profiles.keys())}")
            
        except Exception as e:
            logger.error(f"Błąd ładowania danych konfiguracyjnych: {e}")
            self.config_data = {}

    def _update_system_status(self):
        """Aktualizuje status systemu na podstawie konfiguracji i czasu"""
        now = datetime.now()
        
        # Pobierz konfigurację systemu dla pól takich jak cwz_z_kotla
        system_config = self.config_data.get('system_config', {})
        boiler_config = system_config.get('boiler', {}) if system_config else {}
        default_power = boiler_config.get('default_total_power', {}) if boiler_config else {}

        self.system_status = {
            'timestamp': now.isoformat(),
            'data_str': now.strftime("%A %d %B %Y").replace("Monday", "poniedziałek")
                                                   .replace("Tuesday", "wtorek")
                                                   .replace("Wednesday", "środa")
                                                   .replace("Thursday", "czwartek")
                                                   .replace("Friday", "piątek")
                                                   .replace("Saturday", "sobota")
                                                   .replace("Sunday", "niedziela"),
            'godzina': now.strftime("%H:%M:%S"),
            'rodzaj_dnia': self._get_day_type(now),
            'okno_dobowe': self._get_current_window(now),
            'taryfa': self._get_current_tariff(now),
            # Pobierz stan z głównej konfiguracji (config.py), nie z JSON jednak z JSON
            'cwz_z_kotla': 'WŁ',  # Tymczasowo zawsze WŁ
            'grzalki_zablokowane': 'TAK',  # Tymczasowo zawsze TAK
            'system_active': True,
            'last_update': now.strftime("%H:%M:%S"),
            # Informacje o załadowanych danych JSON
            'config_loaded': bool(self.config_data.get('energy_profiles')),
            'profiles_available': list(self.config_data.get('energy_profiles', {}).get('energy_profiles', {}).keys()) if self.config_data.get('energy_profiles') else [],
            # Informacje o mocy grzałek z konfiguracji JSON
            'boiler_morning_power_w': default_power.get('morning_watts', 0),
            'boiler_evening_power_w': default_power.get('evening_watts', 0)
        }

        self.last_update = now

    def _get_day_type(self, dt: datetime) -> str:
        """Określa rodzaj dnia z uwzględnieniem świąt z konfiguracji"""
        # Najpierw sprawdź święta
        system_config = self.config_data.get('system_config', {})
        calendar_config = system_config.get('calendar', {}) if system_config else {}
        
        fixed_holidays = calendar_config.get('fixed_holidays', [])
        movable_holidays = calendar_config.get('movable_holidays', [])
        
        # Sprawdź czy dzisiejsza data jest świętem
        today_str = dt.strftime("%m-%d")  # Format MM-DD dla świąt stałych
        today_full = dt.strftime("%Y-%m-%d")  # Format RRRR-MM-DD dla ruchomych
        
        if today_str in fixed_holidays or today_full in movable_holidays:
            return "niedziela/święto"  # Święta traktujemy jak niedziele
        
        # Jeśli nie święto, sprawdź dzień tygodnia
        if dt.weekday() < 5:  # 0-4 = poniedziałek-piątek
            return "roboczy"
        elif dt.weekday() == 5:  # sobota
            return "sobota"
        else:  # niedziela
            return "niedziela/święto"

        def _get_current_window(self, dt: datetime) -> str:
            """Określa aktualne okno dobowe na podstawie wschodu/zachodu"""
            # Pobierz współrzędne z konfiguracji
            system_config = get_system_config() or {}
            pv_config = system_config.get('pv_installation', {})
            
            # Współrzędne (domyślnie z JSON, fallback na Twoje)
            coords = pv_config.get('coordinates', '51.290050, 22.818633')
            try:
                lat_str, lon_str = coords.split(',')
                lat = float(lat_str.strip())
                lon = float(lon_str.strip())
            except:
                lat, lon = 51.29, 22.82
            
            # Import tutaj aby uniknąć cyklicznych importów
            from .daily_windows import get_current_window
            return get_current_window(latitude=lat, longitude=lon, current_time=dt)

        def _get_current_tariff(self, dt: datetime) -> str:
            """Określa aktualną taryfę na podstawie konfiguracji JSON"""
            hour = dt.hour
            day_type = self._get_day_type(dt)
        
        # Jeśli święto lub niedziela - cała doba tańsza
        if day_type == "niedziela/święto":
            return "tańsza"
        
        # Pobierz konfigurację taryfy z JSON
        system_config = self.config_data.get('system_config', {})
        tariff_config = system_config.get('tariff_g12w', {}) if system_config else {}
        
        # Tańsza taryfa nocna (zawsze obowiązuje)
        cheaper_night = tariff_config.get('cheaper_night_hours', '22:00-06:00')
        if cheaper_night:
            try:
                start_hour = int(cheaper_night.split('-')[0].split(':')[0])
                end_hour = int(cheaper_night.split('-')[1].split(':')[0])
                
                # Obsługa przedziału przechodzącego przez północ (22:00-06:00)
                if start_hour > end_hour:  # np. 22-06
                    if hour >= start_hour or hour < end_hour:
                        return "tańsza"
                else:  # np. 13-15
                    if start_hour <= hour < end_hour:
                        return "tańsza"
            except (ValueError, IndexError):
                logger.warning(f"Błędny format taryfy nocnej: {cheaper_night}")
        
        # Domyślnie droższa
        return "droższa"

    def refresh_data(self):
        """Odświeża dane systemu"""
        self._load_config_data()  # Przeładuj dane z plików
        self._update_system_status()
        logger.debug("Dane systemu odświeżone")

    def get_system_info(self) -> Dict[str, Any]:
        """Zwraca informacje o systemie"""
        return self.system_status

    def get_config_data(self) -> Dict[str, Any]:
        """Zwraca wszystkie dane konfiguracyjne (dla API)"""
        return self.config_data

    def calculate_balance(self, window_type: str) -> Dict[str, Any]:
        """Oblicza bilans dla danego okna (SZKIELET - do implementacji)"""
        # TODO: Pełna implementacja z użyciem energy_profiles i user_corrections
        profiles = self.config_data.get('energy_profiles', {})
        corrections = self.config_data.get('user_corrections', {})
        
        return {
            'okno': window_type,
            'bilans_kwh': 0.0,
            'szacowana_produkcja_pv': 0.0,
            'potrzebna_energia': 0.0,
            'czas_obliczenia': datetime.now().isoformat(),
            'status': 'szkiet funkcji - do implementacji',
            'zauwazenie': 'Funkcja używa teraz danych z config_loader, a nie z Excela.'
        }

    def toggle_cwu_boiler(self, enabled: bool):
        """Przełącza ogrzewanie CWU z kotła"""
        self.cwu_boiler_enabled = enabled  # Albo self.config['cwu_enabled'] = enabled
        if enabled:
            self.heaters_locked = True
            logger.info("CWU z kotła: WŁĄCZONE (grzałki zablokowane)")
        else:
            logger.warning("CWU z kotła: WYŁĄCZONE (uważaj na grzałki!)")

        self._update_system_status()
        return {'status': 'success', 'cwz_z_kotla': 'WŁ' if enabled else 'WYŁ'}

# Globalna instancja systemu
system_manager = SystemManager()
