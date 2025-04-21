import uuid
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def generate_unique_key():
    """Generate a unique UUID for premium keys."""
    return str(uuid.uuid4())

def is_key_valid(key, keys_database):
    """Check if a key is valid (exists and not expired)."""
    key_data = keys_database.get_key(key)
    
    if not key_data:
        logger.debug(f"Key validation failed: Key {key} not found in database")
        return False, "Invalid key"
    
    # Check if key is expired
    if datetime.now() > key_data.get('expiry_date'):
        logger.debug(f"Key validation failed: Key {key} has expired")
        return False, "Key has expired"
    
    # Check if key is already redeemed
    if key_data.get('user_id_redeemed'):
        logger.debug(f"Key validation failed: Key {key} already redeemed by user {key_data.get('user_id_redeemed')}")
        return False, "Key already redeemed"
    
    return True, key_data
