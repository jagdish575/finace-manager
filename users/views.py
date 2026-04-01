from rest_framework import generics, status
from rest_framework.response import Response
from django.contrib.auth import get_user_model, authenticate
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer, SignupSerializer, ProfileSerializer, FinancialDataSerializer
from .models import Profile, FinancialData
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.timezone import now
from notifications.models import Notification

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_data(request):
    user = request.user  # Get the logged-in user
    serializer = UserSerializer(user)  # Convert user object to JSON
    return Response(serializer.data)  # Return JSON response

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_avatar(request):
    profile = request.user.profile
    if 'avatar' in request.FILES:
        profile.avatar = request.FILES['avatar']
        profile.save()
        return Response({"message": "Avatar updated successfully!", "avatar": profile.avatar.url})
    return Response({"error": "No file uploaded"}, status=400)



class SignupView(APIView):
    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class LoginView(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "message": "Login successful"
            }, status=status.HTTP_200_OK)
        
        return Response({"error": "Invalid Credentials"}, status=status.HTTP_401_UNAUTHORIZED)




class ProfileSetupView(generics.RetrieveUpdateAPIView):
    """Handles Profile Setup"""
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return Profile.objects.get_or_create(user=self.request.user)[0]

    def update(self, request, *args, **kwargs):
        profile = self.get_object()
        user = request.user
        user_fields = {}

        if 'first_name' in request.data:
            user_fields['first_name'] = request.data.get('first_name')
        if 'phone_no' in request.data:
            user_fields['phone_no'] = request.data.get('phone_no')

        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if user_fields:
            for field, value in user_fields.items():
                setattr(user, field, value)
            user.save()

        return Response(serializer.data)

class FinancialInputView(generics.RetrieveUpdateAPIView):
    """Handles Financial Inputs"""
    queryset = FinancialData.objects.all()
    serializer_class = FinancialDataSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return FinancialData.objects.get_or_create(user=self.request.user)[0]

class FinancialDataView(generics.RetrieveAPIView):
    serializer_class = FinancialDataSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        data = get_object_or_404(UsersFinancialData, user_id=user_id)
        return Response(self.get_serializer(data).data)



### 🚀 User Profile API ###
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Fetch user profile details including avatar and username.
    """
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)
    
    profile_data = {
        "id": user.id,
        "username": user.username,
        "avatar": profile.avatar.url if profile.avatar else "https://via.placeholder.com/100"
    }
    return JsonResponse(profile_data)

### 🚀 User Notifications API ###
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_notifications(request):
    """
    Fetch notifications for the authenticated user.
    - If recipient is 'all', fetch for all users.
    - If recipient is 'premium' or 'free', fetch based on user's subscription.
    - If recipient is a specific user, fetch only for that user.
    """
    user = request.user
    subscription_type = "premium" if user.is_premium else "free"  # Determine subscription type based on `is_premium` field

    notifications = Notification.objects.filter(
        recipients__in=["all", subscription_type]
    ).order_by('-timestamp')

    notifications_list = [
        {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "status": notification.status,
            "timestamp": notification.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        } for notification in notifications
    ]

    return JsonResponse(notifications_list, safe=False)
