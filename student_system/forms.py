from django.contrib.auth.forms import PasswordChangeForm


class StyledPasswordChangeForm(PasswordChangeForm):
    """PasswordChangeForm with Bootstrap styling applied to all widgets."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control form-control-lg'})
        self.fields['old_password'].widget.attrs.update({'autofocus': True, 'placeholder': 'Current password'})
        self.fields['new_password1'].widget.attrs.update({'placeholder': 'New password'})
        self.fields['new_password2'].widget.attrs.update({'placeholder': 'Confirm new password'})
