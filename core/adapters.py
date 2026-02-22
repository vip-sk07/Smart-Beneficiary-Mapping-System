from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User


class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter that sets username = email when allauth creates a Django
    auth.User via Google OAuth, preventing the duplicate-empty-username error.
    """

    def pre_social_login(self, request, sociallogin):
        """
        Called after OAuth handshake but before Django user is created/linked.
        If a Django user with this email already exists, connect the social
        account to it instead of creating a duplicate.
        """
        email = sociallogin.account.extra_data.get('email', '').lower().strip()
        if not email:
            return

        try:
            existing_user = User.objects.get(email=email)
            # Link the Google account to the existing Django user
            sociallogin.connect(request, existing_user)
        except User.DoesNotExist:
            pass

    def save_user(self, request, sociallogin, form=None):
        """
        Called when allauth creates a new Django user via social login.
        Sets username = email so it's never empty.
        """
        user = super().save_user(request, sociallogin, form)
        if not user.username:
            email = user.email or ''
            # Truncate to 150 chars (Django's username max_length)
            user.username = email[:150]
            user.save(update_fields=['username'])
        return user