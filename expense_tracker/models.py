from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    expenses = db.relationship('Expense', backref='author', lazy='dynamic')
    budgets = db.relationship('Budget', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    expenses = db.relationship('Expense', backref='category', lazy='dynamic')
    budgets = db.relationship('Budget', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    month = db.Column(db.Integer, nullable=False) # 1-12
    year = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)

    def __repr__(self):
        return f'<Budget {self.amount} for Cat {self.category_id} in {self.month}/{self.year}>'

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    date = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    
    # For shared expenses (simple implementation)
    is_shared = db.Column(db.Boolean, default=False)
    shared_with = db.relationship('SharedExpense', backref='original_expense', lazy='dynamic')

    def __repr__(self):
        return f'<Expense {self.amount} on {self.date}>'

class SharedExpense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expense.id'), nullable=False)
    owed_by_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount_owed = db.Column(db.Float, nullable=False)
    settled = db.Column(db.Boolean, default=False)

    owed_by = db.relationship('User', foreign_keys=[owed_by_user_id])

    def __repr__(self):
        return f'<SharedExpense {self.amount_owed} owed by {self.owed_by_user_id}>'
