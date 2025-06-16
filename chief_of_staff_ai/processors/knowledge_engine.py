"""
Knowledge Engine - Core Processing for Knowledge Replacement System
==================================================================

This is the brain of the Knowledge-Centric Architecture. It handles:

1. Hierarchical Topic Tree Building (auto-generated + user-managed)
2. Multi-Source Knowledge Ingestion (email, slack, dropbox, etc.)
3. Bidirectional People-Topic Relationship Management
4. Source Traceability and Content Retrieval
5. Knowledge Evolution and Quality Management
6. Proactive Intelligence Generation for Auto-Response Capabilities

Goal: Build comprehensive knowledge to enable auto-response and decision-making
"""

import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
import re
import json
from dataclasses import dataclass

from models.database import get_db_manager
from models.knowledge_models import (
    TopicHierarchy, PersonTopicRelationship, KnowledgeSource, 
    UnifiedKnowledgeGraph, ProactiveKnowledgeInsight, KnowledgeEvolutionLog,
    TopicType, SourceType, RelationshipType, KnowledgeConfidence,
    TopicSummary, PersonTopicContext, KnowledgeTraceability
)
from models.email import Email  # Add Email model import

logger = logging.getLogger(__name__)

@dataclass
class KnowledgeExtractionResult:
    """Result of knowledge extraction from content"""
    topics: List[Dict[str, Any]]
    people: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    insights: List[Dict[str, Any]]
    confidence: float
    source_reference: str

@dataclass
class TopicHierarchySuggestion:
    """AI suggestion for topic hierarchy placement"""
    topic_name: str
    suggested_parent: Optional[str]
    suggested_type: TopicType
    confidence: float
    reasoning: str

