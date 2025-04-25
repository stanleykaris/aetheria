from django import forms
from tinymce.widgets import TinyMCE
from .models import Post, User, Comments
from django.utils.translation import gettext_lazy as _

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput(), label="Confirm Password")
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
            'confirm_password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not match")
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long")
        if password:
            if not any(char.isdigit() for char in password):
                raise forms.ValidationError("Password must contain at least one digit")
            if not any(char.isupper() for char in password):
                raise forms.ValidationError("Password must contain at least one uppercase letter")
            if not any(char.islower() for char in password):
                raise forms.ValidationError("Password must contain at least one lowercase letter")
        return password
    
class PostForm(forms.ModelForm):
    content = forms.CharField(
        widget=TinyMCE(
            attrs={
                'class': 'form-control',
                'rows': 10,
                'cols': 80,
                'placeholder': 'Write your post here...'
            },
            mce_attrs={
                'plugins': 'autolink lists link image charmap print preview anchor markdown',
                'toolbar': 'undo redo | formatselect | bold italic underline | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | link image | code',
                'menubar': False,
            }
        )
    )
    
    class Meta:
        model = Post
        fields = ['title', 'content', 'image']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'title': 'Title',
            'content': 'Content',
            'image': 'Image',
        }
        
    def makr_post_publish(self, modeladmin, request, queryset):
        queryset.update(is_active=True)
        
    def makr_post_draft(self, modeladmin, request, queryset):
        queryset.update(is_active=False)
    
    def close_post_commentstatus(self, modeladmin, request, queryset):
        queryset.update(is_active=False)
    
    def open_post_commentstatus(self, modeladmin, request, queryset):
        queryset.update(is_active=True)
        
    makr_post_publish.short_description = _('Publish selected posts')
    makr_post_draft.short_description = _('Draft selected posts')
    close_post_commentstatus.short_description = _('Close comment status for selected posts')
    open_post_commentstatus.short_description = _('Open comment status for selected posts')
    
        
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comments
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Write a comment...'
            })
        }
        labels = {
            'content': 'Comment'
        }