from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg
from django.db import IntegrityError
from django.http import JsonResponse
from datetime import datetime, timedelta
from users.models import User, Profile
from transactions.models import Transaction, Category
from group_expenses.models import Settlement
from insights.models import BudgetInsight, SavingsGoal
from django.contrib.auth import authenticate, login, logout
import json


def get_unique_username(base_username):
    candidate = base_username
    counter = 1
    while User.objects.filter(username=candidate).exists():
        candidate = f"{base_username}{counter}"
        counter += 1
    return candidate


def homepage_view(request):
    """Render the public homepage for guests or redirect authenticated users."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'frontend/homepage.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error_message = None
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        error_message = 'Invalid email or password.'

    return render(request, 'frontend/login.html', {'error_message': error_message})


def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    error_message = None
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        phone_number = request.POST.get('phone_number')

        if password != confirm_password:
            error_message = 'Passwords do not match.'
        elif User.objects.filter(username=username).exists():
            error_message = 'This username is already taken. Please choose another.'
        elif User.objects.filter(email=email).exists():
            error_message = 'A user with this email already exists.'
        else:
            username_value = username.strip() if username else email.split('@')[0]
            username_value = get_unique_username(username_value)
            try:
                user = User.objects.create_user(
                    username=username_value,
                    email=email,
                    password=password,
                    phone_no=phone_number,
                )
                login(request, user)
                return redirect('dashboard')
            except IntegrityError:
                error_message = 'Unable to create account. Please try a different username or email.'

    return render(request, 'frontend/signup.html', {'error_message': error_message})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard_stats(request):
    active_users = User.objects.filter(last_login__gte=datetime.now() - timedelta(days=30)).count()

    total_spending = BudgetInsight.objects.aggregate(Sum('average_spending'))['average_spending__sum'] or 0
    forecasted_spending = BudgetInsight.objects.aggregate(Sum('forecasted_spending'))['forecasted_spending__sum'] or 0
    accuracy_rate = round((forecasted_spending / total_spending) * 100, 2) if total_spending else 0

    total_settlements = Settlement.objects.filter(settled=True).count()
    total_transactions = Settlement.objects.count()
    support_availability = round((total_settlements / total_transactions) * 100, 2) if total_transactions else 0

    today = datetime.now()
    current_month = today.month
    last_month = (today - timedelta(days=30)).month

    monthly_savings = SavingsGoal.objects.filter(created_at__month=current_month).aggregate(Sum('saved_amount'))['saved_amount__sum'] or 0
    last_month_savings = SavingsGoal.objects.filter(created_at__month=last_month).aggregate(Sum('saved_amount'))['saved_amount__sum'] or 0
    savings_growth = round(((monthly_savings - last_month_savings) / last_month_savings) * 100, 2) if last_month_savings else 0

    investment_users = BudgetInsight.objects.values('user_id').distinct().count()
    investment_users_list = BudgetInsight.objects.values('user_id').distinct()[:5]  # Fetch 5 sample users

    average_roi = BudgetInsight.objects.aggregate(Avg('forecasted_spending'))['forecasted_spending__avg'] or 0

    savings_goal_total = SavingsGoal.objects.filter(user=request.user).aggregate(Sum('target_amount'))['target_amount__sum'] or 0
    savings_goal_saved = SavingsGoal.objects.filter(user=request.user).aggregate(Sum('saved_amount'))['saved_amount__sum'] or 0
    savings_progress = round((savings_goal_saved / savings_goal_total) * 100, 2) if savings_goal_total else 0

    total_balance = Transaction.objects.filter(user=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
    monthly_income = Transaction.objects.filter(user=request.user, amount__gt=0, date__month=current_month).aggregate(Sum('amount'))['amount__sum'] or 0
    monthly_expenses = Transaction.objects.filter(user=request.user, amount__lt=0, date__month=current_month).aggregate(Sum('amount'))['amount__sum'] or 0

    last_month_balance = Transaction.objects.filter(user=request.user, date__month=last_month).aggregate(Sum('amount'))['amount__sum'] or 0
    balance_change = round(((total_balance - last_month_balance) / last_month_balance) * 100, 2) if last_month_balance else 0

    last_month_income = Transaction.objects.filter(user=request.user, amount__gt=0, date__month=last_month).aggregate(Sum('amount'))['amount__sum'] or 0
    income_change = round(((monthly_income - last_month_income) / last_month_income) * 100, 2) if last_month_income else 0

    last_month_expenses = Transaction.objects.filter(user=request.user, amount__lt=0, date__month=last_month).aggregate(Sum('amount'))['amount__sum'] or 0
    expense_change = round(((monthly_expenses - last_month_expenses) / abs(last_month_expenses)) * 100, 2) if last_month_expenses else 0

    context = {
        'active_users': active_users,
        'accuracy_rate': accuracy_rate,
        'support_availability': support_availability,
        'monthly_savings': monthly_savings,
        'savings_growth': savings_growth,
        'investment_users': investment_users,
        'investment_users_list': investment_users_list,
        'average_roi': average_roi,
        'savings_progress': savings_progress,
        'total_balance': total_balance,
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
        'balance_change': balance_change,
        'income_change': income_change,
        'expense_change': expense_change,
    }

    return render(request, 'frontend/dashboard.html', context)


@login_required
def dashboard_data(request):
    today = datetime.today()
    current_month = today.month
    last_month = (today - timedelta(days=30)).month

    total_balance = Transaction.objects.filter(user=request.user).aggregate(Sum('amount'))['amount__sum'] or 0
    monthly_income = Transaction.objects.filter(user=request.user, amount__gt=0, date__month=current_month).aggregate(Sum('amount'))['amount__sum'] or 0
    monthly_expenses = Transaction.objects.filter(user=request.user, amount__lt=0, date__month=current_month).aggregate(Sum('amount'))['amount__sum'] or 0

    last_month_balance = Transaction.objects.filter(user=request.user, date__month=last_month).aggregate(Sum('amount'))['amount__sum'] or 0
    last_month_income = Transaction.objects.filter(user=request.user, amount__gt=0, date__month=last_month).aggregate(Sum('amount'))['amount__sum'] or 0
    last_month_expenses = Transaction.objects.filter(user=request.user, amount__lt=0, date__month=last_month).aggregate(Sum('amount'))['amount__sum'] or 0

    balance_change = round(((total_balance - last_month_balance) / last_month_balance) * 100, 2) if last_month_balance else 0
    income_change = round(((monthly_income - last_month_income) / last_month_income) * 100, 2) if last_month_income else 0
    expense_change = round(((monthly_expenses - last_month_expenses) / abs(last_month_expenses)) * 100, 2) if last_month_expenses else 0

    return JsonResponse({
        'total_balance': float(total_balance),
        'monthly_income': float(monthly_income),
        'monthly_expenses': float(monthly_expenses),
        'balance_change': balance_change,
        'income_change': income_change,
        'expense_change': expense_change,
    })


@login_required
def financial_summary(request):
    user = request.user  

    today = datetime.today()
    current_month = today.month
    last_month = (today - timedelta(days=30)).month

    total_balance = Transaction.objects.filter(user=user).aggregate(Sum('amount'))['amount__sum'] or 0

    monthly_income = Transaction.objects.filter(user=user, amount__gt=0, date__month=current_month).aggregate(Sum('amount'))['amount__sum'] or 0

    monthly_expenses = Transaction.objects.filter(user=user, amount__lt=0, date__month=current_month).aggregate(Sum('amount'))['amount__sum'] or 0

    last_month_balance = Transaction.objects.filter(user=user, date__month=last_month).aggregate(Sum('amount'))['amount__sum'] or 0
    balance_change = round(((total_balance - last_month_balance) / last_month_balance) * 100, 2) if last_month_balance else 0

    last_month_income = Transaction.objects.filter(user=user, amount__gt=0, date__month=last_month).aggregate(Sum('amount'))['amount__sum'] or 0
    income_change = round(((monthly_income - last_month_income) / last_month_income) * 100, 2) if last_month_income else 0

    last_month_expenses = Transaction.objects.filter(user=user, amount__lt=0, date__month=last_month).aggregate(Sum('amount'))['amount__sum'] or 0
    expense_change = round(((monthly_expenses - last_month_expenses) / last_month_expenses) * 100, 2) if last_month_expenses else 0

    total_goal = SavingsGoal.objects.filter(user=user).aggregate(Sum('target_amount'))['target_amount__sum'] or 0
    total_savings = SavingsGoal.objects.filter(user=user).aggregate(Sum('saved_amount'))['saved_amount__sum'] or 0
    savings_progress = round((total_savings / total_goal) * 100, 2) if total_goal else 0

    context = {
        'total_balance': total_balance,
        'balance_change': balance_change,
        'monthly_income': monthly_income,
        'income_change': income_change,
        'monthly_expenses': monthly_expenses,
        'expense_change': expense_change,
        'savings_progress': savings_progress,
    }

    return render(request, 'dashboard.html', context) 





@login_required
def add_transaction(request):
    categories = Category.objects.all()
    context = {
        'categories': categories,
    }
    return render(request, 'frontend/transaction.html', context)


@login_required
def spending_analysis(request):
    user_id = request.user.id
    period = request.GET.get('period', 'month')

    # Determine date range
    today = datetime.today().date()
    if period == 'week':
        start_date = today - timedelta(days=today.weekday())
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
    else:  # Default to month
        start_date = today.replace(day=1)

    transactions = Transaction.objects.filter(user_id=user_id, date__gte=start_date)

    # Group by date
    datewise_income = transactions.filter(category_type="income").values('date').annotate(total=Sum('amount'))
    datewise_expense = transactions.filter(category_type="expense").values('date').annotate(total=Sum('amount'))

    # Prepare chart data
    dates = [entry['date'].strftime('%Y-%m-%d') for entry in datewise_income]  # Convert date to string
    income = [entry['total'] for entry in datewise_income]
    expenses = [entry['total'] for entry in datewise_expense]

    # Expense category breakdown
    expense_categories = transactions.filter(category_type="expense").values('category_id').annotate(total=Sum('amount'))
    category_data = [
        {"category": Category.objects.get(id=entry["category_id"]).name, "amount": entry["total"]}
        for entry in expense_categories
    ]

    # Monthly expense trend
    monthly_expenses = transactions.filter(category_type="expense").extra({'month': "EXTRACT(MONTH FROM date)"}).values('month').annotate(total=Sum('amount'))
    months = [f"Month {entry['month']}" for entry in monthly_expenses]
    monthly_totals = [entry['total'] for entry in monthly_expenses]

    context = {
        "dates": dates,
        "income": income,
        "expenses": expenses,
        "expense_categories": category_data,
        "months": months,
        "monthly_expenses": monthly_totals,
    }

    return JsonResponse(context, safe=False)


@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return render(request, 'frontend/profile.html', {
        'user': request.user,
        'profile': profile,
    })


@login_required
def goals_view(request):
    return render(request, 'frontend/goals.html')


