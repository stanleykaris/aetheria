from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from tinymce.models import HTMLField
from markdownify import markdownify as md
import markdown

def validate_image_size(value):
    filesize = value.size
    if filesize > 5 * 1024 * 1024:
        raise ValidationError("The maximum file size that can be uploaded is 5MB")

class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, password, **extra_fields)

class User(AbstractBaseUser):
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True, validators=[validate_image_size])
    bio = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.username

class Post(models.Model):
    post_id = models.AutoField(primary_key=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(max_length=500)
    markdown_content = HTMLField(blank=True)
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='post_images/', null=True, blank=True, validators=[validate_image_size])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.IntegerField(default=0)
    dislikes = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_draft = models.BooleanField(default=False)
    categories = models.ManyToManyField('Categories', related_name='posts')
    tags = models.ManyToManyField('Tag', related_name='posts')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Posts'

    def save(self, *args, **kwargs):
        if not self.is_draft:
            self.markdown_content = md(self.content)
        super(Post, self).save(*args, **kwargs)

    def __str__(self):
        return self.title

class Categories(models.Model):
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=500, blank=True)
    slug = models.SlugField(default='no-slug', max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    index = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-index']
        verbose_name_plural = 'Categories'
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.name.lower().replace(' ', '-')
        super(Categories, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

class Tag(models.Model):
    tag_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.name.lower().replace(' ', '-')
        super(Tag, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

class Comments(models.Model):
    comment_id = models.AutoField(primary_key=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    content = models.TextField(max_length=5000)
    content_markdown = models.TextField(max_length=5000, blank=True, editable=False)
    likes = models.IntegerField(default=0)
    dislikes = models.IntegerField(default=0)
    parent_comment = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    MAX_CONTENT_LENGTH = 5000

    def __str__(self):
        return self.content

    def clean(self):
        if len(self.content) > self.MAX_CONTENT_LENGTH:
            raise ValidationError(
                f"Content exceeds maximum length of {self.MAX_CONTENT_LENGTH} characters."
                f" Current length: {len(self.content)}"
            )

    def save(self, *args, **kwargs):
        md = markdown.Markdown(extensions=[
            'markdown.extensions.fenced_code', 'markdown.extensions.codehilite', 'markdown.extensions.tables', 'markdown.extensions.nl2br'
        ])
        self.content_markdown = md.convert(self.content)
        super(Comments, self).save(*args, **kwargs)
