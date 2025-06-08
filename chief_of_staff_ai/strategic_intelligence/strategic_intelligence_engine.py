"""
Strategic Intelligence Engine

Core engine that transforms raw communications into strategic business intelligence.
Focuses on unified knowledge synthesis rather than individual email processing.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict
import json

logger = logging.getLogger(__name__)

@dataclass
class BusinessContext:
    """Unified business context combining multiple communications"""
    context_id: str
    name: str
    description: str
    context_type: str  # 'opportunity', 'relationship', 'project', 'challenge'
    key_people: List[Dict]
    related_communications: List[Dict]
    timeline: List[Dict]
    current_status: str
    priority_score: float
    impact_assessment: str
    confidence_level: float
    created_at: datetime
    last_updated: datetime

@dataclass 
class StrategicRecommendation:
    """Strategic recommendation with impact analysis"""
    recommendation_id: str
    title: str
    description: str
    rationale: str
    impact_analysis: str
    urgency_level: str  # 'critical', 'high', 'medium', 'low'
    estimated_impact: str  # 'high', 'medium', 'low'
    time_sensitivity: str
    related_contexts: List[str]
    suggested_actions: List[Dict]
    success_metrics: List[str]
    confidence_score: float
    created_at: datetime

@dataclass
class StrategicInsight:
    """Cross-pattern strategic insight"""
    insight_id: str
    title: str
    insight_type: str  # 'trend', 'opportunity', 'risk', 'connection'
    description: str
    supporting_evidence: List[Dict]
    business_implications: str
    recommended_response: str
    confidence_level: float
    created_at: datetime

class StrategyEngine:
    """
    Strategic Intelligence Engine - The Chief of Staff Brain
    
    Transforms raw communications into strategic business intelligence
    through unified knowledge synthesis and pattern analysis.
    """
    
    def __init__(self, claude_client, db_manager):
        self.claude_client = claude_client
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
    
    def generate_strategic_intelligence(self, user_email: str) -> Dict[str, Any]:
        """
        Generate comprehensive strategic intelligence for a user.
        This is the main entry point that replaces email-by-email processing.
        """
        try:
            self.logger.info(f"Generating strategic intelligence for {user_email}")
            
            # Get user and all their content
            user = self.db_manager.get_user_by_email(user_email)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Step 1: Content Ingestion Pipeline - Get raw materials
            content_summary = self._ingest_content_pipeline(user)
            
            # Step 2: Unified Knowledge Synthesis - Build business contexts
            business_contexts = self._synthesize_business_contexts(user, content_summary)
            
            # Step 3: Strategic Pattern Analysis - Find connections and trends
            strategic_insights = self._analyze_strategic_patterns(user, business_contexts)
            
            # Step 4: Generate Strategic Recommendations - Actionable guidance
            recommendations = self._generate_strategic_recommendations(
                user, business_contexts, strategic_insights
            )
            
            # Step 5: Compile Chief of Staff Intelligence Brief
            intelligence_brief = self._compile_intelligence_brief(
                user, business_contexts, strategic_insights, recommendations
            )
            
            return {
                'success': True,
                'user_email': user_email,
                'intelligence_brief': intelligence_brief,
                'business_contexts': business_contexts,
                'strategic_insights': strategic_insights,
                'recommendations': recommendations,
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating strategic intelligence: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _ingest_content_pipeline(self, user) -> Dict[str, Any]:
        """
        Step 1: Content Ingestion Pipeline
        Lightweight processing of all content as raw material
        """
        # Get all communications (emails, tasks, people, projects)
        emails = self.db_manager.get_user_emails(user.id, limit=200)
        people = self.db_manager.get_user_people(user.id, limit=100)
        tasks = self.db_manager.get_user_tasks(user.id, limit=100)
        projects = self.db_manager.get_user_projects(user.id, limit=50)
        
        # Create lightweight content summary
        content_summary = {
            'emails': {
                'total': len(emails),
                'recent': [self._extract_email_essence(email) for email in emails[:50]],
                'timespan': self._get_timespan(emails)
            },
            'people': {
                'total': len(people),
                'key_contacts': [self._extract_person_essence(person) for person in people[:20]]
            },
            'projects': {
                'total': len(projects),
                'active': [self._extract_project_essence(project) for project in projects if project.status == 'active']
            },
            'tasks': {
                'total': len(tasks),
                'pending': [self._extract_task_essence(task) for task in tasks if task.status == 'pending']
            }
        }
        
        return content_summary
    
    def _synthesize_business_contexts(self, user, content_summary) -> List[BusinessContext]:
        """
        Step 2: Unified Knowledge Synthesis
        Combine content into coherent business contexts rather than individual items
        """
        try:
            # Use Claude to synthesize unified business contexts
            synthesis_prompt = self._build_synthesis_prompt(content_summary)
            
            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                system="""You are a strategic business intelligence synthesizer. Your job is to analyze all communications and identify unified business contexts.

