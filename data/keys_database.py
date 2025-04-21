import logging
from datetime import datetime
import json
import os

from utils.time_utils import get_duration_str, format_duration

logger = logging.getLogger(__name__)

class KeysDatabase:
    """A class to manage premium keys in memory."""
    
    def __init__(self):
        """Initialize the keys database."""
        self.keys = {}
        self.load_keys()
    
    def load_keys(self):
        """Load keys from a JSON file if it exists."""
        try:
            if os.path.exists('premium_keys.json'):
                with open('premium_keys.json', 'r') as f:
                    keys_data = json.load(f)
                    
                    # Convert string dates back to datetime objects
                    for key, data in keys_data.items():
                        if 'expiry_date' in data:
                            try:
                                data['expiry_date'] = datetime.fromisoformat(data['expiry_date'])
                            except ValueError:
                                # If date can't be parsed, set to a past date
                                data['expiry_date'] = datetime(2000, 1, 1)
                    
                    self.keys = keys_data
                    logger.info(f"Loaded {len(self.keys)} keys from file")
        except Exception as e:
            logger.error(f"Error loading keys: {e}")
            self.keys = {}
    
    def save_keys(self):
        """Save keys to a JSON file."""
        try:
            # Convert datetime objects to ISO format strings for JSON serialization
            keys_copy = {}
            for key, data in self.keys.items():
                keys_copy[key] = data.copy()
                
                # Convert all datetime objects to ISO format strings
                if 'expiry_date' in keys_copy[key] and isinstance(keys_copy[key]['expiry_date'], datetime):
                    keys_copy[key]['expiry_date'] = keys_copy[key]['expiry_date'].isoformat()
                
                if 'created_at' in keys_copy[key] and isinstance(keys_copy[key]['created_at'], datetime):
                    keys_copy[key]['created_at'] = keys_copy[key]['created_at'].isoformat()
            
            with open('premium_keys.json', 'w') as f:
                json.dump(keys_copy, f, indent=2)
                
            logger.info(f"Saved {len(self.keys)} keys to file")
        except Exception as e:
            logger.error(f"Error saving keys: {e}")
    
    def add_key(self, key, duration_seconds, expiry_date, user_id_created, user_id_redeemed=None):
        """Add a new key to the database."""
        duration_str = get_duration_str(duration_seconds)
        
        # Store datetime objects as strings for JSON serialization
        created_at = datetime.now()
        
        self.keys[key] = {
            'key': key,
            'duration_seconds': duration_seconds,
            'duration_str': duration_str,
            'expiry_date': expiry_date,
            'user_id_created': user_id_created,
            'user_id_redeemed': user_id_redeemed,
            'created_at': created_at
        }
        
        # Save keys to storage
        self.save_keys()
        logger.info(f"Added new key: {key} (duration: {duration_str})")
        return self.keys[key]
    
    def get_key(self, key):
        """Get a key from the database."""
        return self.keys.get(key)
        
    def get_keys_for_user(self, user_id):
        """Get all keys redeemed by a specific user."""
        user_keys = []
        for key, data in self.keys.items():
            if data.get('user_id_redeemed') == user_id:
                user_keys.append(data)
        return user_keys
    
    def has_active_keys(self, user_id):
        """Check if a user has any active (non-expired) keys."""
        now = datetime.now()
        user_keys = self.get_keys_for_user(user_id)
        
        for key_data in user_keys:
            expiry_date = key_data.get('expiry_date')
            if expiry_date and expiry_date > now:
                return True
        
        return False
    
    def update_key_redeemed(self, key, user_id_redeemed):
        """Update a key with the user who redeemed it."""
        if key in self.keys:
            self.keys[key]['user_id_redeemed'] = user_id_redeemed
            self.save_keys()
            logger.info(f"Key {key} redeemed by user {user_id_redeemed}")
            return True
        return False
    
    def update_key_duration(self, key, duration_seconds, new_expiry_date):
        """Update a key's duration and expiry date."""
        if key in self.keys:
            self.keys[key]['duration_seconds'] = duration_seconds
            self.keys[key]['duration_str'] = get_duration_str(duration_seconds)
            self.keys[key]['expiry_date'] = new_expiry_date
            self.save_keys()
            logger.info(f"Updated key {key} duration to {get_duration_str(duration_seconds)}")
            return True
        return False
    
    def delete_key(self, key):
        """Delete a key from the database."""
        if key in self.keys:
            del self.keys[key]
            self.save_keys()
            logger.info(f"Deleted key: {key}")
            return True
        return False
    
    def get_active_keys(self):
        """Get all active (non-expired) keys."""
        now = datetime.now()
        active_keys = []
        
        for key, data in self.keys.items():
            # Убедимся, что expiry_date - это объект datetime для корректного сравнения
            expiry_date = data['expiry_date']
            if isinstance(expiry_date, str):
                try:
                    expiry_date = datetime.fromisoformat(expiry_date)
                except ValueError:
                    continue
            
            if expiry_date > now:
                # Создаем копию данных для безопасного возврата
                key_data = data.copy()
                # Убедимся, что expiry_date - это объект datetime
                if isinstance(key_data['expiry_date'], str):
                    key_data['expiry_date'] = expiry_date
                active_keys.append(key_data)
        
        return active_keys
    
    def get_expired_keys(self):
        """Get all expired keys."""
        now = datetime.now()
        expired_keys = []
        
        for key, data in self.keys.items():
            # Убедимся, что expiry_date - это объект datetime для корректного сравнения
            expiry_date = data['expiry_date']
            if isinstance(expiry_date, str):
                try:
                    expiry_date = datetime.fromisoformat(expiry_date)
                except ValueError:
                    continue
            
            if expiry_date <= now and data.get('user_id_redeemed'):
                # Создаем копию данных для безопасного возврата
                key_data = data.copy()
                # Убедимся, что expiry_date - это объект datetime
                if isinstance(key_data['expiry_date'], str):
                    key_data['expiry_date'] = expiry_date
                expired_keys.append(key_data)
        
        return expired_keys
    
    def cleanup_expired_keys(self):
        """Remove expired keys that have been redeemed."""
        now = datetime.now()
        expired_keys = []
        
        for key in list(self.keys.keys()):
            data = self.keys[key]
            # Убедимся, что expiry_date - это объект datetime для корректного сравнения
            expiry_date = data['expiry_date']
            if isinstance(expiry_date, str):
                try:
                    expiry_date = datetime.fromisoformat(expiry_date)
                except ValueError:
                    continue
                    
            # Keep keys that haven't expired or haven't been redeemed
            if expiry_date <= now and data.get('user_id_redeemed'):
                expired_keys.append(key)
        
        # Don't actually delete expired keys, just track them for reporting
        logger.info(f"Found {len(expired_keys)} expired keys")
        return expired_keys
