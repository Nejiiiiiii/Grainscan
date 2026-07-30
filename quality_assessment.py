import pandas as pd
import numpy as np
from typing import Dict, Tuple, List
import json

class RiceQualityAssessor:
    """
    Comprehensive rice quality assessment system that grades rice samples
    as High, Medium, or Low quality based on grain composition and standards.
    """
    
    def __init__(self):
        # Quality thresholds based on industry standards
        self.quality_thresholds = {
            'Long': {
                'length_range': (6.61, 7.50),
                'weight': 1.0,  # Premium weight
                'description': 'Long grains, premium quality'
            },
            'Medium': {
                'length_range': (5.51, 6.60),
                'weight': 0.8,  # Good weight
                'description': 'Medium-sized grains, standard quality'
            },
            'Short': {
                'length_range': (0, 5.50),
                'weight': 0.4,  # Reduced weight
                'description': 'Short grains, sub-standard quality'
            },
            'Broken': {
                'weight': 0.2,  # Significantly reduced weight
                'description': 'Broken grains, poor quality'
            },
            'Discolored': {
                'weight': 0.3,  # Reduced weight due to appearance
                'description': 'Discolored grains, poor quality'
            }
        }
        
        # Quality grade thresholds (dominant-based rules derived from provided table)
        # We map Best -> High, Good -> Medium, Fair -> Low
        # Chalky is intentionally omitted per request; defects = Broken + Discolored only
        self.grade_thresholds = {
            'dominant_long': {
                'High': {
                    'dominant_min': 80.0,
                    'other1_max': 15.0,  # Medium
                    'other2_max': 5.0,   # Short
                    'broken_max': 5.0,
                    'discolored_max': 3.0,
                },
                'Medium': {
                    'dominant_min': 60.0,
                    'other1_max': 30.0,
                    'other2_max': 10.0,
                    'broken_max': 10.0,
                    'discolored_max': 8.0,
                }
            },
            'dominant_medium': {
                'High': {
                    'dominant_min': 80.0,
                    'other1_max': 15.0,  # Long
                    'other2_max': 5.0,   # Short
                    'broken_max': 5.0,
                    'discolored_max': 3.0,
                },
                'Medium': {
                    'dominant_min': 60.0,
                    'other1_max': 30.0,
                    'other2_max': 10.0,
                    'broken_max': 10.0,
                    'discolored_max': 8.0,
                }
            },
            'dominant_short': {
                'High': {
                    'dominant_min': 80.0,
                    'other1_max': 15.0,  # Medium (non-dominant 1)
                    'other2_max': 5.0,   # Long (non-dominant 2)
                    'broken_max': 5.0,
                    'discolored_max': 3.0,
                },
                'Medium': {
                    'dominant_min': 60.0,
                    'other1_max': 30.0,
                    'other2_max': 10.0,
                    'broken_max': 10.0,
                    'discolored_max': 8.0,
                }
            }
        }
    
    def calculate_quality_score(self, df: pd.DataFrame) -> float:
        """
        Calculate overall quality score based on grain composition.
        
        Args:
            df: DataFrame with grain measurements and classifications
            
        Returns:
            float: Quality score between 0.0 and 1.0
        """
        if df.empty:
            return 0.0
        
        # Get class distribution
        class_counts = df['Class'].value_counts()
        total_grains = len(df)
        
        if total_grains == 0:
            return 0.0
        
        # Calculate weighted score
        weighted_sum = 0.0
        for grain_class, count in class_counts.items():
            weight = self.quality_thresholds.get(grain_class, {}).get('weight', 0.5)
            weighted_sum += (count / total_grains) * weight
        
        return weighted_sum
    
    def calculate_percentages(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate percentage distribution of grain types.
        
        Args:
            df: DataFrame with grain classifications
            
        Returns:
            Dict with percentages for each grain type
        """
        if df.empty:
            return {}
        
        class_counts = df['Class'].value_counts()
        total_grains = len(df)
        
        percentages = {}
        for grain_class in self.quality_thresholds.keys():
            count = class_counts.get(grain_class, 0)
            percentages[grain_class] = (count / total_grains) * 100
        
        return percentages
    
    def assess_quality_grade(self, df: pd.DataFrame) -> Dict:
        """
        Assess overall quality grade (High/Medium/Low) based on comprehensive criteria.
        
        Args:
            df: DataFrame with grain measurements and classifications
            
        Returns:
            Dict containing grade, score, explanation, and detailed breakdown
        """
        if df.empty:
            return {
                'grade': 'Low',
                'score': 0.0,
                'explanation': 'No grains detected',
                'counts': {},
                'percents': {},
                'total': 0
            }
        
        # Calculate basic metrics
        total_grains = len(df)
        quality_score = self.calculate_quality_score(df)
        percentages = self.calculate_percentages(df)

        # Count grains by type
        counts = {}
        for grain_class in self.quality_thresholds.keys():
            counts[grain_class] = len(df[df['Class'] == grain_class])
        
        # Determine dominant grain among Long/Medium/Short
        pct_long = percentages.get('Long', 0.0)
        pct_medium = percentages.get('Medium', 0.0)
        pct_short = percentages.get('Short', 0.0)
        pct_broken = percentages.get('Broken', 0.0)
        pct_discolored = percentages.get('Discolored', 0.0)

        dominant = max((pct_long, 'Long'), (pct_medium, 'Medium'), (pct_short, 'Short'))[1]

        # Apply dominant-based thresholds
        def meets_high(dom_pct, other1_pct, other2_pct, broken_pct, discolored_pct, cfg):
            return (
                dom_pct >= cfg['dominant_min'] and
                other1_pct <= cfg['other1_max'] and
                other2_pct <= cfg['other2_max'] and
                broken_pct <= cfg['broken_max'] and
                discolored_pct <= cfg['discolored_max']
            )

        def meets_medium(dom_pct, other1_pct, other2_pct, broken_pct, discolored_pct, cfg):
            return (
                dom_pct >= cfg['dominant_min'] and
                other1_pct <= cfg['other1_max'] and
                other2_pct <= cfg['other2_max'] and
                broken_pct <= cfg['broken_max'] and
                discolored_pct <= cfg['discolored_max']
            )

        if dominant == 'Long':
            cfg = self.grade_thresholds['dominant_long']
            if meets_high(pct_long, pct_medium, pct_short, pct_broken, pct_discolored, cfg['High']):
                grade = 'High'
            elif meets_medium(pct_long, pct_medium, pct_short, pct_broken, pct_discolored, cfg['Medium']):
                grade = 'Medium'
            else:
                grade = 'Low'
        elif dominant == 'Medium':
            cfg = self.grade_thresholds['dominant_medium']
            if meets_high(pct_medium, pct_long, pct_short, pct_broken, pct_discolored, cfg['High']):
                grade = 'High'
            elif meets_medium(pct_medium, pct_long, pct_short, pct_broken, pct_discolored, cfg['Medium']):
                grade = 'Medium'
            else:
                grade = 'Low'
        else:  # Short dominant
            cfg = self.grade_thresholds['dominant_short']
            if meets_high(pct_short, pct_medium, pct_long, pct_broken, pct_discolored, cfg['High']):
                grade = 'High'
            elif meets_medium(pct_short, pct_medium, pct_long, pct_broken, pct_discolored, cfg['Medium']):
                grade = 'Medium'
            else:
                grade = 'Low'

        # Calculate premium grains percentage (Long + Medium + Short)
        premium_percent = pct_long + pct_medium + pct_short
        
        # Generate explanation
        explanation = self._generate_explanation(grade, quality_score, percentages, counts, total_grains)
        
        return {
            'grade': grade,
            'score': round(quality_score, 3),
            'explanation': explanation,
            'counts': counts,
            'percents': percentages,
            'total': total_grains,
            'premium_percent': round(premium_percent, 1)
        }
    
    def _generate_explanation(self, grade: str, score: float, percentages: Dict, 
                             counts: Dict, total: int) -> str:
        """
        Generate human-readable explanation for the quality grade.
        """
        if grade == 'High':
            return f"Excellent quality rice with {percentages.get('Long', 0):.1f}% long grains and {percentages.get('Medium', 0):.1f}% medium grains. Low defect rate with only {percentages.get('Broken', 0):.1f}% broken and {percentages.get('Discolored', 0):.1f}% discolored grains."
        
        elif grade == 'Medium':
            return f"Standard quality rice with {percentages.get('Long', 0):.1f}% long grains and {percentages.get('Medium', 0):.1f}% medium grains. Moderate defect rate with {percentages.get('Broken', 0):.1f}% broken and {percentages.get('Discolored', 0):.1f}% discolored grains."
        
        else:  # Low
            return f"Sub-standard quality rice with high defect rate. Only {percentages.get('Long', 0):.1f}% long and {percentages.get('Medium', 0):.1f}% medium grains. High defect rate with {percentages.get('Broken', 0):.1f}% broken and {percentages.get('Discolored', 0):.1f}% discolored grains."
    
    def get_detailed_analysis(self, df: pd.DataFrame) -> Dict:
        """
        Get detailed analysis including length statistics and quality breakdown.
        
        Args:
            df: DataFrame with grain measurements
            
        Returns:
            Dict with comprehensive analysis
        """
        if df.empty:
            return {}
        
        # Basic quality assessment
        quality_result = self.assess_quality_grade(df)
        
        # Length statistics if available
        length_stats = {}
        if 'Length (mm)' in df.columns:
            length_stats = {
                'mean': round(df['Length (mm)'].mean(), 2),
                'median': round(df['Length (mm)'].median(), 2),
                'std': round(df['Length (mm)'].std(), 2),
                'min': round(df['Length (mm)'].min(), 2),
                'max': round(df['Length (mm)'].max(), 2)
            }
        
        # Width statistics if available
        width_stats = {}
        if 'Width (mm)' in df.columns:
            width_stats = {
                'mean': round(df['Width (mm)'].mean(), 2),
                'median': round(df['Width (mm)'].median(), 2),
                'std': round(df['Width (mm)'].std(), 2),
                'min': round(df['Width (mm)'].min(), 2),
                'max': round(df['Width (mm)'].max(), 2)
            }
        
        return {
            **quality_result,
            'length_stats': length_stats,
            'width_stats': width_stats,
            'quality_thresholds': self.quality_thresholds,
            'grade_thresholds': self.grade_thresholds
        }

def assess_rice_quality_from_csv(csv_path: str) -> Dict:
    """
    Convenience function to assess rice quality from a CSV file.
    
    Args:
        csv_path: Path to CSV file with grain measurements
        
    Returns:
        Dict with quality assessment results
    """
    try:
        df = pd.read_csv(csv_path)
        assessor = RiceQualityAssessor()
        return assessor.get_detailed_analysis(df)
    except Exception as e:
        return {
            'error': str(e),
            'grade': 'Unknown',
            'score': 0.0,
            'explanation': f'Error processing file: {str(e)}'
        }

if __name__ == "__main__":
    # Example usage
    assessor = RiceQualityAssessor()
    
    # Example data
    sample_data = {
        'Class': ['Long', 'Long', 'Medium', 'Medium', 'Short', 'Broken', 'Discolored'],
        'Length (mm)': [7.0, 6.8, 6.0, 5.8, 5.0, 4.5, 6.2],
        'Width (mm)': [2.1, 2.0, 2.2, 2.1, 1.8, 1.5, 2.0]
    }
    
    df = pd.DataFrame(sample_data)
    result = assessor.get_detailed_analysis(df)
    
    print("Quality Assessment Result:")
    print(json.dumps(result, indent=2))
