from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from transactions.models import Category, Transaction, Budget, BudgetHistory
from insights.models import BudgetInsight, SavingsGoal
from group_expenses.models import Group, GroupMember, GroupExpense, Settlement
from users.models import FinancialData, Profile

User = get_user_model()

class Command(BaseCommand):
    help = 'Seed demo data for users, transactions, insights, savings, and group expenses.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding demo data...')

        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)
        first_of_month = today.replace(day=1)

        # Users
        alice, _ = User.objects.get_or_create(
            email='alice@example.com',
            defaults={
                'username': 'alice',
                'password': 'password123',
                'phone_no': '9876543210',
                'is_premium': True,
                'role': 'user',
            }
        )
        bob, _ = User.objects.get_or_create(
            email='bob@example.com',
            defaults={
                'username': 'bob',
                'password': 'password123',
                'phone_no': '9123456780',
                'is_premium': False,
                'role': 'user',
            }
        )
        carol, _ = User.objects.get_or_create(
            email='carol@example.com',
            defaults={
                'username': 'carol',
                'password': 'password123',
                'phone_no': '9012345678',
                'is_premium': False,
                'role': 'user',
            }
        )

        for user in [alice, bob, carol]:
            user.set_password('password123')
            user.save()

        # FinancialData and Profile
        for user, occupation, income in [
            (alice, 'Employee', '100K+'),
            (bob, 'Business', '50K-100K'),
            (carol, 'Student', '10K-50K'),
        ]:
            FinancialData.objects.get_or_create(
                user=user,
                defaults={
                    'monthly_income_salary': 60000 if user == alice else 35000 if user == bob else 15000,
                    'monthly_income_business': 0 if user == alice else 12000,
                    'monthly_income_freelance': 0 if user != bob else 5000,
                    'monthly_income_other': 2000,
                    'rent': 12000 if user == alice else 15000 if user == bob else 5000,
                    'bills': 6000,
                    'loans': 5000,
                    'subscriptions': 1500,
                    'savings_cash': 12000,
                    'savings_stocks': 8000,
                    'savings_crypto': 2000,
                    'savings_real_estate': 0,
                    'total_debt': 10000,
                }
            )
            Profile.objects.get_or_create(
                user=user,
                defaults={
                    'preferred_currency': 'INR',
                    'date_of_birth': today.replace(year=today.year - 28),
                    'occupation': occupation,
                    'annual_income': income,
                    'financial_goal': 'Savings',
                    'investment_risk': 'Medium',
                    'subscription_plan': 'Premium' if user == alice else 'Free',
                }
            )

        # Categories
        income_category_alice, _ = Category.objects.get_or_create(user=alice, name='Salary - Alice')
        food_category_alice, _ = Category.objects.get_or_create(user=alice, name='Food & Dining - Alice')
        rent_category_alice, _ = Category.objects.get_or_create(user=alice, name='Rent - Alice')
        income_category_bob, _ = Category.objects.get_or_create(user=bob, name='Salary - Bob')
        travel_category_bob, _ = Category.objects.get_or_create(user=bob, name='Travel - Bob')
        utilities_category_carol, _ = Category.objects.get_or_create(user=carol, name='Utilities - Carol')

        # Transactions
        Transaction.objects.get_or_create(
            user=alice,
            amount=75000,
            category=income_category_alice,
            category_type='income',
            description='March salary',
            date=first_of_month,
        )
        Transaction.objects.get_or_create(
            user=alice,
            amount=-2200,
            category=food_category_alice,
            category_type='expense',
            description='Grocery shopping',
            date=yesterday,
        )
        Transaction.objects.get_or_create(
            user=alice,
            amount=-12000,
            category=rent_category_alice,
            category_type='expense',
            description='Home rent',
            date=last_week,
        )
        Transaction.objects.get_or_create(
            user=bob,
            amount=82000,
            category=income_category_bob,
            category_type='income',
            description='Freelance payout',
            date=first_of_month,
        )
        Transaction.objects.get_or_create(
            user=bob,
            amount=-1800,
            category=travel_category_bob,
            category_type='expense',
            description='Taxi fare',
            date=yesterday,
        )
        Transaction.objects.get_or_create(
            user=carol,
            amount=-750,
            category=utilities_category_carol,
            category_type='expense',
            description='Mobile bill',
            date=yesterday,
        )

        # Budget and budget history
        Budget.objects.get_or_create(user=alice, category='Food', monthly_limit=8000)
        Budget.objects.get_or_create(user=alice, category='Rent', monthly_limit=15000)
        BudgetHistory.objects.get_or_create(
            user=alice,
            category='Food',
            month=today.month,
            year=today.year,
            defaults={
                'previous_limit': 9000,
                'actual_spent': 2200,
                'suggested_limit': 8000,
            }
        )

        # Insights and savings goals
        BudgetInsight.objects.get_or_create(
            user=alice,
            category='Food',
            defaults={
                'average_spending': 5400,
                'forecasted_spending': 5000,
                'savings_recommendation': 'Reduce dining out and cook more meals at home.',
                'created_at': today,
            }
        )
        SavingsGoal.objects.get_or_create(
            user=alice,
            goal_name='Vacation Fund',
            defaults={
                'target_amount': 25000,
                'saved_amount': 12000,
                'deadline': today.replace(month=today.month + 2 if today.month <= 10 else 12),
                'status': 'In Progress',
                'created_at': today,
            }
        )

        # Group expenses demo data
        demo_group, _ = Group.objects.get_or_create(
            name='Weekend Trip',
            defaults={
                'description': 'Planning a weekend getaway with friends.',
            }
        )
        alice_member, _ = GroupMember.objects.get_or_create(group=demo_group, user=alice)
        bob_member, _ = GroupMember.objects.get_or_create(group=demo_group, user=bob)
        carol_member, _ = GroupMember.objects.get_or_create(group=demo_group, user=carol)

        dinner_expense, _ = GroupExpense.objects.get_or_create(
            group=demo_group,
            description='Dinner at Lakeside',
            amount=5400,
            category='Food',
            date=yesterday,
            split_type='equal',
            paid_by=alice_member,
            split_amount=1800,
        )
        dinner_expense.split_members.set([alice_member, bob_member, carol_member])

        Settlement.objects.get_or_create(
            group=demo_group,
            expense=dinner_expense,
            member=alice_member,
            amount=1800,
            defaults={'settled': True},
        )
        Settlement.objects.get_or_create(
            group=demo_group,
            expense=dinner_expense,
            member=bob_member,
            amount=1800,
            defaults={'settled': False},
        )
        Settlement.objects.get_or_create(
            group=demo_group,
            expense=dinner_expense,
            member=carol_member,
            amount=1800,
            defaults={'settled': False},
        )

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))
