from django import forms
from .models import Withdrawal


class WithdrawalForm(forms.ModelForm):

    class Meta:
        model = Withdrawal

        fields = [
            "amount",
            "wallet_address"
        ]

        widgets = {
            "wallet_address": forms.TextInput(
                attrs={
                    "placeholder":
                    "TRC20 Wallet Address"
                }
            )
        }