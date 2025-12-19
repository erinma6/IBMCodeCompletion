#!/usr/bin/env python3
"""
Fixed ML Commit Classifier - Addresses Overfitting Issues
Uses Scikit-learn with better hyperparameters, regularization, and feature engineering
"""

import json
import os
import numpy as np
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.model_selection import cross_val_score, StratifiedKFold
    from sklearn.metrics import (
        classification_report, 
        confusion_matrix, 
        accuracy_score,
        f1_score,
        balanced_accuracy_score
    )
    from sklearn.preprocessing import LabelEncoder
    from sklearn.utils.class_weight import compute_class_weight
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("⚠️  scikit-learn not installed. Install with: pip install scikit-learn")


class FixedMLClassifier:
    """Improved ML classifier with fixes for overfitting."""
    
    def __init__(self):
        """Initialize the classifier with better hyperparameters."""
        # Better TF-IDF settings
        self.vectorizer = TfidfVectorizer(
            max_features=50,           # Reduced from 100 to reduce noise
            stop_words='english',
            min_df=3,                  # Word must appear in at least 3 docs
            max_df=0.8,                # Word can't appear in >80% of docs
            ngram_range=(1, 2),
            sublinear_tf=True          # Sublinear term frequency scaling
        )
        
        # Better Random Forest settings with regularization
        self.classifier = RandomForestClassifier(
            n_estimators=50,           # Reduced from 100
            max_depth=8,               # Reduced from 10 (more regularization)
            min_samples_split=10,      # Increased from default
            min_samples_leaf=5,        # Increased from default
            max_features='sqrt',       # Use sqrt of features
            random_state=42,
            n_jobs=-1,
            class_weight='balanced'    # Handle class imbalance
        )
        self.label_encoder = LabelEncoder()
        self.is_trained = False
        self.class_weights_dict = {}
        
    def prepare_data(self, commits: List[Dict]) -> Tuple[List, List, List]:
        """Prepare training, validation, and test data - all from same distribution."""
        # Separate by confidence level
        high_conf = [c for c in commits if c['confidence'] >= 0.95]
        med_conf = [c for c in commits if 0.80 <= c['confidence'] < 0.95]
        low_conf = [c for c in commits if c['confidence'] < 0.80]
        
        print(f"\nData split:")
        print(f"  High confidence (0.95+): {len(high_conf)} commits")
        print(f"    Using: {int(len(high_conf)*0.7)} for training, {int(len(high_conf)*0.3)} for validation")
        print(f"  Medium confidence (0.80-0.94): {len(med_conf)} commits (validation)")
        print(f"  Low confidence (<0.80): {len(low_conf)} commits (test)\n")
        
        # Split high-confidence commits for better validation
        np.random.seed(42)
        shuffle_indices = np.random.permutation(len(high_conf))
        split_point = int(len(high_conf) * 0.7)
        
        train_commits = [high_conf[i] for i in shuffle_indices[:split_point]]
        val_from_high = [high_conf[i] for i in shuffle_indices[split_point:]]
        
        # Combine validation sets
        val_commits = val_from_high + med_conf
        
        return train_commits, val_commits, low_conf
    
    def clean_features(self, message: str) -> str:
        """Remove noise from commit message."""
        # Remove email addresses and author info
        message = message.lower()
        
        # Remove common noise patterns
        noise_patterns = [
            r'signed-off-by.*',
            r'authored by.*',
            r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}',  # Emails
            r'\b[a-z0-9]+08290126\b',                    # User IDs
            r'(com|org|net)\b',                          # Domain extensions
        ]
        
        for pattern in noise_patterns:
            import re
            message = re.sub(pattern, '', message)
        
        return message
    
    def train(self, commits: List[Dict]):
        """Train the ML classifier with better approach."""
        if not SKLEARN_AVAILABLE:
            print("❌ scikit-learn not available. Install it first.")
            return False
        
        print("="*80)
        print("TRAINING FIXED ML CLASSIFIER (v3)")
        print("="*80)
        
        # Prepare data
        train_commits, val_commits, test_commits = self.prepare_data(commits)
        
        if len(train_commits) < 50:
            print("⚠️  Warning: Less than 50 training samples.")
        
        # Clean and extract training data
        print("Preparing training data...")
        train_messages = [self.clean_features(c['commit_message']) for c in train_commits]
        train_labels = [c['primary_class'] for c in train_commits]
        
        # Vectorize messages
        print("Vectorizing commit messages (TF-IDF)...")
        X_train = self.vectorizer.fit_transform(train_messages)
        
        # Encode labels
        y_train = self.label_encoder.fit_transform(train_labels)
        
        # Calculate class weights for imbalance handling
        self.class_weights_dict = compute_class_weight(
            'balanced',
            classes=np.unique(y_train),
            y=y_train
        )
        
        print(f"Class weights: {dict(zip(self.label_encoder.classes_, self.class_weights_dict))}")
        
        # Train classifier
        print("Training Random Forest classifier with regularization...")
        self.classifier.fit(X_train, y_train)
        self.is_trained = True
        
        # Cross-validation on training set
        print("\nPerforming 5-fold cross-validation...")
        cv_fold = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(self.classifier, X_train, y_train, cv=cv_fold, scoring='balanced_accuracy')
        
        print(f"  CV Scores: {cv_scores}")
        print(f"  Mean CV Accuracy: {cv_scores.mean():.2%} (+/- {cv_scores.std():.2%})")
        
        # Training accuracy
        train_pred = self.classifier.predict(X_train)
        train_accuracy = balanced_accuracy_score(y_train, train_pred)
        
        print(f"\n✅ Training complete!")
        print(f"  Training accuracy (balanced): {train_accuracy:.2%}")
        
        # Validation
        if len(val_commits) > 0:
            print("\nEvaluating on validation set...")
            val_messages = [self.clean_features(c['commit_message']) for c in val_commits]
            val_labels = [c['primary_class'] for c in val_commits]
            X_val = self.vectorizer.transform(val_messages)
            y_val = self.label_encoder.transform(val_labels)
            val_pred = self.classifier.predict(X_val)
            
            val_accuracy = balanced_accuracy_score(y_val, val_pred)
            val_f1 = f1_score(y_val, val_pred, average='weighted')
            
            print(f"  Validation accuracy (balanced): {val_accuracy:.2%}")
            print(f"  Validation F1-score (weighted): {val_f1:.2%}")
            print(f"  Overfitting gap: {(train_accuracy - val_accuracy)*100:.1f}%")
            
            if train_accuracy - val_accuracy > 0.15:
                print("  ⚠️  WARNING: Still some overfitting detected")
            else:
                print("  ✓ Good generalization!")
            
            print("\nPer-class performance on validation set:")
            print(classification_report(
                y_val, val_pred,
                target_names=self.label_encoder.classes_,
                digits=3
            ))
        
        # Test set evaluation
        if len(test_commits) > 0:
            print("\n" + "-"*80)
            print("Test set (low-confidence commits):")
            test_messages = [self.clean_features(c['commit_message']) for c in test_commits]
            test_labels = [c['primary_class'] for c in test_commits]
            X_test = self.vectorizer.transform(test_messages)
            y_test = self.label_encoder.transform(test_labels)
            test_pred = self.classifier.predict(X_test)
            
            test_accuracy = balanced_accuracy_score(y_test, test_pred)
            heuristic_accuracy = np.mean([c['confidence'] for c in test_commits])
            
            print(f"  ML accuracy (balanced): {test_accuracy:.2%}")
            print(f"  Heuristic accuracy: {heuristic_accuracy:.2%}")
            
            improvement = (test_accuracy - heuristic_accuracy) * 100
            if improvement > 0:
                print(f"  ✅ Improvement: +{improvement:.1f}%")
            else:
                print(f"  ⚠️  Difference: {improvement:.1f}%")
            
            # Confusion matrix
            cm = confusion_matrix(y_test, test_pred)
            print("\nConfusion Matrix (test set):")
            classes = self.label_encoder.classes_
            print(f"{'':20} {' '.join(f'{c[:8]:>10}' for c in classes)}")
            for i, row in enumerate(cm):
                print(f"{classes[i][:18]:20} {' '.join(f'{v:10d}' for v in row)}")
        
        return True
    
    def predict(self, commit: Dict) -> Tuple[str, float]:
        """Predict category for a single commit."""
        if not self.is_trained:
            print("❌ Model not trained yet. Call train() first.")
            return None, None
        
        message = self.clean_features(commit['commit_message'])
        X = self.vectorizer.transform([message])
        
        # Get prediction
        pred = self.classifier.predict(X)[0]
        pred_class = self.label_encoder.inverse_transform([pred])[0]
        
        # Get confidence (max probability)
        proba = self.classifier.predict_proba(X)[0]
        confidence = float(max(proba))
        
        return pred_class, confidence
    
    def predict_batch(self, commits: List[Dict]) -> List[Dict]:
        """Predict categories for multiple commits."""
        if not self.is_trained:
            print("❌ Model not trained yet.")
            return []
        
        messages = [self.clean_features(c['commit_message']) for c in commits]
        X = self.vectorizer.transform(messages)
        
        predictions = self.classifier.predict(X)
        probabilities = self.classifier.predict_proba(X)
        
        results = []
        for i, commit in enumerate(commits):
            pred_class = self.label_encoder.inverse_transform([predictions[i]])[0]
            confidence = float(max(probabilities[i]))
            
            results.append({
                'commit_sha': commit['commit_sha'],
                'heuristic_class': commit['primary_class'],
                'heuristic_confidence': commit['confidence'],
                'ml_class': pred_class,
                'ml_confidence': confidence,
                'agree': pred_class == commit['primary_class'],
                'improvement': confidence - commit['confidence']
            })
        
        return results
    
    def compare_with_heuristics(self, commits: List[Dict]):
        """Compare ML predictions with heuristic classifications."""
        if not self.is_trained:
            print("❌ Model not trained yet.")
            return
        
        print("\n" + "="*80)
        print("COMPARING FIXED ML vs HEURISTIC CLASSIFICATIONS")
        print("="*80 + "\n")
        
        results = self.predict_batch(commits)
        
        # Statistics
        agree = sum(1 for r in results if r['agree'])
        disagree = len(results) - agree
        avg_improvement = np.mean([r['improvement'] for r in results])
        
        print(f"Total commits: {len(results)}")
        print(f"ML and heuristic agree: {agree} ({agree/len(results)*100:.1f}%)")
        print(f"ML and heuristic disagree: {disagree} ({disagree/len(results)*100:.1f}%)")
        print(f"Average confidence change: {avg_improvement:+.3f}")
        
        # Show improvements
        improvements = sorted(
            [r for r in results if r['improvement'] > 0.05],
            key=lambda x: x['improvement'],
            reverse=True
        )
        
        if improvements:
            print(f"\n✅ Improvements (ML better than heuristic):")
            print(f"   Found {len(improvements)} cases where ML improved confidence")
            for result in improvements[:5]:
                print(f"   SHA: {result['commit_sha']}")
                print(f"      Heuristic: {result['heuristic_class']} ({result['heuristic_confidence']:.2f})")
                print(f"      ML:        {result['ml_class']} ({result['ml_confidence']:.2f})")
                print(f"      Improvement: +{result['improvement']:.2f}\n")
        
        # Show disagreements
        disagreements = [r for r in results if not r['agree'] and r['improvement'] > 0]
        if disagreements:
            print(f"\n⚠️  Beneficial disagreements (ML different but more confident):")
            print(f"   Found {len(disagreements)} cases")
            for result in disagreements[:5]:
                print(f"   SHA: {result['commit_sha']}")
                print(f"      Heuristic: {result['heuristic_class']} ({result['heuristic_confidence']:.2f})")
                print(f"      ML:        {result['ml_class']} ({result['ml_confidence']:.2f})\n")


