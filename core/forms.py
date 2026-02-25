from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .models import CustomUser, Category, Scheme



class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Min. 8 characters'}),
        label="Password", min_length=8
    )
    class Meta:
        model = CustomUser
        fields = ['name', 'dob', 'gender', 'email', 'phone', 'aadhaar_no',
                  'address', 'income', 'occupation', 'education', 'password']
        widgets = {
            'name':       forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'dob':        forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender':     forms.Select(attrs={'class': 'form-select'},
                          choices=[('', 'Select gender'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]),
            'email':      forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'you@example.com'}),
            'phone':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 XXXXX XXXXX'}),
            'aadhaar_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'XXXX XXXX XXXX'}),
            'address':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your address'}),
            'income':     forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0', 'placeholder': 'Annual income (Rs.)'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Farmer, Teacher'}),
            'education':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 10th Pass, Graduate'}),
        }


class CategorySelectionForm(forms.Form):
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="Select Beneficiary Categories"
    )


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email'
        self.fields['username'].help_text = None
        self.fields['username'].widget.attrs.update({'class': 'form-control', 'placeholder': 'you@example.com'})
        self.fields['password'].label = 'Password'
        self.fields['password'].help_text = None
        self.fields['password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Your password'})


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        label='Registered Email',
        widget=forms.EmailInput(attrs={
            'class': 'form-control', 'placeholder': 'you@example.com', 'autofocus': True,
        })
    )


class OTPVerifyForm(forms.Form):
    otp = forms.CharField(
        label='Enter 6-digit OTP',
        max_length=6, min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control otp-input',
            'placeholder': '------',
            'autocomplete': 'one-time-code',
            'inputmode': 'numeric',
            'maxlength': '6',
            'autofocus': True,
        })
    )
    def clean_otp(self):
        otp = self.cleaned_data['otp']
        if not otp.isdigit():
            raise forms.ValidationError('OTP must contain digits only.')
        return otp


class ResetPasswordForm(forms.Form):
    password = forms.CharField(
        label='New Password', min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'placeholder': 'At least 8 characters', 'autofocus': True,
        })
    )
    password_confirm = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 'placeholder': 'Repeat password',
        })
    )
    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password_confirm'):
            raise forms.ValidationError('Passwords do not match.')
        return cleaned


class ChangePasswordForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs.update({'class': 'form-control'})
            f.help_text = None
        self.fields['old_password'].widget.attrs['placeholder'] = 'Current password'
        self.fields['new_password1'].widget.attrs['placeholder'] = 'New password (min 8 chars)'
        self.fields['new_password2'].widget.attrs['placeholder'] = 'Confirm new password'


# ── NEW: Grievance Form ────────────────────────────────────────────────────
class GrievanceForm(forms.Form):
    """
    scheme_queryset is passed dynamically from the view — only the user's
    eligible schemes appear in the dropdown.
    """
    scheme = forms.ModelChoiceField(
        queryset=Scheme.objects.none(),   # overridden in __init__
        required=False,
        empty_label='— General (not scheme-specific) —',
        label='Related Scheme (optional)',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    complaint = forms.CharField(
        label='Describe your grievance',
        min_length=20,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Describe your issue in detail (minimum 20 characters)...',
        })
    )

    def __init__(self, *args, scheme_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        if scheme_queryset is not None:
            self.fields['scheme'].queryset = scheme_queryset


# ── Edit Profile Form ──────────────────────────────────────────────────────
class EditProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['name', 'dob', 'gender', 'phone', 'address', 'income', 'occupation', 'education']
        widgets = {
            'name':       forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full Name'}),
            'dob':        forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender':     forms.Select(attrs={'class': 'form-select'},
                          choices=[('', 'Select gender'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')]),
            'phone':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 XXXXX XXXXX'}),
            'address':    forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your address'}),
            'income':     forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0', 'placeholder': 'Annual income (Rs.)'}),
            'occupation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Farmer, Teacher'}),
            'education':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 10th Pass, Graduate'}),
        }


# ── Admin Scheme Form ──────────────────────────────────────────────────────
class SchemeForm(forms.ModelForm):
    class Meta:
        model = Scheme
        fields = ['scheme_name', 'description', 'target_category', 'eligibility_rules', 'benefits', 'official_link', 'registration_link', 'benefit_type', 'state', 'is_active']
        widgets = {
            'scheme_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'target_category': forms.Select(attrs={'class': 'form-control'}),
            'eligibility_rules': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'benefits': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'official_link': forms.URLInput(attrs={'class': 'form-control'}),
            'registration_link': forms.URLInput(attrs={'class': 'form-control'}),
            'benefit_type': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }