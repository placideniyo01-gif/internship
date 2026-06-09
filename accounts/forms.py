from django import forms


class OTPForm(forms.Form):

    otp = forms.CharField(
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter OTP"
            }
        )
    )


class ForgotPasswordForm(forms.Form):

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Email Address"
            }
        )
    )


class ResetPasswordForm(forms.Form):

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "New Password"
            }
        )
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm Password"
            }
        )
    )