Instead of focusing on individual emails, identify coherent business situations that span multiple communications. Look for:
- Ongoing opportunities (fundraising, partnerships, deals)
- Key relationships and their development
- Strategic projects and initiatives  
- Business challenges requiring attention
- Market or competitive insights

Each context should represent a unified business situation with clear strategic implications.""",
                messages=[{"role": "user", "content": synthesis_prompt}]
            )
            
            # Parse Claude's response into business contexts
            contexts_data = self._parse_business_contexts(response.content[0].text)
            
            # Convert to BusinessContext objects
            business_contexts = []
            for context_data in contexts_data:
                context = BusinessContext(
                    context_id=context_data.get('id', f"context_{len(business_contexts)}"),
                    name=context_data.get('name'),
                    description=context_data.get('description'),
                    context_type=context_data.get('type'),
                    key_people=context_data.get('key_people', []),
                    related_communications=context_data.get('related_communications', []),
                    timeline=context_data.get('timeline', []),
                    current_status=context_data.get('status'),
                    priority_score=context_data.get('priority_score', 0.5),
                    impact_assessment=context_data.get('impact_assessment'),
                    confidence_level=context_data.get('confidence_level', 0.7),
                    created_at=datetime.now(),
                    last_updated=datetime.now()
                )
                business_contexts.append(context)
            
            return business_contexts
            
        except Exception as e:
            self.logger.error(f"Error synthesizing business contexts: {str(e)}")
            return []
    
    def _analyze_strategic_patterns(self, user, business_contexts) -> List[StrategicInsight]:
        """
        Step 3: Strategic Pattern Analysis
        Cross-reference patterns across communications and identify strategic insights
        """
        try:
            # Analyze patterns across business contexts
            pattern_prompt = self._build_pattern_analysis_prompt(business_contexts)
            
            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=3000,
                system="""You are a strategic pattern analyst. Analyze business contexts to identify strategic insights.

Look for:
- Converging opportunities (multiple contexts pointing to same opportunity)
- Timing patterns (windows of opportunity, urgency indicators)
- Relationship networks (how people/contexts connect)
- Resource allocation patterns
- Market trends and competitive insights
- Risk patterns and mitigation opportunities

Focus on insights that have strategic business implications.""",
                messages=[{"role": "user", "content": pattern_prompt}]
            )
            
            # Parse insights from Claude's response
            insights_data = self._parse_strategic_insights(response.content[0].text)
            
            # Convert to StrategicInsight objects
            strategic_insights = []
            for insight_data in insights_data:
                insight = StrategicInsight(
                    insight_id=insight_data.get('id', f"insight_{len(strategic_insights)}"),
                    title=insight_data.get('title'),
                    insight_type=insight_data.get('type'),
                    description=insight_data.get('description'),
                    supporting_evidence=insight_data.get('evidence', []),
                    business_implications=insight_data.get('implications'),
                    recommended_response=insight_data.get('response'),
                    confidence_level=insight_data.get('confidence', 0.7),
                    created_at=datetime.now()
                )
                strategic_insights.append(insight)
            
            return strategic_insights
            
        except Exception as e:
            self.logger.error(f"Error analyzing strategic patterns: {str(e)}")
            return []
    
    def _generate_strategic_recommendations(self, user, business_contexts, strategic_insights) -> List[StrategicRecommendation]:
        """
        Step 4: Generate Strategic Recommendations
        Create actionable recommendations with impact analysis
        """
        try:
            # Generate strategic recommendations
            recommendations_prompt = self._build_recommendations_prompt(business_contexts, strategic_insights)
            
            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                system="""You are a strategic business advisor and Chief of Staff. Generate actionable recommendations based on business contexts and insights.

Each recommendation should:
- Be specific and actionable
- Include clear rationale and impact analysis
- Suggest concrete next steps
- Explain timing and urgency
- Connect multiple business contexts when relevant
- Focus on highest business impact

