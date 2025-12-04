# Expense Tracker

A Python-based Expense Tracker application built with Flask and SQLAlchemy.

## Features
- Log daily expenses with categories.
- Set monthly budgets per category.
- Dashboard with monthly summary and recent expenses.
- Reports showing Budget vs Actuals.
- **Alerts**: Visual and Email (mock) alerts when budget is exceeded or >90% used.
- **Expense Sharing**: Split expenses with other users (Splitwise-like).
- **Dockerized**: Easy to build and run.

## Setup & Run

### Prerequisites
- Python 3.9+
- Docker (optional)

### Local Setup
1. Clone the repository.
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python app.py
   ```
5. Open http://localhost:5000 in your browser.

### Docker Setup
1. Build the image:
   ```bash
   docker build -t expense-tracker .
   ```
2. Run the container:
   ```bash
   docker run -p 5000:5000 expense-tracker
   ```

## Testing
To validate the application:
1. **Dashboard**: Open the home page. It should show $0.00 spent initially.
2. **Set Budget**: Go to "Set Budget". Select "Food", Amount 100, current month/year. Submit.
3. **Add Expense**: Go to "Add Expense". Select "Food", Amount 50. Submit.
   - Dashboard should show $50 spent.
   - Reports should show $50 remaining.
4. **Trigger Warning**: Add another "Food" expense for $45 (Total $95).
   - You should see a warning alert "90% used".
5. **Trigger Alert**: Add another "Food" expense for $10 (Total $105).
   - You should see a danger alert "Budget Exceeded".
   - Console should show "SENDING EMAIL...".
6. **Split Expense**: Add expense, enter an email in "Split with".
   - Flash message should confirm the split.

## Technical Details
- **Backend**: Flask
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML/Jinja2 with Bootstrap 5
