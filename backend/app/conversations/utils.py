"""
Utility functions for conversation handling with comprehensive validation and optimization.
"""

from typing import List, Dict, Optional, Tuple, Any
import logging
import re
import uuid
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class ConversationPriority(Enum):
    """Conversation priority levels for processing."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


def derive_conversation_title(history: List[Dict[str, Any]], fallback: str, max_length: int = 50) -> str:
    """
    Intelligently derives a conversation title from the history.
    
    Args:
        history: List of conversation messages with 'role' and 'content' keys
        fallback: Fallback title if no suitable user message is found
        max_length: Maximum length for the title
        
    Returns:
        A clean, descriptive title for the conversation
    """
    try:
        # Look for the first meaningful user message
        for item in history:
            if item.get("role") == "user":
                text = (item.get("content") or "").strip()
                if text and len(text) > 3:  # Avoid very short messages
                    # Clean up the text
                    clean_text = _clean_title_text(text)
                    return _truncate_title(clean_text, max_length)
        
        # If no user message found, try assistant messages
        for item in history:
            if item.get("role") == "assistant":
                text = (item.get("content") or "").strip()
                if text and "restaurant" in text.lower():
                    # Extract restaurant-related context
                    clean_text = _extract_restaurant_context(text)
                    if clean_text:
                        return _truncate_title(clean_text, max_length)
    
    except Exception as e:
        logger.warning(f"Error deriving conversation title: {e}")
    
    # Fallback processing
    fb = (fallback or "New Search").strip()
    return _truncate_title(fb, max_length)


def _clean_title_text(text: str) -> str:
    """Clean and normalize text for use as a title."""
    # Remove extra whitespace and normalize
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove common conversation starters
    prefixes_to_remove = [
        r'^(hi|hello|hey)\s*,?\s*',
        r'^(can you|could you|please)\s+',
        r'^(i want|i need|i would like)\s+',
        r'^(find|search for|look for)\s+',
    ]
    
    for prefix in prefixes_to_remove:
        text = re.sub(prefix, '', text, flags=re.IGNORECASE).strip()
    
    # Capitalize first letter
    if text:
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    
    return text


def _extract_restaurant_context(text: str) -> str:
    """Extract restaurant-related context from assistant message."""
    # Look for cuisine types
    cuisine_match = re.search(r'(italian|chinese|mexican|indian|thai|japanese|french|american|greek|spanish|korean|vietnamese)\s+restaurants?', text, re.IGNORECASE)
    if cuisine_match:
        return f"{cuisine_match.group(1).title()} restaurants"
    
    # Look for location mentions
    location_match = re.search(r'restaurants?\s+in\s+([^,.!?]+)', text, re.IGNORECASE)
    if location_match:
        return f"Restaurants in {location_match.group(1).strip()}"
    
    # Generic fallback
    if 'restaurant' in text.lower():
        return "Restaurant recommendations"
    
    return ""


def _truncate_title(text: str, max_length: int) -> str:
    """Truncate title to specified length with ellipsis if needed."""
    if not text:
        return "New Search"
    
    if len(text) <= max_length:
        return text
    
    # Try to truncate at word boundary
    truncated = text[:max_length-1]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.7:  # Only use word boundary if it's not too short
        return truncated[:last_space] + "…"
    else:
        return truncated + "…"


def format_chat_history_for_agents(messages: List[Dict[str, Any]], max_messages: int = 10) -> List[Dict[str, str]]:
    """
    Formats conversation messages for use with AI agents with intelligent truncation.
    
    Args:
        messages: List of message dictionaries from UI
        max_messages: Maximum number of messages to include
        
    Returns:
        Formatted list suitable for agent processing
    """
    try:
        # Filter out empty messages and validate structure
        valid_messages = []
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            
            role = msg.get("role", "").strip()
            content = msg.get("content", "").strip()
            
            if role in ["user", "assistant"] and content:
                valid_messages.append({
                    "role": role,
                    "content": content[:2000]  # Limit individual message length
                })
        
        # Keep the most recent messages up to max_messages
        if len(valid_messages) > max_messages:
            valid_messages = valid_messages[-max_messages:]
        
        return valid_messages
    
    except Exception as e:
        logger.warning(f"Error formatting chat history: {e}")
        return []


def validate_user_id(user_id: Optional[str]) -> bool:
    """
    Validates a user ID format with comprehensive checks.
    
    Args:
        user_id: The user ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not user_id or not isinstance(user_id, str):
        return False
    
    user_id = user_id.strip()
    
    # Basic length validation
    if len(user_id) < 1 or len(user_id) > 128:
        return False
    
    # Check for invalid characters (basic alphanumeric + common separators)
    if not re.match(r'^[a-zA-Z0-9_\-@.]+$', user_id):
        return False
    
    return True


