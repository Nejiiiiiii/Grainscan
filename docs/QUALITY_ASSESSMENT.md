# Rice Quality Assessment System

## Overview

The Rice Quality Assessment System provides comprehensive quality grading for rice samples based on grain composition analysis. It integrates with your existing YOLO-based rice grain detection system to automatically grade rice as **High**, **Medium**, or **Low** quality.

## How It Works

### 1. Grain Classification
Your system already detects and classifies 5 types of rice grains:
- **Long** (6.61-7.50mm) - Premium quality
- **Medium** (5.51-6.60mm) - Standard quality  
- **Short** (0-5.50mm) - Sub-standard quality
- **Broken** - Poor quality
- **Discolored** - Poor quality

### 2. Quality Scoring Algorithm

The system uses a **weighted scoring approach**:

| Grain Type | Weight | Description |
|------------|--------|-------------|
| Long | 1.0 | Premium quality (highest value) |
| Medium | 0.8 | Standard quality (good value) |
| Short | 0.4 | Sub-standard (reduced value) |
| Broken | 0.2 | Poor quality (lowest value) |
| Discolored | 0.3 | Poor quality (appearance defect) |

**Quality Score Formula:**
```
Score = Σ(Count of Grain Type × Weight) / Total Grains
```

### 3. Quality Grading Criteria

#### High Quality (Premium)
- **Minimum Score:** 0.75
- **Max Broken Grains:** 5.0%
- **Max Discolored Grains:** 3.0%
- **Min Premium Grains (Long + Medium):** 60.0%

#### Medium Quality (Standard)
- **Minimum Score:** 0.55
- **Max Broken Grains:** 15.0%
- **Max Discolored Grains:** 10.0%
- **Min Premium Grains (Long + Medium):** 40.0%

#### Low Quality (Sub-standard)
- **Minimum Score:** 0.0
- **Max Broken Grains:** 100.0%
- **Max Discolored Grains:** 100.0%
- **Min Premium Grains (Long + Medium):** 0.0%

## Implementation Details

### Files Created/Modified

1. **`quality_assessment.py`** - Core quality assessment engine
2. **`test_main.py`** - Modified to integrate quality assessment
3. **`test_gui.py`** - Enhanced GUI with detailed quality display
4. **`test_quality_system.py`** - Test script demonstrating the system

### Key Features

#### Quality Assessment Engine (`RiceQualityAssessor`)
- **Comprehensive Analysis:** Evaluates multiple quality factors
- **Weighted Scoring:** Industry-standard grain type weights
- **Defect Tolerance:** Considers broken and discolored grains
- **Premium Grain Focus:** Emphasizes Long + Medium grains

#### Enhanced GUI Display
- **Quality Grade:** Clear High/Medium/Low indication with color coding
- **Quality Score:** Numerical score (0.0-1.0) for precision
- **Detailed Breakdown:** Separate sections for premium and defect grains
- **Statistical Analysis:** Length/width statistics when available
- **Human-Readable Explanations:** Clear reasoning for the grade

#### Integration with Existing System
- **Seamless Integration:** Works with your existing YOLO detection
- **JSON Output:** Structured data for GUI consumption
- **Error Handling:** Graceful fallback if assessment fails
- **Backward Compatibility:** Maintains existing CSV output format

## Usage Examples

### Example 1: High Quality Rice
```
Grain Distribution:
- Long: 3 grains (42.9%)
- Medium: 3 grains (42.9%)
- Short: 1 grains (14.3%)

Result: High Quality (Score: 0.829)
Explanation: Excellent quality rice with 42.9% long grains and 42.9% medium grains. 
Low defect rate with only 0.0% broken and 0.0% discolored grains.
```

### Example 2: Medium Quality Rice
```
Grain Distribution:
- Long: 1 grains (14.3%)
- Medium: 2 grains (28.6%)
- Short: 2 grains (28.6%)
- Broken: 1 grains (14.3%)
- Discolored: 1 grains (14.3%)

Result: Medium Quality (Score: 0.571)
Explanation: Standard quality rice with 14.3% long grains and 28.6% medium grains. 
Moderate defect rate with 14.3% broken and 14.3% discolored grains.
```

### Example 3: Low Quality Rice
```
Grain Distribution:
- Medium: 1 grains (14.3%)
- Short: 2 grains (28.6%)
- Broken: 2 grains (28.6%)
- Discolored: 2 grains (28.6%)

Result: Low Quality (Score: 0.371)
Explanation: Sub-standard quality rice with high defect rate. Only 0.0% long and 14.3% medium grains. 
High defect rate with 28.6% broken and 28.6% discolored grains.
```

## Customization Options

### Adjusting Quality Thresholds
You can modify the grading criteria in `quality_assessment.py`:

```python
self.grade_thresholds = {
    'High': {
        'min_score': 0.75,           # Adjust minimum score
        'max_broken_percent': 5.0,   # Adjust broken grain tolerance
        'max_discolored_percent': 3.0, # Adjust discolored grain tolerance
        'min_premium_percent': 60.0   # Adjust premium grain requirement
    },
    # ... similar for Medium and Low
}
```

### Adjusting Grain Weights
You can modify grain type weights:

```python
self.quality_thresholds = {
    'Long': {
        'weight': 1.0,  # Adjust weight for Long grains
        'description': 'Long grains, premium quality'
    },
    # ... similar for other grain types
}
```

## Testing the System

Run the test script to see the system in action:

```bash
python test_quality_system.py
```

This will demonstrate:
- Different quality scenarios
- Quality thresholds and criteria
- Detailed analysis output
- Statistical breakdown

## Benefits

1. **Objective Assessment:** Consistent, data-driven quality evaluation
2. **Industry Standards:** Based on rice industry quality criteria
3. **Comprehensive Analysis:** Considers multiple quality factors
4. **User-Friendly:** Clear, visual quality indicators
5. **Customizable:** Adjustable thresholds for different requirements
6. **Integrated:** Seamless integration with existing detection system

## Future Enhancements

Potential improvements you could consider:

1. **Regional Standards:** Different quality criteria for different rice varieties
2. **Machine Learning:** Learn optimal thresholds from historical data
3. **Batch Analysis:** Compare multiple samples for consistency
4. **Export Reports:** Generate detailed quality reports
5. **Trend Analysis:** Track quality over time for the same supplier

## Conclusion

The Rice Quality Assessment System provides a robust, industry-standard approach to rice quality evaluation. It transforms your grain detection data into meaningful quality insights, helping users make informed decisions about rice quality quickly and accurately.
