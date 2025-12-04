from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, User, Category, Budget, Expense
from datetime import datetime
from sqlalchemy import func

main_bp = Blueprint('main', __name__)

# Mock current user
CURRENT_USER_ID = 1

@main_bp.route('/')
def index():
    # Ensure a user exists
    if not User.query.get(CURRENT_USER_ID):
        user = User(username='testuser', email='test@example.com')
        db.session.add(user)
        db.session.commit()

    today = datetime.today()
    try:
        current_month = int(request.args.get('month', today.month))
        current_year = int(request.args.get('year', today.year))
    except ValueError:
        current_month = today.month
        current_year = today.year

    # Monthly total (Selected Month)
    total_spent = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == CURRENT_USER_ID,
        func.extract('month', Expense.date) == current_month,
        func.extract('year', Expense.date) == current_year
    ).scalar() or 0.0

    # All Months Summary
    monthly_data = db.session.query(
        func.extract('month', Expense.date).label('month'),
        func.extract('year', Expense.date).label('year'),
        func.sum(Expense.amount).label('total')
    ).filter(
        Expense.user_id == CURRENT_USER_ID
    ).group_by(
        func.extract('year', Expense.date),
        func.extract('month', Expense.date)
    ).order_by(
        func.extract('year', Expense.date).desc(),
        func.extract('month', Expense.date).desc()
    ).all()

    monthly_summaries = []
    for m, y, total in monthly_data:
        monthly_summaries.append({
            'month': int(m),
            'year': int(y),
            'total': total
        })

    # Fetch available months for the dropdown (same logic as reports)
    expense_months = db.session.query(func.extract('month', Expense.date).label('month'), func.extract('year', Expense.date).label('year')).filter_by(user_id=CURRENT_USER_ID).distinct()
    budget_months = db.session.query(Budget.month, Budget.year).filter_by(user_id=CURRENT_USER_ID).distinct()
    
    available_months = set()
    for m, y in expense_months:
        available_months.add((int(m), int(y)))
    for m, y in budget_months:
        available_months.add((int(m), int(y)))
    
    available_months = sorted(list(available_months), key=lambda x: (x[1], x[0]), reverse=True)
    if (current_month, current_year) not in available_months:
        available_months.insert(0, (current_month, current_year))

    # Recent expenses
    expenses = Expense.query.filter_by(user_id=CURRENT_USER_ID).order_by(Expense.date.desc()).limit(5).all()

    return render_template('index.html', total_spent=total_spent, expenses=expenses, current_month=f"{current_month}/{current_year}", monthly_summaries=monthly_summaries, available_months=available_months, current_month_int=current_month, current_year_int=current_year)

@main_bp.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    categories = Category.query.all()
    if request.method == 'POST':
        amount = float(request.form['amount'])
        category_id = int(request.form['category_id'])
        description = request.form['description']
        date_str = request.form['date']
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        split_with_email = request.form.get('split_with')
        custom_category_name = request.form.get('custom_category')

        # Check if "Other" was selected and custom name provided
        selected_category = Category.query.get(category_id)
        if selected_category and selected_category.name == 'Other' and custom_category_name:
            # Check if custom category already exists
            existing_category = Category.query.filter(func.lower(Category.name) == func.lower(custom_category_name)).first()
            if existing_category:
                category_id = existing_category.id
            else:
                new_category = Category(name=custom_category_name)
                db.session.add(new_category)
                db.session.commit()
                category_id = new_category.id

        expense = Expense(
            amount=amount,
            category_id=category_id,
            description=description,
            date=date_obj,
            user_id=CURRENT_USER_ID
        )
        db.session.add(expense)
        db.session.commit()

        if split_with_email:
            # Find or create the other user
            other_user = User.query.filter_by(email=split_with_email).first()
            if not other_user:
                other_user = User(username=split_with_email.split('@')[0], email=split_with_email)
                db.session.add(other_user)
                db.session.commit()
            
            # Create shared expense (50/50 split)
            split_amount = amount / 2
            from models import SharedExpense
            shared = SharedExpense(
                expense_id=expense.id,
                owed_by_user_id=other_user.id,
                amount_owed=split_amount
            )
            expense.is_shared = True
            db.session.add(shared)
            db.session.commit()
            flash(f'Expense split with {split_with_email}. You paid ${amount}, they owe ${split_amount}.', 'info')

        # Check budget
        check_budget_alert(category_id, date_obj.month, date_obj.year)

        flash('Expense added successfully!', 'success')
        return redirect(url_for('main.index'))

    return render_template('add_expense.html', categories=categories, today=datetime.today().strftime('%Y-%m-%d'))

