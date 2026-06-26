import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler

# Try to import HuggingFace Transformers
try:
    from transformers import pipeline
    HF_TRANSFORMERS_AVAILABLE = True
except ImportError:
    HF_TRANSFORMERS_AVAILABLE = False

# Try to import NLTK / VADER
try:
    import nltk
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    NLTK_VADER_AVAILABLE = True
except ImportError:
    NLTK_VADER_AVAILABLE = False

# Sentiment lexicon fallback
LEXICON = {
    # Positive words
    "excellent": 0.9, "good": 0.6, "great": 0.8, "perfect": 0.95, "improving": 0.5,
    "consistent": 0.6, "brilliant": 0.9, "diligent": 0.7, "outstanding": 0.95,
    "focused": 0.5, "active": 0.4, "participating": 0.4, "creative": 0.5,
    # Negative words
    "struggles": -0.5, "poor": -0.6, "distracted": -0.4, "failing": -0.8, "weak": -0.5,
    "absent": -0.6, "missing": -0.4, "late": -0.3, "careless": -0.5, "disruptive": -0.7,
    "inattentive": -0.5, "slow": -0.3, "uninterested": -0.6, "bad": -0.6
}

def analyze_remark_sentiment(text: str) -> float:
    """
    Analyzes sentiment of faculty remarks, returning a score from -1.0 (very negative) to 1.0 (very positive).
    Tries HuggingFace Transformers first, then NLTK VADER, and falls back to a lexicon rule engine.
    """
    if not text:
        return 0.0
        
    text_lower = text.lower()
    
    # 1. Try Hugging Face Pipeline
    if HF_TRANSFORMERS_AVAILABLE:
        try:
            # We initialize dynamically to avoid loading it on start if not used
            classifier = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
            result = classifier(text)[0]
            score = result["score"]
            if result["label"] == "NEGATIVE":
                return -float(score)
            return float(score)
        except Exception as e:
            print(f"HuggingFace NLP sentiment analysis failed: {e}. Falling back...")
            
    # 2. Try NLTK VADER
    if NLTK_VADER_AVAILABLE:
        try:
            # Lazy download
            try:
                sia = SentimentIntensityAnalyzer()
            except LookupError:
                nltk.download('vader_lexicon', quiet=True)
                sia = SentimentIntensityAnalyzer()
            scores = sia.polarity_scores(text)
            return float(scores["compound"])
        except Exception as e:
            print(f"NLTK VADER sentiment analysis failed: {e}. Falling back...")
            
    # 3. Custom Lexicon Fallback (Zero Dependency)
    words = text_lower.split()
    score_sum = 0.0
    matches = 0
    
    # Check words and short phrases
    for word in words:
        # Strip punctuation
        clean_word = word.strip(".,!?;:()\"'")
        if clean_word in LEXICON:
            score_sum += LEXICON[clean_word]
            matches += 1
            
    # Simple default modifiers
    if "not" in words or "no" in words or "never" in words:
        score_sum = -score_sum
        
    if matches > 0:
        sentiment = score_sum / matches
    else:
        # Default to a mild positive/negative check if no words match
        sentiment = 0.0
        
    return float(np.clip(sentiment, -1.0, 1.0))

def run_student_clustering(student_df: pd.DataFrame, method: str = "kmeans", n_clusters: int = 3) -> pd.DataFrame:
    """
    Groups students into clusters based on attendance and average academic grades.
    """
    if student_df.empty:
        return student_df
        
    # Standardize column names
    df_clean = student_df.copy()
    if "attendance" in df_clean.columns and "attendance_pct" not in df_clean.columns:
        df_clean["attendance_pct"] = df_clean["attendance"]
        
    features = ["attendance_pct", "overall_academic"]
    X = df_clean[features].copy()
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Safely determine the number of clusters to prevent errors with small datasets
    actual_clusters = min(n_clusters, len(df_clean))
    if actual_clusters < 1:
        df_clean["cluster"] = 0
        df_clean["cluster_name"] = "No Group"
        return df_clean
        
    if method.lower() == "dbscan":
        # DBSCAN
        dbscan = DBSCAN(eps=0.5, min_samples=min(2, len(df_clean)))
        clusters = dbscan.fit_predict(X_scaled)
    else:
        # K-Means
        kmeans = KMeans(n_clusters=actual_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)
        
    df_clean["cluster"] = clusters
    
    # Map cluster numbers to meaningful names based on attendance and marks
    # We rank clusters by the mean overall academic score of the cluster
    cluster_means = df_clean.groupby("cluster")["overall_academic"].mean().sort_values()
    
    cluster_mapping = {}
    names = ["High Risk Group", "Average Achievers", "High Achievers"]
    
    for i, (cluster_id, _) in enumerate(cluster_means.items()):
        if i < len(names):
            cluster_mapping[cluster_id] = names[i]
        else:
            cluster_mapping[cluster_id] = f"Cluster {cluster_id}"
            
    df_clean["cluster_name"] = df_clean["cluster"].map(cluster_mapping)
    
    return df_clean

def predict_exam_pass_probability(attendance: float, internal_marks: float, assignment_completion: float) -> float:
    """
    Predicts the probability of passing the final exam.
    Standard passing grade usually corresponds to achieving an overall score of 40%.
    """
    # Base pass threshold score: 40 out of 100
    # Current indicators of score (internals out of 30, assignment out of 20 = 50 marks total)
    current_score_pct = (internal_marks + (assignment_completion * 20.0)) / 50.0
    
    # Calculate probability
    # Base probability on current scores and attendance
    prob = (current_score_pct * 0.6) + ((attendance / 100.0) * 0.4)
    
    # Adjust probability based on critical factors
    if attendance < 60.0:
        prob -= 0.15  # high absence penalty
    if internal_marks < 10.0:
        prob -= 0.1  # low internal exam performance penalty
        
    return float(np.clip(prob, 0.05, 0.99))

if __name__ == "__main__":
    # Test sentiment
    print("Sentiment (excellent):", analyze_remark_sentiment("The performance is excellent!"))
    print("Sentiment (poor):", analyze_remark_sentiment("Struggles in class and poor homework submission."))
    print("Sentiment (neutral):", analyze_remark_sentiment("He is doing fine, nothing special."))
    
    # Test exam pass probability
    print("Pass Prob (Good student):", predict_exam_pass_probability(92.0, 26.0, 0.95))
    print("Pass Prob (Poor student):", predict_exam_pass_probability(60.0, 11.0, 0.4))
