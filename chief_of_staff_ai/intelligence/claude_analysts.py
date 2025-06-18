# File: chief_of_staff_ai/intelligence/claude_analysts.py
"""
Specialized Claude Opus 4 Analysts for Knowledge Tree Construction
================================================================
5 specialized AI analysts that process emails in parallel to build comprehensive intelligence
"""

import asyncio
import anthropic
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging
import os
import re

logger = logging.getLogger(__name__)

@dataclass
class AnalysisResult:
    """Result from a specialized Claude analyst"""
    analyst_type: str
    insights: Dict
    confidence: float
    evidence: List[Dict]
    relationships: List[Dict]
    topics: List[str]
    entities: List[Dict]
    processing_time: float

class BaseClaudeAnalyst:
    """Base class for specialized Claude analysts"""
    
    def __init__(self, analyst_type: str, model: str = None):
        self.analyst_type = analyst_type
        self.model = model or "claude-opus-4-20250514"
        self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
    async def analyze_emails(self, emails: List[Dict], context: Dict = None) -> AnalysisResult:
        """Analyze a batch of emails with specialized focus"""
        raise NotImplementedError("Subclasses must implement analyze_emails")
    
    def _prepare_email_context(self, emails: List[Dict]) -> str:
        """Prepare email context for Claude"""
        context_parts = []
        for email in emails[:50]:  # Limit to prevent token overflow
            context_parts.append(f"""
Email ID: {email.get('id')}
Date: {email.get('email_date')}
From: {email.get('sender')} 
To: {email.get('recipients')}
Subject: {email.get('subject')}
Body: {(email.get('body_text') or '')[:1000]}...
---
""")
        return "\n".join(context_parts)
    
    def _parse_json_response(self, response_text: str) -> Dict:
        """Parse Claude's JSON response safely"""
        try:
            # Extract JSON from response using regex
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {}
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON from {self.analyst_type} response")
            return {}
    
    def _extract_evidence(self, insights: Dict, emails: List[Dict]) -> List[Dict]:
        """Extract supporting evidence from emails"""
        evidence = []
        for category, items in insights.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and 'evidence' in item:
                        evidence.append({
                            'category': category,
                            'insight': item.get('description', ''),
                            'evidence': item.get('evidence', ''),
                            'confidence': item.get('confidence', 0.0)
                        })
        return evidence
    
    def _extract_topics(self, insights: Dict) -> List[str]:
        """Extract key topics from insights"""
        topics = set()
        for category, items in insights.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        if 'topics' in item:
                            topics.update(item['topics'])
                        if 'keywords' in item:
                            topics.update(item['keywords'])
        return list(topics)
    
    def _extract_entities(self, insights: Dict) -> List[Dict]:
        """Extract entities (people, companies, projects) from insights"""
        entities = []
        for category, items in insights.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and 'entities' in item:
                        entities.extend(item['entities'])
        return entities

