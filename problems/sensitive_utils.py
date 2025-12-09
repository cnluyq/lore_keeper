import re
from django.core.cache import cache
from .models import SensitiveWord

class SensitiveDataProcessor:
    """敏感数据处理工具类"""
    
    @classmethod
    def get_active_sensitive_words(cls):
        """从数据库获取所有启用的敏感词"""
        cached_words = cache.get('active_sensitive_words')
        if cached_words is not None:
            return cached_words
            
        active_words = list(SensitiveWord.objects.filter(is_active=True).values('word', 'replacement'))
        cache.set('active_sensitive_words', active_words, timeout=300)  # 缓存5分钟
        return active_words
    
    @classmethod
    def clear_sensitive_words_cache(cls):
        """清除敏感词缓存"""
        cache.delete('active_sensitive_words')
    
    @classmethod
    def contains_sensitive_data(cls, text):
        """检查文本是否包含敏感数据"""
        if not text:
            return False
            
        text_lower = text.lower()
        sensitive_words = cls.get_active_sensitive_words()
        
        for item in sensitive_words:
            pattern = re.escape(item['word'])
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True

        return False
    
    @classmethod
    def desensitize_text(cls, text):
        """对敏感文本进行脱敏处理"""
        if not text:
            return text
            
        # 获取启用的敏感词
        sensitive_words = cls.get_active_sensitive_words()
        
        # 脱敏敏感关键词
        for item in sensitive_words:
            word = item['word']
            replacement = item['replacement']
            pattern = re.escape(word)
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # 脱敏类似SSN的模式
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', 'XXX-XX-XXXX', text)
        
        # 脱敏电子邮件（保留域名部分）
        text = re.sub(
            r'\b([A-Z0-9._%+-]+)@([A-Z0-9.-]+\.[A-Z]{2,})\b', 
            r'***@\2', 
            text, 
            flags=re.IGNORECASE
        )
        
        return text

    @classmethod
    def validate_and_process_form(cls, form, request=None):
        # 检查敏感内容
        text_fields = ['key_words', 'title', 'description',
                      'root_cause', 'solutions', 'others']

        detected_sensitive_words = []
        form_data = form.cleaned_data.copy()

        for field in text_fields:
            if field in form_data and form_data[field]:
                if cls.contains_sensitive_data(form_data[field]):
                    # 记录检测到的敏感词
                    text_lower = form_data[field].lower()
                    sensitive_words = cls.get_active_sensitive_words()
                    for item in sensitive_words:
                        pattern = re.escape(item['word'])
                        if re.search(pattern, text_lower, re.IGNORECASE):
                            detected_sensitive_words.append(item['word'])
                    # 进行脱敏处理
                    form_data[field] = cls.desensitize_text(form_data[field])

        # 如果检测到敏感词，可以记录日志或返回警告信息
        if detected_sensitive_words:
            # 可以选择记录日志
            #if request and request.user:
            #    print(f"[SECURITY] User {request.user.username} submitted content containing sensitive words: {detected_sensitive_words}")

            # 创建新的表单实例，使用脱敏后的数据
            try:
                processed_form = type(form)(form_data, request.FILES, instance=form.instance if form.instance else None)

                # 验证脱敏后的表单是否有效
                if processed_form.is_valid():
                    error_msg = f"Content has been desensitized (detected words: {', '.join(set(detected_sensitive_words))})."
                    return processed_form, error_msg
                else:
                    # 脱敏后的表单验证失败，返回原始表单
                    print("Warning: Form validation failed after desensitization.")
                    return form, None
            except Exception as e:
                # 创建表单失败，返回原始表单
                print(f"Error creating processed form: {e}")
                return form, None

        return form, None

    @classmethod
    def process_form_data(cls, form_data):
        """处理表单数据中的敏感信息"""
        processed_data = form_data.copy()
        
        # 需要检查的文本字段
        text_fields = [
            'key_words', 'title', 'description',
            'root_cause', 'solutions', 'others'
        ]
        
        for field in text_fields:
            if field in processed_data and processed_data[field]:
                if cls.contains_sensitive_data(processed_data[field]):
                    processed_data[field] = cls.desensitize_text(processed_data[field])
                    
        return processed_data