@main_bp.route('/set_budget', methods=['GET', 'POST'])
def set_budget():
    categories = Category.query.all()
    today = datetime.today()
    
    if request.method == 'POST':
        category_id = int(request.form['category_id'])
        amount = float(request.form['amount'])
        month = int(request.form['month'])
        year = int(request.form['year'])

        # Check if budget exists
        budget = Budget.query.filter_by(
            user_id=CURRENT_USER_ID,
            category_id=category_id,
            month=month,
            year=year
        ).first()

        if budget:
            budget.amount = amount
        else:
            budget = Budget(
                user_id=CURRENT_USER_ID,
                category_id=category_id,
                amount=amount,
                month=month,
                year=year
            )
            db.session.add(budget)
        
        db.session.commit()
        flash('Budget set successfully!', 'success')
        return redirect(url_for('main.reports'))

    return render_template('set_budget.html', categories=categories, current_month=today.month, current_year=today.year)

@main_bp.route('/reports')
def reports():
    # Get month/year from query params or default to current
    today = datetime.today()
    try:
        month = int(request.args.get('month', today.month))
        year = int(request.args.get('year', today.year))
    except ValueError:
        month = today.month
        year = today.year

    # Fetch available months for the dropdown
    # Union of months from Expenses and Budgets
    expense_months = db.session.query(func.extract('month', Expense.date).label('month'), func.extract('year', Expense.date).label('year')).filter_by(user_id=CURRENT_USER_ID).distinct()
    budget_months = db.session.query(Budget.month, Budget.year).filter_by(user_id=CURRENT_USER_ID).distinct()
    
    available_months = set()
    for m, y in expense_months:
        available_months.add((int(m), int(y)))
    for m, y in budget_months:
        available_months.add((int(m), int(y)))
    
    # Sort descending
    available_months = sorted(list(available_months), key=lambda x: (x[1], x[0]), reverse=True)
    
    # If current month not in list (e.g. new user), add it
    if (month, year) not in available_months:
        available_months.insert(0, (month, year))

    categories = Category.query.all()
    report_data = []

    for cat in categories:
        # Get budget
        budget = Budget.query.filter_by(
            user_id=CURRENT_USER_ID,
            category_id=cat.id,
            month=month,
            year=year
        ).first()
        
        budget_amount = budget.amount if budget else 0.0

        # Get actual spent
        spent = db.session.query(func.sum(Expense.amount)).filter(
            Expense.user_id == CURRENT_USER_ID,
            Expense.category_id == cat.id,
            func.extract('month', Expense.date) == month,
            func.extract('year', Expense.date) == year
        ).scalar() or 0.0

        remaining = budget_amount - spent
        
        status = 'OK'
        if budget_amount > 0:
            if spent > budget_amount:
                status = 'Exceeded'
            elif spent > 0.9 * budget_amount:
                status = 'Warning'

        report_data.append({
            'category': cat.name,
            'budget': budget_amount,
            'spent': spent,
            'remaining': remaining,
            'status': status
        })

    return render_template('reports.html', report_data=report_data, current_month=month, current_year=year, available_months=available_months)

