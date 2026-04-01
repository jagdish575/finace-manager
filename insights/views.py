import json
import os
import requests
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import BudgetInsight, SavingsGoal
from .serializers import BudgetInsightSerializer
from .utils import get_spending_insights, predict_future_spending, suggest_savings, track_savings_progress
from transactions.models import Transaction, Budget, BudgetHistory, alerts

GEMINI_API_KEY = getattr(settings, 'GEMINI_API_KEY', '')
GEMINI_MODEL = "gemini-1.5-mini"


def generate_gemini_insights(prompt_text):
    if not GEMINI_API_KEY:
        return None

    api_url = f"https://generativelanguage.googleapis.com/v1beta2/models/{GEMINI_MODEL}:generate?key={GEMINI_API_KEY}"
    payload = {
        "prompt": {"text": prompt_text},
        "temperature": 0.7,
        "maxOutputTokens": 250,
    }

    try:
        response = requests.post(api_url, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        candidates = result.get("candidates", [])
        if candidates:
            return candidates[0].get("output", "").strip()
    except requests.RequestException:
        return None

    return None


@login_required
def spending_insights_view(request):
    """API to get spending insights."""
    insights = get_spending_insights(request.user)
    return JsonResponse({"spending_insights": insights}, safe=False)


@login_required
def forecast_spending_view(request, category):
    """API to predict future spending for a given category."""
    forecast = predict_future_spending(request.user, category)
    return JsonResponse({"forecasted_spending": forecast})


@login_required
def savings_suggestions_view(request):
    """API to provide cost-saving recommendations."""
    suggestions = suggest_savings(request.user)
    return JsonResponse({"savings_recommendations": suggestions})


@csrf_exempt
@login_required
def add_savings_goal(request):
    """API to create a new savings goal."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method."}, status=405)

    data = json.loads(request.body)
    goal = SavingsGoal.objects.create(
        user=request.user,
        goal_name=data.get("goal_name", "New Goal"),
        target_amount=data.get("target_amount", 0),
        deadline=datetime.strptime(data.get("deadline", now().strftime("%Y-%m-%d")), "%Y-%m-%d").date(),
    )
    return JsonResponse({"message": "Goal created successfully!", "goal_id": str(goal.id)})


@login_required
def get_savings_progress(request):
    """API to fetch user's savings goals and progress."""
    track_savings_progress(request.user)
    goals = SavingsGoal.objects.filter(user=request.user).values(
        "id", "goal_name", "target_amount", "saved_amount", "deadline", "status", "created_at"
    )
    return JsonResponse({"goals": list(goals)}, safe=False)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_goal_savings(request):
    """API to manually update savings for a goal."""
    user = request.user
    goal_id = request.data.get("goal_id")
    saved_amount = request.data.get("saved_amount")

    try:
        goal = SavingsGoal.objects.get(id=goal_id, user=user)
        goal.saved_amount = saved_amount
        goal.update_progress()
        goal.save()

        if goal.saved_amount >= goal.target_amount:
            alerts.objects.create(
                user=user,
                message=f"🎉 Congratulations! You have completed your savings goal: {goal.goal_name}",
                is_read=False,
            )

        return Response({"message": "Goal updated successfully."})
    except SavingsGoal.DoesNotExist:
        return Response({"error": "Goal not found."}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def ai_insights(request):
    """Generates AI insights based on budget history and spending patterns."""
    user = request.user
    last_30_days = now() - timedelta(days=30)

    budget_history = BudgetHistory.objects.filter(user=user)
    insights = []

    for record in budget_history:
        category = record.category
        prev_limit = float(record.previous_limit or 0)
        spent = float(record.actual_spent or 0)
        suggested = float(record.suggested_limit or 0)

        if spent > prev_limit:
            insights.append({
                "title": f"Overspending in {category}",
                "message": f"You spent ₹{spent:.2f}, exceeding your ₹{prev_limit:.2f} budget.",
                "suggested_budget": suggested,
                "category": category,
                "action_url": "#",
            })
        else:
            insights.append({
                "title": f"Good budget control in {category}",
                "message": f"You stayed within your ₹{prev_limit:.2f} budget. Suggested new budget: ₹{suggested:.2f}.",
                "suggested_budget": suggested,
                "category": category,
                "action_url": "#",
            })

    if not insights:
        insights.append({
            "title": "Start saving smarter",
            "message": "Add budgets or goals so AI can provide recommendations based on your spending patterns.",
            "suggested_budget": 0,
            "category": "General",
            "action_url": "#",
        })

    prompt_text = (
        "Provide three short actionable personal finance tips for a user based on recent spending habits and savings goals. "
        "Keep the recommendations concise and friendly."
    )
    gemini_response = generate_gemini_insights(prompt_text)
    if gemini_response:
        insights.insert(0, {
            "title": "AI-powered recommendation",
            "message": gemini_response,
            "suggested_budget": 0,
            "category": "General",
            "action_url": "#",
        })

    return Response(insights)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_suggested_budget(request):
    """Updates the user's budget with the AI-suggested limit."""
    user = request.user
    category = request.data.get("category")
    new_limit = request.data.get("new_limit")

    if not category or new_limit is None:
        return Response({"error": "Missing category or new limit"}, status=status.HTTP_400_BAD_REQUEST)

    budget, _ = Budget.objects.get_or_create(user=user, category=category)
    budget.monthly_limit = new_limit
    budget.save()

    return Response({"message": f"Budget updated successfully for {category}!", "new_limit": new_limit})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def finance_chat(request):
    """Finance-focused chat endpoint for the dashboard AI assistant."""
    user = request.user
    prompt = request.data.get("message", "").strip()
    if not prompt:
        return Response({"error": "Please send a valid message."}, status=status.HTTP_400_BAD_REQUEST)

    assistant_prompt = (
        "You are a helpful personal finance assistant focused on budgeting, savings, spending, and smart money management. "
        "Give clear, friendly, actionable advice for goals, budgets, and expense control. "
        f"User: {prompt}\nAssistant:"
    )

    reply = generate_gemini_insights(assistant_prompt)
    if not reply:
        reply = (
            "I couldn't reach the AI service right now, but I can still help with finance tips. "
            "Try asking about budgeting, saving, tracking expenses, or planning your next financial move."
        )

    return Response({"reply": reply})


class BudgetInsightView(generics.ListAPIView):
    serializer_class = BudgetInsightSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BudgetInsight.objects.filter(user_id=self.kwargs['user_id'])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_savings_insights(request):
    """Fetch AI-based savings recommendations for the user."""
    user = request.user
    insights = BudgetInsight.objects.filter(user=user).order_by('-created_at')

    insights_list = [
        {
            "category": insight.category,
            "average_spending": float(insight.average_spending),
            "forecasted_spending": float(insight.forecasted_spending),
            "savings_recommendation": insight.savings_recommendation,
        }
        for insight in insights
    ]

    return Response(insights_list, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_savings_projections(request):
    """Fetch monthly savings projections based on past spending trends."""
    user = request.user
    current_year = now().year
    current_month = now().month

    budget_history = (
        BudgetHistory.objects
        .filter(user=user, year=current_year)
        .values('month')
        .annotate(total_saved=Sum('suggested_limit'))
        .order_by('month')
    )

    total_budget = (
        Budget.objects
        .filter(user=user)
        .aggregate(total_budget=Sum('monthly_limit'))
    )['total_budget'] or 0

    months = []
    savings_data = []

    for entry in budget_history:
        month_name = datetime(current_year, entry['month'], 1).strftime('%b')
        months.append(month_name)
        savings_data.append(float(entry['total_saved'] or 0))

    for i in range(1, 4):
        future_month = (current_month + i - 1) % 12 + 1
        future_month_name = datetime(current_year, future_month, 1).strftime('%b')
        months.append(future_month_name)
        savings_data.append(float(savings_data[-1] + total_budget if savings_data else total_budget))

    return Response({"months": months, "amounts": savings_data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_monthly_savings_history(request):
    """Fetch monthly savings history for the user."""
    user = request.user
    savings_history = (
        BudgetHistory.objects
        .filter(user=user)
        .values('month', 'year')
        .annotate(
            total_saved=Sum('suggested_limit'),
            actual_spent=Sum('actual_spent'),
            previous_limit=Sum('previous_limit')
        )
        .order_by('year', 'month')
    )

    history_list = [
        {
            "month": datetime(year=entry['year'], month=entry['month'], day=1).strftime('%b %Y'),
            "total_saved": float(entry['total_saved'] or 0),
            "actual_spent": float(entry['actual_spent'] or 0),
            "previous_limit": float(entry['previous_limit'] or 0),
        }
        for entry in savings_history
    ]

    return Response(history_list)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    """Fetch unread notifications for the user."""
    notifications = alerts.objects.filter(user=request.user, is_read=False).order_by('-created_at')
    notifications_list = [
        {"id": n.id, "message": n.message, "created_at": n.created_at.strftime("%Y-%m-%d %H:%M:%S")} for n in notifications
    ]
    return Response(notifications_list)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_notifications_read(request):
    """Mark all notifications as read."""
    alerts.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({"message": "Notifications marked as read."})
