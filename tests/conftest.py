import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

RUBRIC = os.path.join(REPO_ROOT, "rubrics", "cawg-identity-1.3.rubric.yml")
FIXTURES = os.path.join(REPO_ROOT, "fixtures")
