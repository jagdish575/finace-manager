from django.contrib import admin
from group_expenses.models import Group, GroupMember, GroupExpense, Settlement

admin.site.register(Group)
admin.site.register(GroupMember)
admin.site.register(GroupExpense)
admin.site.register(Settlement)
