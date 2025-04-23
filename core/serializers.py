from rest_framework import serializers
from .models import User, Post, Comments

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'username', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, data):
        # Password validation
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def create(self, validated_data):
        validated_data.pop('confirm_password', None)
        user = User.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        user.set_password(validated_data['password'])
        
        for field in ['phone_number', 'profile_picture']:
            if field in validated_data:
                setattr(user, field, validated_data[field])
        user.save()
        return user

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
    
class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ['post_id', 'title', 'content', 'author', 'likes', 'dislikes', 'created_at', 'updated_at', 'markdown_content']

    def create(self, validated_data):
        return Post.objects.create(**validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
    
class CommentSerializer(serializers.ModelSerializer):
    MAX_COMMENT_LENGTH = 5000
    class Meta:
        model = Comments
        fields = ['comment_id', 'post', 'author', 'content', 'content_markdown', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'content_markdown']

    def create(self, validated_data):
        return Comments.objects.create(**validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
    
    def delete(self, instance):
        instance.delete()
        return instance
    
    def validate_content(self, value):
        if len(value) > self.MAX_COMMENT_LENGTH:
            raise serializers.ValidationError(
                f"Comment content cannot exceed {self.MAX_COMMENT_LENGTH} characters."
                f" Current length: {len(value)}"
                )
        return value
        
        