from typing import List, Dict
import re


def parse_logs(log_text: str) -> List[Dict]:
    entries = []
    
    # Simple regex for common log format: YYYY-MM-DD HH:MM:SS LEVEL: message
    pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(\w+):\s+(.+)'
    
    for line in log_text.split('\n'):
        match = re.match(pattern, line)
        if match:
            entries.append({
                'timestamp': match.group(1),
                'level': match.group(2),
                'message': match.group(3)
            })
    
    return entries


def filter_errors(log_entries: List[Dict]) -> List[Dict]:
    return [
        entry for entry in log_entries 
        if entry.get('level') in ['ERROR', 'CRITICAL', 'FATAL']
    ]


def extract_error_patterns(log_entries: List[Dict]) -> Dict[str, int]:
    patterns = {}
    
    for entry in log_entries:
        msg = entry.get('message', '')
        
        # Common patterns
        if 'timeout' in msg.lower():
            patterns['timeout'] = patterns.get('timeout', 0) + 1
        elif '429' in msg or 'rate limit' in msg.lower():
            patterns['rate_limit'] = patterns.get('rate_limit', 0) + 1
        elif 'connection' in msg.lower():
            patterns['connection'] = patterns.get('connection', 0) + 1
        elif 'null' in msg.lower() or 'missing' in msg.lower():
            patterns['missing_data'] = patterns.get('missing_data', 0) + 1
        else:
            patterns['other'] = patterns.get('other', 0) + 1
    
    return patterns


# Sample logs for testing
SAMPLE_LOGS = """2024-01-15 10:23:45 ERROR: API returned 429 Too Many Requests
2024-01-15 10:23:46 WARN: Retry attempt 1 failed
2024-01-15 10:24:15 ERROR: API returned 429 Too Many Requests
2024-01-15 10:24:16 WARN: Retry attempt 2 failed
2024-01-15 10:25:00 ERROR: API returned 429 Too Many Requests
2024-01-15 10:25:01 ERROR: Max retries exceeded, pipeline failed
2024-01-15 10:25:02 INFO: Sending alert to ops team"""
