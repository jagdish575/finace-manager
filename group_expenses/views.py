from rest_framework import viewsets
from .models import Group, GroupExpense, GroupMember, Settlement
from .serializers import GroupSerializer, GroupExpenseSerializer, GroupMemberSerializer, SettlementSerializer
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse
from datetime import datetime


def group_expenses_view(request):
    groups = Group.objects.all()
    if groups.exists():
        return redirect('group_expenses:group_dashboard', group_id=groups.first().id)
    return render(request, 'frontend/group_expenses.html', {'groups': groups, 'group': None})



# View to render the group dashboard
def group_dashboard(request, group_id):
    try:
        group = Group.objects.get(id=group_id)
        groups = Group.objects.all()

        return render(request, 'frontend/group_expenses.html', {
            'groups': groups,
            'group': group,
        })
    except Group.DoesNotExist:
        return render(request, 'error.html', {'error': 'Group not found'})

# Add a new expense to the group
def add_expense(request, group_id):
    if request.method == 'POST':
        description = request.POST.get('description')
        amount = float(request.POST.get('amount') or 0)
        category = request.POST.get('category')
        date = request.POST.get('date')
        split_type = request.POST.get('splitType')
        paid_by = request.POST.get('paid_by')  # ID of the member who paid

        if not description or amount <= 0:
            return render(request, 'frontend/group_expenses.html', {
                'error': 'Description and amount are required.',
                'groups': Group.objects.all(),
                'group': Group.objects.filter(id=group_id).first(),
            })

        expense = GroupExpense.objects.create(
            group_id=group_id,
            description=description,
            amount=amount,
            category=category,
            date=date,
            split_type=split_type or 'equal',
            paid_by_id=paid_by,
        )

        members = GroupMember.objects.filter(group_id=group_id)
        expense.split_members.set(members)

        if members.exists():
            split_amount = amount / members.count()
            for member in members:
                Settlement.objects.create(
                    group_id=group_id,
                    member_id=member.id,
                    amount=split_amount,
                    expense=expense,
                )

        return HttpResponseRedirect(reverse('group_expenses:group_dashboard', args=[group_id]))

    return redirect('group_expenses:group_dashboard', group_id=group_id)

# ViewSet for managing groups
class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer

# ViewSet for managing group expenses
class GroupExpenseViewSet(viewsets.ModelViewSet):
    queryset = GroupExpense.objects.all()
    serializer_class = GroupExpenseSerializer

# ViewSet for managing group members
class GroupMemberViewSet(viewsets.ModelViewSet):
    queryset = GroupMember.objects.all()
    serializer_class = GroupMemberSerializer

# ViewSet for managing settlements
class SettlementViewSet(viewsets.ModelViewSet):
    queryset = Settlement.objects.all()
    serializer_class = SettlementSerializer
