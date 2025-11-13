"""
Firebase Cloud Function for Text Categorization System
Production-ready with logging, error handling, validation, and monitoring
"""

import json
import logging
import time
from datetime import datetime
from typing import Dict, Any, Tuple, Optional

from firebase_functions import https_fn, options
from firebase_admin import initialize_app, firestore, storage
import joblib
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firebase Admin
try:
    initialize_app()
    logger.info("Firebase Admin initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firebase Admin: {e}")

# Global variables for model caching
_model = None
_vectorizer = None
_model_loaded = False

# Configuration
CONFIG = {
    'max_text_length': 5000,
    'min_text_length': 3,
    'model_bucket': 'text-cat-feedback.appspot.com',
    'model_path': 'models/textcat_model.pkl',
    'vectorizer_path': 'models/tfidf_vectorizer.pkl',
    'rate_limit_per_minute': 60,
    'cors_origins': ['*'],  # Update with your domain in production
}

# Category metadata for enriched responses
CATEGORY_METADATA = {
    'Bug Report': {
        'icon': '🐛',
        'color': '#e74c3c',
        'priority': 'high',
        'description': 'Technical issues or system errors'
    },
    'Feature Request': {
        'icon': '💡',
        'color': '#9b59b6',
        'priority': 'medium',
        'description': 'Suggestions for new functionality'
    },
    'Pricing Complaint': {
        'icon': '💰',
        'color': '#e67e22',
        'priority': 'high',
        'description': 'Cost or billing concerns'
    },
    'Positive Feedback': {
        'icon': '✅',
        'color': '#27ae60',
        'priority': 'low',
        'description': 'Satisfied customer experiences'
    },
    'Negative Experience': {
        'icon': '😞',
        'color': '#c0392b',
        'priority': 'high',
        'description': 'Poor service or usability issues'
    }
}


def load_models_from_storage() -> Tuple[Any, Any]:
    """
    Load ML models from Cloud Storage with caching
    
    Returns:
        Tuple of (model, vectorizer)
    
    Raises:
        Exception: If models cannot be loaded
    """
    global _model, _vectorizer, _model_loaded
    
    if _model_loaded and _model is not None and _vectorizer is not None:
        logger.info("Using cached models")
        return _model, _vectorizer
    
    try:
        logger.info("Loading models from Cloud Storage...")
        bucket = storage.bucket(CONFIG['model_bucket'])
        
        # Load model
        model_blob = bucket.blob(CONFIG['model_path'])
        model_bytes = model_blob.download_as_bytes()
        _model = joblib.loads(model_bytes)
        
        # Load vectorizer
        vectorizer_blob = bucket.blob(CONFIG['vectorizer_path'])
        vectorizer_bytes = vectorizer_blob.download_as_bytes()
        _vectorizer = joblib.loads(vectorizer_bytes)
        
        _model_loaded = True
        logger.info("Models loaded successfully")
        
        return _model, _vectorizer
        
    except Exception as e:
        logger.error(f"Failed to load models from storage: {e}")
        raise Exception(f"Model loading failed: {str(e)}")


