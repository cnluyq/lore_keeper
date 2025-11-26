import re
from django.core.cache import cache
from .models import SensitiveWord

class SensitiveDataProcessor:
    """敏感数据处理工具类"""
    
    @classmethod
    def get_active_sensitive_words(cls):
        """从数据库获取所有启用的敏感词"""
        # 使用缓存提高性能
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
            if item['word'].lower() in text_lower:
                return True
                
        # 检查可能的敏感模式（如API密钥、密码等）
        #patterns = [
        #    r'[a-zA-Z0-9]{20,}',  # 长字符串（可能为API密钥）
        #    r'\b\d{3}-\d{2}-\d{4}\b',  # 类似SSN的模式
        #    r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',  # 电子邮件
        #]
        
        for pattern in patterns:
            if re.search(pattern, text):
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
            text = re.sub(
                re.compile(re.escape(word), re.IGNORECASE), 
                replacement, 
                text
            )
            
        # 脱敏长字符串（可能为API密钥）
        #text = re.sub(r'[a-zA-Z0-9]{20,}', '[REDACTED]', text)
        
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
