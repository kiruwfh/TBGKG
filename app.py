import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///premium_keys.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Custom Jinja2 template context
@app.context_processor
def inject_now():
    """Inject the current year into the template context"""
    return {'current_year': datetime.now().year}

# Define models
class PremiumKey(db.Model):
    __tablename__ = 'premium_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(36), unique=True, nullable=False)
    duration_seconds = db.Column(db.Integer, nullable=False)
    duration_str = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    expiry_date = db.Column(db.DateTime, nullable=False)
    user_id_created = db.Column(db.BigInteger, nullable=True)
    user_id_redeemed = db.Column(db.BigInteger, nullable=True)
    
    def is_redeemed(self):
        return self.user_id_redeemed is not None
    
    def is_expired(self):
        return datetime.now() > self.expiry_date
    
    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'duration_seconds': self.duration_seconds,
            'duration_str': self.duration_str,
            'created_at': self.created_at.isoformat(),
            'expiry_date': self.expiry_date.isoformat(),
            'user_id_created': self.user_id_created,
            'user_id_redeemed': self.user_id_redeemed,
            'is_redeemed': self.is_redeemed(),
            'is_expired': self.is_expired(),
        }

# Import utility functions
from utils.time_utils import format_timestamp, format_duration

# Routes
@app.route('/')
def index():
    return render_template('index.html', title="Premium Key Manager")

@app.route('/api/keys', methods=['GET'])
def get_keys():
    try:
        # First sync from JSON to database to ensure we have the latest data
        try:
            from utils.sync_keys import sync_json_to_db
            sync_json_to_db()
        except Exception as e:
            logger.error(f"Error syncing keys from JSON to database: {e}")
            
        keys = PremiumKey.query.all()
        return jsonify({
            'success': True,
            'keys': [key.to_dict() for key in keys]
        })
    except Exception as e:
        logger.error(f"Error fetching keys: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/keys/<key_id>', methods=['GET'])
def get_key(key_id):
    try:
        key = PremiumKey.query.filter_by(key=key_id).first()
        if not key:
            return jsonify({
                'success': False,
                'error': 'Key not found'
            }), 404
        
        return jsonify({
            'success': True,
            'key': key.to_dict()
        })
    except Exception as e:
        logger.error(f"Error fetching key: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', title="Premium Key Dashboard")

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        total_keys = PremiumKey.query.count()
        active_keys = PremiumKey.query.filter(PremiumKey.expiry_date > datetime.now()).count()
        redeemed_keys = PremiumKey.query.filter(PremiumKey.user_id_redeemed != None).count()
        expired_keys = PremiumKey.query.filter(PremiumKey.expiry_date < datetime.now()).count()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_keys': total_keys,
                'active_keys': active_keys,
                'redeemed_keys': redeemed_keys,
                'expired_keys': expired_keys,
            }
        })
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Create tables if they don't exist
with app.app_context():
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.warning(f"Tables may already exist: {e}")
        pass

# Import and run key synchronization
try:
    from utils.sync_keys import sync_json_to_db
    with app.app_context():
        sync_json_to_db()
except Exception as e:
    logger.error(f"Error syncing keys from JSON to database: {e}")

# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)