def main():
    """Main execution."""
    if not SKLEARN_AVAILABLE:
        print("❌ scikit-learn is required. Install with:")
        print("   python3 -m pip install --no-cache-dir scikit-learn")
        return
    
    print("Loading classified commits...")
    data_path = os.path.join(os.path.dirname(__file__), 'data', 'classified_commits.json')
    with open(data_path) as f:
        commits = json.load(f)
    
    print(f"Loaded {len(commits)} commits")
    
    # Create and train classifier
    ml_clf = FixedMLClassifier()
    ml_clf.train(commits)
    
    # Compare with heuristics
    ml_clf.compare_with_heuristics(commits)
    
    # Show feature importance
    print("\n" + "="*80)
    print("FEATURE IMPORTANCE")
    print("="*80 + "\n")
    
    feature_names = ml_clf.vectorizer.get_feature_names_out()
    importances = ml_clf.classifier.feature_importances_
    
    # Get top 15 features
    top_indices = np.argsort(importances)[-15:][::-1]
    
    print("Top 15 most important features:")
    for idx in top_indices:
        if idx < len(feature_names):
            print(f"  {feature_names[idx]:30} {importances[idx]:.4f}")
    
    print("\n✅ Fixed ML Classification complete!")
    print("\nSummary:")
    print("  • Better regularization (reduced overfitting)")
    print("  • Cleaner features (removed noise)")
    print("  • Better class balance handling")
    print("  • Cross-validation for robustness")
    print("  • Balanced accuracy metrics")


if __name__ == '__main__':
    main()

