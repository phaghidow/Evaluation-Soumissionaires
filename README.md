# Procurement Offer Evaluation Desktop App

A business-focused desktop application built in Python with PyQt5 for managing bid dossiers, technical qualification, financial review, and final export of procurement evaluation reports.

This project simulates a procurement workflow where a user can manage suppliers, bids, lots, technical checks, and final ranking decisions in a structured and traceable way. It is designed for a French public-sector or tender-evaluation context, where validation rules, lot constraints, and document export quality are critical.

## Project purpose

The application supports the end-to-end lifecycle of a call for tenders:

- registering applicants and their submitted lots
- recording offer data and timing constraints
- validating lot-level minimum delay requirements
- importing DQE/Excel product data
- evaluating technical eligibility and qualification
- processing financial amounts and ranking
- exporting the final results in a readable Word document

The workflow is organized around a clear sequence rather than a loose collection of screens:

1. Dossier
2. Offers
3. Technical evaluation
4. Qualification
5. Financial review
6. Export

## Key features

- PyQt5-based desktop interface with a guided navigation flow
- SQLite database persistence for workflow state and business records
- Lot-aware validation rules to prevent inconsistent delay values
- Automatic import of DQE structure and product references from Excel
- Technical and financial evaluation modules
- Audit history for business actions and key status changes
- Document export in Word format with table formatting optimized for readability
- Focus on user experience, validation stability, and workflow clarity

## Tech stack

- Python 3
- PyQt5
- SQLite
- openpyxl
- python-docx
- unittest

## Repository structure

- `app.py` — main desktop application entry point
- `database.py` — central database logic and workflow persistence
- `input_validation.py` — validation rules for lot-based constraints
- `offer_management.py` — offer summary and selection workflows
- `offer_edit.py` — editing and maintenance of offer-related records
- `technical_evaluation.py` — technical evaluation workflow
- `financial/` — financial modules and ranking logic
- `word_export.py` — Word report generation and table formatting
- `tests/` — workflow and UI validation tests
- `requirements.txt` — Python dependencies

## Installation

1. Clone the repository.
2. Create a virtual environment.
3. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Run the application

```bash
python app.py
```

## Run tests

```bash
python -m unittest discover -s tests -q
```

## Business context

This project was built around a real-world tender management scenario, where procurement teams need a reliable system to track submissions, validate offers, and make decisions based on technical and financial criteria. The solution is especially relevant for organizations managing multiple lots, multiple suppliers, and strict business rules that cannot be left to manual interpretation.

## Portfolio value

This project demonstrates a strong combination of:

- business process automation
- desktop UI design with PyQt5
- data integrity and validation logic
- database modeling with SQLite
- document generation and reporting
- workflow architecture for a complex operational process

It is a solid example of a full-stack-like desktop application built around real operational needs, not just a toy demo.

## Status

The project is in a functional, validated state and includes automated checks for the main workflow and UI interactions.

## Publishing to GitHub

After creating a remote repository on GitHub, run:

```bash
git init
git branch -M main
git add .
git commit -m "Initial portfolio commit"
git remote add origin <your-github-repository-url>
git push -u origin main
```

## License

This project is licensed under the GNU General Public License v3.0. See [LICENSE](LICENSE) for the complete terms.
