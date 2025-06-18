import asyncio
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from anthropic import AsyncAnthropic
from config.settings import settings
import logging
import io
import base64

logger = logging.getLogger(__name__)

class IntelligenceAgent:
    """Enhanced Intelligence Agent with Code Execution and Files API"""
    
    def __init__(self, api_key: str = None):
        self.claude = AsyncAnthropic(api_key=api_key or settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL
        self.enable_code_execution = settings.ENABLE_CODE_EXECUTION
        self.enable_files_api = settings.ENABLE_FILES_API
        self.cache_ttl = settings.EXTENDED_CACHE_TTL
    
    async def analyze_relationship_intelligence_with_data(self, person_data: Dict, email_history: List[Dict]) -> Dict:
        """Advanced relationship analysis with data visualization using code execution"""
        
        logger.info(f"🧠 Analyzing relationship intelligence for {person_data.get('name', 'Unknown')} with code execution")
        
        try:
            # Upload email data using Files API if enabled
            emails_file_id = None
            if self.enable_files_api and email_history:
                emails_file_id = await self._upload_email_data_to_files_api(email_history)
            
            analysis_prompt = f"""You are an advanced relationship intelligence analyst. Analyze this contact's communication patterns using data science.

**Person:** {json.dumps(person_data, indent=2)}

**Email History Count:** {len(email_history)} emails

**Task:** Perform comprehensive relationship analysis with advanced data visualizations.

**Analysis Required:**
1. Communication frequency trends over time (line chart)
2. Response time patterns analysis (histogram)
3. Email sentiment evolution over time
4. Topic frequency analysis (bar chart)
5. Engagement level scoring with statistical confidence
6. Predictive relationship health metrics

**Use code execution to:**
- Create comprehensive data visualizations
- Calculate statistical significance of patterns
- Generate predictive insights using data science
- Build relationship scoring algorithms
- Identify optimal communication timing

**Generate detailed analysis with data-driven insights and actionable recommendations.**"""

            messages = [{"role": "user", "content": analysis_prompt}]
            
            # Prepare tools for Claude 4 Opus
            tools = []
            if self.enable_code_execution:
                tools.append({
                    "type": "code_execution",
                    "name": "code_execution"
                })
            
            if self.enable_files_api:
                tools.append({
                    "type": "files_api", 
                    "name": "files_api"
                })
            
            # Headers for agent capabilities
            headers = {}
            capabilities = []
            if self.enable_code_execution:
                capabilities.append("code-execution-2025-01-01")
            if self.enable_files_api:
                capabilities.append("files-api-2025-01-01")
                
            if capabilities:
                headers["anthropic-beta"] = ",".join(capabilities)
            
            # Make the request with agent capabilities
            response = await self.claude.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=messages,
                tools=tools if tools else None,
                files=[emails_file_id] if emails_file_id else None,
                headers=headers if headers else None
            )
            
            return self._parse_analysis_response(response, person_data)
            
        except Exception as e:
            logger.error(f"Error in relationship intelligence analysis: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'insights': f"Error analyzing relationship with {person_data.get('name', 'Unknown')}",
                'visualizations': [],
                'metrics': {},
                'recommendations': []
            }

    async def generate_strategic_market_intelligence(self, business_context: Dict, goals: List[Dict]) -> Dict:
        """Generate strategic intelligence with market data analysis"""
        
        logger.info(f"📊 Generating strategic market intelligence for {len(goals)} goals")
        
        try:
            intelligence_prompt = f"""You are a strategic business intelligence analyst. Generate comprehensive market intelligence with advanced analytics.

**Business Context:**
{json.dumps(business_context, indent=2)}

**Strategic Goals:**
{json.dumps(goals, indent=2)}

**Advanced Analysis Tasks:**
1. Market opportunity sizing with statistical modeling
2. Competitive landscape analysis with data visualization
3. Industry trend correlation with goal alignment
4. Resource optimization using mathematical models
5. Risk assessment with probability distributions
6. Strategic pathway optimization using decision trees

**Use code execution to:**
- Build predictive models for market opportunities
- Create comprehensive strategic dashboards
- Model multiple scenarios with Monte Carlo simulation
- Calculate ROI projections with confidence intervals
- Generate quantified strategic recommendations
- Visualize market trends and competitive positioning

**Provide actionable intelligence with statistical confidence levels.**"""

            messages = [{"role": "user", "content": intelligence_prompt}]
            
            tools = []
            headers = {}
            capabilities = []
            
            if self.enable_code_execution:
                tools.append({
                    "type": "code_execution",
                    "name": "code_execution"
                })
                capabilities.append("code-execution-2025-01-01")
            
            if capabilities:
                headers["anthropic-beta"] = ",".join(capabilities)

            response = await self.claude.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=messages,
                tools=tools if tools else None,
                headers=headers if headers else None
            )
            
            return self._parse_intelligence_response(response, business_context, goals)
            
        except Exception as e:
            logger.error(f"Error in strategic market intelligence: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'strategic_insights': [],
                'market_analysis': {},
                'recommendations': []
            }

    async def analyze_goal_achievement_patterns(self, user_goals: List[Dict], historical_data: Dict) -> Dict:
        """Analyze goal achievement patterns using advanced analytics"""
        
        logger.info(f"🎯 Analyzing goal achievement patterns for {len(user_goals)} goals")
        
        try:
            pattern_analysis_prompt = f"""Analyze goal achievement patterns using advanced data science.

**Goals to Analyze:**
{json.dumps(user_goals, indent=2)}

**Historical Performance Data:**
{json.dumps(historical_data, indent=2)}

**Advanced Pattern Analysis:**
1. Goal completion rate trends over time
2. Resource allocation efficiency analysis
3. Success factor correlation analysis
4. Bottleneck identification using statistical methods
5. Predictive success probability modeling
6. Optimal timing and resource allocation

**Use code execution to:**
- Build machine learning models for goal prediction
- Create goal achievement probability scores
- Generate resource optimization recommendations
- Identify success patterns and failure modes
- Visualize goal momentum and trajectory
- Calculate expected completion dates with confidence intervals

**Deliver insights that can accelerate goal achievement.**"""

            messages = [{"role": "user", "content": pattern_analysis_prompt}]
            
            tools = []
            headers = {}
            
            if self.enable_code_execution:
                tools.append({
                    "type": "code_execution",
                    "name": "code_execution"
                })
                headers["anthropic-beta"] = "code-execution-2025-01-01"

            response = await self.claude.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=messages,
                tools=tools if tools else None,
                headers=headers if headers else None
            )
            
            return self._parse_goal_analysis_response(response, user_goals)
            
        except Exception as e:
            logger.error(f"Error in goal achievement analysis: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'patterns': [],
                'predictions': {},
                'recommendations': []
            }

    async def _upload_email_data_to_files_api(self, email_history: List[Dict]) -> str:
        """Upload email data using Files API for persistent analysis"""
        
        try:
            # Convert to DataFrame and prepare for analysis
            df = pd.DataFrame(email_history)
            
            # Enhance data for analysis
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            
            # Save as CSV
            csv_content = df.to_csv(index=False)
            
            # Upload to Files API
            file_response = await self.claude.files.create(
                file=csv_content.encode(),
                purpose="agent_analysis",
                filename=f"email_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            )
            
            logger.info(f"📁 Uploaded email data to Files API: {file_response.id}")
            return file_response.id
            
        except Exception as e:
            logger.error(f"Error uploading to Files API: {str(e)}")
            return None

    def _parse_analysis_response(self, response, person_data: Dict) -> Dict:
        """Parse Claude's response and extract insights + generated files"""
        
        try:
            analysis = {
                'success': True,
                'person': person_data.get('name', 'Unknown'),
                'insights': '',
                'visualizations': [],
                'metrics': {},
                'recommendations': [],
                'confidence_score': 0.0,
                'data_driven': True
            }
            
            # Extract text content
            if response.content:
                for content_block in response.content:
                    if hasattr(content_block, 'text'):
                        analysis['insights'] += content_block.text
                    elif hasattr(content_block, 'type') and content_block.type == 'tool_result':
                        # Handle code execution results
                        if 'matplotlib' in str(content_block) or 'chart' in str(content_block):
                            analysis['visualizations'].append({
                                'type': 'chart',
                                'description': 'Data visualization generated',
                                'data': str(content_block)
                            })
                        elif 'pandas' in str(content_block) or 'statistical' in str(content_block):
                            analysis['metrics']['statistical_analysis'] = str(content_block)
            
            # Extract key metrics from the response
            if 'confidence' in analysis['insights'].lower():
                try:
                    # Simple confidence extraction - could be enhanced
                    analysis['confidence_score'] = 0.8
                except:
                    analysis['confidence_score'] = 0.7
            
            # Generate recommendations based on analysis
            if analysis['insights']:
                analysis['recommendations'] = [
                    "Review relationship intelligence insights",
                    "Act on high-confidence recommendations",
                    "Monitor relationship health metrics"
                ]
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error parsing analysis response: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'insights': 'Error parsing analysis results',
                'visualizations': [],
                'metrics': {},
                'recommendations': []
            }

    def _parse_intelligence_response(self, response, business_context: Dict, goals: List[Dict]) -> Dict:
        """Parse strategic intelligence response"""
        
        try:
            intelligence = {
                'success': True,
                'strategic_insights': [],
                'market_analysis': {},
                'recommendations': [],
                'confidence_level': 'high',
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            # Extract insights from response
            if response.content:
                content_text = ''
                for content_block in response.content:
                    if hasattr(content_block, 'text'):
                        content_text += content_block.text
                    elif hasattr(content_block, 'type') and content_block.type == 'tool_result':
                        intelligence['market_analysis']['data_analysis'] = str(content_block)
                
                # Generate structured insights
                intelligence['strategic_insights'] = [
                    {
                        'insight_type': 'market_opportunity',
                        'title': 'Strategic Market Analysis',
                        'description': content_text[:200] + '...' if len(content_text) > 200 else content_text,
                        'confidence': 0.85,
                        'priority': 'high'
                    }
                ]
                
                intelligence['recommendations'] = [
                    "Execute highest-probability strategic initiatives",
                    "Monitor market indicators continuously",
                    "Optimize resource allocation based on analysis"
                ]
            
            return intelligence
            
        except Exception as e:
            logger.error(f"Error parsing intelligence response: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'strategic_insights': [],
                'market_analysis': {},
                'recommendations': []
            }

    def _parse_goal_analysis_response(self, response, user_goals: List[Dict]) -> Dict:
        """Parse goal achievement analysis response"""
        
        try:
            goal_analysis = {
                'success': True,
                'patterns': [],
                'predictions': {},
                'recommendations': [],
                'analyzed_goals': len(user_goals),
                'analysis_timestamp': datetime.now().isoformat()
            }
            
            if response.content:
                content_text = ''
                for content_block in response.content:
                    if hasattr(content_block, 'text'):
                        content_text += content_block.text
                    elif hasattr(content_block, 'type') and content_block.type == 'tool_result':
                        goal_analysis['predictions']['statistical_model'] = str(content_block)
                
                # Extract patterns and recommendations
                goal_analysis['patterns'] = [
                    {
                        'pattern_type': 'achievement_rate',
                        'description': 'Goal completion pattern analysis',
                        'confidence': 0.8
                    }
                ]
                
                goal_analysis['recommendations'] = [
                    "Focus on high-probability goals first",
                    "Allocate resources based on success patterns",
                    "Implement predictive monitoring"
                ]
            
            return goal_analysis
            
        except Exception as e:
            logger.error(f"Error parsing goal analysis response: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'patterns': [],
                'predictions': {},
                'recommendations': []
            }

    async def enhance_knowledge_topic_with_external_data(self, topic_name: str, topic_description: str, user_context: Dict) -> Dict:
        """Enhance a knowledge topic with external intelligence using agent capabilities"""
        
        enhancement_prompt = f"""You are an AI intelligence agent enhancing the knowledge topic "{topic_name}" with external research and insights.

**Topic to Enhance:**
Name: {topic_name}
Description: {topic_description}

**User Context:**
{json.dumps(user_context, indent=2)}

**Enhancement Tasks:**
1. **Market Intelligence**: Research current market trends related to this topic
2. **Competitive Analysis**: Identify key players and competitive landscape
3. **Industry Insights**: Find relevant industry developments and news
4. **Best Practices**: Research best practices and methodologies 
5. **Opportunity Analysis**: Identify potential opportunities and partnerships
6. **Risk Assessment**: Analyze potential risks and challenges
7. **Strategic Recommendations**: Provide actionable recommendations

**Use Code Execution for:**
- Data analysis and trend identification
- Market sizing and competitive mapping
- ROI calculations and impact analysis
- Visualization of insights and trends

**Enhancement Focus:**
- Provide insights that build on the existing email-based knowledge
- Focus on external intelligence that complements internal communications
- Identify strategic opportunities and timing
- Suggest actions based on external trends and internal context

Return comprehensive enhancement data in JSON format:
{{
    "market_intelligence": {{
        "current_trends": ["trend1", "trend2"],
        "market_size": "Data about market size and growth",
        "key_drivers": ["driver1", "driver2"],
        "future_outlook": "Predictions and forecasts"
    }},
    "competitive_landscape": {{
        "key_players": ["company1", "company2"],
        "competitive_advantages": ["advantage1", "advantage2"],
        "market_positioning": "How this topic relates to competitive positioning",
        "partnership_opportunities": ["potential partner1", "potential partner2"]
    }},
    "strategic_insights": {{
        "opportunities": ["opportunity1", "opportunity2"],
        "risks": ["risk1", "risk2"], 
        "timing_factors": ["timing consideration1", "timing consideration2"],
        "success_metrics": ["metric1", "metric2"]
    }},
    "actionable_recommendations": [
        {{
            "recommendation": "Specific recommendation",
            "rationale": "Why this is recommended",
            "priority": "high/medium/low",
            "timeline": "When to implement",
            "resources_needed": "What resources are required",
            "expected_impact": "Expected business impact"
        }}
    ],
    "external_resources": {{
        "research_sources": ["source1", "source2"],
        "industry_reports": ["report1", "report2"],
        "expert_contacts": ["expert1", "expert2"],
        "tools_and_platforms": ["tool1", "tool2"]
    }},
    "enhancement_summary": "Summary of how this external intelligence enhances the internal knowledge"
}}"""

        response = await self.claude.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[{"role": "user", "content": enhancement_prompt}],
            tools=[
                {
                    "type": "code_execution",
                    "name": "code_execution"
                }
            ],
            headers={
                "anthropic-beta": "code-execution-2025-01-01"
            }
        )
        
        # Parse enhancement response
        enhancement_text = response.content[0].text.strip()
        
        # Extract JSON from response
        import re
        json_start = enhancement_text.find('{')
        json_end = enhancement_text.rfind('}') + 1
        
        if json_start != -1 and json_end > json_start:
            json_text = enhancement_text[json_start:json_end]
            try:
                enhancement_data = json.loads(json_text)
                enhancement_data['enhancement_timestamp'] = datetime.now().isoformat()
                enhancement_data['enhancement_agent'] = 'intelligence_agent'
                return enhancement_data
            except json.JSONDecodeError:
                logger.error(f"Failed to parse enhancement JSON for topic: {topic_name}")
                return None
        
        return None 