from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from accounts.views import (
    RegisterView, LoginView, LogoutView, MeView, SendCodeView, UserAPIKeyView,
    ForgotPasswordView, ResetPasswordView, GuestLoginView,
)

urlpatterns = [
    path('send-code/', csrf_exempt(SendCodeView.as_view())),
    path('register/', csrf_exempt(RegisterView.as_view())),
    path('login/', csrf_exempt(LoginView.as_view())),
    path('guest/', csrf_exempt(GuestLoginView.as_view())),
    path('logout/', csrf_exempt(LogoutView.as_view())),
    path('me/', csrf_exempt(MeView.as_view())),
    path('user-api-key/', csrf_exempt(UserAPIKeyView.as_view())),
    path('forgot-password/', csrf_exempt(ForgotPasswordView.as_view())),
    path('reset-password/', csrf_exempt(ResetPasswordView.as_view())),
]
