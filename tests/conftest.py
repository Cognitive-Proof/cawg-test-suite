import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

FIXTURES = os.path.join(REPO_ROOT, "fixtures")

# Statement category -> built rubric.
RUBRICS = {
    "identity": os.path.join(REPO_ROOT, "rubrics", "cawg-identity-1.3.rubric.yml"),
    "metadata": os.path.join(REPO_ROOT, "rubrics", "cawg-metadata-1.1.rubric.yml"),
    "training-mining": os.path.join(REPO_ROOT, "rubrics", "cawg-training-mining-1.1.rubric.yml"),
}