@main_bp.route('/download_report')
def download_report():
    from xhtml2pdf import pisa
    from io import BytesIO, StringIO
    from flask import make_response
    import csv

    today = datetime.today()
    
    # Handle month_year param (e.g., "12-2025") or separate args
    month_year = request.args.get('month_year')
    if month_year:
        try:
            month, year = map(int, month_year.split('-'))
        except ValueError:
            month, year = today.month, today.year
    else:
        try:
            month = int(request.args.get('month', today.month))
            year = int(request.args.get('year', today.year))
        except ValueError:
            month = today.month
            year = today.year

    file_format = request.args.get('format', 'pdf')

    # Fetch Data
    expenses = Expense.query.filter(
        Expense.user_id == CURRENT_USER_ID,
        func.extract('month', Expense.date) == month,
        func.extract('year', Expense.date) == year
    ).order_by(Expense.date).all()

    total_spent = sum(e.amount for e in expenses)

    # Budget Summary
    categories = Category.query.all()
    budget_summary = []
    for cat in categories:
        budget = Budget.query.filter_by(user_id=CURRENT_USER_ID, category_id=cat.id, month=month, year=year).first()
        budget_amount = budget.amount if budget else 0.0
        spent = sum(e.amount for e in expenses if e.category_id == cat.id)
        remaining = budget_amount - spent
        status = 'OK'
        if budget_amount > 0:
            if spent > budget_amount: status = 'Exceeded'
            elif spent > 0.9 * budget_amount: status = 'Warning'
        
        budget_summary.append({
            'category': cat.name,
            'budget': budget_amount,
            'spent': spent,
            'remaining': remaining,
            'status': status
        })

    if file_format == 'csv':
        si = StringIO()
        cw = csv.writer(si)
        
        cw.writerow([f'Expense Report for {month}/{year}'])
        cw.writerow([])
        cw.writerow(['Date', 'Category', 'Description', 'Amount'])
        for e in expenses:
            cw.writerow([e.date.strftime('%Y-%m-%d'), e.category.name, e.description, f"{e.amount:.2f}"])
        
        cw.writerow([])
        cw.writerow(['Total Spent', f"{total_spent:.2f}"])
        cw.writerow([])
        cw.writerow(['Budget Summary'])
        cw.writerow(['Category', 'Budget', 'Spent', 'Remaining', 'Status'])
        for item in budget_summary:
            cw.writerow([item['category'], f"{item['budget']:.2f}", f"{item['spent']:.2f}", f"{item['remaining']:.2f}", item['status']])
            
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=report_{month}_{year}.csv"
        output.headers["Content-type"] = "text/csv"
        return output

    else: # PDF
        html = render_template('pdf_report.html', 
                             expenses=expenses, 
                             total_spent=total_spent, 
                             budget_summary=budget_summary,
                             month=month, 
                             year=year)
        
        pdf = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=pdf)
        
        if pisa_status.err:
            return 'We had some errors <pre>' + html + '</pre>'
        
        pdf.seek(0)
        response = make_response(pdf.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=report_{month}_{year}.pdf'
        return response

def check_budget_alert(category_id, month, year):
    budget = Budget.query.filter_by(
        user_id=CURRENT_USER_ID,
        category_id=category_id,
        month=month,
        year=year
    ).first()

    if not budget:
        return

    spent = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == CURRENT_USER_ID,
        Expense.category_id == category_id,
        func.extract('month', Expense.date) == month,
        func.extract('year', Expense.date) == year
    ).scalar() or 0.0

    if spent > budget.amount:
        flash(f'ALERT: You have exceeded your budget for {budget.category.name}!', 'danger')
        send_email_notification(f"Budget Exceeded: {budget.category.name}")
    elif spent > 0.9 * budget.amount:
        flash(f'WARNING: You have used over 90% of your budget for {budget.category.name}!', 'warning')
        send_email_notification(f"Budget Warning: {budget.category.name} is 90% used")

def send_email_notification(message):
    # Mock email sending
    print(f"--------------------------------------------------")
    print(f"SENDING EMAIL TO user@example.com: {message}")
    print(f"--------------------------------------------------")
