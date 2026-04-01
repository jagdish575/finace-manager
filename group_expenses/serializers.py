from rest_framework import serializers
from .models import Group, GroupExpense, GroupMember, Settlement


from rest_framework import serializers
from .models import Group, GroupExpense, GroupMember, Settlement

class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name', 'description', 'created_at']

class GroupExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupExpense
        fields = ['id', 'group', 'description', 'category', 'amount', 'date', 'split_type', 'paid_by', 'split_members', 'split_amount']

class GroupMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = GroupMember
        fields = ['id', 'group', 'user', 'joined_at']

class SettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settlement
        fields = ['id', 'group', 'expense', 'member', 'amount', 'settled']