class BusinessStrategyAnalyst(BaseClaudeAnalyst):
    """Analyzes emails for strategic business decisions and rationale"""
    
    def __init__(self):
        super().__init__("business_strategy")
        self.analysis_prompt = """You are a senior business strategy analyst with 20+ years of experience. Analyze these emails to extract strategic intelligence:

FOCUS AREAS:
1. Strategic decisions made or discussed
2. Business rationale and reasoning behind decisions  
3. Market positioning and competitive strategy
4. Growth strategies and expansion plans
5. Risk assessments and mitigation strategies
6. Resource allocation and investment decisions
7. Partnership and acquisition opportunities

ANALYSIS REQUIREMENTS:
- For each insight, provide specific evidence (quote relevant email parts)
- Assess confidence level (0.0-1.0) based on evidence strength
- Identify key people involved and their decision-making roles
- Connect insights to business impact and outcomes
- Look for patterns across multiple emails

OUTPUT FORMAT (JSON):
{
  "strategic_decisions": [
    {
      "decision": "specific decision made",
      "rationale": "reasoning behind decision",
      "key_people": ["person1", "person2"],
      "evidence": "quoted email content",
      "confidence": 0.85,
      "business_impact": "expected impact",
      "timeline": "when decision was made/will be implemented"
    }
  ],
  "market_positioning": [...],
  "competitive_intelligence": [...],
  "growth_strategies": [...],
  "risk_assessments": [...],
  "resource_allocation": [...],
  "partnerships": [...]
}

IMPORTANT: Base analysis ONLY on email content. Do not make assumptions beyond what's explicitly stated or strongly implied."""

    async def analyze_emails(self, emails: List[Dict], context: Dict = None) -> AnalysisResult:
        """Extract strategic business intelligence"""
        start_time = datetime.utcnow()
        
        try:
            email_context = self._prepare_email_context(emails)
            
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=4000,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": f"{self.analysis_prompt}\n\nEmails to analyze:\n{email_context}"
                }]
            )
            
            # Parse Claude's response
            result = self._parse_json_response(response.content[0].text)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return AnalysisResult(
                analyst_type=self.analyst_type,
                insights=result,
                confidence=self._calculate_overall_confidence(result),
                evidence=self._extract_evidence(result, emails),
                relationships=self._extract_relationships(result),
                topics=self._extract_topics(result),
                entities=self._extract_entities(result),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Business strategy analysis error: {str(e)}")
            return AnalysisResult(
                analyst_type=self.analyst_type,
                insights={},
                confidence=0.0,
                evidence=[],
                relationships=[],
                topics=[],
                entities=[],
                processing_time=0.0
            )
    
    def _calculate_overall_confidence(self, insights: Dict) -> float:
        """Calculate overall confidence score"""
        confidences = []
        for category, items in insights.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and 'confidence' in item:
                        confidences.append(item['confidence'])
        return sum(confidences) / len(confidences) if confidences else 0.0
    
    def _extract_relationships(self, insights: Dict) -> List[Dict]:
        """Extract relationship insights"""
        relationships = []
        for category, items in insights.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and 'key_people' in item:
                        for person in item['key_people']:
                            relationships.append({
                                'person': person,
                                'role': 'decision_maker',
                                'context': item.get('decision', ''),
                                'strength': item.get('confidence', 0.0)
                            })
        return relationships

class RelationshipDynamicsAnalyst(BaseClaudeAnalyst):
    """Maps relationship dynamics and influence patterns"""
    
    def __init__(self):
        super().__init__("relationship_dynamics")
        self.analysis_prompt = """You are an expert in organizational psychology and relationship mapping. Analyze these emails to understand interpersonal and professional dynamics:

FOCUS AREAS:
1. Communication patterns and frequencies between people
2. Influence hierarchies and decision-making power
3. Team collaboration patterns and effectiveness
4. Relationship quality indicators (trust, tension, respect)
5. Key connectors and network influencers
6. Communication styles and preferences
7. Conflict resolution patterns
8. Mentorship and guidance relationships

ANALYSIS REQUIREMENTS:
- Map who communicates with whom and how often
- Identify formal vs informal influence patterns
- Assess relationship health and trajectory
- Note communication tone and style differences
- Track relationship evolution over time

OUTPUT FORMAT (JSON):
{
  "key_relationships": [
    {
      "person_a": "person1@email.com",
      "person_b": "person2@email.com", 
      "relationship_type": "manager-report",
      "communication_frequency": "high",
      "relationship_quality": "positive",
      "influence_direction": "bidirectional",
      "evidence": "supporting email quotes",
      "confidence": 0.8
    }
  ],
  "influence_network": [
    {
      "person": "person@email.com",
      "influence_level": "high",
      "influence_scope": ["strategy", "technical"],
      "key_connections": ["person1", "person2"],
      "influence_style": "collaborative"
    }
  ],
  "communication_patterns": [...],
  "collaboration_insights": [...],
  "relationship_risks": [...],
  "networking_opportunities": [...]
}"""

    async def analyze_emails(self, emails: List[Dict], context: Dict = None) -> AnalysisResult:
        """Map relationship dynamics and influence patterns"""
        start_time = datetime.utcnow()
        
        try:
            email_context = self._prepare_email_context(emails)
            
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=4000,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": f"{self.analysis_prompt}\n\nEmails to analyze:\n{email_context}"
                }]
            )
            
            result = self._parse_json_response(response.content[0].text)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return AnalysisResult(
                analyst_type=self.analyst_type,
                insights=result,
                confidence=self._calculate_overall_confidence(result),
                evidence=self._extract_evidence(result, emails),
                relationships=self._extract_relationships(result),
                topics=self._extract_topics(result),
                entities=self._extract_entities(result),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Relationship dynamics analysis error: {str(e)}")
            return AnalysisResult(
                analyst_type=self.analyst_type,
                insights={},
                confidence=0.0,
                evidence=[],
                relationships=[],
                topics=[],
                entities=[],
                processing_time=0.0
            )

class TechnicalEvolutionAnalyst(BaseClaudeAnalyst):
    """Tracks technical decisions and architecture evolution"""
    
    def __init__(self):
        super().__init__("technical_evolution")
        self.analysis_prompt = """You are a senior technical architect with deep expertise in system design and technology evolution. Analyze these emails for technical intelligence:

FOCUS AREAS:
1. Technical decisions and their underlying rationale
2. Architecture choices and system design evolution
3. Technology stack discussions and migrations
4. Technical debt identification and management
5. Innovation opportunities and experimental approaches
6. Development methodology and process evolution
7. Performance, scalability, and reliability considerations
8. Security and compliance technical decisions

ANALYSIS REQUIREMENTS:
- Focus on understanding the WHY behind technical choices
- Track architecture evolution and decision points
- Identify technical risks and opportunities
- Map technology adoption patterns
- Assess technical decision quality and outcomes

OUTPUT FORMAT (JSON):
{
  "technical_decisions": [
    {
      "decision": "specific technical choice made",
      "rationale": "reasoning behind the decision",
      "technology": "specific tech/framework/tool",
      "impact": "expected technical impact",
      "decision_makers": ["person1", "person2"],
      "evidence": "supporting email content",
      "confidence": 0.9
    }
  ],
  "architecture_insights": [...],
  "tech_stack_evolution": [...],
  "technical_debt": [...],
  "innovation_opportunities": [...],
  "methodology_patterns": [...],
  "performance_considerations": [...],
  "security_decisions": [...]
}"""

    async def analyze_emails(self, emails: List[Dict], context: Dict = None) -> AnalysisResult:
        """Extract technical decisions and evolution patterns"""
        start_time = datetime.utcnow()
        
        try:
            email_context = self._prepare_email_context(emails)
            
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=4000,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": f"{self.analysis_prompt}\n\nEmails to analyze:\n{email_context}"
                }]
            )
            
            result = self._parse_json_response(response.content[0].text)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return AnalysisResult(
                analyst_type=self.analyst_type,
                insights=result,
                confidence=self._calculate_overall_confidence(result),
                evidence=self._extract_evidence(result, emails),
                relationships=self._extract_relationships_tech(result),
                topics=self._extract_topics(result),
                entities=self._extract_entities(result),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Technical evolution analysis error: {str(e)}")
            return AnalysisResult(
                analyst_type=self.analyst_type,
                insights={},
                confidence=0.0,
                evidence=[],
                relationships=[],
                topics=[],
                entities=[],
                processing_time=0.0
            )
    
    def _extract_relationships_tech(self, insights: Dict) -> List[Dict]:
        """Extract technical relationships and dependencies"""
        relationships = []
        for category, items in insights.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        if 'decision_makers' in item:
                            for person in item['decision_makers']:
                                relationships.append({
                                    'person': person,
                                    'role': 'technical_decision_maker',
                                    'context': item.get('decision', ''),
                                    'technology': item.get('technology', ''),
                                    'strength': item.get('confidence', 0.0)
                                })
        return relationships

class MarketIntelligenceAnalyst(BaseClaudeAnalyst):
    """Identifies market signals and competitive intelligence"""
    
    def __init__(self):
        super().__init__("market_intelligence")
        self.analysis_prompt = """You are a market intelligence analyst specializing in competitive strategy and market dynamics. Extract actionable market intelligence from these emails:

FOCUS AREAS:
1. Market trends and emerging signals
2. Competitive movements and intelligence
3. Customer feedback, needs, and satisfaction
4. Partnership and business development opportunities
5. Industry developments and regulatory changes
6. Timing factors and market windows
7. Pricing strategies and market positioning
8. Customer acquisition and retention insights

ANALYSIS REQUIREMENTS:
- Focus on external market factors and opportunities
- Identify competitive advantages and threats
- Track customer sentiment and market reception
- Assess timing and market readiness
- Connect market signals to business opportunities

OUTPUT FORMAT (JSON):
{
  "market_trends": [
    {
      "trend": "specific market trend identified",
      "evidence": "supporting email content",
      "impact": "potential business impact",
      "timeline": "expected timeline",
      "confidence": 0.8,
      "opportunity_size": "small/medium/large"
    }
  ],
  "competitive_intelligence": [...],
  "customer_insights": [...],
  "partnership_opportunities": [...],
  "industry_developments": [...],
  "timing_factors": [...],
  "market_positioning": [...],
  "customer_acquisition": [...]
}"""

    async def analyze_emails(self, emails: List[Dict], context: Dict = None) -> AnalysisResult:
        """Extract market intelligence and opportunities"""
        start_time = datetime.utcnow()
        
        try:
            email_context = self._prepare_email_context(emails)
            
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=4000,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": f"{self.analysis_prompt}\n\nEmails to analyze:\n{email_context}"
                }]
            )
            
            result = self._parse_json_response(response.content[0].text)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return AnalysisResult(
                analyst_type=self.analyst_type,
                insights=result,
                confidence=self._calculate_overall_confidence(result),
                evidence=self._extract_evidence(result, emails),
                relationships=self._extract_market_relationships(result),
                topics=self._extract_topics(result),
                entities=self._extract_entities(result),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Market intelligence analysis error: {str(e)}")
            return AnalysisResult(
                analyst_type=self.analyst_type,
                insights={},
                confidence=0.0,
                evidence=[],
                relationships=[],
                topics=[],
                entities=[],
                processing_time=0.0
            )
    
    def _extract_market_relationships(self, insights: Dict) -> List[Dict]:
        """Extract market-related relationships"""
        relationships = []
        for category, items in insights.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        # Extract customer relationships
                        if 'customers' in item:
                            for customer in item['customers']:
                                relationships.append({
                                    'entity': customer,
                                    'type': 'customer',
                                    'context': item.get('trend', ''),
                                    'strength': item.get('confidence', 0.0)
                                })
                        # Extract competitor relationships
                        if 'competitors' in item:
                            for competitor in item['competitors']:
                                relationships.append({
                                    'entity': competitor,
                                    'type': 'competitor',
                                    'context': item.get('intelligence', ''),
                                    'strength': item.get('confidence', 0.0)
                                })
        return relationships

class PredictiveAnalyst(BaseClaudeAnalyst):
    """Analyzes patterns to predict future outcomes and opportunities"""
    
    def __init__(self):
        super().__init__("predictive_analysis")
        self.analysis_prompt = """You are a predictive analytics expert specializing in pattern recognition and scenario planning. Based on these emails, identify predictive insights:

FOCUS AREAS:
1. Emerging patterns and trend trajectories
2. Likely future scenarios and outcomes
3. Relationship trajectory predictions
4. Upcoming decision points and inflection moments
5. Risk indicators and early warning signals
6. Opportunity windows and optimal timing
7. Resource and capability gap predictions
8. Market timing and competitive positioning forecasts

ANALYSIS REQUIREMENTS:
- Base predictions on observable patterns in the data
- Provide probabilistic assessments where possible
- Identify leading indicators and causality chains
- Focus on actionable predictions with clear timelines
- Connect historical patterns to future scenarios

OUTPUT FORMAT (JSON):
{
  "predictions": [
    {
      "prediction": "specific future outcome predicted",
      "probability": 0.75,
      "timeline": "3-6 months",
      "evidence_pattern": "pattern in emails supporting prediction",
      "leading_indicators": ["indicator1", "indicator2"],
      "confidence": 0.8,
      "impact": "high/medium/low"
    }
  ],
  "emerging_patterns": [...],
  "decision_points": [...],
  "risk_indicators": [...],
  "opportunity_windows": [...],
  "relationship_trajectories": [...],
  "market_timing": [...],
  "recommended_actions": [...]
}"""

    async def analyze_emails(self, emails: List[Dict], context: Dict = None) -> AnalysisResult:
        """Generate predictions based on patterns"""
        start_time = datetime.utcnow()
        
        try:
            email_context = self._prepare_email_context(emails)
            
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=self.model,
                max_tokens=4000,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": f"{self.analysis_prompt}\n\nEmails to analyze:\n{email_context}"
                }]
            )
            
            result = self._parse_json_response(response.content[0].text)
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            return AnalysisResult(
                analyst_type=self.analyst_type,
                insights=result,
                confidence=self._calculate_overall_confidence(result),
                evidence=self._extract_evidence(result, emails),
                relationships=self._extract_predictive_relationships(result),
                topics=self._extract_topics(result),
                entities=self._extract_entities(result),
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Predictive analysis error: {str(e)}")
            return AnalysisResult(
                analyst_type=self.analyst_type,
                insights={},
                confidence=0.0,
                evidence=[],
                relationships=[],
                topics=[],
                entities=[],
                processing_time=0.0
            )
    
    def _extract_predictive_relationships(self, insights: Dict) -> List[Dict]:
        """Extract predictive relationship insights"""
        relationships = []
        for category, items in insights.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and 'relationship_trajectories' in category:
                        relationships.append({
                            'prediction': item.get('prediction', ''),
                            'probability': item.get('probability', 0.0),
                            'timeline': item.get('timeline', ''),
                            'type': 'predictive_relationship'
                        })
        return relationships

class KnowledgeTreeBuilder:
    """Orchestrates multiple Claude analysts to build comprehensive knowledge tree"""
    
    def __init__(self):
        self.analysts = {
            'business_strategy': BusinessStrategyAnalyst(),
            'relationship_dynamics': RelationshipDynamicsAnalyst(),
            'technical_evolution': TechnicalEvolutionAnalyst(),
            'market_intelligence': MarketIntelligenceAnalyst(),
            'predictive': PredictiveAnalyst()
        }
        
    async def build_knowledge_tree(self, user_id: int, emails: List[Dict], time_window_days: int = 30) -> Dict:
        """Build comprehensive knowledge tree from emails"""
        try:
            if not emails:
                logger.warning(f"No emails provided for knowledge tree building")
                return {'status': 'no_data', 'error': 'No emails to analyze'}
            
            logger.info(f"🧠 Building knowledge tree from {len(emails)} emails with {len(self.analysts)} analysts")
            
            # Run all analysts in parallel
            start_time = datetime.utcnow()
            analysis_tasks = []
            
            for analyst_name, analyst in self.analysts.items():
                logger.info(f"🔬 Starting {analyst_name} analysis...")
                task = analyst.analyze_emails(emails)
                analysis_tasks.append(task)
            
            # Wait for all analyses to complete
            results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # Filter out exceptions and log errors
            valid_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    analyst_name = list(self.analysts.keys())[i]
                    logger.error(f"❌ {analyst_name} analysis failed: {str(result)}")
                else:
                    valid_results.append(result)
                    logger.info(f"✅ {result.analyst_type} analysis completed (confidence: {result.confidence:.2f})")
            
            if not valid_results:
                return {'status': 'error', 'error': 'All analysis tasks failed'}
            
            # Merge results into knowledge tree
            knowledge_tree = self._merge_analysis_results(valid_results)
            
            # Add metadata
            total_time = (datetime.utcnow() - start_time).total_seconds()
            knowledge_tree['metadata'] = {
                'user_id': user_id,
                'time_window_days': time_window_days,
                'email_count': len(emails),
                'analysts_completed': len(valid_results),
                'total_processing_time': total_time,
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'status': 'completed'
            }
            
            logger.info(f"🎯 Knowledge tree completed in {total_time:.1f}s with {len(valid_results)} analysts")
            return knowledge_tree
            
        except Exception as e:
            logger.error(f"❌ Knowledge tree building error: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _merge_analysis_results(self, results: List[AnalysisResult]) -> Dict:
        """Merge results from all analysts into unified knowledge tree"""
        knowledge_tree = {
            'insights': {},
            'relationships': [],
            'topics': set(),
            'entities': [],
            'evidence': [],
            'predictions': [],
            'confidence_scores': {}
        }
        
        for result in results:
            # Store insights by analyst type
            knowledge_tree['insights'][result.analyst_type] = result.insights
            
            # Aggregate relationships
            knowledge_tree['relationships'].extend(result.relationships)
            
            # Collect all topics
            knowledge_tree['topics'].update(result.topics)
            
            # Aggregate entities
            knowledge_tree['entities'].extend(result.entities)
            
            # Collect evidence
            knowledge_tree['evidence'].extend(result.evidence)
            
            # Store confidence scores
            knowledge_tree['confidence_scores'][result.analyst_type] = result.confidence
            
            # Extract predictions from predictive analyst
            if result.analyst_type == 'predictive' and 'predictions' in result.insights:
                knowledge_tree['predictions'] = result.insights['predictions']
        
        # Convert set to list for JSON serialization
        knowledge_tree['topics'] = list(knowledge_tree['topics'])
        
        # Deduplicate and rank entities
        knowledge_tree['entities'] = self._deduplicate_entities(knowledge_tree['entities'])
        
        # Calculate overall confidence
        confidences = list(knowledge_tree['confidence_scores'].values())
        knowledge_tree['overall_confidence'] = sum(confidences) / len(confidences) if confidences else 0.0
        
        return knowledge_tree
    
    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """Deduplicate and merge entity information"""
        entity_map = {}
        
        for entity in entities:
            if not isinstance(entity, dict):
                continue
                
            # Create key from entity type and name/email
            entity_type = entity.get('type', 'unknown')
            entity_name = entity.get('name') or entity.get('email') or entity.get('company')
            
            if not entity_name:
                continue
                
            key = (entity_type, entity_name.lower())
            
            if key in entity_map:
                # Merge information
                existing = entity_map[key]
                existing['mentions'] = existing.get('mentions', 0) + 1
                existing['contexts'] = existing.get('contexts', [])
                if 'context' in entity:
                    existing['contexts'].append(entity['context'])
            else:
                entity['mentions'] = 1
                entity['contexts'] = [entity.get('context', '')]
                entity_map[key] = entity
        
        # Sort by mentions (frequency)
        sorted_entities = sorted(entity_map.values(), key=lambda x: x.get('mentions', 0), reverse=True)
        return sorted_entities[:100]  # Limit to top 100 entities 