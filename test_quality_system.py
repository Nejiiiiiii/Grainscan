#!/usr/bin/env python3
"""
Test script for the Rice Quality Assessment System
This script demonstrates how the quality assessment works with sample data.
"""

import pandas as pd
import json
from quality_assessment import RiceQualityAssessor

def test_quality_assessment():
    """Test the quality assessment system with different scenarios."""
    
    assessor = RiceQualityAssessor()
    
    # Test scenarios
    test_cases = [
        {
            'name': 'High Quality Rice',
            'data': {
                'Class': ['Long', 'Long', 'Long', 'Medium', 'Medium', 'Medium', 'Short'],
                'Length (mm)': [7.0, 6.9, 6.8, 6.2, 6.0, 5.9, 5.2],
                'Width (mm)': [2.1, 2.0, 2.1, 2.2, 2.1, 2.0, 1.8]
            }
        },
        {
            'name': 'Medium Quality Rice',
            'data': {
                'Class': ['Long', 'Medium', 'Medium', 'Short', 'Short', 'Broken', 'Discolored'],
                'Length (mm)': [6.8, 6.0, 5.8, 5.0, 4.8, 4.0, 6.2],
                'Width (mm)': [2.0, 2.1, 2.0, 1.8, 1.7, 1.5, 2.0]
            }
        },
        {
            'name': 'Low Quality Rice',
            'data': {
                'Class': ['Medium', 'Short', 'Short', 'Broken', 'Broken', 'Discolored', 'Discolored'],
                'Length (mm)': [5.8, 4.5, 4.2, 3.5, 3.0, 5.5, 5.0],
                'Width (mm)': [2.0, 1.6, 1.5, 1.2, 1.0, 1.8, 1.7]
            }
        }
    ]
    
    print("Rice Quality Assessment System - Test Results")
    print("=" * 60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        print("-" * 40)
        
        df = pd.DataFrame(test_case['data'])
        result = assessor.get_detailed_analysis(df)
        
        print(f"Grade: {result['grade']}")
        print(f"Score: {result['score']:.3f}")
        print(f"Total Grains: {result['total']}")
        print(f"Premium Grains: {result['premium_percent']:.1f}%")
        print(f"Explanation: {result['explanation']}")
        
        print("\nGrain Distribution:")
        for grain_type, count in result['counts'].items():
            if count > 0:
                percent = result['percents'][grain_type]
                print(f"  {grain_type}: {count} grains ({percent:.1f}%)")
        
        if result.get('length_stats'):
            stats = result['length_stats']
            print(f"\nLength Statistics:")
            print(f"  Mean: {stats['mean']}mm, Median: {stats['median']}mm")
            print(f"  Std Dev: {stats['std']}mm, Range: {stats['min']}-{stats['max']}mm")

def test_quality_thresholds():
    """Test the quality thresholds and grading criteria."""
    
    assessor = RiceQualityAssessor()
    
    print("\n" + "=" * 60)
    print("Quality Thresholds and Grading Criteria")
    print("=" * 60)
    
    print("\nGrain Type Weights:")
    for grain_type, config in assessor.quality_thresholds.items():
        print(f"  {grain_type}: Weight = {config['weight']}, {config['description']}")
    
    print("\nGrade Thresholds:")
    for grade, criteria in assessor.grade_thresholds.items():
        print(f"  {grade} Quality:")
        print(f"    - Minimum Score: {criteria['min_score']}")
        print(f"    - Max Broken: {criteria['max_broken_percent']}%")
        print(f"    - Max Discolored: {criteria['max_discolored_percent']}%")
        print(f"    - Min Premium Grains: {criteria['min_premium_percent']}%")

if __name__ == "__main__":
    test_quality_assessment()
    test_quality_thresholds()
    
    print("\n" + "=" * 60)
    print("Quality Assessment System Ready!")
    print("=" * 60)
    print("The system will now:")
    print("1. Analyze grain composition from your YOLO detections")
    print("2. Calculate quality scores based on grain types")
    print("3. Grade rice as High/Medium/Low quality")
    print("4. Provide detailed explanations and statistics")
    print("5. Display results in the GUI with enhanced visualization")
