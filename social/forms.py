from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Post, Profile, Report


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=False, help_text="Optional; never shown publicly.")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("display_name", "bio")
        widgets = {"bio": forms.Textarea(attrs={"rows": 4})}


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("body",)
        widgets = {"body": forms.Textarea(attrs={"rows": 4, "maxlength": 1000, "placeholder": "Share something…"})}

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("A post cannot be empty.")
        return body


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ("reason",)
        widgets = {"reason": forms.TextInput(attrs={"maxlength": 200})}

    def clean_reason(self):
        reason = self.cleaned_data["reason"].strip()
        if not reason:
            raise forms.ValidationError("Please provide a reason.")
        return reason
