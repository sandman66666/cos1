"""
Claude Response Parser

Parses Claude's natural language responses to extract structured strategic intelligence data.
Handles business contexts, strategic insights, and recommendations.
"""

import json
import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class ClaudeResponseParser:
    """Parser for Claude's strategic intelligence responses"""
    
    @staticmethod
    def parse_business_contexts(response_text: str) -> List[Dict]:
        """Parse business contexts from Claude's response"""
        try:
            contexts = []
            
            # Look for structured JSON first
            json_matches = re.findall(r'\{[^}]*\}', response_text, re.DOTALL)
            if json_matches:
                for match in json_matches:
                    try:
                        context_data = json.loads(match)
                        if 'name' in context_data:
                            contexts.append(context_data)
                    except json.JSONDecodeError:
                        continue
            
            # If no JSON found, parse natural language structure
            if not contexts:
                contexts = ClaudeResponseParser._parse_contexts_from_text(response_text)
            
            return contexts
            
        except Exception as e:
            logger.error(f"Error parsing business contexts: {str(e)}")
            return []
    
    @staticmethod
    def parse_strategic_insights(response_text: str) -> List[Dict]:
        """Parse strategic insights from Claude's response"""
        try:
            insights = []
            
            # Look for insights in structured format
            insight_pattern = r'(?:INSIGHT|Insight)\s*(\d+)?[:\-]?\s*([^\n]+)\n([^]*?)(?=(?:INSIGHT|Insight)\s*\d+|$)'
            matches = re.findall(insight_pattern, response_text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                number, title, content = match
                insight_data = {
                    'id': f"insight_{len(insights)}",
                    'title': title.strip(),
                    'description': content.strip()[:300],
                    'type': ClaudeResponseParser._extract_insight_type(content),
                    'evidence': ClaudeResponseParser._extract_evidence(content),
                    'implications': ClaudeResponseParser._extract_implications(content),
                    'response': ClaudeResponseParser._extract_recommended_response(content),
                    'confidence': 0.8
                }
                insights.append(insight_data)
            
            return insights
            
        except Exception as e:
            logger.error(f"Error parsing strategic insights: {str(e)}")
            return []
    
    @staticmethod
    def parse_strategic_recommendations(response_text: str) -> List[Dict]:
        """Parse strategic recommendations from Claude's response"""
        try:
            recommendations = []
            
            # Look for recommendations in structured format
            rec_pattern = r'(?:RECOMMENDATION|Recommendation)\s*(\d+)?[:\-]?\s*([^\n]+)\n([^]*?)(?=(?:RECOMMENDATION|Recommendation)\s*\d+|$)'
            matches = re.findall(rec_pattern, response_text, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                number, title, content = match
                rec_data = {
                    'id': f"rec_{len(recommendations)}",
                    'title': title.strip(),
                    'description': ClaudeResponseParser._extract_description(content),
                    'rationale': ClaudeResponseParser._extract_rationale(content),
                    'impact_analysis': ClaudeResponseParser._extract_impact_analysis(content),
                    'urgency': ClaudeResponseParser._extract_urgency(content),
                    'impact': ClaudeResponseParser._extract_impact_level(content),
                    'time_sensitivity': ClaudeResponseParser._extract_time_sensitivity(content),
                    'related_contexts': ClaudeResponseParser._extract_related_contexts(content),
                    'actions': ClaudeResponseParser._extract_suggested_actions(content),
                    'metrics': ClaudeResponseParser._extract_success_metrics(content),
                    'confidence': 0.85
                }
                recommendations.append(rec_data)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error parsing strategic recommendations: {str(e)}")
            return []
    
    @staticmethod
    def _parse_contexts_from_text(text: str) -> List[Dict]:
        """Parse business contexts from natural language text"""
        contexts = []
        
        # Look for context blocks
        context_pattern = r'(?:CONTEXT|Context)\s*(\d+)?[:\-]?\s*([^\n]+)\n([^]*?)(?=(?:CONTEXT|Context)\s*\d+|$)'
        matches = re.findall(context_pattern, text, re.IGNORECASE | re.MULTILINE)
        
        for match in matches:
            number, name, content = match
            context_data = {
                'id': f"context_{len(contexts)}",
                'name': name.strip(),
                'description': ClaudeResponseParser._extract_description(content),
                'type': ClaudeResponseParser._extract_context_type(content),
                'key_people': ClaudeResponseParser._extract_key_people(content),
                'related_communications': [],
                'timeline': [],
                'status': ClaudeResponseParser._extract_status(content),
                'priority_score': ClaudeResponseParser._extract_priority_score(content),
                'impact_assessment': ClaudeResponseParser._extract_impact_assessment(content),
                'confidence_level': 0.7
            }
            contexts.append(context_data)
        
        return contexts
    
    @staticmethod
    def _extract_description(content: str) -> str:
        """Extract description from content block"""
        # Look for description patterns
        desc_patterns = [
            r'Description[:\-]\s*([^\n]+)',
            r'Summary[:\-]\s*([^\n]+)',
            r'^([^\.]+\.)'
        ]
        
        for pattern in desc_patterns:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()
        
        # Fallback to first sentence
        sentences = content.split('.')
        return sentences[0].strip() if sentences else content[:200]
    
    @staticmethod
    def _extract_context_type(content: str) -> str:
        """Extract context type from content"""
        type_keywords = {
            'opportunity': ['opportunity', 'deal', 'partnership', 'investment', 'funding'],
            'relationship': ['relationship', 'contact', 'network', 'connection'],
            'project': ['project', 'initiative', 'development', 'implementation'],
            'challenge': ['challenge', 'issue', 'problem', 'risk', 'concern']
        }
        
        content_lower = content.lower()
        for context_type, keywords in type_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                return context_type
        
        return 'project'  # Default
    
    @staticmethod
    def _extract_key_people(content: str) -> List[str]:
        """Extract key people mentioned in content"""
        # Look for name patterns (capitalize words)
        name_pattern = r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b'
        matches = re.findall(name_pattern, content)
        
        # Filter out common false positives
        false_positives = {'Business Context', 'Strategic Intelligence', 'Chief Staff'}
        names = [name for name in matches if name not in false_positives]
        
        return list(set(names))[:5]  # Top 5 unique names
    
    @staticmethod
    def _extract_status(content: str) -> str:
        """Extract current status from content"""
        status_patterns = [
            r'Status[:\-]\s*([^\n]+)',
            r'Currently[:\-]\s*([^\n]+)',
            r'Status:\s*([^\n]+)'
        ]
        
        for pattern in status_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Infer status from keywords
        content_lower = content.lower()
        if any(word in content_lower for word in ['ongoing', 'active', 'in progress']):
            return 'active'
        elif any(word in content_lower for word in ['pending', 'waiting', 'upcoming']):
            return 'pending'
        elif any(word in content_lower for word in ['completed', 'done', 'finished']):
            return 'completed'
        
        return 'active'
    
    @staticmethod
    def _extract_priority_score(content: str) -> float:
        """Extract priority score from content"""
        # Look for explicit priority mentions
        priority_pattern = r'Priority[:\-]\s*(high|medium|low|critical)'
        match = re.search(priority_pattern, content, re.IGNORECASE)
        
        if match:
            priority = match.group(1).lower()
            priority_scores = {'critical': 0.95, 'high': 0.8, 'medium': 0.6, 'low': 0.3}
            return priority_scores.get(priority, 0.6)
        
        # Infer from urgency keywords
        content_lower = content.lower()
        if any(word in content_lower for word in ['urgent', 'critical', 'immediate']):
            return 0.9
        elif any(word in content_lower for word in ['important', 'significant']):
            return 0.7
        
        return 0.6  # Default medium priority
    
    @staticmethod
    def _extract_impact_assessment(content: str) -> str:
        """Extract impact assessment from content"""
        impact_patterns = [
            r'Impact[:\-]\s*([^\n]+)',
            r'This will[:\-]?\s*([^\n]+)',
            r'Expected to[:\-]?\s*([^\n]+)'
        ]
        
        for pattern in impact_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Impact assessment pending"
    
    @staticmethod
    def _extract_insight_type(content: str) -> str:
        """Extract insight type from content"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['trend', 'pattern', 'increasing', 'growing']):
            return 'trend'
        elif any(word in content_lower for word in ['opportunity', 'potential', 'chance']):
            return 'opportunity'
        elif any(word in content_lower for word in ['risk', 'threat', 'concern', 'danger']):
            return 'risk'
        elif any(word in content_lower for word in ['connection', 'relationship', 'link']):
            return 'connection'
        
        return 'trend'
    
    @staticmethod
    def _extract_evidence(content: str) -> List[Dict]:
        """Extract supporting evidence from content"""
        # Look for evidence indicators
        evidence_patterns = [
            r'Evidence[:\-]\s*([^\n]+)',
            r'Based on[:\-]\s*([^\n]+)',
            r'Supported by[:\-]\s*([^\n]+)'
        ]
        
        evidence = []
        for pattern in evidence_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                evidence.append({'type': 'communication', 'description': match.strip()})
        
        return evidence[:3]  # Top 3 pieces of evidence
    
    @staticmethod
    def _extract_implications(content: str) -> str:
        """Extract business implications from content"""
        impl_patterns = [
            r'Implications?[:\-]\s*([^\n]+)',
            r'This means[:\-]?\s*([^\n]+)',
            r'As a result[:\-]?\s*([^\n]+)'
        ]
        
        for pattern in impl_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Business implications require analysis"
    
    @staticmethod
    def _extract_recommended_response(content: str) -> str:
        """Extract recommended response from content"""
        response_patterns = [
            r'Recommend[:\-]\s*([^\n]+)',
            r'Should[:\-]?\s*([^\n]+)',
            r'Next steps?[:\-]\s*([^\n]+)'
        ]
        
        for pattern in response_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Response strategy to be determined"
    
    @staticmethod
    def _extract_rationale(content: str) -> str:
        """Extract rationale from recommendation content"""
        rationale_patterns = [
            r'Why[:\-]\s*([^\n]+)',
            r'Rationale[:\-]\s*([^\n]+)',
            r'Because[:\-]?\s*([^\n]+)'
        ]
        
        for pattern in rationale_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Strategic rationale based on business context analysis"
    
    @staticmethod
    def _extract_impact_analysis(content: str) -> str:
        """Extract impact analysis from recommendation"""
        impact_patterns = [
            r'Impact[:\-]\s*([^\n]+)',
            r'Will result in[:\-]?\s*([^\n]+)',
            r'Expected outcome[:\-]\s*([^\n]+)'
        ]
        
        for pattern in impact_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return "Impact analysis pending"
    
    @staticmethod
    def _extract_urgency(content: str) -> str:
        """Extract urgency level from content"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['critical', 'urgent', 'immediate', 'asap']):
            return 'critical'
        elif any(word in content_lower for word in ['high', 'important', 'soon']):
            return 'high'
        elif any(word in content_lower for word in ['low', 'later', 'eventually']):
            return 'low'
        
        return 'medium'
    
    @staticmethod
    def _extract_impact_level(content: str) -> str:
        """Extract impact level from content"""
        content_lower = content.lower()
        
        if any(word in content_lower for word in ['significant', 'major', 'substantial', 'high impact']):
            return 'high'
        elif any(word in content_lower for word in ['minor', 'small', 'low impact']):
            return 'low'
        
        return 'medium'
    
    @staticmethod
    def _extract_time_sensitivity(content: str) -> str:
        """Extract time sensitivity from content"""
        time_patterns = [
            r'within\s+(\w+)',
            r'by\s+(\w+)',
            r'(\w+)\s+deadline'
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return f"Time sensitive: {match.group(1)}"
        
        content_lower = content.lower()
        if any(word in content_lower for word in ['today', 'tomorrow', 'this week']):
            return 'immediate'
        elif any(word in content_lower for word in ['this month', 'next week']):
            return 'short-term'
        
        return 'flexible'
    
    @staticmethod
    def _extract_related_contexts(content: str) -> List[str]:
        """Extract related contexts from content"""
        # Look for context references
        context_refs = re.findall(r'context[:\-]?\s*([^\n,]+)', content, re.IGNORECASE)
        return [ref.strip() for ref in context_refs][:3]
    
    @staticmethod
    def _extract_suggested_actions(content: str) -> List[Dict]:
        """Extract suggested actions from content"""
        actions = []
        
        # Look for action items
        action_patterns = [
            r'Action[:\-]\s*([^\n]+)',
            r'Step\s*\d+[:\-]\s*([^\n]+)',
            r'Next[:\-]?\s*([^\n]+)'
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                actions.append({
                    'description': match.strip(),
                    'priority': 'medium',
                    'estimated_time': 'TBD'
                })
        
        return actions[:5]  # Top 5 actions
    
    @staticmethod
    def _extract_success_metrics(content: str) -> List[str]:
        """Extract success metrics from content"""
        metric_patterns = [
            r'Metric[s]?[:\-]\s*([^\n]+)',
            r'Measure[:\-]\s*([^\n]+)',
            r'Success[:\-]\s*([^\n]+)'
        ]
        
        metrics = []
        for pattern in metric_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            metrics.extend([match.strip() for match in matches])
        
        return metrics[:3]  # Top 3 metrics


# Global parser instance
claude_parser = ClaudeResponseParser() 