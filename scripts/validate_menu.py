from pathlib import Path
import sys
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from mass_catering.repository import list_recipe_names
from mass_catering.validation import Severity, validate_menu

menu_file = Path(sys.argv[1])

with menu_file.open() as f:
    menu = yaml.safe_load(f)

issues = validate_menu(
    menu,
    set(list_recipe_names())
)

for issue in issues:
    print(
        f"{issue.severity.value.upper():11} "
        f"{issue.location}: {issue.message}"
    )

errors = [
    i for i in issues
    if i.severity == Severity.ERROR
]

print()
print(f"Issues: {len(issues)}")
print(f"Errors: {len(errors)}")

sys.exit(1 if errors else 0)