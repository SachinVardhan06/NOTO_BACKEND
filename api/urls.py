from django.urls import path
from .views import RegisterView, LoginView, SubscriptionView,ProfileView,SendOTPView,VerifyOTPRegisterView,CreateOrderView,VerifyPaymentView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('subscription/', SubscriptionView.as_view(), name='subscription'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('verify-otp-register/', VerifyOTPRegisterView.as_view(), name='verify-otp-register'),
    path('create-order/', CreateOrderView.as_view(), name='create-order'),
    path('verify-payment/', VerifyPaymentView.as_view(), name='verify-payment'),
]
