import os
import json
from datetime import datetime
import logging
import sys

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import db, app, PremiumKey
from data.keys_database import KeysDatabase

logger = logging.getLogger(__name__)

def sync_json_to_db():
    """Sync keys from JSON file to SQLite database"""
    try:
        # Load keys from JSON
        keys_db = KeysDatabase()
        json_keys = keys_db.keys
        
        logger.info(f"Loaded {len(json_keys)} keys from JSON file")
        
        # Initialize counter for new keys
        new_keys_count = 0
        
        # Add each key to the database if it doesn't exist
        with app.app_context():
            for key_id, key_data in json_keys.items():
                # Check if key exists
                existing_key = PremiumKey.query.filter_by(key=key_id).first()
                
                if not existing_key:
                    # Parse the expiry date
                    if isinstance(key_data.get('expiry_date'), str):
                        expiry_date = datetime.fromisoformat(key_data.get('expiry_date').replace('Z', '+00:00'))
                    else:
                        expiry_date = key_data.get('expiry_date')
                    
                    # Parse the created date
                    created_at = None
                    if key_data.get('created_at'):
                        if isinstance(key_data.get('created_at'), str):
                            created_at = datetime.fromisoformat(key_data.get('created_at').replace('Z', '+00:00'))
                        else:
                            created_at = key_data.get('created_at')
                    
                    # Create new key in database
                    new_key = PremiumKey(
                        key=key_id,
                        duration_seconds=key_data.get('duration_seconds', 0),
                        duration_str=key_data.get('duration_str', ''),
                        created_at=created_at or datetime.now(),
                        expiry_date=expiry_date,
                        user_id_created=key_data.get('user_id_created'),
                        user_id_redeemed=key_data.get('user_id_redeemed')
                    )
                    
                    db.session.add(new_key)
                    new_keys_count += 1
            
            if new_keys_count > 0:
                db.session.commit()
                logger.info(f"Added {new_keys_count} new keys to the database")
            else:
                logger.info("No new keys to add to the database")
                
        return new_keys_count
    except Exception as e:
        logger.error(f"Error syncing keys from JSON to database: {e}")
        return 0

def sync_db_to_json():
    """Sync keys from SQLite database to JSON file"""
    try:
        # Load keys from JSON
        keys_db = KeysDatabase()
        json_keys = keys_db.keys
        
        # Initialize counter for new/updated keys
        updates_count = 0
        
        # Get all keys from database
        with app.app_context():
            db_keys = PremiumKey.query.all()
            
            for db_key in db_keys:
                # Check if key exists in JSON
                if db_key.key not in json_keys:
                    # Add key to JSON
                    keys_db.add_key(
                        db_key.key,
                        db_key.duration_seconds,
                        db_key.expiry_date,
                        db_key.user_id_created,
                        db_key.user_id_redeemed
                    )
                    updates_count += 1
                else:
                    # Check if JSON key is outdated (redeemed status changed)
                    json_key = json_keys[db_key.key]
                    if json_key.get('user_id_redeemed') != db_key.user_id_redeemed:
                        # Update the redeemed status
                        json_keys[db_key.key]['user_id_redeemed'] = db_key.user_id_redeemed
                        updates_count += 1
        
        if updates_count > 0:
            # Save updated keys to JSON
            keys_db.save_keys()
            logger.info(f"Updated {updates_count} keys in JSON file")
        else:
            logger.info("No changes to save to JSON file")
            
        return updates_count
    except Exception as e:
        logger.error(f"Error syncing keys from database to JSON: {e}")
        return 0

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Sync keys in both directions
    logger.info("Starting key synchronization...")
    json_to_db_count = sync_json_to_db()
    db_to_json_count = sync_db_to_json()
    
    logger.info(f"Synchronization complete: {json_to_db_count} keys added to DB, {db_to_json_count} keys updated in JSON")