import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from anthropic import AsyncAnthropic
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class AutonomousEmailAgent:
    """Autonomous Email Agent with Extended Thinking and Response Capabilities"""
    
    def __init__(self, api_key: str = None):
        self.claude = AsyncAnthropic(api_key=api_key or settings.ANTHROPIC_API_KEY)
        self.model = settings.CLAUDE_MODEL
        self.autonomous_threshold = settings.AUTONOMOUS_CONFIDENCE_THRESHOLD
        self.supervised_threshold = settings.SUPERVISED_CONFIDENCE_THRESHOLD
        self.max_autonomous_per_day = settings.MAX_AUTONOMOUS_EMAILS_PER_DAY
        self.cache_ttl = settings.EXTENDED_CACHE_TTL
    
    async def process_incoming_email_autonomously(self, email_data: Dict, user_context: Dict) -> Dict:
        """Process incoming email with extended thinking and autonomous response"""
        
        logger.info(f"📧 Processing email autonomously: {email_data.get('subject', 'No subject')}")
        
        try:
            # Use extended prompt caching for user context (1 hour TTL)
            cached_context_prompt = f"""You are the AI Chief of Staff for {user_context['user_name']}.

**Complete Business Context:**
{json.dumps(user_context.get('business_context', {}), indent=2)}

**Communication Style:**
{json.dumps(user_context.get('communication_style', {}), indent=2)}

**Strategic Goals:**
{json.dumps(user_context.get('goals', []), indent=2)}

**Relationship Intelligence:**
{json.dumps(user_context.get('relationship_data', {}), indent=2)}

This context is cached for efficient processing of multiple emails."""

            email_analysis_prompt = f"""Analyze this incoming email and determine autonomous action using EXTENDED THINKING.

**Incoming Email:**
Subject: {email_data.get('subject', 'No subject')}
From: {email_data.get('sender', 'Unknown')}
Date: {email_data.get('date', 'Unknown')}
Body: {email_data.get('body', 'No content')[:1000]}...

**COMPREHENSIVE ANALYSIS FRAMEWORK:**

1. **Strategic Relevance Assessment**:
   - How does this email relate to user's strategic goals?
   - What business opportunities or risks does it present?
   - What is the potential impact on key relationships?

2. **Relationship Context Analysis**:
   - What's the relationship history with this sender?
   - What's their tier in the user's network (Tier 1, 2, or lower)?
   - What communication patterns exist with this person?

3. **Urgency and Timing Assessment**:
   - What's the true urgency level (not just stated)?
   - Are there time-sensitive elements requiring immediate action?
   - What are the consequences of delayed response?

4. **Response Necessity Evaluation**:
   - Does this email require a response at all?
   - What type of response would be most appropriate?
   - What are the risks of autonomous vs manual response?

5. **Autonomous Action Decision**:
   - Can this be handled autonomously with high confidence?
   - What level of risk exists with autonomous action?
   - Should this be queued for approval or manual review?

**DECISION MATRIX:**
- Confidence > 85% AND Risk = Low: Execute autonomous response
- Confidence 70-85% OR Risk = Medium: Queue for approval  
- Confidence < 70% OR Risk = High: Flag for manual review

**Use EXTENDED THINKING to:**
- Deeply analyze the email's strategic implications
- Consider multiple response strategies and their outcomes
- Evaluate short-term and long-term relationship impact
- Assess business risks and opportunities
- Determine the optimal course of action

Think through this comprehensively and provide detailed decision rationale."""

            messages = [
                {"role": "system", "content": cached_context_prompt},
                {"role": "user", "content": email_analysis_prompt}
            ]
            
            # Headers for extended thinking and caching
            headers = {
                "anthropic-beta": "extended-thinking-2025-01-01"
            }
            
            response = await self.claude.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=messages,
                headers=headers,
                thinking_mode="extended"  # Enable extended thinking
            )
            
            return await self._process_email_decision(response, email_data, user_context)
            
        except Exception as e:
            logger.error(f"Error in autonomous email processing: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'action_taken': 'error',
                'requires_manual_review': True
            }

    async def craft_autonomous_response(self, email_data: Dict, decision_analysis: Dict, user_context: Dict) -> Dict:
        """Craft autonomous email response that perfectly matches user's style"""
        
        logger.info(f"✍️ Crafting autonomous response with style matching")
        
        try:
            response_prompt = f"""Craft an autonomous email response that is indistinguishable from the user's own writing.

**Original Email to Respond To:**
{json.dumps(email_data, indent=2)}

**Decision Analysis:**
{json.dumps(decision_analysis, indent=2)}

**User's Communication Style Profile:**
{json.dumps(user_context.get('communication_style', {}), indent=2)}

**RESPONSE CRAFTING REQUIREMENTS:**

1. **Perfect Style Matching**:
   - Match the user's tone, formality level, and writing patterns
   - Use their typical greeting and closing phrases
   - Reflect their communication personality and preferences

2. **Strategic Alignment**:
   - Align response with user's strategic goals and priorities
   - Consider the relationship tier and appropriate level of engagement
   - Include value-driven content that strengthens the relationship

3. **Appropriate Relationship Management**:
   - Acknowledge the sender's communication appropriately
   - Maintain or enhance the professional relationship
   - Set appropriate expectations for next steps

4. **Clear Value Delivery**:
   - Provide helpful information or next steps
   - Demonstrate understanding of the sender's needs
   - Position the user as responsive and professional

5. **Professional Excellence**:
   - Maintain high professional standards
   - Be concise but comprehensive
   - Include appropriate call-to-action or follow-up

**Use EXTENDED THINKING to:**
- Analyze the user's communication patterns and preferences
- Consider the relationship dynamics and appropriate tone
- Craft a response that adds genuine value
- Ensure the response advances strategic objectives
- Validate that the response sounds authentically like the user

Generate a complete email response including subject line and signature."""

            messages = [{"role": "user", "content": response_prompt}]
            
            headers = {
                "anthropic-beta": "extended-thinking-2025-01-01"
            }

            response = await self.claude.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=messages,
                thinking_mode="extended",
                headers=headers
            )
            
            return self._parse_response_content(response, email_data)
            
        except Exception as e:
            logger.error(f"Error crafting autonomous response: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'subject': 'Error generating response',
                'body': 'Error occurred while generating response'
            }

    async def _process_email_decision(self, analysis_response, email_data: Dict, user_context: Dict) -> Dict:
        """Process the email analysis and execute autonomous actions"""
        
        try:
            # Parse Claude's extended thinking analysis
            decision = self._parse_decision_analysis(analysis_response)
            
            # Check if draft mode is enabled (safer approach)
            draft_mode = settings.ENABLE_EMAIL_DRAFT_MODE if hasattr(settings, 'ENABLE_EMAIL_DRAFT_MODE') else True
            
            # Check daily autonomous email limits
            daily_count = await self._get_daily_autonomous_count(user_context.get('user_id'))
            if daily_count >= self.max_autonomous_per_day:
                logger.warning(f"Daily autonomous email limit reached: {daily_count}/{self.max_autonomous_per_day}")
                return {
                    'action_taken': 'queued_for_approval',
                    'reason': 'daily_limit_reached',
                    'decision': decision
                }
            
            # ALWAYS CREATE DRAFT MODE - Modified logic
            if draft_mode or not settings.ENABLE_AUTONOMOUS_EMAIL_RESPONSES:
                # Create draft for user review regardless of confidence
                logger.info(f"📝 Creating email draft for review (confidence: {decision['confidence']:.2f})")
                
                draft_content = await self.craft_autonomous_response(
                    email_data, decision, user_context
                )
                
                # Store draft for review (instead of sending)
                draft_id = await self._create_email_draft(email_data, decision, draft_content, user_context)
                
                return {
                    'success': True,
                    'action_taken': 'draft_created_for_review',
                    'confidence': decision['confidence'],
                    'draft_id': draft_id,
                    'draft_preview': draft_content['body'][:200] + '...',
                    'strategic_impact': decision.get('strategic_impact', 'medium'),
                    'draft_quality': 'high' if decision['confidence'] > 0.8 else 'good',
                    'ready_to_send': decision['confidence'] > 0.85,
                    'review_required': True
                }
            
            # Original autonomous logic (only if autonomous mode explicitly enabled)
            elif decision['autonomous_action'] and decision['confidence'] > self.autonomous_threshold:
                # Execute autonomous response
                logger.info(f"🤖 Executing autonomous email response (confidence: {decision['confidence']:.2f})")
                
                response_content = await self.craft_autonomous_response(
                    email_data, decision, user_context
                )
                
                # Send email via MCP connector (Gmail integration)
                send_result = await self._send_email_via_mcp(
                    to=email_data['sender'],
                    subject=response_content['subject'],
                    body=response_content['body'],
                    user_context=user_context
                )
                
                # Log autonomous action
                await self._log_autonomous_action(email_data, decision, response_content, send_result)
                
                return {
                    'success': True,
                    'action_taken': 'autonomous_response_sent',
                    'confidence': decision['confidence'],
                    'response_preview': response_content['body'][:200] + '...',
                    'strategic_impact': decision.get('strategic_impact', 'medium'),
                    'send_result': send_result
                }
            
            elif decision['confidence'] > self.supervised_threshold:
                # Queue for approval
                logger.info(f"📋 Queuing email for approval (confidence: {decision['confidence']:.2f})")
                await self._queue_for_approval(email_data, decision, user_context)
                return {
                    'success': True,
                    'action_taken': 'queued_for_approval',
                    'confidence': decision['confidence'],
                    'decision': decision,
                    'estimated_response': await self._generate_draft_response(email_data, decision, user_context)
                }
            
            else:
                # Flag for manual review
                logger.info(f"🚨 Flagging email for manual review (confidence: {decision['confidence']:.2f})")
                await self._flag_for_manual_review(email_data, decision)
                return {
                    'success': True,
                    'action_taken': 'flagged_for_review',
                    'confidence': decision['confidence'],
                    'reason': decision.get('review_reason', 'Low confidence or high risk'),
                    'requires_manual_attention': True
                }
                
        except Exception as e:
            logger.error(f"Error processing email decision: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'action_taken': 'error',
                'requires_manual_review': True
            }

    async def _send_email_via_mcp(self, to: str, subject: str, body: str, user_context: Dict) -> Dict:
        """Send email using MCP connector via Gmail"""
        
        logger.info(f"📤 Sending autonomous email via MCP to {to}")
        
        try:
            # Check if MCP is enabled and configured
            if not settings.ENABLE_MCP_CONNECTOR:
                logger.warning("MCP connector not enabled, simulating email send")
                return {
                    'success': True,
                    'simulated': True,
                    'message': 'Email send simulated (MCP not configured)'
                }
            
            send_prompt = f"""Send an email using the Gmail MCP connector.

**Email Details:**
- To: {to}
- Subject: {subject}
- Body: {body}

**User Context:**
- Email Signature: {user_context.get('email_signature', '')}
- From: {user_context.get('user_email', '')}

Execute this email send operation and confirm delivery."""

            # Configure MCP servers for Gmail
            mcp_servers = []
            gmail_config = settings.MCP_SERVERS.get('gmail')
            if gmail_config and gmail_config.get('token'):
                mcp_servers.append({
                    "name": "gmail",
                    "url": gmail_config['url'],
                    "authorization_token": gmail_config['token']
                })

            if not mcp_servers:
                logger.warning("Gmail MCP server not configured, simulating send")
                return {
                    'success': True,
                    'simulated': True,
                    'message': 'Email send simulated (Gmail MCP not configured)'
                }

            response = await self.claude.messages.create(
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": send_prompt}],
                mcp_servers=mcp_servers,
                headers={
                    "anthropic-beta": "mcp-client-2025-04-04"
                }
            )
            
            return {
                'success': True,
                'mcp_response': str(response),
                'sent_to': to,
                'subject': subject
            }
            
        except Exception as e:
            logger.error(f"Error sending email via MCP: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'sent_to': to,
                'subject': subject
            }

    def _parse_decision_analysis(self, response) -> Dict:
        """Parse Claude's extended thinking analysis"""
        
        try:
            decision = {
                'confidence': 0.5,
                'autonomous_action': False,
                'strategic_impact': 'unknown',
                'risk_level': 'unknown',
                'reasoning': '',
                'recommended_action': 'manual_review'
            }
            
            if response.content:
                content_text = ''
                for content_block in response.content:
                    if hasattr(content_block, 'text'):
                        content_text += content_block.text
                
                decision['reasoning'] = content_text
                
                # Extract confidence score (simplified parsing)
                if 'confidence' in content_text.lower():
                    try:
                        # Look for confidence percentages
                        import re
                        confidence_match = re.search(r'confidence[:\s]*(\d+)%?', content_text.lower())
                        if confidence_match:
                            decision['confidence'] = int(confidence_match.group(1)) / 100.0
                    except:
                        pass
                
                # Determine autonomous action eligibility
                if 'autonomous' in content_text.lower() and 'execute' in content_text.lower():
                    decision['autonomous_action'] = True
                    decision['recommended_action'] = 'autonomous_response'
                elif 'approval' in content_text.lower() or 'queue' in content_text.lower():
                    decision['recommended_action'] = 'queue_for_approval'
                else:
                    decision['recommended_action'] = 'manual_review'
                
                # Extract strategic impact
                if 'high impact' in content_text.lower() or 'strategic' in content_text.lower():
                    decision['strategic_impact'] = 'high'
                elif 'medium impact' in content_text.lower():
                    decision['strategic_impact'] = 'medium'
                else:
                    decision['strategic_impact'] = 'low'
                    
                # Extract risk level
                if 'high risk' in content_text.lower():
                    decision['risk_level'] = 'high'
                elif 'medium risk' in content_text.lower():
                    decision['risk_level'] = 'medium'
                else:
                    decision['risk_level'] = 'low'
            
            return decision
            
        except Exception as e:
            logger.error(f"Error parsing decision analysis: {str(e)}")
            return {
                'confidence': 0.3,
                'autonomous_action': False,
                'strategic_impact': 'unknown',
                'risk_level': 'high',
                'reasoning': f'Error parsing analysis: {str(e)}',
                'recommended_action': 'manual_review'
            }

    def _parse_response_content(self, response, email_data: Dict) -> Dict:
        """Parse the autonomous response content"""
        
        try:
            response_content = {
                'success': True,
                'subject': f"Re: {email_data.get('subject', 'Your message')}",
                'body': '',
                'signature': '',
                'style_matched': True
            }
            
            if response.content:
                content_text = ''
                for content_block in response.content:
                    if hasattr(content_block, 'text'):
                        content_text += content_block.text
                
                # Extract subject line
                import re
                subject_match = re.search(r'subject[:\s]+(.*?)(?:\n|$)', content_text, re.IGNORECASE)
                if subject_match:
                    response_content['subject'] = subject_match.group(1).strip()
                
                # Extract body content (simplified - would need more sophisticated parsing)
                response_content['body'] = content_text
            
            return response_content
            
        except Exception as e:
            logger.error(f"Error parsing response content: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'subject': f"Re: {email_data.get('subject', 'Your message')}",
                'body': 'Error generating response content'
            }

    async def _get_daily_autonomous_count(self, user_id: int) -> int:
        """Get count of autonomous emails sent today"""
        # This would query the database for autonomous actions today
        # For now, return 0 (would need database integration)
        return 0

    async def _log_autonomous_action(self, email_data: Dict, decision: Dict, response_content: Dict, send_result: Dict):
        """Log autonomous action for monitoring and learning"""
        
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action_type': 'autonomous_email_response',
                'email_subject': email_data.get('subject', ''),
                'sender': email_data.get('sender', ''),
                'confidence': decision['confidence'],
                'strategic_impact': decision['strategic_impact'],
                'response_subject': response_content['subject'],
                'send_success': send_result.get('success', False),
                'simulated': send_result.get('simulated', False)
            }
            
            logger.info(f"📝 Logged autonomous action: {json.dumps(log_entry)}")
            
            # This would save to database for monitoring and improvement
            
        except Exception as e:
            logger.error(f"Error logging autonomous action: {str(e)}")

    async def _create_email_draft(self, email_data: Dict, decision: Dict, draft_content: Dict, user_context: Dict) -> str:
        """Create and store email draft for user review"""
        
        try:
            import uuid
            draft_id = str(uuid.uuid4())
            
            draft_data = {
                'draft_id': draft_id,
                'created_at': datetime.now().isoformat(),
                'original_email': {
                    'subject': email_data.get('subject', ''),
                    'sender': email_data.get('sender', ''),
                    'date': email_data.get('date', ''),
                    'body': email_data.get('body', '')[:500] + '...'  # Truncated for storage
                },
                'draft_response': {
                    'subject': draft_content['subject'],
                    'body': draft_content['body'],
                    'recipient': email_data.get('sender', '')
                },
                'ai_analysis': {
                    'confidence': decision['confidence'],
                    'strategic_impact': decision.get('strategic_impact', 'medium'),
                    'reasoning': decision.get('reasoning', '')[:300] + '...',
                    'risk_level': decision.get('risk_level', 'low')
                },
                'user_id': user_context.get('user_id'),
                'status': 'pending_review',
                'ready_to_send': decision['confidence'] > 0.85
            }
            
            # Store draft (this would integrate with your database)
            # For now, log it for demonstration
            logger.info(f"📧 Created email draft {draft_id} for review")
            logger.info(f"   To: {draft_data['draft_response']['recipient']}")
            logger.info(f"   Subject: {draft_data['draft_response']['subject']}")
            logger.info(f"   Confidence: {decision['confidence']:.1%}")
            logger.info(f"   Quality: {'High' if decision['confidence'] > 0.8 else 'Good'}")
            
            # This would save to database:
            # await save_email_draft_to_database(draft_data)
            
            return draft_id
            
        except Exception as e:
            logger.error(f"Error creating email draft: {str(e)}")
            return f"draft_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    async def _queue_for_approval(self, email_data: Dict, decision: Dict, user_context: Dict):
        """Queue email action for user approval"""
        logger.info(f"📋 Queued email for approval: {email_data.get('subject', 'No subject')}")
        # This would add to approval queue in database

    async def _flag_for_manual_review(self, email_data: Dict, decision: Dict):
        """Flag email for manual review"""
        logger.info(f"🚨 Flagged email for manual review: {email_data.get('subject', 'No subject')}")
        # This would add to manual review queue in database

    async def _generate_draft_response(self, email_data: Dict, decision: Dict, user_context: Dict) -> Dict:
        """Generate draft response for approval queue"""
        # Simplified version of craft_autonomous_response for preview
        return {
            'subject': f"Re: {email_data.get('subject', 'Your message')}",
            'body': f"Draft response for approval (confidence: {decision['confidence']:.0%})",
            'status': 'draft'
        } 