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
    
    def generate_strategic_intelligence(self, user_email: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Generate comprehensive strategic intelligence for a user.
        Uses caching to prevent expensive regeneration on every request.
        
        Args:
            user_email: User's email address
            force_refresh: If True, bypass cache and generate fresh intelligence
        """
        try:
            # Import cache here to avoid circular imports
            from .strategic_intelligence_cache import strategic_intelligence_cache
            
            # Check cache first (unless force refresh)
            if not force_refresh:
                cached_result = strategic_intelligence_cache.get(user_email)
                if cached_result:
                    self.logger.info(f"Returning cached Strategic Intelligence for {user_email}")
                    return cached_result
            
            self.logger.info(f"Generating strategic intelligence for {user_email}")
            
            # Get user and all their content
            user = self.db_manager.get_user_by_email(user_email)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Step 1: Content Ingestion Pipeline - ENGAGEMENT-DRIVEN
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
            
            # Prepare result
            result = {
                'success': True,
                'user_email': user_email,
                'intelligence_brief': intelligence_brief,
                'business_contexts': business_contexts,
                'strategic_insights': strategic_insights,
                'recommendations': recommendations,
                'generated_at': datetime.now().isoformat(),
                'cache_info': {
                    'generated_fresh': True,
                    'force_refresh': force_refresh
                }
            }
            
            # Cache the result for future use (30 minute TTL)
            strategic_intelligence_cache.set(user_email, result, ttl_minutes=30)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating strategic intelligence: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _ingest_content_pipeline(self, user) -> Dict[str, Any]:
        """
        Step 1: Content Ingestion Pipeline - ENGAGEMENT-DRIVEN
        Uses Smart Contact Strategy to focus only on business-relevant communications
        """
        try:
            # Initialize Smart Contact Strategy
            from chief_of_staff_ai.engagement_analysis.smart_contact_strategy import smart_contact_strategy
            
            self.logger.info(f"Building engagement-driven content pipeline for user {user.id}")
            
            # Step 1: Ensure trusted contact database exists
            trusted_result = smart_contact_strategy.build_trusted_contact_database(
                user_email=user.email,
                days_back=365  # 1 year of engagement analysis
            )
            
            if trusted_result.get('success'):
                self.logger.info(f"Trusted contact database: {trusted_result.get('trusted_contacts_count', 0)} contacts")
            
            # Step 2: Get ALL communications first
            all_emails = self.db_manager.get_user_emails(user.id, limit=500)  # Increased limit for filtering
            all_people = self.db_manager.get_user_people(user.id, limit=200)
            all_tasks = self.db_manager.get_user_tasks(user.id, limit=200)
            all_projects = self.db_manager.get_user_projects(user.id, limit=100)
            
            # Step 3: Apply Smart Contact Strategy filtering
            engagement_filtered_emails = []
            business_relevant_people = []
            
            # Filter emails using Smart Contact Strategy
            for email in all_emails:
                if email.sender and email.subject:
                    # Create email data for classification
                    email_data = {
                        'sender': email.sender,
                        'sender_name': email.sender_name,
                        'subject': email.subject,
                        'body_preview': email.body_preview or email.snippet,
                        'date': email.email_date.isoformat() if email.email_date else None,
                        'has_attachments': email.has_attachments,
                        'labels': email.labels or []
                    }
                    
                    # Classify email using Smart Contact Strategy
                    classification = smart_contact_strategy.classify_incoming_email(
                        user_email=user.email,
                        email_data=email_data
                    )
                    
                    # Only include emails that should be processed by AI
                    if classification.action in ['PROCESS_WITH_AI', 'QUICK_CHECK']:
                        engagement_filtered_emails.append(email)
                        self.logger.debug(f"Included email: {email.subject[:50]}... (Action: {classification.action})")
                    else:
                        self.logger.debug(f"Filtered out email: {email.subject[:50]}... (Action: {classification.action})")
            
            # Filter people to focus on trusted contacts and business relationships
            trusted_contacts_result = smart_contact_strategy.get_engagement_insights(user.email)
            trusted_emails = set()
            
            if trusted_contacts_result.get('success'):
                # Extract trusted contact emails from engagement insights
                engagement_patterns = trusted_contacts_result.get('engagement_patterns', {})
                for pattern_data in engagement_patterns.values():
                    if isinstance(pattern_data, dict) and pattern_data.get('emails'):
                        trusted_emails.update(email.lower() for email in pattern_data['emails'])
            
            for person in all_people:
                if person.email_address and person.name:
                    # Include if trusted contact OR high business value
                    is_trusted = person.email_address.lower() in trusted_emails
                    is_business_relevant = (
                        person.total_emails and person.total_emails >= 2 and  # Multiple interactions
                        person.relationship_type not in ['spam', 'automated', None] and
                        not any(pattern in person.email_address.lower() for pattern in ['noreply', 'no-reply', 'automated', 'system'])
                    )
                    
                    if is_trusted or is_business_relevant:
                        business_relevant_people.append(person)
            
            # Filter tasks and projects (keep all for now, but could filter by assignee/stakeholder engagement)
            strategic_tasks = [task for task in all_tasks if task.description and len(task.description.strip()) > 10]
            strategic_projects = [proj for proj in all_projects if proj.name and proj.status in ['active', 'planning']]
            
            # Calculate efficiency metrics
            total_emails_processed = len(all_emails)
            engagement_emails_processed = len(engagement_filtered_emails)
            efficiency_ratio = engagement_emails_processed / max(total_emails_processed, 1)
            
            self.logger.info(f"Smart Content Filtering Results:")
            self.logger.info(f"  - Total emails: {total_emails_processed}")
            self.logger.info(f"  - Engagement-filtered emails: {engagement_emails_processed}")
            self.logger.info(f"  - Efficiency ratio: {efficiency_ratio:.2%}")
            self.logger.info(f"  - Business-relevant people: {len(business_relevant_people)}")
            self.logger.info(f"  - Strategic tasks: {len(strategic_tasks)}")
            self.logger.info(f"  - Strategic projects: {len(strategic_projects)}")
            
            # Create strategic content summary - FOCUSED ON ENGAGEMENT
            content_summary = {
                'emails': {
                    'total_available': total_emails_processed,
                    'engagement_filtered': engagement_emails_processed,
                    'efficiency_ratio': efficiency_ratio,
                    'strategic_content': [self._extract_email_essence(email) for email in engagement_filtered_emails[:50]],
                    'timespan': self._get_timespan(engagement_filtered_emails),
                    'filtering_strategy': 'smart_contact_engagement'
                },
                'people': {
                    'total_available': len(all_people),
                    'business_relevant': len(business_relevant_people),
                    'trusted_contacts': len(trusted_emails),
                    'key_relationships': [self._extract_person_essence(person) for person in business_relevant_people[:25]]
                },
                'projects': {
                    'total': len(strategic_projects),
                    'strategic_active': [self._extract_project_essence(project) for project in strategic_projects]
                },
                'tasks': {
                    'total': len(strategic_tasks),
                    'strategic_pending': [self._extract_task_essence(task) for task in strategic_tasks if task.status == 'pending']
                },
                'engagement_intelligence': {
                    'trusted_contact_database_size': len(trusted_emails),
                    'engagement_filtering_active': True,
                    'business_focus_ratio': len(business_relevant_people) / max(len(all_people), 1),
                    'content_quality_score': efficiency_ratio * 0.7 + (len(business_relevant_people) / max(len(all_people), 1)) * 0.3
                }
            }
            
            return content_summary
            
        except Exception as e:
            self.logger.error(f"Error in engagement-driven content pipeline: {str(e)}")
            # Fallback to basic content ingestion if Smart Contact Strategy fails
            return self._basic_content_fallback(user)
    
    def _basic_content_fallback(self, user) -> Dict[str, Any]:
        """Fallback content ingestion if Smart Contact Strategy fails"""
        self.logger.warning("Falling back to basic content ingestion")
        
        # Get basic communications without engagement filtering
        emails = self.db_manager.get_user_emails(user.id, limit=100)
        people = self.db_manager.get_user_people(user.id, limit=50)
        tasks = self.db_manager.get_user_tasks(user.id, limit=50)
        projects = self.db_manager.get_user_projects(user.id, limit=25)
        
        return {
            'emails': {
                'total_available': len(emails),
                'engagement_filtered': len(emails),
                'efficiency_ratio': 1.0,
                'strategic_content': [self._extract_email_essence(email) for email in emails[:30]],
                'timespan': self._get_timespan(emails),
                'filtering_strategy': 'basic_fallback'
            },
            'people': {
                'total_available': len(people),
                'business_relevant': len(people),
                'trusted_contacts': 0,
                'key_relationships': [self._extract_person_essence(person) for person in people[:15]]
            },
            'projects': {
                'total': len(projects),
                'strategic_active': [self._extract_project_essence(project) for project in projects if project.status == 'active']
            },
            'tasks': {
                'total': len(tasks),
                'strategic_pending': [self._extract_task_essence(task) for task in tasks if task.status == 'pending']
            },
            'engagement_intelligence': {
                'trusted_contact_database_size': 0,
                'engagement_filtering_active': False,
                'business_focus_ratio': 1.0,
                'content_quality_score': 0.5
            }
        }
    
    def _synthesize_business_contexts(self, user, content_summary) -> List[BusinessContext]:
        """
        Step 2: Unified Knowledge Synthesis
        Combine content into coherent business contexts rather than individual items
        """
        try:
            # Use Claude to synthesize unified business contexts
            synthesis_prompt = self._build_synthesis_prompt(content_summary)
            
            response = self.claude_client.messages.create(
                model=settings.CLAUDE_MODEL,
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
                model=settings.CLAUDE_MODEL,
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
                model=settings.CLAUDE_MODEL,
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
        Step 5: Compile Chief of Staff Intelligence Brief with Smart Contact Strategy metrics
        Create the final strategic intelligence summary highlighting engagement efficiency
        """
        # Prioritize recommendations by urgency and impact
        critical_recommendations = [r for r in recommendations if r.urgency_level == 'critical']
        high_priority_recommendations = [r for r in recommendations if r.urgency_level == 'high']
        
        # Identify key opportunities and risks
        opportunities = [ctx for ctx in business_contexts if ctx.context_type == 'opportunity']
        risks = [insight for insight in strategic_insights if insight.insight_type == 'risk']
        
        # Get Smart Contact Strategy insights for efficiency metrics
        smart_insights = self.get_smart_contact_insights(user.email)
        
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
            },
            'engagement_intelligence': {
                'smart_contact_strategy_active': smart_insights.get('strategy_active', False),
                'trusted_contacts_count': len(smart_insights.get('trusted_contacts', {}).get('trusted_contacts', [])),
                'engagement_efficiency': smart_insights.get('engagement_insights', {}).get('efficiency_metrics', {}),
                'content_quality_improvement': 'Focused on proven business relationships and engagement patterns'
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
        """Build prompt for business context synthesis using engagement-filtered content"""
        
        # Extract engagement intelligence metrics
        engagement_info = content_summary.get('engagement_intelligence', {})
        efficiency_ratio = content_summary.get('emails', {}).get('efficiency_ratio', 0)
        filtering_strategy = content_summary.get('emails', {}).get('filtering_strategy', 'unknown')
        
        prompt = f"""Analyze this ENGAGEMENT-DRIVEN business communication data and identify unified strategic business contexts:

ENGAGEMENT INTELLIGENCE SUMMARY:
- Content Filtering Strategy: {filtering_strategy}
- Email Efficiency Ratio: {efficiency_ratio:.1%} (focused on business-relevant communications)
- Trusted Contact Database: {engagement_info.get('trusted_contact_database_size', 0)} proven relationships
- Business Focus Ratio: {engagement_info.get('business_focus_ratio', 0):.1%} of contacts are business-relevant
- Content Quality Score: {engagement_info.get('content_quality_score', 0):.1%}

FILTERED BUSINESS CONTENT:
{json.dumps(content_summary, indent=2)}

STRATEGIC CONTEXT IDENTIFICATION:
Based on this engagement-driven content (focused only on communications with people you actually engage with), identify 3-7 coherent business contexts that represent ongoing strategic business situations.

Each context should:
1. Combine multiple related communications from your TRUSTED NETWORK
2. Focus on PROVEN BUSINESS RELATIONSHIPS (people you send emails to)
3. Represent genuine opportunities, challenges, projects, or strategic relationships
4. Have clear strategic business implications requiring your attention
5. Connect ENGAGEMENT PATTERNS with business value

For each context, provide:
- Name and description
- Type (opportunity/relationship/project/challenge)  
- Key people involved (from your trusted network)
- Current status and strategic priority
- Impact assessment on your business
- Timeline of developments
- Why this matters strategically

FOCUS ON: What requires your strategic attention based on your actual engagement patterns, not random emails. These should be business situations involving people you consistently communicate with and that drive real business value."""
        
        return prompt
    
    def _build_pattern_analysis_prompt(self, business_contexts) -> str:
        """Build prompt for strategic pattern analysis focused on engagement-driven insights"""
        contexts_text = "\n\n".join([
            f"Context: {ctx.name}\nType: {ctx.context_type}\nDescription: {ctx.description}\nKey People: {ctx.key_people}\nStatus: {ctx.current_status}\nPriority: {ctx.priority_score:.1%}"
            for ctx in business_contexts
        ])
        
        return f"""Analyze these ENGAGEMENT-DRIVEN business contexts for strategic patterns and insights:

STRATEGIC BUSINESS CONTEXTS (from trusted network):
{contexts_text}

PATTERN ANALYSIS FOCUS:
These contexts represent business situations involving people you actively engage with - your proven business network. Identify strategic insights by looking for:

1. CONVERGING OPPORTUNITIES: Multiple contexts pointing to the same strategic opportunity or moment
2. RELATIONSHIP MOMENTUM: How trusted relationships are creating business value or opening doors
3. TIMING PATTERNS: Windows of opportunity, urgent situations, or strategic timing based on engagement
4. NETWORK EFFECTS: How your trusted contacts connect to each other or create compound value
5. ENGAGEMENT TRENDS: Patterns in how your business relationships are evolving
6. RESOURCE FOCUS: Where your attention and resources should focus for maximum impact
7. STRATEGIC POSITIONING: How your network and engagement patterns position you for opportunities

GENERATE 3-5 STRATEGIC INSIGHTS focusing on:
- How your engagement patterns reveal strategic opportunities
- What your trusted network is telling you about market/business trends  
- Where relationship momentum creates actionable opportunities
- How to leverage your proven business relationships for maximum impact
- What patterns suggest about timing for strategic moves

Each insight should connect multiple contexts and explain the strategic implications for your business."""
    
    def _build_recommendations_prompt(self, business_contexts, strategic_insights) -> str:
        """Build prompt for engagement-driven strategic recommendations"""
        contexts_summary = "\n".join([
            f"- {ctx.name}: {ctx.description} (Priority: {ctx.priority_score:.1%}, People: {', '.join(ctx.key_people[:3])})"
            for ctx in business_contexts
        ])
        insights_summary = "\n".join([
            f"- {insight.title}: {insight.description}"
            for insight in strategic_insights
        ])
        
        return f"""Based on these ENGAGEMENT-DRIVEN business contexts and strategic insights, generate strategic recommendations:

BUSINESS CONTEXTS (from your trusted network):
{contexts_summary}

STRATEGIC INSIGHTS (from engagement patterns):
{insights_summary}

GENERATE 3-7 STRATEGIC RECOMMENDATIONS that:

1. LEVERAGE YOUR TRUSTED NETWORK: Recommendations should utilize your proven business relationships
2. ADDRESS HIGHEST ENGAGEMENT VALUE: Focus on opportunities revealed by your engagement patterns
3. CONNECT MULTIPLE CONTEXTS: Link related business situations for compound impact
4. PROVIDE SPECIFIC NEXT STEPS: Clear actions involving specific people from your network
5. EXPLAIN STRATEGIC TIMING: Why now is the right time based on relationship momentum
6. QUANTIFY BUSINESS IMPACT: Expected outcomes and business value
7. UTILIZE RELATIONSHIP CAPITAL: How to leverage your proven connections

Each recommendation should:
- Be ACTIONABLE with specific people and next steps
- Explain WHY this matters based on your engagement patterns
- Detail WHAT impact it will create for your business
- Specify WHO to contact from your trusted network
- Include TIMING based on relationship momentum and context
- Connect to multiple business contexts when relevant

FOCUS ON: Strategic actions that leverage your actual business relationships and engagement patterns for maximum business impact. These should feel like advice from someone who deeply understands your business network and strategic position."""
    
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
        """Generate executive summary highlighting engagement-driven strategic intelligence"""
        
        # Count strategic elements
        critical_recommendations = [r for r in recommendations if r.urgency_level == 'critical']
        high_priority_recommendations = [r for r in recommendations if r.urgency_level == 'high']
        opportunities = [ctx for ctx in business_contexts if ctx.context_type == 'opportunity']
        key_relationships = [ctx for ctx in business_contexts if ctx.context_type == 'relationship']
        
        # Build strategic summary
        summary_parts = []
        
        # Core intelligence summary
        summary_parts.append(f"Strategic intelligence analysis of your business network identified {len(business_contexts)} key business contexts, {len(strategic_insights)} strategic insights, and {len(recommendations)} actionable recommendations.")
        
        # Engagement efficiency highlight
        if critical_recommendations:
            summary_parts.append(f"CRITICAL: {len(critical_recommendations)} actions require immediate attention based on your trusted relationship patterns.")
        
        if opportunities:
            summary_parts.append(f"Your engagement-driven analysis reveals {len(opportunities)} strategic opportunities involving your proven business network.")
        
        if key_relationships:
            summary_parts.append(f"Relationship intelligence shows {len(key_relationships)} key relationship contexts requiring strategic attention.")
        
        # Strategic focus summary
        total_recommendations = len(critical_recommendations) + len(high_priority_recommendations)
        if total_recommendations > 0:
            summary_parts.append(f"Focus: {total_recommendations} high-impact actions leverage your trusted contacts for maximum business value.")
        else:
            summary_parts.append("Your business contexts show stable strategic positioning with opportunities for relationship-driven growth.")
        
        return " ".join(summary_parts)
    
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

    def get_smart_contact_insights(self, user_email: str) -> Dict[str, Any]:
        """Get Smart Contact Strategy insights for dashboard display"""
        try:
            from chief_of_staff_ai.engagement_analysis.smart_contact_strategy import smart_contact_strategy
            
            # Get engagement insights (this method exists)
            insights = smart_contact_strategy.get_engagement_insights(user_email)
            
            # Extract trusted contacts from insights if available
            trusted_contacts = []
            if insights.get('success') and insights.get('engagement_patterns'):
                for pattern_name, pattern_data in insights['engagement_patterns'].items():
                    if isinstance(pattern_data, dict) and pattern_data.get('emails'):
                        for email in pattern_data['emails'][:10]:  # Top 10 per pattern
                            trusted_contacts.append({
                                'email': email,
                                'pattern': pattern_name,
                                'engagement_type': 'trusted_contact'
                            })
            
            return {
                'success': True,
                'engagement_insights': insights,
                'trusted_contacts': {'trusted_contacts': trusted_contacts},
                'strategy_active': True
            }
            
        except Exception as e:
            self.logger.error(f"Error getting Smart Contact Strategy insights: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'strategy_active': False
            }


# Initialize the strategy engine instance
strategy_engine = None

def get_strategy_engine(claude_client=None, db_manager=None):
    """Get or create strategy engine instance"""
    global strategy_engine
    if strategy_engine is None and claude_client and db_manager:
        strategy_engine = StrategyEngine(claude_client, db_manager)
    return strategy_engine 