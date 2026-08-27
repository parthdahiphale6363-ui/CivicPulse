import sys
sys.path.append('.')
from app import determine_priority

# Test 1: Standard pothole with image and time bonus (should cap at 79)
priority, score, factors = determine_priority("Pothole", "A big pothole on the road", False, True, False)
print(f"Test 1 Score: {score}, Priority: {priority}")
print(factors)

# Test 2: Standard pothole with emergency keyword (should reach Urgent)
priority, score, factors = determine_priority("Pothole", "A big pothole on the road causing an accident", False, True, False)
print(f"Test 2 Score: {score}, Priority: {priority}")
print(factors)

# Test 3: Standard pothole with emergency checkbox (should reach Urgent)
priority, score, factors = determine_priority("Pothole", "A big pothole on the road", True, True, False)
print(f"Test 3 Score: {score}, Priority: {priority}")
print(factors)
