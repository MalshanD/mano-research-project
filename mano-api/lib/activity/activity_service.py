import sys
import os
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from model.activity_response import ActivityResponse
from schemas.activity.activityInSchema import RecommendationRequest
from data.activities import (
    ACTIVITIES_DATABASE,
    get_activities_for_problem,
    get_activity_by_id,
    get_activities_by_category,
    get_activities_for_condition
)

from lib.activity.gmm_predictor import predict_community
from lib.activity.recommendation_predictor import score_all_activities as ml_score_activities

MAX_RECOMMENDATIONS = 3
DISEASE_SEVERITY_THRESHOLDS = {
    'minimal': 2,
    'low': 4,
    'moderate': 6,
    'high': 8,
    'severe': 10
}

class ActivityService:
    def __init__(self):
        self.activities = ACTIVITIES_DATABASE
        self.max_recommendations = MAX_RECOMMENDATIONS
        self.severity_thresholds = DISEASE_SEVERITY_THRESHOLDS

        self.condition_mapping = {
            'stress': {
                'problems': ['high_stress', 'overwhelm', 'physical_tension', 'work_stress'],
                'activity_categories': ['stress_relief', 'mindfulness', 'routine']
            },
            'anxiety': {
                'problems': ['anxiety', 'panic', 'racing_thoughts', 'constant_worry', 'avoidance'],
                'activity_categories': ['anxiety_relief', 'mindfulness']
            },
            'depression': {
                'problems': ['depression', 'low_motivation', 'withdrawal', 'hopelessness',
                             'low_energy', 'isolation', 'anhedonia'],
                'activity_categories': ['depression_relief', 'emotional', 'social']
            }
        }

        self.category_problem_mapping = {
            'body': {
                'low_threshold': 40,
                'problems': ['physical_health', 'low_energy', 'fatigue', 'sleep_issues'],
                'categories': ['physical', 'sleep']
            },
            'behavior': {
                'low_threshold': 40,
                'problems': ['poor_routine', 'daily_habits', 'screen_addiction', 'chaos'],
                'categories': ['routine']
            },
            'social': {
                'low_threshold': 40,
                'problems': ['social_connections', 'loneliness', 'isolation'],
                'categories': ['social']
            }
        }

        self.urgency_mapping = {
            'severe': {'urgency': 5, 'include_professional': True},
            'high': {'urgency': 4, 'include_professional': True},
            'moderate': {'urgency': 3, 'include_professional': False},
            'low': {'urgency': 2, 'include_professional': False},
            'minimal': {'urgency': 1, 'include_professional': False}
        }

    def _get_severity(self, level: float) -> str:
        if level <= self.severity_thresholds['minimal']:
            return 'minimal'
        elif level <= self.severity_thresholds['low']:
            return 'low'
        elif level <= self.severity_thresholds['moderate']:
            return 'moderate'
        elif level <= self.severity_thresholds['high']:
            return 'high'
        else:
            return 'severe'

    def identify_conditions(self, scores: Dict) -> List[Dict]:
        conditions = []
        condition_levels = {
            'stress': scores.get('stress_level', 0),
            'anxiety': scores.get('anxiety_level', 0),
            'depression': scores.get('depression_level', 0)
        }

        if isinstance(condition_levels['stress'], str):
            level_map = {'very_low': 1, 'low': 3, 'medium': 5, 'high': 7, 'very_high': 9}
            condition_levels['stress'] = level_map.get(condition_levels['stress'], 5)

        for condition, level in condition_levels.items():
            if level is None or level == 0:
                continue

            level = float(level)
            severity = self._get_severity(level)

            if severity != 'minimal':
                config = self.condition_mapping[condition]
                urgency = self.urgency_mapping[severity]['urgency']

                conditions.append({
                    'condition': condition,
                    'level': level,
                    'severity': severity,
                    'urgency': urgency,
                    'problems': config['problems'],
                    'activity_categories': config['activity_categories']
                })

        conditions.sort(key=lambda x: x['urgency'], reverse=True)
        return conditions

    def identify_category_problems(self, scores: Dict) -> List[Dict]:
        problems = []
        category_scores = scores.get('category_scores', {})

        for category, config in self.category_problem_mapping.items():
            score = category_scores.get(category, 50)
            if score is None:
                score = 50
            threshold = config['low_threshold']

            if score < threshold:
                if score < 20:
                    severity = 'critical'
                    priority = 5
                elif score < 30:
                    severity = 'high'
                    priority = 4
                elif score < 40:
                    severity = 'medium'
                    priority = 3
                else:
                    severity = 'low'
                    priority = 2

                problems.append({
                    'category': category,
                    'score': score,
                    'severity': severity,
                    'priority': priority,
                    'problem_types': config['problems'],
                    'activity_categories': config['categories']
                })

        problems.sort(key=lambda x: x['priority'], reverse=True)
        return problems

    def find_matching_activities(self, conditions: List[Dict], category_problems: List[Dict], difficulty_preference: str = 'easy') -> List[Dict]:
        activity_scores = {}

        for condition_info in conditions:
            condition_name = condition_info['condition']
            urgency = condition_info['urgency']

            condition_activities = get_activities_for_condition(condition_name)
            for activity in condition_activities:
                activity_id = activity['id']
                if activity_id not in activity_scores:
                    activity_scores[activity_id] = {
                        'activity': activity, 'relevance_score': 0, 'matched_conditions': [], 'matched_problems': []
                    }
                activity_scores[activity_id]['relevance_score'] += urgency * 15
                if condition_name not in activity_scores[activity_id]['matched_conditions']:
                    activity_scores[activity_id]['matched_conditions'].append(condition_name)

            for problem_type in condition_info['problems']:
                matching = get_activities_for_problem(problem_type)
                for activity in matching:
                    activity_id = activity['id']
                    if activity_id not in activity_scores:
                        activity_scores[activity_id] = {
                            'activity': activity, 'relevance_score': 0, 'matched_conditions': [], 'matched_problems': []
                        }
                    activity_scores[activity_id]['relevance_score'] += urgency * 5
                    if problem_type not in activity_scores[activity_id]['matched_problems']:
                        activity_scores[activity_id]['matched_problems'].append(problem_type)

        for problem in category_problems:
            problem_priority = problem['priority']

            for problem_type in problem['problem_types']:
                matching = get_activities_for_problem(problem_type)
                for activity in matching:
                    activity_id = activity['id']
                    if activity_id not in activity_scores:
                        activity_scores[activity_id] = {
                            'activity': activity, 'relevance_score': 0, 'matched_conditions': [], 'matched_problems': []
                        }
                    activity_scores[activity_id]['relevance_score'] += problem_priority * 8
                    if problem_type not in activity_scores[activity_id]['matched_problems']:
                        activity_scores[activity_id]['matched_problems'].append(problem_type)

            for category in problem['activity_categories']:
                category_activities = get_activities_by_category(category)
                for activity in category_activities:
                    activity_id = activity['id']
                    if activity_id not in activity_scores:
                        activity_scores[activity_id] = {
                            'activity': activity, 'relevance_score': 0, 'matched_conditions': [], 'matched_problems': []
                        }
                    activity_scores[activity_id]['relevance_score'] += problem_priority * 4

        result = []
        for activity_id, data in activity_scores.items():
            activity = data['activity']
            final_score = data['relevance_score']

            if activity.get('difficulty') == difficulty_preference:
                final_score += 15
            elif activity.get('difficulty') == 'easy':
                final_score += 10

            final_score += activity.get('effectiveness_score', 70) * 0.3

            if activity.get('scientific_backing', False):
                final_score += 5

            result.append({
                'activity': activity,
                'relevance_score': round(final_score, 2),
                'matched_conditions': data['matched_conditions'],
                'matched_problems': data['matched_problems']
            })

        result.sort(key=lambda x: x['relevance_score'], reverse=True)
        return result

    def get_recommendations(self, scores: Dict, num_recommendations: int = None, difficulty_preference: str = 'easy', max_duration_minutes: int = None, exclude_categories: List[str] = None) -> Dict:
        if num_recommendations is None:
            num_recommendations = self.max_recommendations

        if exclude_categories is None:
            exclude_categories = []

        # Identify conditions for metadata and professional support check
        conditions = self.identify_conditions(scores)
        category_problems = self.identify_category_problems(scores)

        if not conditions and not category_problems:
            return self._get_general_recommendations(num_recommendations)

        # ============================================================
        # ML-BASED ACTIVITY RECOMMENDATION (Component 4 - PyTorch)
        # ============================================================
        # Try the trained PyTorch neural network first. If it fails or
        # isn't available, fall back to the original rule-based scoring.
        # ============================================================

        # Extract user scores for ML model (0-100 scale)
        stress_val = float(scores.get('stress_level', 0))
        anxiety_val = float(scores.get('anxiety_level', 0))
        depression_val = float(scores.get('depression_level', 0))
        # Convert 0-10 scale to 0-100 if needed
        if stress_val <= 10:
            stress_val *= 10.0
        if anxiety_val <= 10:
            anxiety_val *= 10.0
        if depression_val <= 10:
            depression_val *= 10.0

        cat_scores = scores.get('category_scores', {})
        body_val = float(cat_scores.get('body', 50))
        behavior_val = float(cat_scores.get('behavior', 50))
        emotional_val = float(cat_scores.get('emotional', 50))
        social_val = float(cat_scores.get('social', 50))

        # Try ML scoring
        ml_scored = ml_score_activities(
            stress_score=stress_val,
            anxiety_score=anxiety_val,
            depression_score=depression_val,
            body_score=body_val,
            behavior_score=behavior_val,
            emotional_score=emotional_val,
            social_score=social_val,
            activities_database=self.activities
        )

        recommendation_method = "ml"

        if ml_scored is not None:
            matching_activities = ml_scored
        else:
            recommendation_method = "rule_based"
            matching_activities = self.find_matching_activities(conditions, category_problems, difficulty_preference)

        # Apply filters (same for both ML and rule-based)
        filtered = []
        for item in matching_activities:
            activity = item['activity']
            if max_duration_minutes and activity.get('duration_minutes', 0) > max_duration_minutes:
                continue
            if activity.get('category') in exclude_categories:
                continue
            filtered.append(item)

        needs_professional = any(
            self.urgency_mapping.get(c['severity'], {}).get('include_professional', False)
            for c in conditions
        )

        recommendations = []
        for item in filtered:
            activity = item['activity']
            category = activity.get('category')
            category_count = sum(1 for r in recommendations if r['activity'].get('category') == category)
            if category_count >= 2:
                continue

            recommendations.append({
                'activity_id': activity['id'],
                'activity': activity,
                'relevance_score': item['relevance_score'],
                'matched_conditions': item['matched_conditions'],
                'matched_problems': item['matched_problems'],
                'why_recommended': self._generate_recommendation_reason(activity, item['matched_conditions'], item['matched_problems'])
            })

            if len(recommendations) >= num_recommendations:
                break

        if needs_professional:
            professional = get_activity_by_id('professional_001')
            if professional:
                if not any(r['activity_id'] == 'professional_001' for r in recommendations):
                    severe_conditions = [c['condition'] for c in conditions if c['severity'] in ['severe', 'high']]
                    recommendations.insert(0, {
                        'activity_id': professional['id'],
                        'activity': professional,
                        'relevance_score': 100,
                        'matched_conditions': severe_conditions,
                        'matched_problems': ['professional_support'],
                        'why_recommended': f"Given your {', '.join(severe_conditions)} levels, professional support could be very helpful.",
                        'priority': 'high'
                    })

        return {
            'success': True,
            'conditions_detected': [{'condition': c['condition'], 'level': c['level'], 'severity': c['severity']} for c in conditions],
            'identified_problems': [{'category': p['category'], 'severity': p['severity'], 'score': p['score']} for p in category_problems],
            'recommendations': recommendations,
            'total_matching_activities': len(matching_activities),
            'recommendation_method': recommendation_method,
            'filters_applied': {
                'difficulty_preference': difficulty_preference,
                'max_duration_minutes': max_duration_minutes,
                'excluded_categories': exclude_categories
            },
            'generated_at': datetime.now().isoformat()
        }

    def _generate_recommendation_reason(self, activity: Dict, matched_conditions: List[str], matched_problems: List[str]) -> str:
        name = activity['name']
        if matched_conditions:
            condition_str = ', '.join(matched_conditions)
            base_reason = f"'{name}' is recommended to help with your {condition_str}"
        else:
            category = activity.get('category', '')
            reasons = {
                'stress_relief': f"'{name}' can help reduce your stress levels",
                'anxiety_relief': f"'{name}' can help manage your anxiety",
                'depression_relief': f"'{name}' can help improve your mood and energy",
                'sleep': f"'{name}' can improve your sleep quality",
                'physical': f"'{name}' can boost your physical wellbeing",
                'social': f"'{name}' can help you feel more connected",
                'emotional': f"'{name}' can help improve your emotional state",
                'mindfulness': f"'{name}' can help calm your mind",
                'routine': f"'{name}' can help establish healthier habits",
                'professional': f"'{name}' provides expert support"
            }
            base_reason = reasons.get(category, f"'{name}' matches your current needs")

        if 'sleep_issues' in matched_problems:
            base_reason += " and help you sleep better"
        if 'loneliness' in matched_problems or 'isolation' in matched_problems:
            base_reason += " and reduce feelings of isolation"

        return base_reason + "."

    def _get_general_recommendations(self, num_recommendations: int) -> Dict:
        general_activities = [
            get_activity_by_id('mindful_001'),
            get_activity_by_id('physical_002'),
            get_activity_by_id('emotional_001'),
        ]

        recommendations = []
        for activity in general_activities[:num_recommendations]:
            if activity:
                recommendations.append({
                    'activity_id': activity['id'],
                    'activity': activity,
                    'relevance_score': 70,
                    'matched_conditions': [],
                    'matched_problems': ['general_wellness'],
                    'why_recommended': f"'{activity['name']}' is great for maintaining overall wellbeing."
                })

        return {
            'success': True,
            'conditions_detected': [],
            'identified_problems': [],
            'message': "Your scores look good! Here are some activities to maintain your wellbeing.",
            'recommendations': recommendations,
            'generated_at': datetime.now().isoformat()
        }

    @staticmethod
    def generate_and_save_recommendation(
        db: Session, 
        user_id: int, 
        condition: str, 
        level: float, 
        request: RecommendationRequest
    ) -> Dict:
        
        body_score = 50.0
        behavior_score = 50.0
        emotional_score = 50.0
        social_score = 50.0
        
        if request.answers and len(request.answers) >= 20:
            # Helper to calculate 0-100 score where lower sum (better) -> 100, higher sum (worse) -> 0
            def calc_score(ans_slice):
                total = sum(ans_slice)
                return max(0, min(100, 100 - ((total - 5) / 20.0 * 100)))

            body_score = calc_score(request.answers[0:5])
            behavior_score = calc_score(request.answers[5:10])
            emotional_score = calc_score(request.answers[10:15])
            social_score = calc_score(request.answers[15:20])

        scores = {
            'stress_level': (level / 10.0) if condition == 'stress' else 0,
            'anxiety_level': (level / 10.0) if condition == 'anxiety' else 0,
            'depression_level': (level / 10.0) if condition == 'depression' else 0,
            'category_scores': {
                'body': body_score,
                'behavior': behavior_score,
                'emotional': emotional_score,
                'social': social_score
            }
        }
        
        svc = ActivityService()
        result_json = svc.get_recommendations(
            scores=scores,
            num_recommendations=request.num_recommendations,
            difficulty_preference=request.difficulty_preference,
            max_duration_minutes=request.max_duration_minutes,
            exclude_categories=request.exclude_categories
        )

        activity_response = ActivityResponse(
            user_id=user_id,
            result_json=result_json
        )
        db.add(activity_response)
        
        # ============================================================
        # GMM-BASED COMMUNITY ASSIGNMENT (Component 4)
        # ============================================================
        # Use the trained Gaussian Mixture Model to assign the user
        # to a community cluster based on their full 7-dimensional
        # mental health profile, instead of simple threshold rules.
        #
        # Input: stress_score, anxiety_score, depression_score (0-100)
        #        body_score, behavior_score, emotional_score, social_score (0-100)
        # Output: community_name, description, confidence, probabilities
        # ============================================================

        # Build the 7-dimensional score vector for GMM input
        # Stress/anxiety/depression: normalize from the condition+level format to 0-100
        stress_for_gmm = (scores['stress_level'] * 10.0) if scores.get('stress_level', 0) <= 10 else scores.get('stress_level', 0)
        anxiety_for_gmm = (scores['anxiety_level'] * 10.0) if scores.get('anxiety_level', 0) <= 10 else scores.get('anxiety_level', 0)
        depression_for_gmm = (scores['depression_level'] * 10.0) if scores.get('depression_level', 0) <= 10 else scores.get('depression_level', 0)

        # If only one condition was provided (the primary condition), use level param for it
        if condition == 'stress' and stress_for_gmm == 0:
            stress_for_gmm = float(level) if float(level) > 10 else float(level) * 10.0
        if condition == 'anxiety' and anxiety_for_gmm == 0:
            anxiety_for_gmm = float(level) if float(level) > 10 else float(level) * 10.0
        if condition == 'depression' and depression_for_gmm == 0:
            depression_for_gmm = float(level) if float(level) > 10 else float(level) * 10.0

        # Predict community using GMM
        gmm_result = predict_community(
            stress_score=stress_for_gmm,
            anxiety_score=anxiety_for_gmm,
            depression_score=depression_for_gmm,
            body_score=body_score,
            behavior_score=behavior_score,
            emotional_score=emotional_score,
            social_score=social_score
        )

        comm_name = gmm_result["community_name"]
        desc = gmm_result["description"]

        # Add GMM clustering info to the result JSON
        result_json["community_assignment"] = {
            "community_name": comm_name,
            "description": desc,
            "confidence": gmm_result["confidence"],
            "all_probabilities": gmm_result["all_probabilities"],
            "method": gmm_result["method"]
        }

        from model.community import Community
        existing_comm = db.query(Community).filter(Community.user_id == user_id).first()
        if existing_comm:
            existing_comm.community_name = comm_name
            existing_comm.description = desc
        else:
            new_comm = Community(
                user_id=user_id,
                community_name=comm_name,
                description=desc
            )
            db.add(new_comm)

        db.commit()
        db.refresh(activity_response)

        return result_json

    @staticmethod
    def get_user_recommended_activities(db: Session, user_id: int):
        # order_by(ActivityResponse.id.desc()).first() gets the LAST recommended JSON for this user
        response = db.query(ActivityResponse).filter(
            ActivityResponse.user_id == user_id
        ).order_by(ActivityResponse.id.desc()).first()
        
        if not response or not response.result_json:
            return {}
            
        result = response.result_json
        
        import json
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except:
                result = {}
                    
        return result

    @staticmethod
    def get_user_recommended_activities_by_category(db: Session, user_id: int, category_name: str):
        response = db.query(ActivityResponse).filter(
            ActivityResponse.user_id == user_id
        ).order_by(ActivityResponse.id.desc()).first()
        
        if not response or not response.result_json:
            return {"category": category_name, "activities": []}
            
        result = response.result_json
        import json
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except:
                result = {}
                
        filtered_activities = []
        if 'recommendations' in result:
            for rec in result['recommendations']:
                act = rec.get('activity', {})
                if act.get('category') == category_name:
                    filtered_activities.append(act)
                    
        return {"category": category_name, "activities": filtered_activities}

    @staticmethod
    def log_completed_activity(db: Session, user_id: int, activity_id: str):
        from model.completed_activity import CompletedActivity
        from data.activities import get_activity_by_id
        from datetime import datetime
        
        # Load full activity JSON dynamically by ID
        activity_json = get_activity_by_id(activity_id)
        if not activity_json:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Activity not found in system")

        # Check if user already completed this activity before
        existing = db.query(CompletedActivity).filter(
            CompletedActivity.user_id == user_id,
            CompletedActivity.activity_id == activity_id
        ).first()

        if existing:
            existing.count += 1
            existing.last_completed = datetime.now()
            existing.activity_json = activity_json # Update logic in case json changed
            db.commit()
            db.refresh(existing)
            return existing
        else:
            new_completion = CompletedActivity(
                user_id=user_id,
                activity_id=activity_id,
                activity_json=activity_json,
                count=1,
                last_completed=datetime.now()
            )
            db.add(new_completion)
            db.commit()
            db.refresh(new_completion)
            return new_completion

    @staticmethod
    def get_user_completed_activities(db: Session, user_id: int):
        from model.completed_activity import CompletedActivity
        return db.query(CompletedActivity).filter(CompletedActivity.user_id == user_id).all()
