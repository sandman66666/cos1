import React, { useState } from 'react';
import { RefreshCw, Mail, Users, Calendar, Brain, AlertCircle, Database, Eye, CheckSquare, UserPlus } from 'lucide-react';
import clsx from 'clsx';

interface Notification {
  message: string;
  timestamp: Date;
  data?: any;
}

const SettingsPage: React.FC = () => {
  const [processing, setProcessing] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [showFlushConfirm, setShowFlushConfirm] = useState(false);
  const [currentStatus, setCurrentStatus] = useState<string | null>(null);
  const [showDataInspector, setShowDataInspector] = useState(false);
  const [inspectorData, setInspectorData] = useState<any>(null);

  const addNotification = (message: string, data?: any) => {
    const newNotification: Notification = {
      message,
      timestamp: new Date(),
      data
    };
    setNotifications(prev => [...prev, newNotification]);
  };

  const updateStatus = (status: string | null) => {
    setCurrentStatus(status);
  };

  const flushDatabase = async () => {
    setProcessing(true);
    updateStatus('🗑️ Flushing database...');
    addNotification('🗑️ Flushing database...');
    
    try {
      const response = await fetch('/api/flush-database', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const data = await response.json();
      
      if (data.success) {
        addNotification('✅ Database flushed successfully! All data cleared.');
        setShowFlushConfirm(false);
      } else {
        addNotification('❌ Database flush failed: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      addNotification('❌ Database flush failed: Network error');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  const fetchSentEmails = async () => {
    setProcessing(true);
    updateStatus('🔄 Analyzing sent emails for contacts...');
    addNotification('🔄 Analyzing sent emails for contacts...');
    try {
      const response = await fetch('/api/extract-sent-contacts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          days_back: 56, // 8 weeks
          metadata_only: true,
          sent_only: true
        })
      });
      const data = await response.json();
      
      if (data.success) {
        const inspectorData = {
          title: 'Sent Emails Analysis',
          data: {
            emails_analyzed: data.emails_analyzed,
            unique_contacts: data.unique_contacts,
            contact_patterns: data.contact_patterns,
            statistics: {
              total_contacts: data.contact_patterns.total_contacts,
              tier_1_contacts: data.contact_patterns.tier_1_contacts,
              trusted_contacts: data.contact_patterns.trusted_contacts_created,
              analyzed_period_days: data.contact_patterns.analyzed_period_days
            },
            processing_metadata: data.processing_metadata
          }
        };

        addNotification(`✅ Analyzed ${data.emails_analyzed} sent emails - Found ${data.unique_contacts} contacts`, inspectorData);
        setInspectorData(inspectorData);
      } else {
        console.error('Failed to analyze sent emails:', data.error);
        addNotification('❌ Failed to analyze sent emails: ' + data.error);
      }
    } catch (error) {
      console.error('Error analyzing sent emails:', error);
      addNotification('❌ Error analyzing sent emails');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  const normalizeEmails = async () => {
    setProcessing(true);
    updateStatus('🔄 Normalizing email content...');
    addNotification('🔄 Normalizing email content for processing...');
    try {
      const response = await fetch('/api/email/normalize-emails', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 200 })
      });
      const data = await response.json();
      if (data.success) {
        addNotification(`✅ Normalized ${data.processed} emails - Ready for intelligence processing`);
        setInspectorData({
          title: 'Email Normalization Data',
          data: {
            processed: data.processed,
            errors: data.errors,
            normalizer_version: data.normalizer_version,
            user_email: data.user_email
          }
        });
      } else {
        addNotification('❌ Failed to normalize emails: ' + data.error);
      }
    } catch (error) {
      addNotification('❌ Error normalizing emails');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  const buildContactRules = async () => {
    setProcessing(true);
    updateStatus('🔄 Building contact rules...');
    addNotification('🔄 Building contact rules from sent emails...');
    try {
      const response = await fetch('/api/email-quality/build-tier-rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await response.json();
      if (data.success) {
        addNotification(`✅ Built contact rules: ${data.tier_summary.tier_1_contacts} Tier 1 contacts`);
        setInspectorData({
          title: 'Contact Rules Data',
          data: {
            tier_summary: data.tier_summary,
            contact_patterns: data.contact_patterns,
            rules_created: data.rules_created,
            sample_contacts: data.sample_contacts?.slice(0, 5)
          }
        });
      } else {
        addNotification('❌ Failed to build contact rules: ' + data.error);
      }
    } catch (error) {
      addNotification('❌ Error building contact rules');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  const fetchCalendarEvents = async () => {
    setProcessing(true);
    updateStatus('🔄 Fetching calendar events...');
    addNotification('🔄 Fetching calendar events...');
    try {
      const response = await fetch('/api/calendar/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days_back: 30, days_forward: 30 })
      });
      const data = await response.json();
      if (data.success) {
        addNotification(`✅ Fetched ${data.events_fetched} calendar events`);
        setInspectorData({
          title: 'Calendar Events Data',
          data: {
            events_fetched: data.events_fetched,
            participants_added: data.participants_added,
            date_range: {
              start: data.date_range?.start,
              end: data.date_range?.end
            },
            sample_events: data.events?.slice(0, 5)
          }
        });
      } else {
        addNotification('❌ Failed to fetch calendar events: ' + data.error);
      }
    } catch (error) {
      addNotification('❌ Error fetching calendar events');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  const fetchAllEmails = async () => {
    setProcessing(true);
    updateStatus('🔄 Fetching all emails...');
    addNotification('🔄 Fetching all emails...');
    try {
      const response = await fetch('/api/emails/fetch-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_size: 50 })
      });
      const data = await response.json();
      if (data.success) {
        addNotification(`✅ Fetched ${data.emails_fetched} emails`);
        setInspectorData({
          title: 'All Emails Data',
          data: {
            emails_fetched: data.emails_fetched,
            remaining_count: data.remaining_count,
            batch_size: 50,
            sample_emails: data.emails?.slice(0, 5)
          }
        });
      } else {
        addNotification('❌ Failed to fetch emails: ' + data.error);
      }
    } catch (error) {
      addNotification('❌ Error fetching emails');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  // NEW: Build/Refine Knowledge Tree
  const buildRefineTree = async () => {
    setProcessing(true);
    updateStatus('🌳 Building/Refining knowledge tree...');
    addNotification('🌳 Building/Refining knowledge tree from emails...');
    try {
      const response = await fetch('/api/emails/build-knowledge-tree', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_size: 50 })
      });
      const data = await response.json();
      if (data.success) {
        const treeStats = data.tree_stats;
        addNotification(`✅ ${treeStats.is_refinement ? 'Refined' : 'Built'} knowledge tree: ${treeStats.topics_count} topics, ${treeStats.people_count} people, ${treeStats.projects_count} projects`);
        setInspectorData({
          title: 'Knowledge Tree Data',
          data: {
            tree_stats: treeStats,
            emails_analyzed: treeStats.emails_analyzed,
            is_refinement: treeStats.is_refinement,
            tree_structure: data.tree
          }
        });
      } else {
        addNotification('❌ Failed to build knowledge tree: ' + data.error);
      }
    } catch (error) {
      addNotification('❌ Error building knowledge tree');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  // NEW: Assign Emails to Tree
  const assignEmailsToTree = async () => {
    setProcessing(true);
    updateStatus('📧 Assigning emails to knowledge tree...');
    addNotification('📧 Assigning emails to knowledge tree categories...');
    try {
      const response = await fetch('/api/emails/assign-to-tree', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_size: 50 })
      });
      const data = await response.json();
      if (data.success) {
        addNotification(`✅ Assigned ${data.processed_count} emails to knowledge tree. ${data.remaining_count} emails remaining.`);
        setInspectorData({
          title: 'Email Assignment Data',
          data: {
            processed_count: data.processed_count,
            remaining_count: data.remaining_count,
            assignments: data.assignments,
            batch_size: 50
          }
        });
      } else {
        addNotification('❌ Failed to assign emails: ' + data.error);
      }
    } catch (error) {
      addNotification('❌ Error assigning emails');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  // NEW: Create Tactical Tasks (with knowledge context)
  const createTacticalTasks = async () => {
    setProcessing(true);
    updateStatus('✅ Creating tactical tasks with knowledge context...');
    addNotification('✅ Creating tactical tasks from knowledge-categorized emails...');
    try {
      const response = await fetch('/api/tasks/create-tactical', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          use_knowledge_tree: true,
          tactical_only: true,
          confidence_threshold: 0.7 // Only create tasks with high confidence
        })
      });
      const data = await response.json();
      if (data.success) {
        addNotification(`✅ Created ${data.tasks_created} tactical tasks with knowledge context`);
        setInspectorData({
          title: 'Tactical Tasks Data',
          data: {
            tasks_created: data.tasks_created,
            high_priority_tasks: data.high_priority_tasks,
            knowledge_context_applied: data.knowledge_context_applied,
            sample_tasks: data.sample_tasks?.slice(0, 5)
          }
        });
      } else {
        addNotification('❌ Failed to create tactical tasks: ' + data.error);
      }
    } catch (error) {
      addNotification('❌ Error creating tactical tasks');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  // NEW: Augment People with Knowledge
  const augmentPeople = async () => {
    setProcessing(true);
    updateStatus('👥 Augmenting people with knowledge...');
    addNotification('👥 Enhancing people profiles with knowledge tree context...');
    try {
      const response = await fetch('/api/people/augment-with-knowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          use_knowledge_tree: true,
          enhance_relationships: true,
          add_business_context: true
        })
      });
      const data = await response.json();
      if (data.success) {
        addNotification(`✅ Augmented ${data.people_enhanced} people with knowledge context`);
        setInspectorData({
          title: 'People Augmentation Data',
          data: {
            people_enhanced: data.people_enhanced,
            relationships_enhanced: data.relationships_enhanced,
            business_contexts_added: data.business_contexts_added,
            strategic_relationships: data.strategic_relationships,
            sample_people: data.sample_people?.slice(0, 5)
          }
        });
      } else {
        addNotification('❌ Failed to augment people: ' + data.error);
      }
    } catch (error) {
      addNotification('❌ Error augmenting people');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  // NEW: Augment Meetings with Knowledge
  const augmentMeetings = async () => {
    setProcessing(true);
    updateStatus('📅 Augmenting meetings with knowledge...');
    addNotification('📅 Enhancing meetings with knowledge tree context...');
    try {
      const response = await fetch('/api/calendar/augment-with-knowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          use_knowledge_tree: true,
          add_attendee_context: true,
          generate_preparation_tasks: true
        })
      });
      const data = await response.json();
      if (data.success) {
        addNotification(`✅ Augmented ${data.meetings_enhanced} meetings with knowledge context`);
        setInspectorData({
          title: 'Meetings Augmentation Data',
          data: {
            meetings_enhanced: data.meetings_enhanced,
            attendee_intelligence_added: data.attendee_intelligence_added,
            preparation_tasks_created: data.preparation_tasks_created,
            strategic_meetings: data.strategic_meetings,
            sample_meetings: data.sample_meetings?.slice(0, 5)
          }
        });
      } else {
        addNotification('❌ Failed to augment meetings: ' + data.error);
      }
    } catch (error) {
      addNotification('❌ Error augmenting meetings');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  // ENHANCED KNOWLEDGE-DRIVEN PIPELINE PHASES
  const runPhase1 = async () => {
    setProcessing(true);
    updateStatus('🚀 Phase 1: Smart Contact Filtering...');
    addNotification('🚀 Phase 1: Analyzing sent emails to build trusted contact database...');
    try {
      const response = await fetch('/api/email/knowledge-pipeline/phase1-contacts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days_back: 365 })
      });
      const data = await response.json();
      if (data.success) {
        addNotification(`✅ Phase 1 Complete: ${data.message}`, {
          title: 'Phase 1: Smart Contact Filtering Results',
          data: {
            phase_results: data.results,
            contacts_created: data.contacts_created,
            next_step: data.next_step,
            people_tab_message: `Go to People tab to see ${data.results.total_people_in_database} contacts created!`
          }
        });
      } else {
        addNotification('❌ Phase 1 Failed: ' + data.error);
      }
    } catch (error) {
      addNotification('❌ Phase 1 Network Error');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  const runPhase2 = async () => {
    setProcessing(true);
    updateStatus('🧠 Phase 2: Knowledge Tree Creation...');
    addNotification('🧠 Phase 2: Creating comprehensive knowledge tree from filtered emails...');
    try {
      const response = await fetch('/api/email/knowledge-pipeline/phase2-knowledge-tree', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ max_emails: 50, force_rebuild: false })
      });
      const data = await response.json();
      if (data.success) {
        addNotification(`✅ Phase 2 Complete: ${data.message}`, {
          title: 'Phase 2: Knowledge Tree Creation Results',
          data: {
            phase_results: data.results,
            knowledge_tree: data.knowledge_tree,
            next_step: data.next_step,
            knowledge_tab_message: `Go to Knowledge tab to explore ${data.results.knowledge_topics} topics created!`
          }
        });
      } else {
        addNotification('❌ Phase 2 Failed: ' + data.error);
      }
    } catch (error) {
      addNotification('❌ Phase 2 Network Error');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  const runPhase3 = async () => {
    setProcessing(true);
    updateStatus('📅 Phase 3: Calendar Sync & Contact Augmentation...');
    addNotification('📅 Phase 3: Syncing calendar events and augmenting contact data...');
    try {
      const response = await fetch('/api/email/knowledge-pipeline/phase3-calendar-sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days_back: 30 })
      });
      const data = await response.json();
      if (data.success) {
        addNotification(`✅ Phase 3 Complete: ${data.message}`, {
          title: 'Phase 3: Calendar Sync & Contact Augmentation Results',
          data: {
            phase_results: data.results,
            calendar_contacts: data.calendar_contacts,
            meeting_insights: data.meeting_insights,
            next_step: data.next_step,
            enhancement_message: `Contacts now enhanced with meeting data - check People tab for updates!`
          }
        });
      } else {
        addNotification('❌ Phase 3 Failed: ' + data.error);
      }
    } catch (error) {
      addNotification('❌ Phase 3 Network Error');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  const runPhase4 = async () => {
    setProcessing(true);
    updateStatus('📧 Phase 4: Email Knowledge Enhancement...');
    addNotification('📧 Phase 4: Fetching more emails and enhancing knowledge tree...');
    try {
      const response = await fetch('/api/email/knowledge-pipeline/phase4-email-enhancement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ additional_emails: 50, days_back: 60 })
      });
      const data = await response.json();
      if (data.success) {
        addNotification(`✅ Phase 4 Complete: ${data.message}`, {
          title: 'Phase 4: Email Knowledge Enhancement Results',
          data: {
            phase_results: data.results,
            topic_enhancements: data.topic_enhancements,
            enhancement_summary: data.enhancement_summary,
            next_step: data.next_step,
            knowledge_growth_message: `Knowledge tree enhanced with ${data.results.emails_assigned_to_topics} new emails across ${data.results.topics_enhanced} topics!`
          }
        });
      } else {
        addNotification('❌ Phase 4 Failed: ' + data.error);
      }
    } catch (error) {
      addNotification('❌ Phase 4 Network Error');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  const runPhase5 = async () => {
    setProcessing(true);
    updateStatus('💡 Phase 5: Cross-Topic Intelligence Generation...');
    addNotification('💡 Phase 5: Generating strategic tasks and insights from knowledge tree...');
    try {
      const response = await fetch('/api/email/knowledge-pipeline/phase5-intelligence', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      const data = await response.json();
      if (data.success) {
        addNotification(`✅ Phase 5 Complete: ${data.message}`, {
          title: 'Phase 5: Cross-Topic Intelligence Generation Results',
          data: {
            phase_results: data.results,
            cross_topic_intelligence: data.cross_topic_intelligence,
            knowledge_tree_stats: data.knowledge_tree_stats,
            next_step: data.next_step,
            completion_message: `Generated ${data.results.strategic_tasks_generated} strategic tasks and ${data.results.knowledge_insights_generated} insights!`
          }
        });
      } else {
        addNotification('❌ Phase 5 Failed: ' + data.error);
      }
    } catch (error) {
      addNotification('❌ Phase 5 Network Error');
    } finally {
      setProcessing(false);
      updateStatus(null);
    }
  };

  const showNotificationData = (data: any) => {
    if (data) {
      setInspectorData(data);
    }
  };

  return (
    <div className="p-6 space-y-8">
      {/* Real-time Status Indicator */}
      {currentStatus && (
        <div className="fixed top-4 right-4 z-50 bg-blue-600/90 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span className="text-sm">{currentStatus}</span>
        </div>
      )}

      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-white">Data Processing Pipeline</h2>
        
        {/* Step 1: Contact Building */}
        <div className="bg-gray-800 p-4 rounded-lg space-y-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Users className="w-5 h-5" />
            Step 1: Build Contact Base
          </h3>
          <div className="flex gap-4 flex-wrap">
            <button
              onClick={fetchSentEmails}
              disabled={processing}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              1. Fetch Sent Emails
            </button>
            <button
              onClick={normalizeEmails}
              disabled={processing}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              2. Normalize Content
            </button>
            <button
              onClick={buildContactRules}
              disabled={processing}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              3. Build Contact Rules
            </button>
            <button
              onClick={fetchCalendarEvents}
              disabled={processing}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              4. Fetch Calendar Events
            </button>
          </div>
        </div>

        {/* Step 2: Knowledge Tree Building */}
        <div className="bg-gray-800 p-4 rounded-lg space-y-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Brain className="w-5 h-5" />
            Step 2: Build Knowledge Tree
          </h3>
          <p className="text-sm text-gray-400">Build master knowledge tree first, then assign emails to it</p>
          <div className="flex gap-4 flex-wrap">
            <button
              onClick={fetchAllEmails}
              disabled={processing}
              className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
            >
              1. Fetch All Emails
            </button>
            <button
              onClick={buildRefineTree}
              disabled={processing}
              className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
            >
              2. Build/Refine Tree
            </button>
            <button
              onClick={assignEmailsToTree}
              disabled={processing}
              className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
            >
              3. Assign Emails to Tree
            </button>
          </div>
        </div>

        {/* Step 3: Augment with Knowledge */}
        <div className="bg-gray-800 p-4 rounded-lg space-y-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Database className="w-5 h-5" />
            Step 3: Augment with Knowledge
          </h3>
          <p className="text-sm text-gray-400">Use knowledge tree to enhance tasks, people, and meetings with rich context</p>
          <div className="flex gap-4 flex-wrap">
            <button
              onClick={createTacticalTasks}
              disabled={processing}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
            >
              <CheckSquare className="w-4 h-4" />
              Create Tactical Tasks
            </button>
            <button
              onClick={augmentPeople}
              disabled={processing}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
            >
              <UserPlus className="w-4 h-4" />
              Augment People
            </button>
            <button
              onClick={augmentMeetings}
              disabled={processing}
              className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
            >
              <Calendar className="w-4 h-4" />
              Augment Meetings
            </button>
          </div>
        </div>

        {/* NEW: Enhanced Knowledge-Driven Pipeline Testing */}
        <div className="bg-gradient-to-br from-blue-900 to-purple-900 p-6 rounded-lg border border-blue-500/30 space-y-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">🧠 Enhanced Knowledge-Driven Pipeline Testing</h3>
              <p className="text-blue-200 text-sm">Test each phase individually to see step-by-step results and incremental improvements</p>
            </div>
          </div>

          {/* Phase 1: Smart Contact Filtering */}
          <div className="bg-black/20 rounded-lg p-4 border border-blue-400/20">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">1</div>
                <h4 className="text-white font-semibold">🚀 Smart Contact Filtering</h4>
              </div>
              <button
                onClick={runPhase1}
                disabled={processing}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                Run Phase 1
              </button>
            </div>
            <p className="text-blue-200 text-sm">Analyzes sent emails to build trusted contact database. <span className="font-medium">Expected Result:</span> Contacts appear in People tab with engagement scores.</p>
          </div>

          {/* Phase 2: Knowledge Tree Creation */}
          <div className="bg-black/20 rounded-lg p-4 border border-purple-400/20">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 bg-purple-500 text-white rounded-full flex items-center justify-center text-sm font-bold">2</div>
                <h4 className="text-white font-semibold">🧠 Knowledge Tree Creation</h4>
              </div>
              <button
                onClick={runPhase2}
                disabled={processing}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 transition-colors"
              >
                Run Phase 2
              </button>
            </div>
            <p className="text-purple-200 text-sm">Creates comprehensive knowledge topics from filtered emails. <span className="font-medium">Expected Result:</span> Knowledge tree with business topics and relationships.</p>
          </div>

          {/* Phase 3: Calendar Sync & Contact Augmentation */}
          <div className="bg-black/20 rounded-lg p-4 border border-green-400/20">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 bg-green-500 text-white rounded-full flex items-center justify-center text-sm font-bold">3</div>
                <h4 className="text-white font-semibold">📅 Calendar Sync & Contact Augmentation</h4>
              </div>
              <button
                onClick={runPhase3}
                disabled={processing}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                Run Phase 3
              </button>
            </div>
            <p className="text-green-200 text-sm">Syncs calendar events and enhances contacts with meeting data. <span className="font-medium">Expected Result:</span> Contacts updated with meeting frequency and context.</p>
          </div>

          {/* Phase 4: Email Knowledge Enhancement */}
          <div className="bg-black/20 rounded-lg p-4 border border-yellow-400/20">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 bg-yellow-500 text-white rounded-full flex items-center justify-center text-sm font-bold">4</div>
                <h4 className="text-white font-semibold">📧 Email Knowledge Enhancement</h4>
              </div>
              <button
                onClick={runPhase4}
                disabled={processing}
                className="px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 disabled:opacity-50 transition-colors"
              >
                Run Phase 4
              </button>
            </div>
            <p className="text-yellow-200 text-sm">Fetches more emails and enhances knowledge tree with additional context. <span className="font-medium">Expected Result:</span> Knowledge topics grow richer with more email content.</p>
          </div>

          {/* Phase 5: Cross-Topic Intelligence */}
          <div className="bg-black/20 rounded-lg p-4 border border-red-400/20">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center text-sm font-bold">5</div>
                <h4 className="text-white font-semibold">💡 Cross-Topic Intelligence Generation</h4>
              </div>
              <button
                onClick={runPhase5}
                disabled={processing}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                Run Phase 5
              </button>
            </div>
            <p className="text-red-200 text-sm">Generates strategic tasks and insights from the complete knowledge tree. <span className="font-medium">Expected Result:</span> Strategic tasks and cross-topic insights for action.</p>
          </div>

          {/* Pipeline Status */}
          <div className="bg-black/30 rounded-lg p-4 border border-gray-400/30">
            <h4 className="text-white font-semibold mb-2">📊 Pipeline Progress Tips</h4>
            <ul className="text-gray-300 text-sm space-y-1">
              <li>• Run phases in order for best results</li>
              <li>• Each phase builds on the previous one</li>
              <li>• Click notification results to inspect detailed data</li>
              <li>• Check People, Knowledge, and Tasks tabs after each phase</li>
              <li>• Run Phase 4 multiple times to enhance knowledge tree</li>
            </ul>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-gray-800 rounded-lg border border-red-700 p-6 mt-8">
          <h4 className="text-red-300 font-medium mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            Danger Zone
          </h4>
          <div className="p-4 bg-red-900/20 border border-red-800/50 rounded-lg">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 mt-0.5" />
              <div className="flex-1">
                <h5 className="text-red-300 font-medium">Flush Database</h5>
                <p className="text-sm text-red-200 mt-1">
                  Permanently delete all your data including emails, contacts, tasks, topics, and AI analysis. This action cannot be undone.
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowFlushConfirm(true)}
              disabled={processing}
              className="mt-3 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
            >
              Flush Database
            </button>
          </div>
        </div>

        {/* Updated Notifications */}
        <div className="mt-8 space-y-2">
          {notifications.map((notification, index) => (
            <div
              key={index}
              onClick={() => notification.data && showNotificationData(notification.data)}
              className={clsx(
                "p-2 bg-gray-700 rounded text-white",
                notification.data && "cursor-pointer hover:bg-gray-600 transition-colors"
              )}
            >
              <div className="flex items-center justify-between">
                <span>{notification.message}</span>
                {notification.data && (
                  <Eye className="w-4 h-4 text-gray-400" />
                )}
              </div>
              <div className="text-xs text-gray-400 mt-1">
                {notification.timestamp.toLocaleTimeString()}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Flush Database Confirmation Modal */}
      {showFlushConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-800 rounded-xl border border-red-700 max-w-md w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-red-300 flex items-center gap-2">
                  <AlertCircle className="w-6 h-6" />
                  Confirm Database Flush
                </h2>
                <button
                  onClick={() => setShowFlushConfirm(false)}
                  className="text-gray-400 hover:text-white text-2xl"
                >
                  ×
                </button>
              </div>

              <div className="space-y-4">
                <div className="p-4 bg-red-900/20 border border-red-800/50 rounded-lg">
                  <p className="text-red-200 text-sm">
                    This will permanently delete <strong>ALL</strong> your data including:
                  </p>
                  <ul className="mt-2 text-red-200 text-sm list-disc list-inside space-y-1">
                    <li>All emails and AI analysis</li>
                    <li>All contacts and relationships</li>
                    <li>All tasks and projects</li>
                    <li>All topics and insights</li>
                    <li>All calendar events</li>
                  </ul>
                  <p className="mt-3 text-red-300 text-sm font-medium">
                    This action cannot be undone!
                  </p>
                </div>

                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => setShowFlushConfirm(false)}
                    className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={flushDatabase}
                    disabled={processing}
                    className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                  >
                    {processing ? 'Flushing...' : 'Yes, Flush Database'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Data Inspector Modal */}
      {inspectorData && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-800 rounded-xl border border-gray-700 max-w-4xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <Eye className="w-6 h-6" />
                  {inspectorData.title}
                </h2>
                <button
                  onClick={() => setInspectorData(null)}
                  className="text-gray-400 hover:text-white text-2xl"
                >
                  ×
                </button>
              </div>

              <div className="overflow-y-auto max-h-[60vh] pr-2 space-y-4">
                {Object.entries(inspectorData.data).map(([key, value]) => (
                  <div key={key} className="bg-gray-700/50 rounded-lg p-4">
                    <h3 className="text-blue-300 font-medium mb-2 capitalize">
                      {key.replace(/_/g, ' ')}
                    </h3>
                    <pre className="text-sm text-gray-300 whitespace-pre-wrap">
                      {JSON.stringify(value, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>

              <div className="mt-6 pt-4 border-t border-gray-700">
                <button
                  onClick={() => setInspectorData(null)}
                  className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                >
                  Close Inspector
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SettingsPage; 