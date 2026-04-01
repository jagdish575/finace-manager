from django.urls import path
from .views import (
    dashboard_stats,
    dashboard_data,
    financial_summary,
    spending_analysis,
    add_transaction,
    goals_view,
    profile_view,
    homepage_view,
    login_view,
    signup_view,
    logout_view,
)

urlpatterns = [
    path('', homepage_view, name='home'),
    path('login/', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('logout/', logout_view, name='logout'),
    path('dashboard/', dashboard_stats, name='dashboard'),
    path('dashboard-data/', dashboard_data, name='dashboard_data'),
    path('profile/', profile_view, name='frontend_profile'),
    path('financial-summary/', financial_summary, name='financial_summary'),
    path('spending-analysis/', spending_analysis, name='spending_analysis'),
    path('all-transactions/', add_transaction, name='transactions'),
    path('add-transaction/', add_transaction, name='add_transaction'),
    path('goals/', goals_view, name='goals'),
]
