from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .models import CustomUser, Category


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