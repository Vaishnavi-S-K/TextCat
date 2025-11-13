from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# ---- Load trained model and vectorizer ----
model = joblib.load("textcat_model.pkl")
vectorizer = joblib.load("tfidf_vectorizer.pkl")

# ---- Define routes ----
@app.route('/')
def home():
    return "✅ Text Categorization API is running!"

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "message": "API is running"
    })

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        
        if data is None:
            return jsonify({"error": "Invalid or missing JSON body"}), 400
        
        # Accept either 'text' or 'feedback' field
        feedback_text = data.get("feedback") or data.get("text")

        if not feedback_text:
            return jsonify({"error": "No feedback text provided"}), 400

        # Convert text → TF-IDF → predict
        X = vectorizer.transform([feedback_text])
        prediction = model.predict(X)[0]

        # Get prediction probability for confidence
        confidence = None
        all_probabilities = {}
        try:
            probabilities = model.predict_proba(X)[0]
            classes = model.classes_
            
            # Get max confidence
            max_prob = max(probabilities)
            confidence = round(max_prob * 100, 2)
            
            # Get all probabilities
            for cls, prob in zip(classes, probabilities):
                all_probabilities[cls] = round(prob * 100, 2)
        except Exception as e:
            print(f"Probability calculation error: {e}")

        # Log to console
        print(f"Feedback: {feedback_text}")
        print(f"Prediction: {prediction}")
        print(f"Confidence: {confidence}%")

        response = {
            "success": True,
            "prediction": prediction,
            "confidence": confidence,
            "feedback": feedback_text,
            "all_probabilities": all_probabilities,
            "processing_time_ms": 0
        }

        return jsonify(response)

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ---- Run locally ----
if __name__ == '__main__':
    # For local development
    app.run(debug=True)
    
    # For production with gunicorn (Procfile handles this)
    # gunicorn will use: app:app
