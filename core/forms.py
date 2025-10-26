from django import forms
from .models import CustomUser, Category
from django.contrib.auth.forms import AuthenticationForm

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Password", min_length=8)  # Add password field

    class Meta:
        model = CustomUser
        fields = ['name', 'dob', 'gender', 'email', 'phone', 'aadhaar_no', 'address', 'income', 'occupation', 'education', 'password']  # Include password
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'income': forms.NumberInput(attrs={'step': '0.01'}),
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
        self.fields['username'].label = 'Email'  # Label as "Email"
        self.fields['username'].help_text = None
        self.fields['password'].label = 'Password'
        self.fields['password'].help_text = None