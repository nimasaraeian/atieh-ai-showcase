"""Configuration settings for Atieh scheduling engine."""
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import logging

logger = logging.getLogger(__name__)


class Config:
    """Application configuration."""
    
    # Base paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    INPUT_DIR = DATA_DIR / "inputs"
    OUTPUT_DIR = DATA_DIR / "outputs"
    
    # CSV catalog paths
    DOCTOR_SHIFTS_CSV = OUTPUT_DIR / "doctor_shifts.csv"
    SERVICES_CATALOG_CSV = OUTPUT_DIR / "services_catalog.csv"
    UNFINISHED_TREATMENTS_CSV = OUTPUT_DIR / "unfinished_treatments.csv"
    INSURANCE_PRIORITY_CSV = OUTPUT_DIR / "insurance_priority.csv"
    
    # Output paths
    SLOT_RECOMMENDATIONS_CSV = OUTPUT_DIR / "slot_recommendations.csv"
    SCHEDULE_DRAFT_CSV = OUTPUT_DIR / "schedule_draft.csv"
    
    # Time blocks configuration
    SLOT_MINUTES = 30
    SHIFT_D_START = "08:00"
    SHIFT_D_END = "14:00"
    SHIFT_E_START = "14:00"
    SHIFT_E_END = "20:00"
    SHIFT_N_START = "20:00"
    SHIFT_N_END = "24:00"
    
    # Scoring weights (must mirror app.engine.scoring)
    WEIGHT_URGENCY = 0.30
    WEIGHT_FINANCIAL = 0.25
    WEIGHT_AVAILABILITY = 0.20
    WEIGHT_COMPLEXITY_FIT = 0.15
    
    # Recommendation limits
    TOP_RECOMMENDATIONS = 10
    
    # CRM configuration
    CRM_BASE_URL: Optional[str] = None
    CRM_API_KEY: Optional[str] = None
    CRM_TIMEOUT_SECONDS = 30
    USE_MOCK_CRM = True  # Set to False when real CRM is ready
    
    # Decision Engine version (v1 or v2)
    # v1: Traditional slot-centric scoring
    # v2: Value-based scheduling (Patient TVS + Slot Fit)
    ENGINE_VERSION = "v1"  # Set to "v2" to enable value-based scheduling
    
    # Preferred Doctor Matching Mode
    # Controls how preferred doctor requests are handled
    # - "boost": Boosts matching slots (+0.15) but always returns recommendations
    # - "strict": Returns only matching slots (falls back if none found with warning)
    PREFERRED_DOCTOR_MODE = "boost"  # Recommended: "boost" for best user experience
    
    @classmethod
    def ensure_output_dir(cls):
        """Ensure output directory exists."""
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class WeightsConfig:
    """AI Weights Configuration loaded from YAML."""
    
    DEFAULT_WEIGHTS = {
        'weights': {
            'payment': 0.40,
            'treatment': 0.35,
            'lifetime': 0.25
        },
        'penalties': {
            'no_show': 25,
            'late_payment': 20
        },
        'boosts': {
            'high_value': 10
        },
        'confidence': {
            'high': 0.80,
            'medium': 0.60,
            'low': 0.40
        },
        'risk_thresholds': {
            'no_show': {
                'high': 0.30,
                'medium': 0.15,
                'low': 0.05
            },
            'late_payment': {
                'high': 0.25,
                'medium': 0.10,
                'low': 0.03
            }
        },
        'value_thresholds': {
            'high': 80,
            'medium': 50,
            'low': 30
        },
        'slot_recommendation': {
            'max_suggestions': 5,
            'min_suggestions': 3,
            'prefer_morning': True,
            'prefer_afternoon': False,
            'avoid_lunch_hours': True,
            'lunch_start': '13:00',
            'lunch_end': '14:00'
        },
        'scheduling': {
            'min_slot_duration': 15,
            'max_slot_duration': 240,
            'default_slot_duration': 30,
            'buffer_between_appointments': 5
        },
        'time_preferences': {
            'morning': 1.0,
            'afternoon': 0.8,
            'evening': 0.6
        },
        'urgency_weights': {
            'critical': 1.0,
            'high': 0.8,
            'medium': 0.5,
            'low': 0.3
        },
        'payment_weights': {
            'cash': 1.0,
            'insurance_tier_1': 0.9,
            'insurance_tier_2': 0.7,
            'insurance_tier_3': 0.4
        },
        'tvs': {
            'alpha': 0.55,
            'beta': 0.35,
            'gamma': 0.25,
            'epsilon': 0.20,
            'delta': 0.10
        },
        'final': {
            'patient_weight': 0.70,
            'slot_weight': 0.30
        }
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize weights configuration.
        
        Args:
            config_path: Path to weights.yaml file. If None, uses default location.
        """
        self._config_path = config_path or (Config.BASE_DIR / "config" / "weights.yaml")
        self._config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self):
        """Load configuration from YAML file with fallback to defaults."""
        try:
            if self._config_path.exists():
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f"Loaded weights configuration from {self._config_path}")
            else:
                logger.warning(
                    f"Weights file not found at {self._config_path}, using defaults"
                )
                self._config = {}
        except Exception as e:
            logger.error(f"Error loading weights configuration: {e}, using defaults")
            self._config = {}
    
    def get_weights(self) -> Dict[str, float]:
        """Get scoring weights (payment, treatment, lifetime)."""
        return self._config.get('weights', self.DEFAULT_WEIGHTS['weights'])
    
    def get_penalties(self) -> Dict[str, float]:
        """Get risk penalties (no_show, late_payment)."""
        return self._config.get('penalties', self.DEFAULT_WEIGHTS['penalties'])
    
    def get_boosts(self) -> Dict[str, float]:
        """Get value boosts (high_value)."""
        return self._config.get('boosts', self.DEFAULT_WEIGHTS['boosts'])
    
    def get_confidence_thresholds(self) -> Dict[str, float]:
        """Get confidence thresholds."""
        return self._config.get('confidence', self.DEFAULT_WEIGHTS['confidence'])
    
    def get_risk_thresholds(self) -> Dict[str, Dict[str, float]]:
        """Get risk thresholds."""
        return self._config.get('risk_thresholds', self.DEFAULT_WEIGHTS['risk_thresholds'])
    
    def get_value_thresholds(self) -> Dict[str, int]:
        """Get value score thresholds."""
        return self._config.get('value_thresholds', self.DEFAULT_WEIGHTS['value_thresholds'])
    
    def get_slot_recommendation_config(self) -> Dict[str, Any]:
        """Get slot recommendation settings."""
        return self._config.get('slot_recommendation', self.DEFAULT_WEIGHTS['slot_recommendation'])
    
    def get_scheduling_config(self) -> Dict[str, int]:
        """Get scheduling constraints."""
        return self._config.get('scheduling', self.DEFAULT_WEIGHTS['scheduling'])
    
    def get_time_preferences(self) -> Dict[str, float]:
        """Get time of day preferences."""
        return self._config.get('time_preferences', self.DEFAULT_WEIGHTS['time_preferences'])
    
    def get_urgency_weights(self) -> Dict[str, float]:
        """Get urgency level weights."""
        return self._config.get('urgency_weights', self.DEFAULT_WEIGHTS['urgency_weights'])
    
    def get_payment_weights(self) -> Dict[str, float]:
        """Get payment type weights."""
        return self._config.get('payment_weights', self.DEFAULT_WEIGHTS['payment_weights'])
    
    def get_tvs_weights(self) -> Dict[str, float]:
        """Get TVS (v2) component weights."""
        return self._config.get('tvs', self.DEFAULT_WEIGHTS['tvs'])
    
    def get_final_weights(self) -> Dict[str, float]:
        """Get final score (v2) combination weights."""
        return self._config.get('final', self.DEFAULT_WEIGHTS['final'])
    
    def get_v2_weights(self) -> Dict[str, Dict[str, float]]:
        """Get all v2 weights (tvs + final)."""
        return {
            'tvs': self.get_tvs_weights(),
            'final': self.get_final_weights()
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get any configuration value by key."""
        return self._config.get(key, self.DEFAULT_WEIGHTS.get(key, default))
    
    def reload(self):
        """Reload configuration from file."""
        self._load_config()


# Default configuration instances
config = Config()
weights_config = WeightsConfig()