class KnowledgeEngine:
    """
    Core Knowledge Processing Engine
    
    This is the central intelligence that builds and maintains the knowledge base
    that can eventually replace the user's decision-making capabilities.
    """
    
    def __init__(self):
        self.db_manager = get_db_manager()
        
        # Configuration for topic hierarchy building
        self.TOPIC_CONFIDENCE_THRESHOLD = 0.6
        self.RELATIONSHIP_CONFIDENCE_THRESHOLD = 0.5
        self.HIERARCHY_MAX_DEPTH = 6
        self.AUTO_ORGANIZE_THRESHOLD = 10  # topics before auto-organizing
        
        # Knowledge quality thresholds
        self.MIN_EVIDENCE_COUNT = 2
        self.KNOWLEDGE_DECAY_DAYS = 30
        
    # ==========================================================================
    # TOPIC HIERARCHY MANAGEMENT
    # ==========================================================================
    
    def build_topic_hierarchy_from_content(self, user_id: int, source_content: List[Dict]) -> Dict[str, Any]:
        """
        Automatically build topic hierarchy from content analysis.
        This is core to making the system intelligent about business structure.
        """
        logger.info(f"🏗️  Building topic hierarchy for user {user_id} from {len(source_content)} content sources")
        
        try:
            with self.db_manager.get_session() as session:
                # Step 1: Extract all topics from content
                all_topics = self._extract_topics_from_content(source_content, user_id)
                
                # Step 2: Analyze and categorize topics
                categorized_topics = self._categorize_topics(all_topics)
                
                # Step 3: Build hierarchical structure
                hierarchy = self._build_hierarchy_structure(categorized_topics, session, user_id)
                
                # Step 4: Create/update topic records
                created_topics = self._create_topic_records(hierarchy, session, user_id)
                
                # Step 5: Update topic relationships and metadata
                self._update_topic_relationships(created_topics, session, user_id)
                
                session.commit()
                
                result = {
                    'success': True,
                    'topics_created': len(created_topics),
                    'hierarchy_depth': max([t.depth_level for t in created_topics]) if created_topics else 0,
                    'auto_generated': len([t for t in created_topics if t.auto_generated]),
                    'categories_found': len(set([t.topic_type for t in created_topics])),
                    'top_level_topics': [t.name for t in created_topics if t.depth_level == 0]
                }
                
                logger.info(f"✅ Topic hierarchy built: {result}")
                return result
                
        except Exception as e:
            logger.error(f"❌ Error building topic hierarchy: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _extract_topics_from_content(self, content: List[Dict], user_id: int) -> List[Dict]:
        """Extract topics from various content types"""
        topics = []
        
        for item in content:
            source_type = item.get('source_type', 'unknown')
            content_text = item.get('content', '') or item.get('body_text', '') or item.get('text', '')
            
            if not content_text:
                continue
            
            # Use AI to extract topics (would integrate with Claude here)
            extracted = self._ai_extract_topics(content_text, source_type)
            
            for topic in extracted:
                topics.append({
                    'name': topic['name'],
                    'confidence': topic['confidence'],
                    'source_type': source_type,
                    'source_id': item.get('id', 'unknown'),
                    'context': topic.get('context', ''),
                    'mentions': topic.get('mentions', 1),
                    'category_hints': topic.get('category_hints', [])
                })
        
        # Consolidate duplicate topics
        return self._consolidate_topics(topics)
    
    def _ai_extract_topics(self, content: str, source_type: str) -> List[Dict]:
        """
        AI-powered topic extraction from content.
        In production, this would use Claude API.
        """
        # Placeholder for AI extraction - would integrate with Claude
        # For now, use pattern matching for common business topics
        
        topics = []
        content_lower = content.lower()
        
        # Business structure patterns
        company_patterns = [
            r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(?:company|corp|inc|ltd)\b',
            r'\b(?:company|organization|business)\s+([A-Z][a-zA-Z\s]+)\b'
        ]
        
        project_patterns = [
            r'\bproject\s+([A-Z][a-zA-Z\s]+)\b',
            r'\b([A-Z][a-zA-Z]+)\s+project\b',
            r'\binitiative\s+([A-Z][a-zA-Z\s]+)\b'
        ]
        
        product_patterns = [
            r'\b([A-Z][a-zA-Z]+)\s+(?:app|application|software|platform|system)\b',
            r'\bproduct\s+([A-Z][a-zA-Z\s]+)\b'
        ]
        
        # Extract patterns
        patterns = {
            'company': company_patterns,
            'project': project_patterns,
            'product': product_patterns
        }
        
        for category, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    topic_name = match.strip() if isinstance(match, str) else ' '.join(match).strip()
                    if len(topic_name) > 2:  # Filter out very short matches
                        topics.append({
                            'name': topic_name,
                            'confidence': 0.7,
                            'context': f"Extracted from {source_type}",
                            'mentions': content_lower.count(topic_name.lower()),
                            'category_hints': [category]
                        })
        
        return topics
    
    def _consolidate_topics(self, topics: List[Dict]) -> List[Dict]:
        """Consolidate duplicate and similar topics"""
        consolidated = {}
        
        for topic in topics:
            name = topic['name'].lower().strip()
            
            if name in consolidated:
                # Merge with existing
                consolidated[name]['mentions'] += topic['mentions']
                consolidated[name]['confidence'] = max(consolidated[name]['confidence'], topic['confidence'])
                consolidated[name]['category_hints'].extend(topic['category_hints'])
                consolidated[name]['sources'] = consolidated[name].get('sources', []) + [topic.get('source_id', '')]
            else:
                topic['sources'] = [topic.get('source_id', '')]
                topic['category_hints'] = list(set(topic['category_hints']))
                consolidated[name] = topic
        
        return list(consolidated.values())
    
    def _categorize_topics(self, topics: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize topics into hierarchy levels"""
        categorized = {
            'company': [],
            'department': [],
            'product': [],
            'project': [],
            'feature': [],
            'custom': []
        }
        
        for topic in topics:
            category = self._determine_topic_category(topic)
            categorized[category].append(topic)
        
        return categorized
    
    def _determine_topic_category(self, topic: Dict) -> str:
        """Determine the category/type of a topic"""
        name = topic['name'].lower()
        hints = topic.get('category_hints', [])
        
        # Use hints if available
        if 'company' in hints:
            return 'company'
        elif 'project' in hints:
            return 'project'
        elif 'product' in hints:
            return 'product'
        
        # Pattern-based categorization
        if any(word in name for word in ['company', 'corp', 'inc', 'organization']):
            return 'company'
        elif any(word in name for word in ['department', 'team', 'division', 'group']):
            return 'department'
        elif any(word in name for word in ['app', 'application', 'platform', 'system', 'software']):
            return 'product'
        elif any(word in name for word in ['project', 'initiative', 'program']):
            return 'project'
        elif any(word in name for word in ['feature', 'component', 'module', 'function']):
            return 'feature'
        else:
            return 'custom'
    
    def _build_hierarchy_structure(self, categorized: Dict, session: Session, user_id: int) -> Dict[str, Any]:
        """Build the hierarchical structure"""
        hierarchy = {
            'root_topics': [],
            'relationships': [],
            'suggestions': []
        }
        
        # Create hierarchy: Company -> Department -> Product -> Project -> Feature
        depth_order = ['company', 'department', 'product', 'project', 'feature', 'custom']
        
        for depth, category in enumerate(depth_order):
            topics = categorized.get(category, [])
            
            for topic in topics:
                # Find potential parent based on content analysis
                parent = self._find_topic_parent(topic, hierarchy, depth, session, user_id)
                
                topic_record = {
                    'name': topic['name'],
                    'topic_type': category,
                    'depth_level': depth,
                    'parent': parent,
                    'confidence_score': topic['confidence'],
                    'mentions': topic['mentions'],
                    'auto_generated': True,
                    'sources': topic.get('sources', [])
                }
                
                if parent:
                    hierarchy['relationships'].append({
                        'child': topic['name'],
                        'parent': parent,
                        'confidence': topic['confidence']
                    })
                else:
                    hierarchy['root_topics'].append(topic_record)
        
        return hierarchy
    
    def _find_topic_parent(self, topic: Dict, hierarchy: Dict, depth: int, session: Session, user_id: int) -> Optional[str]:
        """Find the most likely parent for a topic"""
        if depth == 0:  # Root level
            return None
        
        # Look for parent relationships in content
        # This would use more sophisticated AI analysis in production
        
        # Simple heuristic: look for topics mentioned together
        topic_name = topic['name'].lower()
        
        # Check existing topics at higher levels
        existing_topics = session.query(TopicHierarchy).filter(
            and_(
                TopicHierarchy.depth_level < depth,
                TopicHierarchy.depth_level >= 0
            )
        ).all()
        
        best_parent = None
        best_score = 0
        
        for existing in existing_topics:
            # Calculate relationship score based on co-occurrence
            score = self._calculate_topic_relationship_score(topic_name, existing.name.lower())
            if score > best_score and score > 0.3:
                best_score = score
                best_parent = existing.name
        
        return best_parent
    
    def _calculate_topic_relationship_score(self, topic1: str, topic2: str) -> float:
        """Calculate how likely two topics are related"""
        # Placeholder for more sophisticated relationship scoring
        # Would analyze co-occurrence in content, semantic similarity, etc.
        
        # Simple word overlap scoring
        words1 = set(topic1.split())
        words2 = set(topic2.split())
        
        if len(words1.union(words2)) == 0:
            return 0.0
        
        overlap = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return overlap / union
    
    def _create_topic_records(self, hierarchy: Dict, session: Session, user_id: int) -> List[TopicHierarchy]:
        """Create topic records in database"""
        created_topics = []
        topic_map = {}  # name -> TopicHierarchy object
        
        # First pass: create all topics
        all_topics = hierarchy['root_topics'] + [
            rel for rel in hierarchy.get('relationships', [])
        ]
        
        for topic_data in hierarchy['root_topics']:
            topic = TopicHierarchy(
                name=topic_data['name'],
                topic_type=topic_data['topic_type'],
                depth_level=topic_data['depth_level'],
                confidence_score=topic_data['confidence_score'],
                mention_count=topic_data['mentions'],
                auto_generated=topic_data['auto_generated'],
                user_created=False,
                hierarchy_path=topic_data['name']
            )
            
            session.add(topic)
            session.flush()  # Get ID
            
            topic_map[topic.name] = topic
            created_topics.append(topic)
        
        # Second pass: establish parent-child relationships
        for rel in hierarchy.get('relationships', []):
            child_name = rel['child']
            parent_name = rel['parent']
            
            if parent_name in topic_map:
                parent = topic_map[parent_name]
                
                # Create child topic
                child_topic = next((t for t in all_topics if isinstance(t, dict) and t.get('name') == child_name), None)
                if child_topic:
                    child = TopicHierarchy(
                        name=child_name,
                        topic_type=child_topic.get('topic_type', 'custom'),
                        depth_level=parent.depth_level + 1,
                        parent_topic_id=parent.id,
                        confidence_score=rel['confidence'],
                        auto_generated=True,
                        hierarchy_path=f"{parent.hierarchy_path}/{child_name}"
                    )
                    
                    session.add(child)
                    session.flush()
                    
                    topic_map[child.name] = child
                    created_topics.append(child)
        
        return created_topics
    
    def _update_topic_relationships(self, topics: List[TopicHierarchy], session: Session, user_id: int):
        """Update topic relationships and cross-references"""
        # This would analyze content to establish topic relationships
        # and update the unified knowledge graph
        pass
    
    # ==========================================================================
    # MULTI-SOURCE KNOWLEDGE INGESTION
    # ==========================================================================
    
    def ingest_knowledge_from_source(self, source_type: SourceType, content: Dict, user_id: int) -> KnowledgeExtractionResult:
        """
        Ingest knowledge from any source type.
        This is the unified entry point for all knowledge ingestion.
        """
        logger.info(f"🔄 Ingesting knowledge from {source_type.value} for user {user_id}")
        
        try:
            with self.db_manager.get_session() as session:
                # Step 1: Store source content with full traceability
                source_record = self._store_source_content(content, source_type, session, user_id)
                
                # Step 2: Extract knowledge entities
                extraction_result = self._extract_knowledge_entities(content, source_type, user_id)
                
                # Step 3: Update knowledge graph
                self._update_knowledge_graph(extraction_result, source_record, session, user_id)
                
                # Step 4: Generate proactive insights
                insights = self._generate_proactive_insights(extraction_result, session, user_id)
                
                session.commit()
                
                logger.info(f"✅ Knowledge ingestion complete: {len(extraction_result.topics)} topics, {len(extraction_result.people)} people")
                return extraction_result
                
        except Exception as e:
            logger.error(f"❌ Knowledge ingestion error: {str(e)}")
            raise
    
    def _store_source_content(self, content: Dict, source_type: SourceType, session: Session, user_id: int) -> KnowledgeSource:
        """Store source content with full traceability"""
        source = KnowledgeSource(
            source_type=source_type.value,
            source_id=content.get('id', 'unknown'),
            raw_content=json.dumps(content.get('raw_content', content)),
            processed_content=content.get('processed_content', ''),
            content_summary=content.get('summary', ''),
            title=content.get('title', '') or content.get('subject', ''),
            author=content.get('author', '') or content.get('sender', ''),
            timestamp=datetime.fromisoformat(content.get('timestamp', datetime.utcnow().isoformat())),
            processing_status='pending'
        )
        
        session.add(source)
        session.flush()
        return source
    
    def _extract_knowledge_entities(self, content: Dict, source_type: SourceType, user_id: int) -> KnowledgeExtractionResult:
        """Extract all knowledge entities from content"""
        # This would integrate with Claude AI for sophisticated extraction
        # For now, using pattern-based extraction
        
        text = content.get('processed_content', '') or content.get('raw_content', '')
        
        return KnowledgeExtractionResult(
            topics=self._extract_topics_from_text(text),
            people=self._extract_people_from_text(text),
            relationships=self._extract_relationships_from_text(text),
            tasks=self._extract_tasks_from_text(text),
            insights=self._extract_insights_from_text(text),
            confidence=0.7,
            source_reference=content.get('id', 'unknown')
        )
    
    def _extract_topics_from_text(self, text: str) -> List[Dict]:
        """Extract topics from text"""
        # Placeholder - would use AI in production
        return []
    
    def _extract_people_from_text(self, text: str) -> List[Dict]:
        """Extract people mentions from text"""
        # Placeholder - would use AI in production
        return []
    
    def _extract_relationships_from_text(self, text: str) -> List[Dict]:
        """Extract relationships from text"""
        # Placeholder - would use AI in production
        return []
    
    def _extract_tasks_from_text(self, text: str) -> List[Dict]:
        """Extract tasks from text"""
        # Placeholder - would use AI in production
        return []
    
    def _extract_insights_from_text(self, text: str) -> List[Dict]:
        """Extract insights from text"""
        # Placeholder - would use AI in production
        return []
    
    def _update_knowledge_graph(self, extraction: KnowledgeExtractionResult, source: KnowledgeSource, session: Session, user_id: int):
        """Update the unified knowledge graph with new relationships"""
        # Update extraction results in source record
        source.extracted_topics = extraction.topics
        source.extracted_people = extraction.people
        source.extracted_tasks = extraction.tasks
        source.extracted_insights = extraction.insights
        source.processing_status = 'processed'
        
        # Create knowledge graph entries for relationships
        for relationship in extraction.relationships:
            graph_entry = UnifiedKnowledgeGraph(
                entity_type_1=relationship['entity_type_1'],
                entity_id_1=relationship['entity_id_1'],
                entity_type_2=relationship['entity_type_2'],
                entity_id_2=relationship['entity_id_2'],
                relationship_type=relationship['type'],
                relationship_strength=relationship.get('strength', 0.5),
                confidence=relationship.get('confidence', 0.5),
                evidence_sources=[source.id],
                evidence_count=1
            )
            session.add(graph_entry)
    
    def _generate_proactive_insights(self, extraction: KnowledgeExtractionResult, session: Session, user_id: int) -> List[Dict]:
        """Generate proactive insights from knowledge extraction"""
        insights = []
        
        # Analyze patterns and generate insights
        # This would use sophisticated AI analysis in production
        
        return insights
    
    # ==========================================================================
    # KNOWLEDGE RETRIEVAL AND TRACEABILITY
    # ==========================================================================
    
    def get_source_content(self, source_type: str, source_id: str, user_id: int) -> Optional[Dict]:
        """
        Retrieve full source content for traceability.
        Critical for user to verify AI decisions.
        """
        try:
            with self.db_manager.get_session() as session:
                source = session.query(KnowledgeSource).filter(
                    and_(
                        KnowledgeSource.source_type == source_type,
                        KnowledgeSource.source_id == source_id
                    )
                ).first()
                
                if source:
                    return {
                        'source_type': source.source_type,
                        'source_id': source.source_id,
                        'raw_content': json.loads(source.raw_content) if source.raw_content else {},
                        'processed_content': source.processed_content,
                        'summary': source.content_summary,
                        'title': source.title,
                        'author': source.author,
                        'timestamp': source.timestamp.isoformat() if source.timestamp else None,
                        'extraction_results': {
                            'topics': source.extracted_topics,
                            'people': source.extracted_people,
                            'tasks': source.extracted_tasks,
                            'insights': source.extracted_insights
                        }
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving source content: {str(e)}")
            return None
    
    def get_knowledge_traceability(self, entity_type: str, entity_id: int, user_id: int) -> List[KnowledgeTraceability]:
        """
        Get complete traceability for any knowledge entity.
        Shows all sources that contributed to this knowledge.
        """
        try:
            with self.db_manager.get_session() as session:
                # Query knowledge source references
                references = session.query(KnowledgeSource).join(
                    # Would join through knowledge_source_association table
                ).filter(
                    # Filter by entity
                ).all()
                
                traceability = []
                for ref in references:
                    traceability.append(KnowledgeTraceability(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        source_type=ref.source_type,
                        source_id=ref.source_id,
                        source_content_snippet=ref.content_summary[:200] if ref.content_summary else '',
                        confidence=0.8,  # Would calculate based on extraction confidence
                        timestamp=ref.timestamp,
                        can_access_full_content=True
                    ))
                
                return traceability
                
        except Exception as e:
            logger.error(f"Error getting knowledge traceability: {str(e)}")
            return []

    # ==========================================================================
    # KNOWLEDGE FOUNDATION BOOTSTRAPPING
    # ==========================================================================
    
    def build_knowledge_foundation_from_bulk_emails(self, user_id: int, months_back: int = 6) -> Dict[str, Any]:
        """
        Build comprehensive knowledge foundation from bulk historical emails.
        This creates the context skeleton that makes all future ingestion more accurate.
        
        This is the "Automatic Approach" - analyze large amounts of historical data
        to understand the user's complete business context before processing new content.
        """
        logger.info(f"🏗️  Building knowledge foundation from {months_back} months of historical emails for user {user_id}")
        
        try:
            with self.db_manager.get_session() as session:
                # Step 1: Get quality-filtered historical emails
                historical_emails = self._fetch_foundation_emails(user_id, months_back, session)
                
                if len(historical_emails) < 10:
                    return {
                        'success': False,
                        'error': 'Insufficient historical data for foundation building',
                        'recommendation': 'Use manual interview approach instead'
                    }
                
                # Step 2: Analyze complete corpus with Claude for comprehensive understanding
                foundation_analysis = self._analyze_complete_email_corpus(historical_emails, user_id)
                
                # Step 3: Build comprehensive hierarchical structure
                foundation_hierarchy = self._build_foundation_hierarchy(foundation_analysis, session, user_id)
                
                # Step 4: Create detailed topic records with rich context
                created_topics = self._create_foundation_topic_records(foundation_hierarchy, session, user_id)
                
                # Step 5: Build people-topic relationships from the foundation
                self._establish_foundation_relationships(foundation_analysis, created_topics, session, user_id)
                
                session.commit()
                
                result = {
                    'success': True,
                    'foundation_type': 'automatic_bulk_analysis',
                    'emails_analyzed': len(historical_emails),
                    'topics_created': len(created_topics),
                    'hierarchy_depth': max([t.depth_level for t in created_topics]) if created_topics else 0,
                    'business_areas_identified': len([t for t in created_topics if t.topic_type == 'department']),
                    'projects_identified': len([t for t in created_topics if t.topic_type == 'project']),
                    'people_connected': len(set([rel.person_id for rel in session.query(PersonTopicRelationship).all()])),
                    'foundation_quality_score': self._calculate_foundation_quality(created_topics, session)
                }
                
                logger.info(f"✅ Knowledge foundation built: {result}")
                return result
                
        except Exception as e:
            logger.error(f"❌ Error building knowledge foundation: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _fetch_foundation_emails(self, user_id: int, months_back: int, session: Session) -> List[Dict]:
        """Fetch quality-filtered historical emails for foundation building"""
        from chief_of_staff_ai.processors.email_quality_filter import email_quality_filter, ContactTier
        from datetime import datetime, timedelta
        
        # Get emails from the past N months
        cutoff_date = datetime.utcnow() - timedelta(days=months_back * 30)
        
        # Get all emails in date range
        all_emails = session.query(Email).filter(
            Email.user_id == user_id,
            Email.email_date >= cutoff_date,
            Email.ai_summary.isnot(None)  # Only processed emails
        ).order_by(Email.email_date.desc()).limit(1000).all()
        
        # Apply quality filtering - only include Tier 1 and Tier 2 contacts
        foundation_emails = []
        for email in all_emails:
            if email.sender:
                contact_stats = email_quality_filter._get_contact_stats(email.sender.lower(), user_id)
                if contact_stats.tier in [ContactTier.TIER_1, ContactTier.TIER_2]:
                    foundation_emails.append({
                        'id': email.gmail_id,
                        'subject': email.subject or '',
                        'sender': email.sender,
                        'body_text': email.body_text or '',
                        'ai_summary': email.ai_summary or '',
                        'date': email.email_date.isoformat() if email.email_date else '',
                        'contact_tier': contact_stats.tier.value,
                        'response_rate': contact_stats.response_rate
                    })
        
        logger.info(f"📧 Foundation emails: {len(foundation_emails)} quality emails from {len(all_emails)} total")
        return foundation_emails
    
    def _analyze_complete_email_corpus(self, emails: List[Dict], user_id: int) -> Dict[str, Any]:
        """
        Send complete email corpus to Claude for comprehensive business analysis.
        This is where we get the "big picture" understanding.
        """
        # Prepare comprehensive prompt for Claude
        corpus_text = self._prepare_corpus_for_analysis(emails)
        
        # This would integrate with Claude API in production
        # For now, we'll simulate comprehensive analysis
        analysis = {
            'business_structure': {
                'company_focus': 'Technology consulting and software development',
                'departments': ['Engineering', 'Sales', 'Marketing', 'Operations'],
                'core_products': ['Mobile Apps', 'Web Platforms', 'API Services']
            },
            'project_hierarchy': {
                'major_initiatives': [
                    {
                        'name': 'Mobile Platform Redesign',
                        'department': 'Engineering',
                        'key_people': ['john@company.com', 'sarah@company.com'],
                        'sub_projects': ['iOS App', 'Android App', 'Backend API']
                    },
                    {
                        'name': 'Q1 Sales Campaign', 
                        'department': 'Sales',
                        'key_people': ['mike@company.com'],
                        'sub_projects': ['Lead Generation', 'Client Presentations']
                    }
                ]
            },
            'relationship_mapping': {
                'internal_team': ['john@company.com', 'sarah@company.com', 'mike@company.com'],
                'key_clients': ['client@bigcorp.com', 'contact@startup.com'],
                'external_partners': ['partner@vendor.com'],
                'decision_makers': ['ceo@company.com', 'cto@company.com']
            },
            'business_priorities': [
                'Product launch deadline: March 2024',
                'Client retention and satisfaction',
                'Team scaling and hiring',
                'Technology stack modernization'
            ],
            'topic_confidence_scores': {
                'Mobile Platform Redesign': 0.95,
                'Q1 Sales Campaign': 0.87,
                'Engineering': 0.92,
                'Sales': 0.88
            }
        }
        
        return analysis
    
    def _build_foundation_hierarchy(self, analysis: Dict, session: Session, user_id: int) -> Dict[str, Any]:
        """Build hierarchical topic structure from comprehensive analysis"""
        hierarchy = {
            'root_topics': [],
            'topic_relationships': [],
            'people_topic_connections': [],
            'business_context': analysis
        }
        
        # Build from business structure analysis
        business_structure = analysis.get('business_structure', {})
        
        # Create company/organization root
        company_topic = {
            'name': business_structure.get('company_focus', 'Business Operations'),
            'topic_type': 'company',
            'depth_level': 0,
            'confidence_score': 0.95,
            'description': 'Main business focus and operations',
            'children': []
        }
        
        # Add departments as children
        for dept in business_structure.get('departments', []):
            dept_topic = {
                'name': dept,
                'topic_type': 'department', 
                'depth_level': 1,
                'parent': company_topic['name'],
                'confidence_score': 0.9,
                'children': []
            }
            company_topic['children'].append(dept_topic)
        
        # Add projects under departments
        for project in analysis.get('project_hierarchy', {}).get('major_initiatives', []):
            project_topic = {
                'name': project['name'],
                'topic_type': 'project',
                'depth_level': 2,
                'parent': project.get('department', 'Operations'),
                'confidence_score': analysis.get('topic_confidence_scores', {}).get(project['name'], 0.8),
                'people': project.get('key_people', []),
                'children': []
            }
            
            # Add sub-projects
            for sub_project in project.get('sub_projects', []):
                sub_topic = {
                    'name': sub_project,
                    'topic_type': 'feature',
                    'depth_level': 3,
                    'parent': project['name'],
                    'confidence_score': 0.75
                }
                project_topic['children'].append(sub_topic)
            
            # Find parent department and add project
            for dept in company_topic['children']:
                if dept['name'] == project.get('department'):
                    dept['children'].append(project_topic)
                    break
        
        hierarchy['root_topics'] = [company_topic]
        return hierarchy
    
    def _create_foundation_topic_records(self, hierarchy: Dict, session: Session, user_id: int) -> List[TopicHierarchy]:
        """Create detailed topic records with foundation context"""
        created_topics = []
        
        def create_topic_recursive(topic_data, parent_id=None, parent_path=""):
            # Create topic record
            topic = TopicHierarchy(
                name=topic_data['name'],
                topic_type=topic_data['topic_type'],
                depth_level=topic_data['depth_level'],
                parent_topic_id=parent_id,
                confidence_score=topic_data['confidence_score'],
                auto_generated=True,
                user_created=False,
                status='active',
                priority='medium',
                description=topic_data.get('description', f"Auto-generated {topic_data['topic_type']} from email analysis"),
                hierarchy_path=f"{parent_path}/{topic_data['name']}" if parent_path else topic_data['name'],
                mention_count=0,  # Will be updated when we process the source emails
                strategic_importance=topic_data['confidence_score'],
                keywords=topic_data.get('keywords', []),
                related_entities=topic_data.get('people', [])
            )
            
            session.add(topic)
            session.flush()  # Get ID
            
            created_topics.append(topic)
            
            # Create child topics recursively
            for child in topic_data.get('children', []):
                create_topic_recursive(child, topic.id, topic.hierarchy_path)
            
            return topic
        
        # Create all topics from hierarchy
        for root_topic in hierarchy['root_topics']:
            create_topic_recursive(root_topic)
        
        return created_topics
    
    def _establish_foundation_relationships(self, analysis: Dict, topics: List[TopicHierarchy], session: Session, user_id: int):
        """Establish people-topic relationships from foundation analysis"""
        # This would create PersonTopicRelationship records based on the analysis
        # Implementation would map people from the relationship_mapping to topics
        pass
    
    def _calculate_foundation_quality(self, topics: List[TopicHierarchy], session: Session) -> float:
        """Calculate quality score for the foundation"""
        if not topics:
            return 0.0
        
        # Quality factors:
        # - Hierarchy depth (deeper = more detailed)
        # - Confidence scores
        # - Topic distribution across types
        # - People-topic connections
        
        avg_confidence = sum([t.confidence_score for t in topics]) / len(topics)
        max_depth = max([t.depth_level for t in topics])
        type_diversity = len(set([t.topic_type for t in topics]))
        
        quality_score = (avg_confidence * 0.4) + (min(max_depth / 5, 1.0) * 0.3) + (min(type_diversity / 6, 1.0) * 0.3)
        
        return round(quality_score, 2)
    
    def _prepare_corpus_for_analysis(self, emails: List[Dict]) -> str:
        """Prepare email corpus for Claude analysis"""
        corpus_parts = []
        
        for email in emails[:50]:  # Limit for token management
            corpus_parts.append(f"""
Email from {email['sender']} | Subject: {email['subject']}
Date: {email['date']} | Tier: {email['contact_tier']}
Summary: {email['ai_summary'][:200]}...
""")
        
        return "\n".join(corpus_parts)

# Global instance
knowledge_engine = KnowledgeEngine() 