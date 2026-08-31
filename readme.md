# 🍲 Mass Catering

Mass Catering is a recipe scaling, menu planning and shopping-list generation tool designed for catering large groups.

It was originally developed to support hostel and expedition-style catering, where meals need to be scaled for varying group sizes while maintaining a single source of truth for recipes and provisioning.

The application can:

- Scale recipes automatically based on attendance.
- Support multiple meals across multiple days.
- Generate aggregated shopping lists.
- Handle shared ingredients across recipes.
- Generate chef-friendly recipe packs as PDF documents.
- Validate menus before compilation.
- Detect likely duplicate ingredient names.
- Support browser-based menu uploads via YAML.
- Export shopping lists and catering packs.

---

# 🌐 Live Application

The latest hosted version is available at:

**https://mass-catering-planner.streamlit.app/**

The web application allows users to:

- Select existing menus.
- Upload new YAML menus.
- Paste YAML menus directly.
- Validate catering plans.
- Generate shopping lists.
- Download shopping lists as Markdown.
- Download complete catering packs as PDF.

---

# ✨ Features

## Menu Planning

A menu consists of one or more catering events:

```yaml
events:
  - day: Saturday
    meal: Dinner
    people: 20

    dishes:
      - recipe: fish_pie

      - recipe: vegan_fish_pie
        people: 2
```

Recipes can be scaled using:

- Event attendance
- Dish-specific attendance overrides

This is useful when most attendees eat one meal but a smaller group requires a vegetarian or vegan alternative.

---

## Recipe Scaling

Recipes are stored once and scaled automatically.

Example:

```yaml
name: Fish Pie
serves: 6

ingredients:
  potato: 1000 g
  salmon: 400 g
```

If 18 people are attending, quantities are scaled automatically.

---

## Shopping List Generation

Multiple recipes are compiled into a single shopping list:

```text
potato        12.4 kg
milk           4.2 l
salmon         2.8 kg
```

Identical ingredients are aggregated automatically.

---

## General Provisions

General catering supplies can be added outside scheduled meals.

Example:

```yaml
general_provisions:
  - recipe: hostel

  - recipe: hostel_by_people
    people: 38
```

This allows weekend-wide provisioning such as:

- Tea
- Coffee
- Biscuits
- Cleaning supplies
- Kitchen consumables

---

## PDF Catering Packs

The application generates a complete PDF including:

- Menu overview
- Weekend schedule
- General provisions
- Scaled recipes
- Chef preparation notes
- Shopping lists

This provides a complete catering pack for the cooking team.

---

## Validation

The system validates menus before compilation.

### Structural Validation

Checks:

- Missing fields
- Invalid menu structure
- Missing recipe references
- Invalid attendance values

### Ingredient Validation

The validator can detect likely duplicates such as:

```text
banana
bananas
```

and suggest user review.

It can also identify probable spelling mistakes such as:

```text
coriander
corriander
```

Warnings never modify quantities automatically.

---

## Helpful Error Messages

Compilation errors include:

- Recipe name
- Expected recipe file
- Event context
- Ingredient name
- Invalid value

Example:

```text
Could not compile recipe 'game_stew'

File:
recipe/game_stew.yaml

Context:
Saturday - Dinner

Ingredient:
thyme

Value:
'2 spring'

Reason:
Could not parse quantity
```

This makes recipe debugging straightforward.

---

# 📁 Project Structure

```text
MassCatering/

├── streamlit_app.py
├── requirements.txt
├── pyproject.toml
├── food.yaml
├── unit_registry.txt
│
├── menu/
│   ├── hostel_feb26.yaml
│   ├── hostel_oct26.yaml
│   └── ...
│
├── recipe/
│   ├── fish_pie.yaml
│   ├── vegan_fish_pie.yaml
│   └── ...
│
├── mass_catering/
│   ├── compiler.py
│   ├── pdf.py
│   ├── rendering.py
│   ├── repository.py
│   ├── units.py
│   └── validation.py
│
└── tests/
```

---

# 📋 Menu Format

Menus use schema version 2.

Example:

```yaml
schema_version: 2

name: Hostel Oct26

events:
  - day: Friday
    meal: Dinner
    people: 17

    dishes:
      - recipe: fish_pie

      - recipe: vegan_fish_pie
        people: 2
```

---

# 📖 Recipe Format

Recipes are stored as YAML.

Example:

```yaml
name: Fish Pie

serves: 6

ingredients:
  salmon: 400 g
  potato: 1000 g
  milk: 600 ml

method: |
  Prepare the filling.
  Top with mashed potato.
  Bake until golden.
```

---

# 🚀 Running Locally

Clone the repository:

```bash
git clone git@github.com:djmoffat/MassCateringWebapp.git
cd MassCateringWebapp
```

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
streamlit run streamlit_app.py
```

---

# ✅ Running Tests

Execute the complete test suite:

```bash
pytest -v
```

The project includes tests covering:

- Menu validation
- Ingredient validation
- Recipe scaling
- Shopping list compilation
- Quantity handling
- Rendering
- PDF generation

---

# ☁️ Deployment

The application is currently deployed using Streamlit Community Cloud.

Required Python dependencies:

```text
streamlit
PyYAML
pint
rapidfuzz
reportlab
```

Updates are automatically deployed when changes are pushed to GitHub.

---

# 🗺️ Roadmap

Potential future developments include:

- Browser-based menu editor
- Browser-based recipe editor
- Ingredient catalogue management
- Unit conversion administration tools
- Shopping lists grouped by supplier
- Cost estimation
- Nutritional analysis
- Printable meal cards
- Multi-user recipe repositories
- GitHub-backed menu submission workflows

---

# 🤝 Contributing

Contributions, bug reports and recipe improvements are welcome.

Suggested workflow:

1. Create a feature branch.
2. Add or update tests.
3. Run:

   ```bash
   pytest -v
   ```

4. Submit a pull request.

---

# 📜 Licence

This project is intended to support outdoor education, expeditions, hostels and community catering activities.

Please refer to the repository licence for usage terms.

---

# 🙏 Acknowledgements

Mass Catering was inspired by the practical challenges of planning meals for:

- Outdoor centres
- Hostels
- Scout camps
- Field expeditions
- Community events
- Residential training courses

where recipe scaling, provisioning and shopping logistics quickly become difficult to manage manually.

The project aims to make large-group catering simpler, more repeatable and less error-prone.