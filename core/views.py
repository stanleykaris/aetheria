from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import markdown
import logging
from .models import User, Post, Comment
from .serializers import PostSerializer, CommentSerializer
from .forms import PostForm  # Import PostForm from the forms module
from django.core.exceptions import ValidationError  # Import ValidationError
from django.db import IntegrityError, transaction  # Import IntegrityError and transaction
from utils.translation import ContentTranslator
# Create your views here.
class PostView(APIView):
    permission_classes = [IsAuthenticated] # Allows any user to access this view including guest users
    
    def get_queryset(self, user=None):
        qs = Post.objects.all().select_related("author").prefetch_related("comment_set").filter(is_active=True)
        # If a user is provided, filter the posts by that user
        # and prefetch the related comments
        if user is not None:
            user_posts = Post.objects.filter(author=user).prefetch_related("comment_set")
            qs = (qs | user_posts).distinct()
        return qs
            
    def get(self, request, *args, **kwargs):
        posts = self.get_queryset()
        is_authenticated = request.user.is_authenticated
        
        # Limiting the number of posts for guest users
        if not is_authenticated:
            posts = posts[:10]
        
        serialiazer = PostSerializer(posts, many=True, context={"request": request})
        return Response(serialiazer.data, status=status.HTTP_200_OK)
    
    @method_decorator(login_required)
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            form = PostForm(request.POST, request.FILES or None)
            if request.method == "POST" and form.is_valid():
                post = form.save(commit=False)
                post.author = request.user
                post.save()
                return Response({"message": "Post created successfully"}, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            return Response({"validation error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            return Response({"integrity error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @method_decorator(login_required)
    @transaction.atomic
    def put(self, request, post_id, *args, **kwargs):
        try:
            post = Post.objects.select_for_update().get(id=post_id, author=request.user)
            form = PostForm(request.POST, request.FILES or None, instance=post)
            if request.method == "POST" and form.is_valid():
                form.save()
                return Response({"message": "Post updated successfully"}, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({"validation error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            return Response({"integrity error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @method_decorator(login_required)
    @transaction.atomic
    def delete(self, request, post_id, *args, **kwargs):
        try:
            post = Post.objects.get(id=post_id, author=request.user)
            post.is_active = False
            post.save()
            return Response({"message": "Post deleted successfully"}, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @method_decorator(login_required)
    @transaction.atomic
    def save_draft(self, request, *args, **kwargs):
        try:
            form = PostForm(request.POST, request.FILES or None)
            if request.method == "POST" and form.is_valid():
                post = form.save(commit=False)
                post.author = request.user
                post.is_draft = True  # Mark the post as a draft
                post.save()
                return Response({"message": "Draft saved successfully"}, status=status.HTTP_201_CREATED)
            return Response({"error": "Invalid form data"}, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({"validation error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            return Response({"integrity error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @method_decorator(login_required)
    @transaction.atomic
    def publish_draft(self, request, post_id, *args, **kwargs):
        try:
            post = Post.objects.select_for_update().get(id=post_id, author=request.user, is_draft=True)
            post.is_draft = False  # Mark the post as published
            post.save()
            return Response({"message": "Draft published successfully"}, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({"error": "Draft not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @method_decorator(login_required)
    @transaction.atomic
    def edit_draft(self, request, post_id, *args, **kwargs):
            try:
                post = Post.objects.select_for_update().get(id=post_id, author=request.user, is_draft=True)
                form = PostForm(request.POST, request.FILES or None, instance=post)
                if request.method == "POST" and form.is_valid():
                    form.save()
                    return Response({"message": "Draft updated successfully"}, status=status.HTTP_200_OK)
                return Response({"error": "Invalid form data"}, status=status.HTTP_400_BAD_REQUEST)
            except Post.DoesNotExist:
                return Response({"error": "Draft not found"}, status=status.HTTP_404_NOT_FOUND)
    
class CommentView(APIView):
    permission_classes = [AllowAny]
    MAX_COMMENTS_PER_HOUR = 10
    
    def _check_rate_limit(self, user_id):
        cache_key = f"comment_rate_limit:{user_id}"
        comment_count = cache.get(cache_key, 0)
        if comment_count >= self.MAX_COMMENTS_PER_HOUR:
            return False
        cache.set(cache_key, comment_count + 1, 3600)  # Set cache expiration to 1 hour
        return True

    def get_queryset(self, post_id):
        return Comment.objects.filter(post__id=post_id, is_active=True)
    
    def get(self, request, post_id, *args, **kwargs):
        comments = self.get_queryset(post_id)
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @method_decorator(login_required)
    @transaction.atomic
    def post(self, request, post_id, *args, **kwargs):
        user_id = request.user.id if request.user.is_authenticated else request.META.get('REMOTE_ADDR')
        
        if not self._check_rate_limit(user_id):
            return Response({"error": "Rate limit exceeded. Please try again later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        if not request.user.is_authenticated:
            return Response({"error": "You must be logged in to comment."}, status=status.HTTP_401_UNAUTHORIZED)
        if not request.data.get('content'):
            return Response({"error": "Comment content is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            serializer = CommentSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            # Handling markdown preview if requested
            if request.data.get('markdown_preview'):
                md = markdown.Markdown(extensions=[
                    'markdown.extensions.fenced_code', 'markdown.extensions.codehilite', 'markdown.extensions.tables', 'markdown.extensions.nl2br'
                ])
                preview_content = md.convert(serializer.validated_data['content'])
                return Response({"preview": preview_content}, status=status.HTTP_200_OK)
            
            # Saving the comment
            comment = serializer.save(
                post_id=post_id,
                author=request.user if request.user.is_authenticated else None
            )
            serializer = CommentSerializer(comment)
            return Response({
                "message": "Comment created successfully",
                "data": serializer.data
                }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"validation error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            return Response({"integrity error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @method_decorator(login_required)
    @transaction.atomic
    def get_comment(self, request, comment_id, *args, **kwargs):
        try:
            comment = Comment.objects.get(id=comment_id)
            serializer = CommentSerializer(comment)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Comment.DoesNotExist:
            return Response({"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @method_decorator(login_required)
    @transaction.atomic
    def update_comment(self, request, comment_id, *args, **kwargs):
        try:
            comment = Comment.objects.get(id=comment_id, author=request.user)
            serializer = CommentSerializer(comment, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Comment.DoesNotExist:
            return Response({"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    @method_decorator(login_required)
    @transaction.atomic
    def delete_comment(self, request, comment_id, *args, **kwargs):
        try:
            comment = Comment.objects.get(id=comment_id, author=request.user)
            comment.is_active = False
            comment.save()
            return Response({"message": "Comment deleted successfully"}, status=status.HTTP_200_OK)
        except Comment.DoesNotExist:
            return Response({"error": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class TranslationView(APIView):
    permission_classes = [IsAuthenticated]
    
    def __init__(self):
        self.translator = ContentTranslator()
    
    @method_decorator(login_required)
    @transaction.atomic
    def post(self, request, post_id, *args, **kwargs):
        try:
            post = Post.objects.get(id=post_id)
            target_lang = request.data.get('target_lang')
            
            if not target_lang:
                return Response({"error": "Target language is required."}, status=status.HTTP_400_BAD_REQUEST)
            
            translation_result = self.translator.translate_post(post, target_lang)
            
            if "error" in translation_result:
                return Response({"error": translation_result["error"]}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"message": "Post translated successfully"}, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @method_decorator(login_required)
    @transaction.atomic    
    def get(self, request):
        try:
            result = self.translator.get_supported_languages()
        except Exception as e:
            logging.error(f"Exception occurred while fetching languages: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if "error" in result:
            logging.error(f"Error fetching languages: {result['error']}")
            return Response({"error": result["error"]}, status=status.HTTP_400_BAD_REQUEST)

        languages = result.get("languages")
        if not isinstance(languages, list):
            logging.error("Invalid languages data")
            return Response({"error": "Invalid languages data"}, status=status.HTTP_400_BAD_REQUEST)

        if not languages:
            logging.error("No languages found")
            return Response({"error": "No languages found"}, status=status.HTTP_404_NOT_FOUND)

        return Response({"languages": languages}, status=status.HTTP_200_OK)
    
    @method_decorator(login_required)
    @transaction.atomic
    def get_translations(self, request, post_id, *args, **kwargs):
        try:
            # Fetch the post by id
            post = Post.objects.get(id=post_id)
            
            # Get the target language from the request
            target_lang = request.query_params.get('target_lang')
            if not target_lang:
                return Response({"error": "Target language is required."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Translate the post content
            translation_result = self.translator.translate_post(post, target_lang)
            
            if "error" in translation_result:
                return Response({"error": translation_result["error"]}, status=status.HTTP_400_BAD_REQUEST)
            
            # Return the translated content
            return Response({
                "message": "Post and comments translated successfully",
                "translated_post": {
                    
                    "title": translation_result["title"],
                    "content": translation_result["content"],
                    "markdown_content": post.markdown_content
                },
                "translated_comments": translation_result.get("comments", [])
            }, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logging.error(f"Exception occurred while translating post: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @method_decorator(login_required)
    @transaction.atomic
    def get_translation_status(self, request, post_id, *args, **kwargs):
        try:
            post = Post.objects.get(id=post_id)
            translation_status = self.translator.get_translation_status(post)
            return Response({"translation_status": translation_status}, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
