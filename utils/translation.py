import os
import logging
import deepl
import hashlib
from typing import Optional, Dict, List
from django.conf import settings
from django.core.cache import cache

class DeepLTranslator:
    def __init__(self):
        # Get the API key from environment variables
        self.api_key = os.environ.get('DEEPL_API_KEY')
        if not self.api_key:
            raise ValueError("DEEPL_API_KEY environment variable is not set")
        
        self.translator = deepl.Translator(self.api_key)
        
        # Supported language pairs
        self.supported_languages = self._get_supported_languages()
        
        # Cache settings
        self.cache_timeout = 60 * 60 * 24
        
    def _get_supported_languages(self) -> Dict[str, List[str]]:
        """
        Get list of supported languages from DeepL API
        """
        try:
            response = self.translator.get_target_languages()
            supported_languages = {}
            for language in response:
                source_lang, target_lang = language.split('-')
                if source_lang not in supported_languages:
                    supported_languages[source_lang] = []
                supported_languages[source_lang].append(target_lang)
                
            # Filter or override with source languages from settings.py
            source_languages = getattr(settings, 'DEEPL_SOURCE_LANGUAGES', [])
            if source_languages:
                filtered_languages = {lang: targets for lang, targets in supported_languages.items() if lang in source_languages}
                return {k: v for k, v in filtered_languages.items() if k in source_languages}
            return supported_languages
        except Exception as e:
            logging(f"Error fetching supported languages: {e}")
            return {}
        
    def _get_cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        Generate a unique cache key for the given text, source language, and target language
        """
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"translation_{text_hash}_{source_lang}_{target_lang}"
    
    def translate_text(self,
                       text: str,
                       target_lang: str,
                       source_lang: Optional[str] = None,
                       use_cache: bool = True,
                       preserve_formatting: bool = True) -> Dict[str, str]:
        
        if not text:
            return {"error": "No text provided for translation"}
        
        # Check if the target language is supported
        if target_lang not in self.supported_languages:
            return {"error": f"Target language '{target_lang}' is not supported"}
        
        # Check if the source language is supported
        if source_lang and source_lang not in self.supported_languages:
            return {"error": f"Source language '{source_lang}' is not supported"}
        
        # Check if the translation is cached
        if use_cache:
            cache_key = self._get_cache_key(text, source_lang, target_lang)
            cached_translation = cache.get(cache_key)
            if cached_translation:
                return cached_translation
            
        try:
            # Perform translation
            if source_lang:
                result = self.translator.translate_text(text, target_lang=target_lang, source_lang=source_lang, preserve_formatting=preserve_formatting)
            else:
                result = self.translator.translate_text(text, target_lang=target_lang, preserve_formatting=preserve_formatting)
            translated_text = result.text
            detected_source_lang = result.detected_source_lang
            
            # Cache the translation
            if use_cache:
                cache.set(cache_key, {"translated_text": translated_text, "detected_source_lang": detected_source_lang}, timeout=self.cache_timeout)
            return {"translated_text": translated_text, "detected_source_lang": detected_source_lang}
        except deepl.DeepLException as e:
            return {"error": f"Translation failed: {e}"}
        except deepl.exceptions.QuotaExceededException:
            return {"error": "Translation quota exceeded. Please try again later."}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {e}"}
        
    def batch_translate(self,
                        texts: List[str],
                        target_lang: str,
                        source_lang: Optional[str] = None,
                        use_cache: bool = True,
                        preserve_formatting: bool = True) -> List[Dict[str, str]]:
        """
        Translate a list of texts in batch
        """
        return [self.translate_text(text, target_lang, source_lang, use_cache, preserve_formatting) for text in texts]

class ContentTranslator:
    def __init__(self):
        self.translator = DeepLTranslator()
        
    def translate_post(self, post, target_lang: str) -> Dict[str, str]:
        """
        Translate the content of a post and its comments
        """
        try:
            # Translate post content
            post_translation = self.translator.translate_text(post.content, target_lang=target_lang)
            if "error" in post_translation:
                return {"error": post_translation["error"]}
            
            # Translate post title if it exists
            title_translation = None
            if hasattr(post, 'title'):
                title_translation = self.translator.translate_text(post.title, target_lang=target_lang)
                if "error" in title_translation:
                    return {"error": title_translation["error"]}
                post.title = title_translation["translated_text"]
            else:
                post.title = post_translation["translated_text"]
                post.save()
                
            # Translate markdown content if it exists
            if post.markdown_content:
                markdown_translation = self.translator.translate_text(post.markdown_content, target_lang=target_lang)
                if "error" in markdown_translation:
                    return {"error": markdown_translation["error"]}
                post.markdown_content = markdown_translation["translated_text"]
            else:
                post.markdown_content = post_translation["translated_text"]
                post.save()

            # Translate comments
            comments_translation = []
            for comment in post.comments.all():
                comment_translation = self.translator.translate_text(comment.content, target_lang=target_lang)
                if "error" in comment_translation:
                    return {"error": comment_translation["error"]}
                comments_translation.append({
                    "comment_id": comment.comment_id,
                    "translated_text": comment_translation["translated_text"]
                })

            # Update post and comments with translated content
            post.content = post_translation["translated_text"]
            post.save()
            for comment, translation in zip(post.comments.all(), comments_translation):
                comment.content = translation["translated_text"]
                comment.save()

            return {"message": "Post and comments translated successfully"}
        except Exception as e:
            return {"error": f"An unexpected error occurred: {e}"}
        
    def get_supported_languages(self):
        """
        Get list of supported languages from DeepL API
        """
        return self.translator.supported_languages