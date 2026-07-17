from django import forms
from accounts.models import Role
from .models import Announcement, Message

ROLE_CHOICES = [
    (Role.SUPER_ADMIN, 'Super Administrator'),
    (Role.ICT_ADMIN, 'ICT Administrator'),
    (Role.PRINCIPAL, 'Principal'),
    (Role.VICE_PRINCIPAL, 'Vice Principal'),
    (Role.ADMISSION_OFFICER, 'Admission Officer'),
    (Role.ACCOUNTANT, 'Accountant'),
    (Role.TEACHER, 'Teacher'),
    (Role.CLASS_TEACHER, 'Class Teacher'),
    (Role.STUDENT, 'Student'),
    (Role.PARENT, 'Parent'),
]


class AnnouncementForm(forms.ModelForm):
    target_roles = forms.MultipleChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text='Leave blank to target all roles.'
    )

    class Meta:
        model = Announcement
        fields = ['title', 'body', 'target_roles', 'priority', 'is_published', 'expiry_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Announcement title'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'expiry_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

    def clean_target_roles(self):
        return list(self.cleaned_data.get('target_roles', []))


class MessageComposeForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['recipient', 'subject', 'body']
        widgets = {
            'recipient': forms.Select(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject'}),
            'body': forms.Textarea(attrs={'class': 'form-control', 'rows': 8, 'placeholder': 'Write your message...'}),
        }

    def __init__(self, *args, **kwargs):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        super().__init__(*args, **kwargs)
        self.fields['recipient'].queryset = User.objects.filter(is_active=True).order_by('last_name', 'first_name')
        self.fields['recipient'].label_from_instance = lambda u: f"{u.get_full_name()} ({u.get_role_display()})"


class MessageReplyForm(forms.Form):
    body = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Write your reply...'}),
        label='Reply'
    )
