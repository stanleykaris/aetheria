from django.contrib import admin
from django.contrib.auth import get_user_model
from .forms import PostForm
import logging
from .models import Post, Tag, Categories, Comments
from django.utils.html import format_html
from django.urls import reverse

# Register your models here.
class TagInline(admin.TabularInline):
    model = Post.tags.through
    extra = 1

class CategoryInline(admin.TabularInline):
    model = Post.categories.through
    extra = 1

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['post_id', 'title', 'created_at']
    list_select_related = ('author',)
    inlines = [TagInline, CategoryInline]
    list_filter = ('is_active', 'is_draft', 'tags', 'categories')
    search_fields = ('title', 'content', 'tags', 'categories')
    filter_horizontal = ('tags', 'categories')
    exclude = ('post_id', 'author', 'created_at', 'updated_at', 'markdown_content')
    view_on_site = True
    ordering = ('-created_at',)
    list_per_page = 20
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    actions = [
        PostForm.makr_post_publish,
        PostForm.makr_post_draft,
        PostForm.close_post_commentstatus,
        PostForm.open_post_commentstatus,
    ]
    
    def link_to_category(self, obj):
        if obj.categories is None:
            return 'No Category'
        
        info = (obj.categories.name, obj.categories.category_id)
        link = reverse('admin:core_category_change', args=[info])
        return format_html('<a href="{}">{}</a>', link, info)
    
    link_to_category.short_description = 'Category'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request=request, obj=obj, **kwargs)
        if "author" in form.base_fields:
            form.base_fields['author'].queryset = get_user_model().objects.filter(is_active=True)
        else:
            logging.warning("Author field not found in form base fields.")
        return form    
    
    def save_model(self, request, obj, form, change):
        super(PostAdmin, self).save_model(request=request, obj=obj, form=form, change=change)
        
        if not change:
            obj.author = request.user
            obj.save()
        else:
            obj.save()
        logging.info(f"Post {obj.title} saved by {request.user.username}.")
        return obj
    
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    exclude = ('tag_id', 'slug')
    list_display = ['tag_id', 'name', 'slug']
    search_fields = ['name']
    list_filter = ['name']
    list_per_page = 20

@admin.register(Categories)
class CategoriesAdmin(admin.ModelAdmin):
    exclude = ('category_id', 'slug')
    list_display = ['category_id', 'name', 'slug']
    search_fields = ['name']
    list_filter = ['name']
    list_per_page = 20
    ordering = ['-index']
    
@admin.register(Comments)
class CommentsAdmin(admin.ModelAdmin):
    list_display = ['comment_id', 'post', 'author', 'created_at']
    list_select_related = ('author', 'post')
    list_filter = ['is_active', 'is_draft', 'post']
    search_fields = ['content', 'post', 'author']
    list_per_page = 20
    ordering = ['-created_at']
    readonly_fields = ('created_at', 'updated_at')
    actions = [
        'makr_comment_publish',
        'makr_comment_draft',
    ]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request=request, obj=obj, **kwargs)
        if "author" in form.base_fields:
            form.base_fields['author'].queryset = get_user_model().objects.filter(is_active=True)
        else:
            logging.warning("Author field not found in form base fields.")
        return form

    def save_model(self, request, obj, form, change):
        super(CommentsAdmin, self).save_model(request=request, obj=obj, form=form, change=change)

        if not change:
            obj.author = request.user
            obj.save()
        else:
            obj.save()
        logging.info(f"Comment {obj.comment_id} saved by {request.user.username}.")
        return obj
       