Be persuasive and strategic - explain WHY this matters and WHAT impact it will have.""",
                messages=[{"role": "user", "content": recommendations_prompt}]
            )
            
            # Parse recommendations from Claude's response
            recommendations_data = self._parse_strategic_recommendations(response.content[0].text)
            
            # Convert to StrategicRecommendation objects
            recommendations = []
            for rec_data in recommendations_data:
                recommendation = StrategicRecommendation(
                    recommendation_id=rec_data.get('id', f"rec_{len(recommendations)}"),
                    title=rec_data.get('title'),
                    description=rec_data.get('description'),
                    rationale=rec_data.get('rationale'),
                    impact_analysis=rec_data.get('impact_analysis'),
                    urgency_level=rec_data.get('urgency', 'medium'),
                    estimated_impact=rec_data.get('impact', 'medium'),
                    time_sensitivity=rec_data.get('time_sensitivity'),
                    related_contexts=rec_data.get('related_contexts', []),
                    suggested_actions=rec_data.get('actions', []),
                    success_metrics=rec_data.get('metrics', []),
                    confidence_score=rec_data.get('confidence', 0.8),
                    created_at=datetime.now()
                )
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating strategic recommendations: {str(e)}")
            return []
    
    def _compile_intelligence_brief(self, user, business_contexts, strategic_insights, recommendations) -> Dict[str, Any]:
        """
        Step 5: Compile Chief of Staff Intelligence Brief
        Create the final strategic intelligence summary
        """
        # Prioritize recommendations by urgency and impact
        critical_recommendations = [r for r in recommendations if r.urgency_level == 'critical']
        high_priority_recommendations = [r for r in recommendations if r.urgency_level == 'high']
        
        # Identify key opportunities and risks
        opportunities = [ctx for ctx in business_contexts if ctx.context_type == 'opportunity']
        risks = [insight for insight in strategic_insights if insight.insight_type == 'risk']
        
        intelligence_brief = {
            'executive_summary': self._generate_executive_summary(business_contexts, strategic_insights, recommendations),
            'critical_actions': {
                'count': len(critical_recommendations),
                'items': [self._format_recommendation_brief(r) for r in critical_recommendations]
            },
            'high_priority_actions': {
                'count': len(high_priority_recommendations),
                'items': [self._format_recommendation_brief(r) for r in high_priority_recommendations[:5]]
            },
            'key_opportunities': {
                'count': len(opportunities),
                'items': [self._format_context_brief(ctx) for ctx in opportunities[:3]]
            },
            'strategic_insights': {
                'count': len(strategic_insights),
                'items': [self._format_insight_brief(insight) for insight in strategic_insights[:5]]
            },
            'business_contexts_summary': {
                'total_contexts': len(business_contexts),
                'by_type': self._summarize_contexts_by_type(business_contexts)
            }
        }
        
        return intelligence_brief
    
    def _extract_email_essence(self, email) -> Dict[str, Any]:
        """Extract essential elements from email for synthesis"""
        return {
            'subject': email.subject,
            'sender': email.sender_name or email.sender,
            'date': email.email_date.isoformat() if email.email_date else None,
            'summary': email.ai_summary,
            'topics': email.topics,
            'priority_score': email.priority_score,
            'key_insights': email.key_insights
        }
    
    def _extract_person_essence(self, person) -> Dict[str, Any]:
        """Extract essential elements from person for synthesis"""
        return {
            'name': person.name,
            'email': person.email_address,
            'company': person.company,
            'title': person.title,
            'relationship': person.relationship_type,
            'total_emails': person.total_emails,
            'last_interaction': person.last_interaction.isoformat() if person.last_interaction else None
        }
    
    def _extract_project_essence(self, project) -> Dict[str, Any]:
        """Extract essential elements from project for synthesis"""
        return {
            'name': project.name,
            'description': project.description,
            'status': project.status,
            'priority': project.priority,
            'stakeholders': project.stakeholders,
            'total_emails': project.total_emails
        }
    
    def _extract_task_essence(self, task) -> Dict[str, Any]:
        """Extract essential elements from task for synthesis"""
        return {
            'description': task.description,
            'assignee': task.assignee,
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'priority': task.priority,
            'category': task.category,
            'confidence': task.confidence
        }
    
    def _get_timespan(self, emails) -> Dict[str, Any]:
        """Get timespan of communications"""
        if not emails:
            return {}
        
        dates = [email.email_date for email in emails if email.email_date]
        if not dates:
            return {}
        
        return {
            'earliest': min(dates).isoformat(),
            'latest': max(dates).isoformat(),
            'span_days': (max(dates) - min(dates)).days
        }
    
    def _build_synthesis_prompt(self, content_summary) -> str:
        """Build prompt for business context synthesis"""
        return f"""Analyze this business communication data and identify unified business contexts:

CONTENT SUMMARY:
{json.dumps(content_summary, indent=2)}

Identify 3-7 coherent business contexts that represent ongoing business situations. Each context should:

