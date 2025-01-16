from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import User, Subscription
from .serializers import RegisterSerializer, SubscriptionSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from datetime import timedelta


# Helper function for creating or updating subscription
def create_or_update_subscription(user, membership_type):
    membership_duration = {'Basic': 30, 'Premium': 365, 'Free': 0}
    duration = membership_duration.get(membership_type, 30)  # Default to 30 days if membership_type is invalid

    subscription, created = Subscription.objects.update_or_create(
        user=user,
        defaults={
            'membership_type': membership_type,
            'purchase_date': timezone.now(),
            'start_date': timezone.now(),
            'end_date': timezone.now() + timedelta(days=duration),
        },
    )
    return subscription


# Helper function to create JWT tokens for authenticated users
def create_jwt_tokens(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


# User Registration View
class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """Handle user registration."""
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Create a free subscription by default
            create_or_update_subscription(user, 'Free')
            return Response({"message": "User registered successfully!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# User Login View
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        """Handle user login and token generation."""
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({"error": "Both email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(request, email=email, password=password)
        if user is not None:
            tokens = create_jwt_tokens(user)
            return Response(tokens, status=status.HTTP_200_OK)

        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


# Subscription View
class SubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve the current user's subscription details."""
        try:
            subscription = Subscription.objects.get(user=request.user)
            serializer = SubscriptionSerializer(subscription)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Subscription.DoesNotExist:
            return Response({"detail": "No active subscription found."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        """Upgrade or create a subscription for the user."""
        membership_type = request.data.get('membership_type')
        if not membership_type:
            return Response({"error": "Membership type is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate membership_type
        valid_memberships = ['Free', 'Basic', 'Premium']
        if membership_type not in valid_memberships:
            return Response({"error": "Invalid membership type."}, status=status.HTTP_400_BAD_REQUEST)

        # Create or update the subscription
        subscription = create_or_update_subscription(request.user, membership_type)
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)

from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'subscription': {
                'membership_type': user.subscription.membership_type if hasattr(user, 'subscription') else 'Free',
                'time_left': user.subscription.time_left if hasattr(user, 'subscription') else None
            }
        }
        return Response(data)
    

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.core.mail import send_mail
from django.conf import settings
import random

class SendOTPView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'message': 'Email is required'}, status=400)
            
        try:
            # Generate OTP
            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            # Store in session
            request.session['otp'] = otp
            request.session['email'] = email
            
            # Send email
            send_mail(
                'Your OTP for Registration',
                f'Your OTP is: {otp}',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return Response({'message': 'OTP sent successfully'})
        except Exception as e:
            print(f"Error sending OTP: {str(e)}")
            return Response({'message': 'Failed to send OTP'}, status=500)

class VerifyOTPRegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        otp = request.data.get('otp')
        stored_otp = request.session.get('otp')
        stored_email = request.session.get('email')
        
        if not stored_otp or not stored_email:
            return Response({'message': 'Please request new OTP'}, status=400)
            
        if otp != stored_otp:
            return Response({'message': 'Invalid OTP'}, status=400)
            
        try:
            # Create user
            user_data = {
                'email': stored_email,
                'password': request.data.get('password'),
                'first_name': request.data.get('first_name'),
                'last_name': request.data.get('last_name')
            }
            User.objects.create_user(**user_data)
            
            # Clear session
            del request.session['otp']
            del request.session['email']
            
            return Response({'message': 'Registration successful'}, status=201)
        except Exception as e:
            print(f"Error registering user: {str(e)}")
            return Response({'message': 'Registration failed'}, status=500)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.utils import timezone
import razorpay
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)

class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            amount = request.data.get('amount')
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            
            order_data = {
                'amount': amount,
                'currency': 'INR',
                'receipt': f'order_{request.user.id}_{timezone.now().timestamp()}'
            }
            
            order = client.order.create(data=order_data)
            return Response(order)
        except Exception as e:
            logger.error(f"Order creation failed: {str(e)}")
            return Response({'error': str(e)}, status=400)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from .models import Subscription
import razorpay
from django.conf import settings

# class VerifyPaymentView(APIView):
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request):
#         try:
#             # Initialize Razorpay client
#             client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
#             # Get payment details
#             payment_data = {
#                 'razorpay_payment_id': request.data.get('razorpay_payment_id'),
#                 'razorpay_order_id': request.data.get('razorpay_order_id'),
#                 'razorpay_signature': request.data.get('razorpay_signature')
#             }
            
#             # Verify signature
#             client.utility.verify_payment_signature(payment_data)
            
#             # Get or create subscription
#             subscription, created = Subscription.objects.get_or_create(
#                 user=request.user,
#                 defaults={
#                     'membership_type': 'Free',
#                     'start_date': timezone.now(),
#                     'end_date': timezone.now() + timedelta(days=5)
#                 }
#             )
            
#             # Update subscription
#             plan_id = request.data.get('plan_id')
#             subscription.membership_type = plan_id
#             subscription.start_date = timezone.now()
#             if plan_id == 'basic':
#                 subscription.end_date = timezone.now() + timedelta(days=30)
#             elif plan_id == 'premium':
#                 subscription.end_date = timezone.now() + timedelta(days=365)
#             subscription.save()
            
            
#             return Response({
#                 'status': 'success',
#                 'message': 'Payment verified successfully',
#                 'subscription': {
#                     'type': subscription.membership_type,
#                     'end_date': subscription.end_date.isoformat()
#                 }
#             })
            
#         except Exception as e:
#             return Response({
#                 'status': 'error',
#                 'message': str(e)
#             }, status=400)
        

# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from django.contrib.auth.models import Permission
# from django.contrib.contenttypes.models import ContentType
# from rest_framework.authtoken.models import Token
# from .models import User, Subscription

# class CustomUserAdmin(BaseUserAdmin):
#     def save_model(self, request, obj, form, change):
#         super().save_model(request, obj, form, change)
#         if obj.is_superuser:
#             # Get token content type
#             token_content_type = ContentType.objects.get_for_model(Token)
#             # Add token delete permission
#             token_permission = Permission.objects.get(
#                 content_type=token_content_type,
#                 codename='delete_token'
#             )
#             obj.user_permissions.add(token_permission)

#     def delete_model(self, request, obj):
#         if request.user.has_perm('authtoken.delete_token'):
#             Token.objects.filter(user=obj).delete()
#             Subscription.objects.filter(user=obj).delete()
#             obj.delete()

#     def delete_queryset(self, request, queryset):
#         if request.user.has_perm('authtoken.delete_token'):
#             Token.objects.filter(user__in=queryset).delete()
#             Subscription.objects.filter(user__in=queryset).delete()
#             queryset.delete()




from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from .models import Subscription
import razorpay
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            # Initialize Razorpay client
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            # Log request data
            logger.info(f"Payment verification request: {request.data}")
            
            # Get payment details
            payment_data = {
                'razorpay_payment_id': request.data.get('razorpay_payment_id'),
                'razorpay_order_id': request.data.get('razorpay_order_id'),
                'razorpay_signature': request.data.get('razorpay_signature')
            }
            
            # Verify signature
            client.utility.verify_payment_signature(payment_data)
            
            # Get plan details
            plan_id = request.data.get('plan_id')
            logger.info(f"Updating subscription for user {request.user.id} to plan {plan_id}")
            
            # Get or create subscription
            subscription = Subscription.objects.filter(user=request.user).first()
            
            if not subscription:
                subscription = Subscription.objects.create(
                    user=request.user,
                    membership_type='Free',
                    start_date=timezone.now(),
                    end_date=timezone.now() + timedelta(days=5)
                )
            
            # Update subscription based on plan
            subscription.membership_type = plan_id.capitalize()  # Ensure proper case
            subscription.start_date = timezone.now()
            
            if plan_id.lower() == 'basic':
                subscription.end_date = timezone.now() + timedelta(days=30)
            elif plan_id.lower() == 'premium':
                subscription.end_date = timezone.now() + timedelta(days=365)
                
            subscription.save()
            logger.info(f"Subscription updated successfully: {subscription.membership_type}")
            
            return Response({
                'status': 'success',
                'message': 'Payment verified and subscription updated',
                'subscription': {
                    'type': subscription.membership_type,
                    'start_date': subscription.start_date,
                    'end_date': subscription.end_date
                }
            })
            
        except Exception as e:
            logger.error(f"Error in payment verification: {str(e)}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=400)