def sanitize_message_content(content: str, max_length: int = 5000) -> str:
    """
    Sanitizes message content for safe storage and processing.
    
    Args:
        content: Raw message content
        max_length: Maximum allowed length
        
    Returns:
        Sanitized and cleaned content
    """
    if not content:
        return ""
    
    # Normalize whitespace
    content = re.sub(r'\s+', ' ', content).strip()
    
    # Remove potentially dangerous content (basic XSS prevention)
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
    content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
    
    # Limit length
    if len(content) > max_length:
        content = content[:max_length-3] + "..."
    
    return content


def generate_session_id() -> str:
    """Generate a new unique session ID."""
    return str(uuid.uuid4())


def generate_preview_text(user_msg: str, assistant_msg: str, max_length: int = 200) -> str:
    """
    Generate a preview text from user and assistant messages.
    
    Args:
        user_msg: User message content
        assistant_msg: Assistant message content
        max_length: Maximum length of preview
        
    Returns:
        Formatted preview text
    """
    try:
        user_preview = _truncate_text(user_msg, 60)
        assistant_preview = _truncate_text(assistant_msg, 80)
        
        preview = f"You: {user_preview}\nAI: {assistant_preview}"
        
        if len(preview) > max_length:
            # Redistribute space more evenly
            available = max_length - 10  # Account for labels and newline
            user_len = min(30, available // 2)
            assistant_len = available - user_len
            
            user_preview = _truncate_text(user_msg, user_len)
            assistant_preview = _truncate_text(assistant_msg, assistant_len)
            preview = f"You: {user_preview}\nAI: {assistant_preview}"
        
        return preview
    
    except Exception as e:
        logger.warning(f"Error generating preview text: {e}")
        return "Conversation preview unavailable"


def _truncate_text(text: str, max_length: int) -> str:
    """Truncate text to specified length with ellipsis."""
    if not text:
        return ""
    
    text = text.strip()
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."


def calculate_conversation_priority(message_count: int, last_activity: datetime) -> ConversationPriority:
    """
    Calculate conversation priority based on activity metrics.
    
    Args:
        message_count: Number of messages in conversation
        last_activity: When the conversation was last active
        
    Returns:
        Calculated priority level
    """
    try:
        now = datetime.now(timezone.utc)
        hours_since_activity = (now - last_activity).total_seconds() / 3600
        
        # High activity conversations
        if message_count > 20 and hours_since_activity < 1:
            return ConversationPriority.HIGH
        
        # Recent active conversations
        if message_count > 5 and hours_since_activity < 6:
            return ConversationPriority.NORMAL
        
        # Old or inactive conversations
        if hours_since_activity > 24:
            return ConversationPriority.LOW
        
        return ConversationPriority.NORMAL
    
    except Exception as e:
        logger.warning(f"Error calculating conversation priority: {e}")
        return ConversationPriority.NORMAL


def extract_restaurant_keywords(content: str) -> List[str]:
    """
    Extract restaurant-related keywords from message content.
    
    Args:
        content: Message content to analyze
        
    Returns:
        List of extracted keywords
    """
    keywords = []
    content_lower = content.lower()
    
    # Cuisine types
    cuisines = [
        'italian', 'chinese', 'mexican', 'indian', 'thai', 'japanese',
        'french', 'american', 'greek', 'spanish', 'korean', 'vietnamese',
        'mediterranean', 'middle eastern', 'seafood', 'steakhouse', 'pizza',
        'sushi', 'barbecue', 'bbq', 'fast food', 'fine dining'
    ]
    
    for cuisine in cuisines:
        if cuisine in content_lower:
            keywords.append(cuisine)
    
    # Price ranges
    price_terms = ['cheap', 'expensive', 'budget', 'affordable', 'luxury', 'fine dining', 'casual']
    for term in price_terms:
        if term in content_lower:
            keywords.append(term)
    
    # Location indicators
    location_patterns = [
        r'in\s+([a-zA-Z\s]+?)(?:\s|$|,|\.|!|\?)',
        r'near\s+([a-zA-Z\s]+?)(?:\s|$|,|\.|!|\?)',
        r'around\s+([a-zA-Z\s]+?)(?:\s|$|,|\.|!|\?)'
    ]
    
    for pattern in location_patterns:
        matches = re.finditer(pattern, content_lower)
        for match in matches:
            location = match.group(1).strip()
            if len(location) > 2 and len(location) < 30:
                keywords.append(f"location:{location}")
    
    return list(set(keywords))  # Remove duplicates