def validate_input(data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate incoming request data
    
    Args:
        data: Request JSON data
        
    Returns:
        Tuple of (is_valid, error_message, feedback_text)
    """
    if not data:
        return False, "Request body is empty or invalid JSON", None
    
    # Accept either 'text' or 'feedback' field
    feedback_text = data.get('feedback') or data.get('text')
    
    if not feedback_text:
        return False, "Missing 'feedback' or 'text' field in request body", None
    
    if not isinstance(feedback_text, str):
        return False, "'feedback' must be a string", None
    
    feedback_text = feedback_text.strip()
    
    if len(feedback_text) < CONFIG['min_text_length']:
        return False, f"Text too short (minimum {CONFIG['min_text_length']} characters)", None
    
    if len(feedback_text) > CONFIG['max_text_length']:
        return False, f"Text too long (maximum {CONFIG['max_text_length']} characters)", None
    
    return True, None, feedback_text


def sanitize_text(text: str) -> str:
    """
    Sanitize input text for security and processing
    
    Args:
        text: Raw input text
        
    Returns:
        Sanitized text
    """
    # Remove null bytes and control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # Trim whitespace
    text = text.strip()
    
    return text


def make_prediction(model: Any, vectorizer: Any, text: str) -> Dict[str, Any]:
    """
    Make prediction using ML model
    
    Args:
        model: Trained classifier
        vectorizer: TF-IDF vectorizer
        text: Input text to classify
        
    Returns:
        Dict containing prediction results
    """
    try:
        # Transform text to TF-IDF features
        X = vectorizer.transform([text])
        
        # Make prediction
        prediction = model.predict(X)[0]
        
        # Get confidence scores
        confidence = None
        all_probabilities = None
        
        try:
            probabilities = model.predict_proba(X)[0]
            max_prob = float(np.max(probabilities))
            confidence = round(max_prob * 100, 2)
            
            # Get all class probabilities for transparency
            all_probabilities = {
                category: round(float(prob) * 100, 2)
                for category, prob in zip(model.classes_, probabilities)
            }
        except AttributeError:
            logger.warning("Model does not support predict_proba")
        
        # Enrich prediction with metadata
        category_info = CATEGORY_METADATA.get(prediction, {})
        
        result = {
            'prediction': prediction,
            'confidence': confidence,
            'all_probabilities': all_probabilities,
            'metadata': category_info,
            'text_length': len(text),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise Exception(f"Prediction failed: {str(e)}")


def save_to_firestore(db, text: str, prediction_result: Dict[str, Any], 
                      processing_time_ms: float) -> Optional[str]:
    """
    Save prediction result to Firestore
    
    Args:
        db: Firestore client
        text: Input text
        prediction_result: Prediction results
        processing_time_ms: Time taken for prediction
        
    Returns:
        Document ID if successful, None otherwise
    """
    try:
        doc_data = {
            'text': text,
            'category': prediction_result['prediction'],
            'confidence': prediction_result.get('confidence'),
            'all_probabilities': prediction_result.get('all_probabilities'),
            'metadata': prediction_result.get('metadata'),
            'text_length': prediction_result.get('text_length'),
            'processing_time_ms': processing_time_ms,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'version': '1.0'
        }
        
        doc_ref = db.collection('predictions').add(doc_data)
        doc_id = doc_ref[1].id
        logger.info(f"Saved to Firestore with ID: {doc_id}")
        
        return doc_id
        
    except Exception as e:
        logger.error(f"Firestore save error: {e}")
        # Don't fail the request if Firestore save fails
        return None


@https_fn.on_request(
    cors=options.CorsOptions(
        cors_origins=CONFIG['cors_origins'],
        cors_methods=["GET", "POST", "OPTIONS"],
    ),
    memory=options.MemoryOption.MB_512,
    timeout_sec=60,
    max_instances=10
)
def predict(req: https_fn.Request) -> https_fn.Response:
    """
    Cloud Function endpoint for text categorization
    
    Handles POST requests with JSON body: {"feedback": "text to classify"}
    
    Returns:
        JSON response with prediction results
    """
    start_time = time.time()
    
    try:
        # Log request
        logger.info(f"Received {req.method} request from {req.headers.get('origin', 'unknown')}")
        
        # Handle preflight OPTIONS request
        if req.method == 'OPTIONS':
            return https_fn.Response(
                status=204,
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Max-Age': '3600'
                }
            )
        
        # Only allow POST for predictions
        if req.method != 'POST':
            return https_fn.Response(
                json.dumps({
                    'error': 'Method not allowed',
                    'allowed_methods': ['POST']
                }),
                status=405,
                headers={'Content-Type': 'application/json'}
            )
        
        # Parse request data
        try:
            data = req.get_json(silent=True)
        except Exception as e:
            logger.error(f"JSON parse error: {e}")
            return https_fn.Response(
                json.dumps({'error': 'Invalid JSON in request body'}),
                status=400,
                headers={'Content-Type': 'application/json'}
            )
        
        # Validate input
        is_valid, error_msg, feedback_text = validate_input(data)
        if not is_valid:
            logger.warning(f"Validation error: {error_msg}")
            return https_fn.Response(
                json.dumps({'error': error_msg}),
                status=400,
                headers={'Content-Type': 'application/json'}
            )
        
        # Sanitize input
        feedback_text = sanitize_text(feedback_text)
        
        # Load models (cached after first load)
        try:
            model, vectorizer = load_models_from_storage()
        except Exception as e:
            logger.error(f"Model loading failed: {e}")
            return https_fn.Response(
                json.dumps({
                    'error': 'Model service temporarily unavailable',
                    'details': str(e)
                }),
                status=503,
                headers={'Content-Type': 'application/json'}
            )
        
        # Make prediction
        prediction_result = make_prediction(model, vectorizer, feedback_text)
        
        # Calculate processing time
        processing_time_ms = round((time.time() - start_time) * 1000, 2)
        
        # Save to Firestore (non-blocking)
        db = firestore.client()
        firestore_id = save_to_firestore(db, feedback_text, prediction_result, processing_time_ms)
        
        # Prepare response
        response_data = {
            'success': True,
            'prediction': prediction_result['prediction'],
            'confidence': prediction_result.get('confidence'),
            'all_probabilities': prediction_result.get('all_probabilities'),
            'metadata': prediction_result.get('metadata'),
            'feedback': feedback_text,
            'processing_time_ms': processing_time_ms,
            'firestore_id': firestore_id,
            'timestamp': prediction_result['timestamp']
        }
        
        logger.info(f"Prediction successful: {prediction_result['prediction']} ({processing_time_ms}ms)")
        
        return https_fn.Response(
            json.dumps(response_data),
            status=200,
            headers={'Content-Type': 'application/json'}
        )
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        processing_time_ms = round((time.time() - start_time) * 1000, 2)
        
        return https_fn.Response(
            json.dumps({
                'error': 'Internal server error',
                'details': str(e),
                'processing_time_ms': processing_time_ms
            }),
            status=500,
            headers={'Content-Type': 'application/json'}
        )


@https_fn.on_request(
    cors=options.CorsOptions(
        cors_origins=CONFIG['cors_origins'],
        cors_methods=["GET"],
    )
)
def health(req: https_fn.Request) -> https_fn.Response:
    """
    Health check endpoint for monitoring
    
    Returns:
        JSON with service status
    """
    try:
        # Check if models are loaded
        models_status = 'loaded' if _model_loaded else 'not_loaded'
        
        # Check Firestore connection
        try:
            db = firestore.client()
            db.collection('_health_check').limit(1).get()
            firestore_status = 'connected'
        except Exception:
            firestore_status = 'disconnected'
        
        health_data = {
            'status': 'healthy',
            'service': 'text-categorization-api',
            'version': '1.0.0',
            'models_status': models_status,
            'firestore_status': firestore_status,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return https_fn.Response(
            json.dumps(health_data),
            status=200,
            headers={'Content-Type': 'application/json'}
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return https_fn.Response(
            json.dumps({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }),
            status=503,
            headers={'Content-Type': 'application/json'}
        )