1. Combine multiple related communications into one unified situation
2. Have clear strategic business implications  
3. Involve key people and relationships
4. Represent opportunities, challenges, projects, or strategic relationships

For each context, provide:
- Name and description
- Type (opportunity/relationship/project/challenge)
- Key people involved
- Current status and priority
- Impact assessment
- Timeline of developments

Focus on what requires strategic attention, not individual email management."""
    
    def _build_pattern_analysis_prompt(self, business_contexts) -> str:
        """Build prompt for strategic pattern analysis"""
        contexts_text = "\n\n".join([
            f"Context: {ctx.name}\nType: {ctx.context_type}\nDescription: {ctx.description}\nPeople: {ctx.key_people}\nStatus: {ctx.current_status}"
            for ctx in business_contexts
        ])
        
        return f"""Analyze these business contexts for strategic patterns and insights:

BUSINESS CONTEXTS:
{contexts_text}

Identify strategic insights by looking for:
1. Converging opportunities (multiple contexts creating momentum)
2. Timing patterns (windows of opportunity, urgent situations)
3. Relationship networks (how people/contexts connect strategically)
4. Resource patterns (where attention/resources should focus)
5. Market/competitive insights
6. Risk patterns requiring mitigation

Provide 3-5 strategic insights with supporting evidence and business implications."""
    
    def _build_recommendations_prompt(self, business_contexts, strategic_insights) -> str:
        """Build prompt for strategic recommendations"""
        contexts_summary = "\n".join([f"- {ctx.name}: {ctx.description}" for ctx in business_contexts])
        insights_summary = "\n".join([f"- {insight.title}: {insight.description}" for insight in strategic_insights])
        
        return f"""Based on these business contexts and strategic insights, generate strategic recommendations:

BUSINESS CONTEXTS:
{contexts_summary}

STRATEGIC INSIGHTS:
{insights_summary}

Generate 3-7 strategic recommendations that:
1. Address the highest impact opportunities
2. Connect multiple business contexts when relevant
3. Include specific next steps and timing
4. Explain the business rationale and expected impact
5. Prioritize by urgency and potential value

Each recommendation should persuade WHY it matters and WHAT impact it will create."""
    
    # Parsing methods for Claude responses
    def _parse_business_contexts(self, response_text) -> List[Dict]:
        """Parse business contexts from Claude response"""
        from .claude_response_parser import claude_parser
        return claude_parser.parse_business_contexts(response_text)
    
    def _parse_strategic_insights(self, response_text) -> List[Dict]:
        """Parse strategic insights from Claude response"""
        from .claude_response_parser import claude_parser
        return claude_parser.parse_strategic_insights(response_text)
    
    def _parse_strategic_recommendations(self, response_text) -> List[Dict]:
        """Parse recommendations from Claude response"""
        from .claude_response_parser import claude_parser
        return claude_parser.parse_strategic_recommendations(response_text)
    
    def _generate_executive_summary(self, business_contexts, strategic_insights, recommendations) -> str:
        """Generate executive summary of strategic intelligence"""
        return f"Strategic intelligence analysis identified {len(business_contexts)} key business contexts, {len(strategic_insights)} strategic insights, and {len(recommendations)} actionable recommendations."
    
    def _format_recommendation_brief(self, recommendation) -> Dict[str, Any]:
        """Format recommendation for brief display"""
        return {
            'title': recommendation.title,
            'description': recommendation.description,
            'urgency': recommendation.urgency_level,
            'impact': recommendation.estimated_impact,
            'rationale': recommendation.rationale
        }
    
    def _format_context_brief(self, context) -> Dict[str, Any]:
        """Format business context for brief display"""
        return {
            'name': context.name,
            'type': context.context_type,
            'description': context.description,
            'status': context.current_status,
            'priority_score': context.priority_score
        }
    
    def _format_insight_brief(self, insight) -> Dict[str, Any]:
        """Format strategic insight for brief display"""
        return {
            'title': insight.title,
            'type': insight.insight_type,
            'description': insight.description,
            'implications': insight.business_implications
        }
    
    def _summarize_contexts_by_type(self, business_contexts) -> Dict[str, int]:
        """Summarize business contexts by type"""
        summary = defaultdict(int)
        for context in business_contexts:
            summary[context.context_type] += 1
        return dict(summary)


# Initialize the strategy engine instance
strategy_engine = None

def get_strategy_engine(claude_client=None, db_manager=None):
    """Get or create strategy engine instance"""
    global strategy_engine
    if strategy_engine is None and claude_client and db_manager:
        strategy_engine = StrategyEngine(claude_client, db_manager)
    return strategy_engine 