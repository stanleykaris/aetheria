from django.db import models
from django.core.exceptions import ValidationError
from tinymce.models import HTMLField
from markdownify import markdownify as md
import markdown

# Create your models here.
def validate_image_size(value):
    filesize = value.size
    
    if filesize > 5 * 1024 * 1024:
        raise ValidationError("The maximum file size that can be uploaded is 5MB")

class User(models.Model):
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True,)
    phone_number = models.CharField(max_length=20, blank=True)
    password = models.CharField(max_length=100)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True, validators=[validate_image_size]),
    bio = models.TextField(max_length=500, blank=True),
    created_at = models.DateTimeField(auto_now_add=True),
    updated_at = models.DateTimeField(auto_now=True),
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username
    
    def save(self, *args, **kwargs):
        # Delete the old profile picture if it exists
        try:
            this = User.objects.get(user_id=self.user_id)
            if this.profile_picture != self.profile_picture:
                this.profile_picture.delete()
        except User.DoesNotExist:
            pass
        super(User, self).save(*args, **kwargs)
        
    def set_password(self, password):
        self.password = password
        self.save()
        
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Tag(models.Model):
    tag_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, default=name)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class PostTag(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    def __str__(self):
        return self.tag.name
    
class PostCategory(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    category = models.ForeignKey(Categories, on_delete=models.CASCADE)

    def __str__(self):
        return self.category.name
    
class Comments(models.Model):
    comment_id = models.AutoField(primary_key=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    content = models.TextField(max_length=5000)
    content_markdown = models.TextField(max_length=5000, blank=True, editable=False)
    likes = models.IntegerField(default=0)
    dislikes = models.IntegerField(default=0)
    parent_comment = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='replies') # To allow nested comments
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    MAX_CONTENT_LENGTH = 5000

    def __str__(self):
        return self.content
    
    def clean(self):
        # Validate content length
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