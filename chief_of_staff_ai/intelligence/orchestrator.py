"""
Strategic Intelligence Orchestrator
==================================
Coordinates all intelligence operations: contact enrichment, knowledge tree building, and predictive analysis
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

from .claude_analysts import KnowledgeTreeBuilder
from .web_scrapers import WebIntelligenceManager
from ..storage.storage_manager import storage_manager, Contact, KnowledgeNode, IntelligenceTask
from chief_of_staff_ai.ingest.gmail_fetcher import GmailFetcher

logger = logging.getLogger(__name__)

class IntelligenceOrchestrator:
    """
    Master orchestrator for all Strategic Intelligence Platform operations
    ===================================================================
    Coordinates contact enrichment, knowledge tree construction, and predictive analysis
    """
    
    def __init__(self):
        self.knowledge_builder = KnowledgeTreeBuilder()
        self.web_intelligence = WebIntelligenceManager()
        self.initialized = False
    
    async def initialize(self):
        """Initialize all intelligence components"""
        if self.initialized:
            return
            
        try:
            logger.info("🚀 Initializing Strategic Intelligence Orchestrator...")
            
            # Initialize storage layer
            await storage_manager.initialize()
            
            # Initialize web intelligence manager
            await self.web_intelligence.initialize()
            
            self.initialized = True
            logger.info("✅ Strategic Intelligence Orchestrator ready")
            
        except Exception as e:
            logger.error(f"❌ Orchestrator initialization failed: {str(e)}")
            raise
    
    # ==================== PHASE 1: CONTACT ENRICHMENT ====================
    
    async def enrich_contacts(self, user_id: int, task_id: str) -> Dict:
        """
        Phase 1: Extract contacts from sent emails and enrich with web intelligence
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            logger.info(f"🔍 Phase 1: Starting contact enrichment for user {user_id}")
            
            # Update task status
            await storage_manager.update_task_progress(task_id, 5, 'running')
            
            # Step 1: Extract contacts from sent emails
            contacts = await self._extract_sent_contacts(user_id)
            await storage_manager.update_task_progress(task_id, 20, 'running')
            
            if not contacts:
                await storage_manager.update_task_progress(task_id, 100, 'completed')
                return {
                    'status': 'completed',
                    'message': 'No contacts found in sent emails',
                    'contacts_found': 0,
                    'contacts_enriched': 0
                }
            
            logger.info(f"📧 Found {len(contacts)} contacts from sent emails")
            
            # Step 2: Filter contacts that need enrichment
            contacts_for_enrichment = await self._filter_contacts_for_enrichment(contacts)
            await storage_manager.update_task_progress(task_id, 30, 'running')
            
            logger.info(f"🎯 {len(contacts_for_enrichment)} contacts need enrichment")
            
            # Step 3: Batch web intelligence enrichment
            enriched_contacts = await self._run_web_enrichment_batch(contacts_for_enrichment, task_id)
            await storage_manager.update_task_progress(task_id, 80, 'running')
            
            # Step 4: Save enriched contacts to database
            saved_count = await self._save_enriched_contacts(user_id, enriched_contacts)
            await storage_manager.update_task_progress(task_id, 100, 'completed')
            
            result = {
                'status': 'completed',
                'contacts_found': len(contacts),
                'contacts_enriched': saved_count,
                'enrichment_timestamp': datetime.utcnow().isoformat(),
                'task_id': task_id
            }
            
            logger.info(f"✅ Phase 1 completed: {saved_count} contacts enriched")
            return result
            
        except Exception as e:
            logger.error(f"❌ Contact enrichment failed: {str(e)}")
            await storage_manager.update_task_progress(task_id, 0, 'failed')
            return {
                'status': 'error',
                'error': str(e),
                'task_id': task_id
            }
    
    async def _extract_sent_contacts(self, user_id: int) -> List[Dict]:
        """Extract unique contacts from sent emails"""
        try:
            # Get user email from user_id
            user = await storage_manager.get_user_by_id(user_id)
            if not user:
                logger.error(f"User with ID {user_id} not found")
                return []
            
            user_email = user.get('email') if isinstance(user, dict) else getattr(user, 'email', None)
            if not user_email:
                logger.error(f"No email found for user ID {user_id}")
                return []
            
            gmail_fetcher = GmailFetcher()
            
            # Get sent emails from last 90 days
            sent_emails_result = gmail_fetcher.fetch_sent_emails(
                user_email=user_email,
                days_back=90,
                max_emails=500
            )
            
            if not sent_emails_result.get('success'):
                logger.warning(f"Failed to fetch sent emails: {sent_emails_result.get('error', 'Unknown error')}")
                return []
            
            sent_emails = sent_emails_result.get('emails', [])
            if not sent_emails:
                logger.warning("No sent emails found")
                return []
            
            # Extract unique recipients from sent emails
            contacts_map = {}
            
            for email in sent_emails:
                # Get recipients from the email data
                recipients = email.get('recipient_emails', [])
                if not recipients:
                    # Fallback to other recipient fields
                    recipients = email.get('recipients', [])
                    if isinstance(recipients, str):
                        recipients = [recipients]
                
                for recipient in recipients:
                    email_addr = recipient.strip().lower()
                    if '@' in email_addr and email_addr not in contacts_map:
                        # Extract name from email if available
                        name = self._extract_name_from_email(email_addr, email)
                        
                        contacts_map[email_addr] = {
                            'email': email_addr,
                            'name': name,
                            'company': self._extract_company_from_email(email_addr),
                            'last_contact': email.get('email_date'),
                            'interaction_count': 1
                        }
                    elif email_addr in contacts_map:
                        # Increment interaction count
                        contacts_map[email_addr]['interaction_count'] += 1
                        # Update last contact if this email is more recent
                        if email.get('email_date') and email['email_date'] > contacts_map[email_addr].get('last_contact', datetime.min):
                            contacts_map[email_addr]['last_contact'] = email['email_date']
            
            # Convert to list and sort by interaction frequency
            contacts = list(contacts_map.values())
            contacts.sort(key=lambda x: x.get('interaction_count', 0), reverse=True)
            
            logger.info(f"📧 Extracted {len(contacts)} unique contacts from {len(sent_emails)} sent emails")
            return contacts
            
        except Exception as e:
            logger.error(f"Contact extraction failed: {str(e)}")
            return []
    
    def _extract_name_from_email(self, email_addr: str, email_data: Dict) -> str:
        """Extract contact name from email address or email data"""
        # Try to get name from email headers
        if 'sender_name' in email_data:
            return email_data['sender_name']
        
        # Extract from email address (before @)
        local_part = email_addr.split('@')[0]
        
        # Convert common patterns to names
        if '.' in local_part:
            parts = local_part.split('.')
            return ' '.join(part.capitalize() for part in parts)
        elif '_' in local_part:
            parts = local_part.split('_')
            return ' '.join(part.capitalize() for part in parts)
        else:
            return local_part.capitalize()
    
    def _extract_company_from_email(self, email_addr: str) -> str:
        """Extract company name from email domain"""
        try:
            domain = email_addr.split('@')[1]
            
            # Remove common email providers
            if domain in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com']:
                return ''
            
            # Extract company name from domain
            company_part = domain.split('.')[0]
            return company_part.capitalize()
            
        except:
            return ''
    
    async def _filter_contacts_for_enrichment(self, contacts: List[Dict]) -> List[Dict]:
        """Filter contacts that need web intelligence enrichment"""
        try:
            contacts_needing_enrichment = []
            
            for contact in contacts:
                # Check if contact already exists in database
                existing_contacts = await storage_manager.get_contacts_for_enrichment(
                    user_id=1,  # This would be passed from calling function
                    limit=1000
                )
                
                # Check if this email already exists and is enriched
                is_already_enriched = any(
                    c.email == contact['email'] and c.enrichment_status == 'enriched'
                    for c in existing_contacts
                )
                
                if not is_already_enriched:
                    contacts_needing_enrichment.append(contact)
            
            # Limit batch size to avoid overwhelming services
            return contacts_needing_enrichment[:50]
            
        except Exception as e:
            logger.error(f"Contact filtering failed: {str(e)}")
            return contacts
    
    async def _run_web_enrichment_batch(self, contacts: List[Dict], task_id: str) -> List:
        """Run web intelligence enrichment in batches"""
        try:
            enriched_contacts = []
            batch_size = 10  # Process in smaller batches
            
            for i in range(0, len(contacts), batch_size):
                batch = contacts[i:i + batch_size]
                
                logger.info(f"🔬 Processing enrichment batch {i//batch_size + 1}/{(len(contacts) + batch_size - 1)//batch_size}")
                
                # Run batch enrichment
                batch_results = await self.web_intelligence.enrich_contact_batch(batch)
                enriched_contacts.extend(batch_results)
                
                # Update progress
                progress = 30 + int((i + len(batch)) / len(contacts) * 50)
                await storage_manager.update_task_progress(task_id, progress, 'running')
                
                # Rate limiting - pause between batches
                if i + batch_size < len(contacts):
                    await asyncio.sleep(2)
            
            return enriched_contacts
            
        except Exception as e:
            logger.error(f"Batch enrichment failed: {str(e)}")
            return []
    
    async def _save_enriched_contacts(self, user_id: int, enriched_contacts: List) -> int:
        """Save enriched contacts to database"""
        try:
            saved_count = 0
            
            for enriched_contact in enriched_contacts:
                try:
                    # Convert to Contact dataclass
                    contact = Contact(
                        user_id=user_id,
                        email=enriched_contact.email,
                        name=enriched_contact.name,
                        company=enriched_contact.company,
                        linkedin_url=self._extract_linkedin_url(enriched_contact.linkedin_data),
                        twitter_handle=self._extract_twitter_handle(enriched_contact.twitter_data),
                        enrichment_status='enriched' if enriched_contact.enrichment_status == 'completed' else 'failed',
                        engagement_score=enriched_contact.confidence_score,
                        last_interaction=datetime.utcnow(),
                        intelligence_data={
                            'linkedin': enriched_contact.linkedin_data,
                            'twitter': enriched_contact.twitter_data,
                            'company': enriched_contact.company_data,
                            'enrichment_timestamp': enriched_contact.enrichment_timestamp.isoformat() if enriched_contact.enrichment_timestamp else None
                        }
                    )
                    
                    await storage_manager.save_contact(contact)
                    saved_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to save contact {enriched_contact.email}: {str(e)}")
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Contact saving failed: {str(e)}")
            return 0
    
    def _extract_linkedin_url(self, linkedin_data: Dict) -> Optional[str]:
        """Extract LinkedIn URL from enrichment data"""
        if linkedin_data and linkedin_data.get('status') == 'success':
            profile = linkedin_data.get('profile', {})
            return profile.get('profile_url')
        return None
    
    def _extract_twitter_handle(self, twitter_data: Dict) -> Optional[str]:
        """Extract Twitter handle from enrichment data"""
        if twitter_data and twitter_data.get('status') == 'success':
            profile = twitter_data.get('profile', {})
            return profile.get('handle')
        return None
    
    # ==================== PHASE 2: KNOWLEDGE TREE CONSTRUCTION ====================
    
    async def build_knowledge_tree(self, user_id: int, task_id: str, time_window_days: int = 30) -> Dict:
        """
        Phase 2: Build comprehensive knowledge tree using Claude analysts
        """
        if not self.initialized:
            await self.initialize()
        
        try:
            logger.info(f"🧠 Phase 2: Starting knowledge tree construction for user {user_id}")
            
            # Update task status
            await storage_manager.update_task_progress(task_id, 5, 'running')
            
            # Step 1: Get emails from trusted contacts within time window
            emails = await self._get_trusted_contact_emails(user_id, time_window_days)
            await storage_manager.update_task_progress(task_id, 15, 'running')
            
            if not emails:
                await storage_manager.update_task_progress(task_id, 100, 'completed')
                return {
                    'status': 'completed',
                    'message': 'No emails found from trusted contacts',
                    'knowledge_nodes': 0,
                    'time_window_days': time_window_days
                }
            
            logger.info(f"📧 Found {len(emails)} emails from trusted contacts in {time_window_days} day window")
            
            # Step 2: Run Claude analysts in parallel
            knowledge_tree = await self.knowledge_builder.build_knowledge_tree(
                user_id, emails, time_window_days
            )
            await storage_manager.update_task_progress(task_id, 70, 'running')
            
            if knowledge_tree.get('status') == 'error':
                await storage_manager.update_task_progress(task_id, 0, 'failed')
                return knowledge_tree
            
            # Step 3: Save knowledge nodes to database
            saved_nodes = await self._save_knowledge_tree(user_id, knowledge_tree)
            await storage_manager.update_task_progress(task_id, 90, 'running')
            
            # Step 4: Generate summary insights
            summary = self._generate_knowledge_summary(knowledge_tree)
            await storage_manager.update_task_progress(task_id, 100, 'completed')
            
            result = {
                'status': 'completed',
                'knowledge_tree': knowledge_tree,
                'summary': summary,
                'knowledge_nodes_saved': saved_nodes,
                'emails_analyzed': len(emails),
                'time_window_days': time_window_days,
                'task_id': task_id
            }
            
            logger.info(f"✅ Phase 2 completed: {saved_nodes} knowledge nodes created")
            return result
            
        except Exception as e:
            logger.error(f"❌ Knowledge tree construction failed: {str(e)}")
            await storage_manager.update_task_progress(task_id, 0, 'failed')
            return {
                'status': 'error',
                'error': str(e),
                'task_id': task_id
            }
    
    async def _get_trusted_contact_emails(self, user_id: int, time_window_days: int) -> List[Dict]:
        """Get emails from trusted contacts within time window"""
        try:
            # Get enriched contacts (our trusted contacts)
            trusted_contacts = await storage_manager.get_contacts_for_enrichment(user_id, limit=500)
            
            # Filter to only enriched contacts
            enriched_contacts = [c for c in trusted_contacts if c.enrichment_status == 'enriched']
            
            if not enriched_contacts:
                logger.warning("No enriched contacts found - cannot build knowledge tree")
                return []
            
            trusted_emails = {c.email for c in enriched_contacts}
            logger.info(f"🎯 Found {len(trusted_emails)} trusted contacts for knowledge tree")
            
            # Get user email from user_id
            user = await storage_manager.get_user_by_id(user_id)
            if not user:
                logger.error(f"User with ID {user_id} not found")
                return []
            
            user_email = user.get('email') if isinstance(user, dict) else getattr(user, 'email', None)
            if not user_email:
                logger.error(f"No email found for user ID {user_id}")
                return []
            
            # Get emails within time window using GmailFetcher
            gmail_fetcher = GmailFetcher()
            cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
            
            # Fetch received emails from trusted contacts
            all_emails_result = gmail_fetcher.fetch_recent_emails(
                user_email=user_email,
                days_back=time_window_days,
                limit=1000
            )
            
            if not all_emails_result.get('success'):
                logger.warning(f"Failed to fetch emails: {all_emails_result.get('error', 'Unknown error')}")
                return []
            
            all_emails = all_emails_result.get('emails', [])
            if not all_emails:
                logger.warning("No emails found in the specified time window")
                return []
            
            # Filter emails from trusted contacts only
            filtered_emails = []
            for email in all_emails:
                sender = email.get('sender', '')
                if sender in trusted_emails:
                    filtered_emails.append(email)
            
            logger.info(f"📧 Found {len(filtered_emails)} emails from trusted contacts in {time_window_days} day window")
            return filtered_emails
            
        except Exception as e:
            logger.error(f"Failed to get trusted contact emails: {str(e)}")
            return []
    
    async def _save_knowledge_tree(self, user_id: int, knowledge_tree: Dict) -> int:
        """Save knowledge tree nodes to database"""
        try:
            saved_count = 0
            
            # Save insights as knowledge nodes
            for analyst_type, insights in knowledge_tree.get('insights', {}).items():
                for category, items in insights.items():
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                try:
                                    node = KnowledgeNode(
                                        user_id=user_id,
                                        node_type=f"{analyst_type}_{category}",
                                        title=item.get('decision') or item.get('prediction') or item.get('trend') or category,
                                        content=item,
                                        confidence=item.get('confidence', 0.0),
                                        analyst_source=analyst_type,
                                        evidence=[item.get('evidence', '')],
                                        relationships=[],
                                        created_at=datetime.utcnow()
                                    )
                                    
                                    await storage_manager.save_knowledge_node(node)
                                    saved_count += 1
                                    
                                except Exception as e:
                                    logger.warning(f"Failed to save knowledge node: {str(e)}")
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Knowledge tree saving failed: {str(e)}")
            return 0
    
    def _generate_knowledge_summary(self, knowledge_tree: Dict) -> Dict:
        """Generate executive summary of knowledge tree"""
        try:
            insights = knowledge_tree.get('insights', {})
            metadata = knowledge_tree.get('metadata', {})
            
            summary = {
                'total_insights': sum(
                    len(items) if isinstance(items, list) else 1
                    for analyst_insights in insights.values()
                    for items in analyst_insights.values()
                ),
                'confidence_scores': knowledge_tree.get('confidence_scores', {}),
                'overall_confidence': knowledge_tree.get('overall_confidence', 0.0),
                'key_topics': knowledge_tree.get('topics', [])[:10],  # Top 10 topics
                'top_entities': knowledge_tree.get('entities', [])[:5],  # Top 5 entities
                'predictions_count': len(knowledge_tree.get('predictions', [])),
                'analysis_timestamp': metadata.get('analysis_timestamp'),
                'emails_analyzed': metadata.get('email_count', 0),
                'processing_time': metadata.get('total_processing_time', 0.0)
            }
            
            # Extract key strategic insights
            strategic_highlights = []
            business_insights = insights.get('business_strategy', {})
            
            for category, items in business_insights.items():
                if isinstance(items, list) and items:
                    for item in items[:2]:  # Top 2 from each category
                        if isinstance(item, dict):
                            strategic_highlights.append({
                                'category': category,
                                'insight': item.get('decision') or item.get('description', ''),
                                'confidence': item.get('confidence', 0.0)
                            })
            
            summary['strategic_highlights'] = strategic_highlights
            
            return summary
            
        except Exception as e:
            logger.error(f"Summary generation failed: {str(e)}")
            return {}
    
    # ==================== TASK MANAGEMENT ====================
    
    async def create_intelligence_task(self, user_id: int, task_type: str) -> str:
        """Create new intelligence task and return task ID"""
        try:
            task = await storage_manager.create_intelligence_task(user_id, task_type)
            return task.task_id
        except Exception as e:
            logger.error(f"Task creation failed: {str(e)}")
            raise
    
    async def get_task_status(self, task_id: str) -> Dict:
        """Get current status of intelligence task"""
        try:
            return await storage_manager.get_task_status(task_id)
        except Exception as e:
            logger.error(f"Task status retrieval failed: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    # ==================== COMBINED WORKFLOWS ====================
    
    async def run_full_intelligence_pipeline(self, user_id: int) -> Dict:
        """
        Run complete intelligence pipeline: contact enrichment + knowledge tree building
        """
        try:
            logger.info(f"🚀 Starting full intelligence pipeline for user {user_id}")
            
            # Phase 1: Contact enrichment
            enrichment_task_id = await self.create_intelligence_task(user_id, 'contact_enrichment')
            enrichment_result = await self.enrich_contacts(user_id, enrichment_task_id)
            
            if enrichment_result.get('status') != 'completed':
                return {
                    'status': 'error',
                    'phase': 'contact_enrichment',
                    'error': enrichment_result.get('error', 'Contact enrichment failed')
                }
            
            # Phase 2: Knowledge tree construction
            knowledge_task_id = await self.create_intelligence_task(user_id, 'knowledge_tree_building')
            knowledge_result = await self.build_knowledge_tree(user_id, knowledge_task_id)
            
            if knowledge_result.get('status') != 'completed':
                return {
                    'status': 'error',
                    'phase': 'knowledge_tree_building',
                    'error': knowledge_result.get('error', 'Knowledge tree building failed')
                }
            
            # Combined results
            pipeline_result = {
                'status': 'completed',
                'phases': {
                    'contact_enrichment': enrichment_result,
                    'knowledge_tree_building': knowledge_result
                },
                'summary': {
                    'contacts_enriched': enrichment_result.get('contacts_enriched', 0),
                    'knowledge_nodes_created': knowledge_result.get('knowledge_nodes_saved', 0),
                    'overall_confidence': knowledge_result.get('knowledge_tree', {}).get('overall_confidence', 0.0),
                    'pipeline_timestamp': datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"✅ Full intelligence pipeline completed for user {user_id}")
            return pipeline_result
            
        except Exception as e:
            logger.error(f"❌ Full intelligence pipeline failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'pipeline_timestamp': datetime.utcnow().isoformat()
            }
    
    # ==================== CLEANUP ====================
    
    async def cleanup(self):
        """Clean up orchestrator resources"""
        try:
            if hasattr(self, 'web_intelligence'):
                await self.web_intelligence.cleanup()
            
            if hasattr(storage_manager, 'close'):
                await storage_manager.close()
                
            logger.info("✅ Intelligence Orchestrator cleanup completed")
            
        except Exception as e:
            logger.warning(f"Cleanup warning: {str(e)}")

# Global orchestrator instance
intelligence_orchestrator = IntelligenceOrchestrator() 