from django.urls import path
from . import views

app_name = 'group_expenses'

urlpatterns = [
    path('', views.group_expenses_view, name='group_expenses'),
    path('<int:group_id>/', views.group_dashboard, name='group_dashboard'),
    path('<int:group_id>/add-expense/', views.add_expense, name='add_expense'),
]
