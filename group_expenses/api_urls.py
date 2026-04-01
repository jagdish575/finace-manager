from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import GroupViewSet, GroupExpenseViewSet, GroupMemberViewSet, SettlementViewSet

router = DefaultRouter()
router.register(r'groups', GroupViewSet)
router.register(r'group-expenses', GroupExpenseViewSet)
router.register(r'group-members', GroupMemberViewSet)
router.register(r'settlements', SettlementViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
