import React, { useState, useEffect, useCallback } from 'react';
import { 
  Brain, Search, RefreshCw, AlertCircle, Plus, Star, Activity, 
  Database, Mail, Settings, Users, Calendar, CheckSquare, TrendingUp,
  Filter, MoreHorizontal, MapPin, Video, Clock, Zap, MessageCircle,
  BarChart3, Network, Target, Eye, ThumbsUp, ThumbsDown, Phone,
  Send, CalendarPlus, UserPlus, BookOpen, FileText, Trash2,
  ChevronDown, ChevronRight, X
} from 'lucide-react';
import clsx from 'clsx';
import SettingsPage from './components/SettingsPage';

// Enhanced Interfaces for Intelligence Dashboard
interface IntelligenceMetrics {
  total_entities: number;
  topics: number;
  people: number;
  tasks: number;
  emails: number;
  intelligence_quality: number;
  active_insights: number;
  entity_relationships: number;
  topic_momentum: number;
  relationship_density: number;
  processing_health: number;
  last_sync?: string;
}

interface ProactiveInsight {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  insight_type: string;
  confidence: number;
  created_at: string;
  action_required: boolean;
  expires_at?: string;
  related_entity_type?: string;
  related_entity_id?: number;
  business_context?: string;
  details?: string;
}

interface Task {
  id: number;
  description: string;
  priority: 'high' | 'medium' | 'low';
  status: string;
  category?: string;
  due_date?: string;
  confidence?: number;
  comprehensive_context_story?: string;
  detailed_task_meaning?: string;
  comprehensive_importance_analysis?: string;
  comprehensive_origin_details?: string;
  business_intelligence?: any;
  strategic_importance?: number;
  source_context?: any;
  relationship_context?: any;
}

interface Person {
  id: number;
  name: string;
  email: string;
  company?: string;
  title?: string;
  total_emails: number;
  engagement_score: number;
  last_contact?: string;
  relationship_intelligence?: any;
  business_context?: any;
  relationship_analytics?: any;
}

interface CalendarEvent {
  id: string;
  title: string;
  start_time: string;
  end_time: string;
  location?: string;
  attendee_count: number;
  strategic_importance: number;
  preparation_needed: boolean;
  meeting_context_story?: string;
  preparation_tasks?: any[];
  attendee_intelligence?: any[];
  business_impact?: string;
}

interface Topic {
  id: number;
  name: string;
  description?: string;
  topic_type: string;
  hierarchy_path: string;
  depth_level: number;
  parent_topic_id?: number;
  confidence_score: number;
  mention_count: number;
  auto_generated: boolean;
  user_created: boolean;
  status: string;
  priority: string;
  last_mentioned?: string;
  children?: Topic[];
  people_count?: number;
  strategic_importance?: number;
}

interface TopicHierarchy {
  hierarchy: Topic[];
  stats: {
    total_topics: number;
    max_depth: number;
    auto_generated: number;
    user_created: number;
    by_type: Record<string, number>;
    recent_activity: number;
  };
}

type ViewType = 'dashboard' | 'tasks' | 'people' | 'calendar' | 'topics' | 'settings';

// Authentication check hook
const useAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Check if user is authenticated by calling a protected endpoint
        const response = await fetch('/api/sync-settings', {
          credentials: 'include' // Include session cookies
        });
        
        if (response.ok) {
          setIsAuthenticated(true);
        } else if (response.status === 401 || response.status === 403) {
          setIsAuthenticated(false);
        } else {
          // For other errors, assume not authenticated
          setIsAuthenticated(false);
        }
      } catch (error) {
        console.error('Auth check failed:', error);
        setIsAuthenticated(false);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  return { isAuthenticated, isLoading };
};

// Loading component
const AuthLoading: React.FC = () => (
  <div className="flex items-center justify-center h-screen bg-gray-950">
    <div className="text-center">
      <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-blue-400" />
      <p className="text-gray-300">Checking authentication...</p>
    </div>
  </div>
);

// Login redirect component
const LoginRedirect: React.FC = () => {
  useEffect(() => {
    // Redirect to Flask login page
    window.location.href = 'http://localhost:8080/login';
  }, []);

  return (
    <div className="flex items-center justify-center h-screen bg-gray-950">
      <div className="text-center">
        <div className="text-blue-400 mb-4">🔐</div>
        <p className="text-gray-300">Redirecting to login...</p>
      </div>
    </div>
  );
};

const IntelligenceDashboard: React.FC = () => {
  // Authentication check
  const { isAuthenticated, isLoading } = useAuth();

  // Show loading screen while checking authentication
  if (isLoading) {
    return <AuthLoading />;
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <LoginRedirect />;
  }

  // If authenticated, show the main dashboard
  return <AuthenticatedDashboard />;
};

const AuthenticatedDashboard: React.FC = () => {
  // Core State
  const [currentView, setCurrentView] = useState<ViewType>('dashboard');
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [error, setError] = useState<string | null>(null);
  
  // Intelligence Data
  const [metrics, setMetrics] = useState<IntelligenceMetrics | null>(null);
  const [insights, setInsights] = useState<ProactiveInsight[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [topics, setTopics] = useState<Topic[]>([]);
  
  // UI State
  const [selectedInsight, setSelectedInsight] = useState<ProactiveInsight | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [selectedPerson, setSelectedPerson] = useState<Person | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<CalendarEvent | null>(null);
  const [insightFilter, setInsightFilter] = useState('all');
  const [processing, setProcessing] = useState(false);
  const [notifications, setNotifications] = useState<string[]>([]);
  
  // Missing state variables
  const [syncProgress, setSyncProgress] = useState(false);
  const [syncResults, setSyncResults] = useState<string | null>(null);
  const [showCreateTopic, setShowCreateTopic] = useState(false);
  const [newTopic, setNewTopic] = useState({
    name: '',
    description: '',
    keywords: '',
    is_official: false
  });
  
  // Enhanced Topics state
  const [topicHierarchy, setTopicHierarchy] = useState<TopicHierarchy | null>(null);
  const [selectedTopic, setSelectedTopic] = useState<Topic | null>(null);
  const [showTopicDetails, setShowTopicDetails] = useState(false);
  const [buildingTopicsFromEmails, setBuildingTopicsFromEmails] = useState(false);
  const [topicTraceability, setTopicTraceability] = useState<any>(null);
  const [expandedTopics, setExpandedTopics] = useState<Set<number>>(new Set());
  const [topicView, setTopicView] = useState<'hierarchy' | 'list'>('hierarchy');
  
  // Chat State
  const [chatMessages, setChatMessages] = useState<Array<{id: string, sender: 'user' | 'ai', message: string, timestamp: Date}>>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  // Entity Detail Modal State
  const [showEntityDetail, setShowEntityDetail] = useState(false);
  const [selectedEntityDetail, setSelectedEntityDetail] = useState<any>(null);
  const [entityContext, setEntityContext] = useState<any>(null);
  const [rawSources, setRawSources] = useState<any[]>([]);
  const [loadingEntityContext, setLoadingEntityContext] = useState(false);

  // Settings state
  const [emailSyncProgress, setEmailSyncProgress] = useState(0);
  const [emailSyncStatus, setEmailSyncStatus] = useState<string | null>(null);
  const [showFlushConfirm, setShowFlushConfirm] = useState(false);
  const [integrationStatus, setIntegrationStatus] = useState({
    gmail: { connected: true, lastSync: null as string | null },
    calendar: { connected: true, lastSync: null as string | null },
    claude: { connected: true, status: 'active' }
  });

  // Email quality filter state
  const [contactTiers, setContactTiers] = useState<any>(null);
  const [tierRefreshing, setTierRefreshing] = useState(false);

  // Sync settings state
  const [syncSettings, setSyncSettings] = useState({
    email: {
      maxEmails: 25,
      daysBack: 7
    },
    calendar: {
      daysBack: 3,
      daysForward: 14
    }
  });
  const [syncSettingsLoading, setSyncSettingsLoading] = useState(false);
  const [syncSettingsSaved, setSyncSettingsSaved] = useState(false);

  // Navigation items
  const navItems = [
    { id: 'dashboard', label: 'Intelligence Dashboard', icon: Brain, count: insights.length },
    { id: 'tasks', label: 'Tasks & Actions', icon: CheckSquare, count: tasks.length },
    { id: 'people', label: 'People & Relationships', icon: Users, count: people.length },
    { id: 'calendar', label: 'Calendar Intelligence', icon: Calendar, count: events.length },
    { id: 'topics', label: 'Topics & Insights', icon: TrendingUp, count: topics.length },
    { id: 'settings', label: 'Settings', icon: Settings, count: 0 }
  ];

  // API Functions with better error handling
  const handleAPIError = (error: Error, operation: string) => {
    console.error(`${operation} failed:`, error);
    setError(`${operation} failed: ${error.message}`);
    setTimeout(() => setError(null), 5000);
  };

  const fetchIntelligenceMetrics = useCallback(async () => {
    try {
      const response = await fetch('/api/intelligence-metrics');
      const data = await response.json();
      if (data.success) {
        setMetrics(data.metrics);
      }
    } catch (error) {
      handleAPIError(error as Error, 'Fetch intelligence metrics');
    }
  }, []);

  const fetchProactiveInsights = useCallback(async () => {
    try {
      const response = await fetch('/api/intelligence-insights?status=new&limit=20');
      const data = await response.json();
      if (data.success) {
        setInsights(data.insights || []);
      }
    } catch (error) {
      handleAPIError(error as Error, 'Fetch insights');
    }
  }, []);

  const fetchTasks = useCallback(async () => {
    try {
      const response = await fetch('/api/tasks?limit=50');
      const data = await response.json();
      if (data.success) {
        setTasks(data.tasks || []);
      }
    } catch (error) {
      handleAPIError(error as Error, 'Fetch tasks');
    }
  }, []);

  const fetchPeople = useCallback(async () => {
    try {
      const response = await fetch('/api/people?limit=50');
      const data = await response.json();
      if (data.success) {
        setPeople(data.people || []);
      }
    } catch (error) {
      handleAPIError(error as Error, 'Fetch people');
    }
  }, []);

  const fetchCalendarEvents = useCallback(async () => {
    try {
      const response = await fetch('/api/calendar/events?days_ahead=14');
      const data = await response.json();
      if (data.success) {
        setEvents(data.events || []);
      }
    } catch (error) {
      handleAPIError(error as Error, 'Fetch calendar events');
    }
  }, []);

  const fetchTopics = useCallback(async () => {
    try {
      const response = await fetch('/api/knowledge/topics/hierarchy');
      const data = await response.json();
      if (data.success) {
        setTopicHierarchy({
          hierarchy: data.hierarchy || [],
          stats: data.stats || {
            total_topics: 0,
            max_depth: 0,
            auto_generated: 0,
            user_created: 0,
            by_type: {},
            recent_activity: 0
          }
        });
        // Update the legacy topics array for compatibility
        setTopics(data.hierarchy || []);
      }
    } catch (error) {
      handleAPIError(error as Error, 'Fetch topic hierarchy');
    }
  }, []);

  // Missing handler functions
  const handleSync = async () => {
    setProcessing(true);
    addNotification('🚀 Starting unified intelligence sync...');
    
    try {
      const response = await fetch('/api/trigger-email-sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          max_emails: syncSettings.email.maxEmails,
          days_back: syncSettings.email.daysBack,
          calendar_days_back: syncSettings.calendar.daysBack,
          calendar_days_forward: syncSettings.calendar.daysForward,
          force_refresh: false
        })
      });
      
      const data = await response.json();
      
      if (data.success) {
        addNotification(`✅ Processed ${data.summary?.emails_fetched || 0} emails and ${data.summary?.calendar_events_fetched || 0} events!`);
        await refreshAllData();
      } else {
        addNotification('❌ Sync failed: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Sync error:', error);
      addNotification('❌ Sync failed: Network error');
    } finally {
      setProcessing(false);
    }
  };

  const createTopic = async () => {
    try {
      const response = await fetch('/api/topics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newTopic)
      });
      
      const data = await response.json();
      if (data.success) {
        addNotification('✅ Topic created successfully');
        setShowCreateTopic(false);
        setNewTopic({ name: '', description: '', keywords: '', is_official: false });
        await fetchTopics();
      } else {
        addNotification('❌ Failed to create topic');
      }
    } catch (error) {
      handleAPIError(error as Error, 'Create topic');
    }
  };

  // Enhanced email sync with progress tracking
  const runEmailSyncWithProgress = async () => {
    setEmailSyncProgress(0);
    setEmailSyncStatus('Initializing sync...');
    setSyncProgress(true);
    
    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setEmailSyncProgress(prev => {
          if (prev < 90) return prev + 10;
          return prev;
        });
      }, 500);

      // Add safety checks for syncSettings to prevent undefined access
      const safeMaxEmails = syncSettings?.email?.maxEmails || 25;
      const safeDaysBack = syncSettings?.email?.daysBack || 7;
      const safeCalendarDaysBack = syncSettings?.calendar?.daysBack || 3;
      const safeCalendarDaysForward = syncSettings?.calendar?.daysForward || 14;

      const response = await fetch('/api/trigger-email-sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          max_emails: safeMaxEmails,
          days_back: safeDaysBack,
          calendar_days_back: safeCalendarDaysBack,
          calendar_days_forward: safeCalendarDaysForward,
          force_refresh: false
        })
      });
      
      const data = await response.json();
      clearInterval(progressInterval);
      
      if (data.success) {
        setEmailSyncProgress(100);
        setEmailSyncStatus(`✅ Processed ${data.summary?.emails_fetched || 0} emails and ${data.summary?.calendar_events_fetched || 0} events!`);
        addNotification(`✅ Email sync completed: ${data.summary?.emails_fetched || 0} emails processed`);
        
        // Update integration status
        setIntegrationStatus(prev => ({
          ...prev,
          gmail: { ...prev.gmail, lastSync: new Date().toISOString() },
          calendar: { ...prev.calendar, lastSync: new Date().toISOString() }
        }));
        
        await refreshAllData();
      } else {
        setEmailSyncProgress(0);
        setEmailSyncStatus('❌ Sync failed: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      setEmailSyncProgress(0);
      setEmailSyncStatus('❌ Sync failed: Network error');
      handleAPIError(error as Error, 'Email sync');
    } finally {
      setSyncProgress(false);
      setTimeout(() => {
        setEmailSyncStatus(null);
        setEmailSyncProgress(0);
      }, 5000);
    }
  };

  // Database flush functionality
  const flushDatabase = async () => {
    setProcessing(true);
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
        
        // Reset all state
        setMetrics(null);
        setInsights([]);
        setTasks([]);
        setPeople([]);
        setEvents([]);
        setTopics([]);
        setTopicHierarchy(null);
      } else {
        addNotification('❌ Database flush failed: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      handleAPIError(error as Error, 'Database flush');
    } finally {
      setProcessing(false);
    }
  };

  // Email quality filter functions
  const fetchContactTiers = async () => {
    try {
      const response = await fetch('/api/email-quality/contact-tiers');
      const data = await response.json();
      
      if (data.success) {
        setContactTiers(data.tier_summary);
      } else {
        addNotification('❌ Failed to fetch contact tiers: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Contact tiers fetch error:', error);
      addNotification('❌ Failed to fetch contact tiers');
    }
  };

  const refreshContactTiers = async () => {
    setTierRefreshing(true);
    addNotification('🔄 Refreshing contact tiers...');
    
    try {
      const response = await fetch('/api/email-quality/refresh-tiers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const data = await response.json();
      
      if (data.success) {
        addNotification(`✅ Updated ${data.contacts_analyzed} contact tiers`);
        await fetchContactTiers(); // Reload the tiers
      } else {
        addNotification('❌ Failed to refresh contact tiers');
      }
    } catch (error) {
      console.error('Refresh contact tiers error:', error);
      addNotification('❌ Failed to refresh contact tiers');
    } finally {
      setTierRefreshing(false);
    }
  };

  const cleanupLowQualityData = async () => {
    if (!confirm(
      "⚠️ This will remove emails, tasks, and insights from Tier LAST contacts (people you consistently ignore). " +
      "This action cannot be undone. Are you sure you want to proceed?"
    )) {
      return;
    }
    
    setTierRefreshing(true);
    addNotification('🧹 Cleaning up low-quality data...');
    
    try {
      const response = await fetch('/api/email-quality/cleanup-existing', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const data = await response.json();
      
      if (data.success) {
        const stats = data.stats || {};
        addNotification(
          `✅ Cleanup complete! Removed ${stats.emails_removed || 0} emails and ` +
          `${stats.tasks_removed || 0} tasks from ${stats.tier_last_contacts || 0} low-quality contacts`
        );
        await Promise.all([
          fetchContactTiers(),
          refreshAllData() // Refresh all data to show clean results
        ]);
      } else {
        addNotification('❌ Cleanup failed: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Cleanup error:', error);
      addNotification('❌ Cleanup failed: Network error');
    } finally {
      setTierRefreshing(false);
    }
  };

  // Sync settings functions
  const loadSyncSettings = async () => {
    try {
      const response = await fetch('/api/sync-settings');
      const data = await response.json();
      
      if (data.success) {
        // Handle the nested structure returned by the API
        const settings = {
          email: {
            maxEmails: data.email?.maxEmails || data.maxEmails || 25,
            daysBack: data.email?.daysBack || data.emailDaysBack || 7
          },
          calendar: {
            daysBack: data.calendar?.daysBack || data.calendarDaysBack || 3,
            daysForward: data.calendar?.daysForward || data.calendarDaysForward || 14
          }
        };
        setSyncSettings(settings);
      }
    } catch (error) {
      console.error('Failed to load sync settings:', error);
      // Keep the default settings if loading fails
    }
  };

  const saveSyncSettings = async () => {
    setSyncSettingsLoading(true);
    try {
      const response = await fetch('/api/sync-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(syncSettings)
      });
      
      const data = await response.json();
      
      if (data.success) {
        addNotification('✅ Sync settings saved successfully!');
        setSyncSettingsSaved(true);
        setTimeout(() => setSyncSettingsSaved(false), 2000);
      } else {
        addNotification('❌ Failed to save sync settings: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      handleAPIError(error as Error, 'Save sync settings');
    } finally {
      setSyncSettingsLoading(false);
    }
  };

  const updateSyncSetting = (category: 'email' | 'calendar', key: string, value: number) => {
    setSyncSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value
      }
    }));
  };

  // Missing utility functions
  const addNotification = (message: string) => {
    setNotifications(prev => [...prev, message]);
    setTimeout(() => {
      setNotifications(prev => prev.slice(1));
    }, 5000);
  };

  // Logout function
  const handleLogout = async () => {
    console.log('🚪 Logout button clicked');
    
    try {
      // Add a notification before logout
      addNotification('🚪 Logging out...');
      
      // Redirect to Flask logout, which will clear session and redirect to login
      console.log('Redirecting to Flask logout...');
      window.location.href = 'http://localhost:8080/logout';
      
    } catch (error) {
      console.error('Logout error:', error);
      addNotification('❌ Logout failed, trying direct redirect...');
      
      // Fallback: direct redirect to Flask login
      setTimeout(() => {
        window.location.href = 'http://localhost:8080/login';
      }, 1000);
    }
  };

  const refreshAllData = async () => {
    await Promise.all([
      fetchIntelligenceMetrics(),
      fetchProactiveInsights(),
      fetchTasks(),
      fetchPeople(),
      fetchCalendarEvents(),
      fetchTopics()
    ]);
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'border-red-500 bg-red-500/10 text-red-300';
      case 'medium': return 'border-yellow-500 bg-yellow-500/10 text-yellow-300';
      case 'low': return 'border-green-500 bg-green-500/10 text-green-300';
      default: return 'border-gray-500 bg-gray-500/10 text-gray-300';
    }
  };

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.round(diffMs / 60000);
    const diffHours = Math.round(diffMs / 3600000);
    const diffDays = Math.round(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  // Enhanced topic functions
  const buildTopicsFromEmails = async () => {
    setBuildingTopicsFromEmails(true);
    addNotification('🧠 Building knowledge foundation from your emails...');
    
    try {
      const response = await fetch('/api/knowledge/foundation/build-from-bulk-emails', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ months_back: 6 })
      });
      
      const data = await response.json();
      
      if (data.success) {
        const stats = data.foundation_stats;
        addNotification(
          `✅ Built knowledge foundation! Created ${stats.topics_created} topics from ${stats.emails_analyzed} emails ` +
          `(${stats.business_areas} business areas, ${stats.projects} projects)`
        );
        await fetchTopics();
      } else {
        addNotification('❌ Failed to build knowledge foundation: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      console.error('Build topics from emails error:', error);
      addNotification('❌ Failed to build topics from emails');
    } finally {
      setBuildingTopicsFromEmails(false);
    }
  };

  const viewTopicDetails = async (topic: Topic) => {
    setSelectedTopic(topic);
    setShowTopicDetails(true);
    
    // Fetch traceability data
    try {
      const response = await fetch(`/api/knowledge/traceability/topic/${topic.id}`);
      const data = await response.json();
      
      if (data.success) {
        setTopicTraceability(data.sources || []);
      }
    } catch (error) {
      console.error('Error fetching topic traceability:', error);
    }
  };

  const toggleTopicExpansion = (topicId: number) => {
    setExpandedTopics(prev => {
      const newSet = new Set(prev);
      if (newSet.has(topicId)) {
        newSet.delete(topicId);
      } else {
        newSet.add(topicId);
      }
      return newSet;
    });
  };

  const renderTopicHierarchy = (topics: Topic[], depth: number = 0): React.ReactNode => {
    return topics.map(topic => (
      <div key={topic.id} className={`${depth > 0 ? 'ml-4' : ''}`}>
        <div className="flex items-center gap-2 p-2 hover:bg-gray-700/50 rounded transition-colors">
          {topic.children && topic.children.length > 0 && (
            <button
              onClick={() => toggleTopicExpansion(topic.id)}
              className="text-gray-400 hover:text-white"
            >
              {expandedTopics.has(topic.id) ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>
          )}
          <div 
            className="flex-1 cursor-pointer"
            onClick={() => viewTopicDetails(topic)}
          >
            <span className="text-white text-sm">{topic.name}</span>
            <span className="text-xs text-gray-400 ml-2">
              ({topic.topic_type}, {topic.mention_count} mentions)
            </span>
          </div>
        </div>
        {topic.children && topic.children.length > 0 && expandedTopics.has(topic.id) && (
          <div className="ml-2">
            {renderTopicHierarchy(topic.children, depth + 1)}
          </div>
        )}
      </div>
    ));
  };

  // Streamlined workflow state
  const [workflowStep, setWorkflowStep] = useState(0);
  const [workflowResults, setWorkflowResults] = useState<any[]>([]);
  const [showWorkflowModal, setShowWorkflowModal] = useState(false);
  const [currentStepResult, setCurrentStepResult] = useState<any>(null);
  const [emailsToIngest, setEmailsToIngest] = useState(50);
  const [processingStep, setProcessingStep] = useState<number | null>(null); // Track which step is processing

  // Streamlined workflow steps
  const workflowSteps = [
    {
        title: '1. Build People Filtering System',
        description: 'Analyze your sent email patterns to categorize contacts by engagement level',
        action: 'Fetch Sent Emails & Build Contact Rules',
        icon: '👥'
    },
    {
        title: '2. Import Calendar Intelligence',
        description: 'Fetch calendar events and add all meeting participants to Tier 1',
        action: 'Import Calendar & Add Participants',
        icon: '📅'
    },
    {
        title: '3. Fetch All Emails & Build Knowledge Base',
        description: 'Pull all emails and create comprehensive topic hierarchy and business knowledge',
        action: 'Fetch All Emails & Create Topics',
        icon: '📧'
    },
    {
        title: '4. Re-organize Content by Topics',
        description: 'Now that topics exist, properly categorize all emails and content',
        action: 'Organize Content by Topics',
        icon: '🗂️'
    },
    {
        title: '5. Augment Smart Contacts',
        description: 'Enhance people profiles with extracted knowledge and relationships',
        action: 'Smart Contact Enhancement',
        icon: '⚡'
    },
    {
        title: '6. Enhance Calendar Intelligence',
        description: 'Add business context and preparation insights to calendar events',
        action: 'Enhance Calendar Events',
        icon: '📅'
    }
];

  const executeWorkflowStep = async (stepIndex: number) => {
    setWorkflowStep(stepIndex);
    setCurrentStepResult(null);
    setProcessingStep(stepIndex);

    try {
        switch (stepIndex) {
            case 0: // Build People Filtering
                await executeStep1();
                break;
            case 1: // Import Calendar & Add Participants
                await executeStep2();
                break;
            case 2: // Ingest 6 months emails
                await executeStep3();
                break;
            case 3: // Extract knowledge
                await executeStep4();
                break;
            case 4: // Smart contacts
                await executeStep5();
                break;
            case 5: // Organize topics
                await executeStep6();
                break;
        }
    } catch (error) {
        setCurrentStepResult({
            success: false,
            error: `Step ${stepIndex + 1} failed: ${error}`
        });
        setShowWorkflowModal(true);
        setProcessingStep(null);
    }
};

  const executeStep1 = async () => {
    try {
        addNotification('👥 Extracting contacts from sent emails...');
        
        // Only fetch sent email metadata (no AI processing)
        const emailSyncResponse = await fetch('/api/extract-sent-contacts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                days_back: 180, // 6 months for good pattern analysis
                metadata_only: true, // Only get recipients, dates, subjects - no AI processing
                sent_only: true
            })
        });
        
        const contactData = await emailSyncResponse.json();
        
        if (contactData.success) {
            addNotification(`📧 Analyzed ${contactData.emails_analyzed || 0} sent emails`);
            
            // Now build contact tier rules from the extracted patterns
            addNotification('🧠 Building contact engagement tier rules...');
            
            const tierResponse = await fetch('/api/email-quality/build-tier-rules', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contact_patterns: contactData.contact_patterns,
                    build_rules_only: true // Don't process any emails yet
                })
            });
            
            const tierData = await tierResponse.json();
            
            if (tierData.success) {
                setCurrentStepResult({
                    success: true,
                    title: 'Contact Filtering Rules Built',
                    data: {
                        emails_analyzed: contactData.emails_analyzed || 0,
                        unique_contacts: contactData.unique_contacts || 0,
                        tier_1_contacts: tierData.rules?.tier_1_count || 0,
                        tier_last_contacts: tierData.rules?.tier_last_count || 0,
                        rules_created: true,
                        next_step: 'Ready to fetch calendar events and add participants to Tier 1'
                    }
                });
                setShowWorkflowModal(true);
                addNotification('✅ Step 1 completed: Contact tier filtering rules created!');
                setProcessingStep(null);
            } else {
                addNotification(`❌ Failed to build tier rules: ${tierData.error || 'Unknown error'}`);
                setProcessingStep(null);
            }
        } else {
            addNotification(`❌ Failed to extract sent contacts: ${contactData.error || 'Unknown error'}`);
            setProcessingStep(null);
        }
    } catch (error) {
        console.error('Step 1 error:', error);
        addNotification(`❌ Step 1 failed: ${error instanceof Error ? error.message : String(error)}`);
        setProcessingStep(null);
    }
};

  // Add new calendar import step
  const executeStep2 = async () => {
    try {
        addNotification('📅 Fetching calendar events and participants...');
        
        // Fetch calendar events and add participants to Tier 1
        const calendarResponse = await fetch('/api/calendar/import-and-tier', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                days_back: 180,  // 6 months history
                days_forward: 90,  // 3 months future
                add_participants_tier_1: true
            })
        });
        
        const calendarData = await calendarResponse.json();
        
        if (calendarData.success) {
            addNotification(`📅 Imported ${calendarData.events_imported} calendar events`);
            
            setCurrentStepResult({
                success: true,
                title: 'Calendar Events Imported & Participants Added',
                data: {
                    events_imported: calendarData.events_imported || 0,
                    participants_added: calendarData.participants_added || 0,
                    tier_1_contacts: calendarData.tier_1_contacts || 0,
                    days_analyzed: 180,
                    days_future: 90,
                    next_step: 'Ready to fetch and analyze all emails'
                }
            });
            setShowWorkflowModal(true);
            addNotification('✅ Step 2 completed: Calendar imported and participants added to Tier 1!');
            setProcessingStep(null);
        } else {
            addNotification(`❌ Calendar import failed: ${calendarData.error || 'Unknown error'}`);
            setProcessingStep(null);
        }
    } catch (error) {
        console.error('Step 2 error:', error);
        addNotification(`❌ Step 2 failed: ${error instanceof Error ? error.message : String(error)}`);
        setProcessingStep(null);
    }
};

  // Rename existing steps
  const executeStep3 = async () => {
    try {
      addNotification('📧 Fetching all emails and filtering by contact tier rules...');
      
      // Fetch all emails but use tier filtering to only process quality contacts
      const emailSyncResponse = await fetch('/api/trigger-email-sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          max_emails: emailsToIngest || 200,
          days_back: 180, // 6 months for comprehensive analysis
          use_tier_filtering: true, // Use the rules from Step 1
          only_process_tier_1_and_2: true, // Only run AI on quality contacts
          force_refresh: true,
          create_claude_analysis: true
        })
      });
      
      const emailData = await emailSyncResponse.json();
      
      if (emailData.success) {
        addNotification(`📧 Fetched ${emailData.summary?.emails_fetched || 0} emails, processed ${emailData.summary?.quality_emails_processed || 0} through AI`);
        
        // Now build the knowledge foundation and topic hierarchy from the filtered content
        addNotification('🧠 Building knowledge foundation and topic hierarchy from quality emails...');
        
        const knowledgeResponse = await fetch('/api/knowledge/foundation/build-from-bulk-emails', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            months_back: 6,
            use_tier_filtered_emails: true // Only use emails from quality contacts
          })
        });
        
        const knowledgeData = await knowledgeResponse.json();
        
        if (knowledgeData.success) {
          setCurrentStepResult({
            success: true,
            title: 'Knowledge Base & Topics Created from Quality Contacts',
            data: {
              total_emails_fetched: emailData.summary?.emails_fetched || 0,
              quality_emails_processed: emailData.summary?.quality_emails_processed || 0,
              filtered_out_emails: (emailData.summary?.emails_fetched || 0) - (emailData.summary?.quality_emails_processed || 0),
              topics_created: knowledgeData.foundation_stats?.topics_created || 0,
              business_areas: knowledgeData.foundation_stats?.business_areas || 0,
              projects: knowledgeData.foundation_stats?.projects || 0,
              next_step: 'Ready to re-organize all content into the topic hierarchy'
            }
          });
          setShowWorkflowModal(true);
          addNotification('✅ Step 2 completed: Knowledge base built from quality contacts only!');
          setProcessingStep(null);
        } else {
          addNotification(`❌ Knowledge building failed: ${knowledgeData.error || 'Unknown error'}`);
          setProcessingStep(null);
        }
      } else {
        addNotification(`❌ Failed to fetch and filter emails: ${emailData.error || 'Unknown error'}`);
        setProcessingStep(null);
      }
    } catch (error) {
      console.error('Step 2 error:', error);
      addNotification(`❌ Step 2 failed: ${error instanceof Error ? error.message : String(error)}`);
      setProcessingStep(null);
    }
  };

  const executeStep4 = async () => {
    try {
      addNotification('🗂️ Re-organizing all content into topic hierarchy...');
      
      // Re-process emails to properly categorize them into the now-existing topics
      const reorganizeResponse = await fetch('/api/knowledge/reorganize-content', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          reprocess_emails: true,
          reprocess_tasks: true,
          update_relationships: true
        })
      });
      
      const data = await reorganizeResponse.json();
      
      if (data.success) {
        setCurrentStepResult({
          success: true,
          title: 'Content Organized by Topics',
          data: {
            emails_categorized: data.stats?.emails_categorized || 0,
            tasks_categorized: data.stats?.tasks_categorized || 0,
            relationships_updated: data.stats?.relationships_updated || 0,
            topics_populated: data.stats?.topics_populated || 0,
            next_step: 'Ready to enhance contact profiles with knowledge'
          }
        });
        setShowWorkflowModal(true);
        addNotification('✅ Step 3 completed: All content organized into topic hierarchy!');
        setProcessingStep(null);
      } else {
        addNotification(`❌ Content organization failed: ${data.error || 'Unknown error'}`);
        setProcessingStep(null);
      }
    } catch (error) {
      console.error('Step 3 error:', error);
      addNotification(`❌ Step 3 failed: ${error instanceof Error ? error.message : String(error)}`);
      setProcessingStep(null);
    }
  };

  const executeStep5 = async () => {
    try {
      addNotification('⚡ Enhancing contact profiles with knowledge and relationships...');
      
      // Smart contact enhancement with the knowledge base
      const enhanceResponse = await fetch('/api/people/enhance-with-knowledge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          enhance_profiles: true,
          build_relationships: true,
          add_business_context: true,
          calculate_engagement: true
        })
      });
      
      const data = await enhanceResponse.json();
      
      if (data.success) {
        setCurrentStepResult({
          success: true,
          title: 'Smart Contact Enhancement Complete',
          data: {
            people_enhanced: data.stats?.people_enhanced || 0,
            relationships_created: data.stats?.relationships_created || 0,
            business_contexts_added: data.stats?.business_contexts_added || 0,
            engagement_scores_calculated: data.stats?.engagement_scores_calculated || 0,
            next_step: 'Ready to enhance calendar with business intelligence'
          }
        });
        setShowWorkflowModal(true);
        addNotification('✅ Step 4 completed: Contact profiles enhanced with knowledge!');
        setProcessingStep(null);
      } else {
        addNotification(`❌ Contact enhancement failed: ${data.error || 'Unknown error'}`);
        setProcessingStep(null);
      }
    } catch (error) {
      console.error('Step 4 error:', error);
      addNotification(`❌ Step 4 failed: ${error instanceof Error ? error.message : String(error)}`);
      setProcessingStep(null);
    }
  };

  const executeStep6 = async () => {
    try {
      addNotification('📅 Enhancing calendar events with business intelligence...');
      
      // Enhance calendar with business context and preparation insights
      const calendarResponse = await fetch('/api/calendar/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          days_back: 30,
          days_forward: 30
        })
      });
      
      const data = await calendarResponse.json();
      
      if (data.success) {
        setCurrentStepResult({
          success: true,
          title: 'Calendar Intelligence Complete',
          data: {
            events_enhanced: data.events_fetched || 0,
            attendee_intelligence_added: data.participants_added || 0,
            preparation_tasks_generated: 0,
            business_contexts_added: data.events_fetched || 0,
            next_step: 'Your AI Chief of Staff knowledge system is now complete!'
          }
        });
        setShowWorkflowModal(true);
        addNotification('✅ Step 6 completed: Your AI Chief of Staff is fully operational!');
        setProcessingStep(null);
      } else {
        addNotification(`❌ Calendar enhancement failed: ${data.error || 'Unknown error'}`);
        setProcessingStep(null);
      }
    } catch (error) {
      console.error('Step 6 error:', error);
      addNotification(`❌ Step 6 failed: ${error instanceof Error ? error.message : String(error)}`);
      setProcessingStep(null);
    }
  };

  const renderListView = () => {
    switch (currentView) {
      case 'dashboard':
        return (
          <div>
            <IntelligenceMetricsCard />
            <ProactiveInsightsPanel />
            <EntityNetworkPanel />
            <IntelligenceChatPanel />
          </div>
        );
      
      case 'tasks':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-semibold text-white">📋 Tasks & Actions</h3>
              <span className="text-sm text-gray-400">{tasks.length} tasks</span>
            </div>
            <div className="space-y-3">
              {tasks.map(task => (
                <div
                  key={task.id}
                  onClick={() => openEntityDetail('task', task.id, task)}
                  className={clsx(
                    'bg-gray-800 rounded-lg border p-4 cursor-pointer hover:bg-gray-750 transition-all',
                    getPriorityColor(task.priority)
                  )}
                >
                  <h4 className="text-white font-medium">{task.description}</h4>
                  <div className="flex items-center gap-2 mt-2">
                    <span className={clsx('text-xs px-2 py-1 rounded-full', getPriorityColor(task.priority))}>
                      {task.priority.toUpperCase()}
                    </span>
                    <span className="text-xs text-gray-400">{task.status}</span>
                    <Eye className="w-3 h-3 text-gray-400 ml-auto" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      
      case 'people':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-semibold text-white">👥 People & Relationships</h3>
              <span className="text-sm text-gray-400">{people.length} contacts</span>
            </div>
            <div className="space-y-3">
              {people.map(person => (
                <div
                  key={person.id}
                  onClick={() => openEntityDetail('person', person.id, person)}
                  className="bg-gray-800 rounded-lg border border-gray-700 p-4 cursor-pointer hover:bg-gray-750 transition-all"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
                      {person.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1">
                      <h4 className="text-white font-medium">{person.name}</h4>
                      <p className="text-sm text-gray-400">{person.company || 'Unknown company'}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-sm text-gray-300">{person.total_emails} emails</div>
                      <div className="text-xs text-yellow-400">
                        {Math.round(person.engagement_score * 100)}% engagement
                      </div>
                    </div>
                    <Eye className="w-4 h-4 text-gray-400" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      
      case 'calendar':
        return (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-xl font-semibold text-white">📅 Calendar Intelligence</h3>
              <span className="text-sm text-gray-400">{events.length} upcoming events</span>
            </div>
            <div className="space-y-3">
              {events.map(event => (
                <div
                  key={event.id}
                  onClick={() => openEntityDetail('calendar', parseInt(event.id), event)}
                  className="bg-gray-800 rounded-lg border border-gray-700 p-4 hover:bg-gray-750 transition-all cursor-pointer"
                >
                  <div className="flex items-center justify-between">
                    <h4 className="text-white font-medium">{event.title}</h4>
                    <Eye className="w-4 h-4 text-gray-400" />
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-sm text-gray-400">
                    <span>📍 {event.location || 'No location'}</span>
                    <span>👥 {event.attendee_count} attendees</span>
                    <span>⭐ {Math.round(event.strategic_importance * 100)}% strategic</span>
                  </div>
                  {event.preparation_needed && (
                    <div className="mt-2 text-xs bg-yellow-900/30 text-yellow-300 px-2 py-1 rounded">
                      Preparation needed
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        );
      
      case 'topics':
        return (
          <div className="space-y-6">
            {/* Simplified topics view - removed action buttons */}
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-semibold text-white flex items-center gap-2">
                  🧠 Knowledge Base Topics
                </h3>
                <p className="text-gray-400 text-sm mt-1">
                  View your topic hierarchy. Use Settings to build or modify the knowledge base.
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setTopicView(topicView === 'hierarchy' ? 'list' : 'hierarchy')}
                  className="px-3 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors text-sm"
                >
                  {topicView === 'hierarchy' ? 'List View' : 'Tree View'}
                </button>
              </div>
            </div>

            {/* Statistics Panel */}
            {topicHierarchy?.stats && (
              <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                <h4 className="text-white font-medium mb-3">Knowledge Base Statistics</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                  <div className="text-center">
                    <div className="text-lg font-bold text-blue-400">{topicHierarchy.stats.total_topics}</div>
                    <div className="text-xs text-gray-400">Total Topics</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-purple-400">{topicHierarchy.stats.max_depth}</div>
                    <div className="text-xs text-gray-400">Max Depth</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-green-400">{topicHierarchy.stats.user_created}</div>
                    <div className="text-xs text-gray-400">User Created</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-blue-400">{topicHierarchy.stats.auto_generated}</div>
                    <div className="text-xs text-gray-400">AI Generated</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-yellow-400">{topicHierarchy.stats.recent_activity}</div>
                    <div className="text-xs text-gray-400">Recent Activity</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-indigo-400">
                      {Object.keys(topicHierarchy.stats.by_type).length}
                    </div>
                    <div className="text-xs text-gray-400">Categories</div>
                  </div>
                </div>
                
                {/* Topic Types Breakdown */}
                {Object.keys(topicHierarchy.stats.by_type).length > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-700">
                    <h5 className="text-sm text-gray-300 mb-2">By Type:</h5>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(topicHierarchy.stats.by_type).map(([type, count]) => (
                        <span 
                          key={type}
                          className="text-xs bg-gray-700 text-gray-300 px-2 py-1 rounded"
                        >
                          {type}: {count}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Topic Display */}
            {topicHierarchy ? (
              topicView === 'hierarchy' ? (
                <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
                  <h4 className="text-white font-medium mb-4 flex items-center gap-2">
                    <Network className="w-5 h-5" />
                    Topic Hierarchy Tree
                  </h4>
                  {topicHierarchy.hierarchy.length > 0 ? (
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {renderTopicHierarchy(topicHierarchy.hierarchy)}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <div className="text-gray-400 mb-4">
                        <Network className="w-12 h-12 mx-auto mb-2 opacity-50" />
                        No topics found
                      </div>
                      <p className="text-gray-400 mb-4">
                        Build your knowledge base in Settings using the 5-step workflow.
                      </p>
                      <button
                        onClick={() => setCurrentView('settings')}
                        className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                      >
                        Go to Settings
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {(topicHierarchy.hierarchy || []).map(topic => (
                    <div
                      key={topic.id}
                      onClick={() => openEntityDetail('topic', topic.id, topic)}
                      className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-lg p-4 hover:bg-blue-500/20 transition-colors cursor-pointer"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-white font-medium">{topic.name}</h4>
                        <Eye className="w-4 h-4 text-gray-400" />
                      </div>
                      {topic.description && (
                        <p className="text-sm text-gray-400 mb-3">{topic.description}</p>
                      )}
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-400">{topic.mention_count || 0} mentions</span>
                        {topic.user_created && (
                          <span className="text-xs bg-green-600 text-white px-2 py-1 rounded">User Created</span>
                        )}
                        {topic.auto_generated && !topic.user_created && (
                          <span className="text-xs bg-blue-600 text-white px-2 py-1 rounded">AI Generated</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )
            ) : (
              <div className="text-center py-8">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-4 text-gray-400" />
                <p className="text-gray-400">Loading topic hierarchy...</p>
              </div>
            )}

            {/* Topic Details Modal */}
            {showTopicDetails && selectedTopic && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                <div className="bg-gray-800 rounded-lg border border-gray-700 max-w-4xl w-full max-h-[90vh] overflow-y-auto">
                  <div className="p-6">
                    <div className="flex items-center justify-between mb-6">
                      <div>
                        <h3 className="text-xl font-bold text-white">{selectedTopic.name}</h3>
                        <p className="text-gray-400">Topic Details & Traceability</p>
                      </div>
                      <button
                        onClick={() => setShowTopicDetails(false)}
                        className="text-gray-400 hover:text-white"
                      >
                        <X className="w-6 h-6" />
                      </button>
                    </div>

                    <div className="space-y-6">
                      {/* Topic Information */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                          <h4 className="text-white font-medium mb-3">Topic Information</h4>
                          <div className="space-y-2 text-sm">
                            <div className="flex justify-between">
                              <span className="text-gray-400">Type:</span>
                              <span className="text-white capitalize">{selectedTopic.topic_type}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Hierarchy Path:</span>
                              <span className="text-white">{selectedTopic.hierarchy_path}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Mentions:</span>
                              <span className="text-white">{selectedTopic.mention_count}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Confidence:</span>
                              <span className="text-white">{Math.round(selectedTopic.confidence_score * 100)}%</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Priority:</span>
                              <span className={`capitalize ${
                                selectedTopic.priority === 'high' ? 'text-red-400' :
                                selectedTopic.priority === 'medium' ? 'text-yellow-400' :
                                'text-gray-400'
                              }`}>
                                {selectedTopic.priority}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-gray-400">Source:</span>
                              <span className="text-white">
                                {selectedTopic.user_created ? 'User Created' : 'AI Generated'}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div>
                          <h4 className="text-white font-medium mb-3">Description</h4>
                          <p className="text-gray-300 text-sm">
                            {selectedTopic.description || 'No description available'}
                          </p>
                        </div>
                      </div>

                      {/* Source Traceability */}
                      {topicTraceability && topicTraceability.length > 0 && (
                        <div>
                          <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                            <FileText className="w-4 h-4" />
                            Source Traceability ({topicTraceability.length} sources)
                          </h4>
                          <div className="space-y-2 max-h-64 overflow-y-auto">
                            {topicTraceability.map((source: any, index: number) => (
                              <div key={index} className="p-3 bg-gray-700/50 rounded-lg">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="text-xs font-medium text-blue-400 uppercase">
                                    {source.source_type}
                                  </span>
                                  <span className="text-xs text-gray-400">
                                    {source.confidence}% confidence
                                  </span>
                                </div>
                                <p className="text-sm text-gray-300">{source.snippet}</p>
                                {source.can_access_full && (
                                  <button className="text-xs text-blue-400 hover:text-blue-300 mt-2">
                                    View full content →
                                  </button>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      
      case 'settings':
        return <SettingsPage />;
      
      default:
        return <div>View not implemented</div>;
    }
  };

  // Add knowledge tree aware chat function
  const sendChatMessage = useCallback(async () => {
    if (!chatInput.trim() || chatLoading) return;
    
    const userMessage = chatInput.trim();
    const messageId = Date.now().toString();
    
    // Add user message to chat
    setChatMessages(prev => [...prev, {
      id: messageId,
      sender: 'user',
      message: userMessage,
      timestamp: new Date()
    }]);
    
    setChatInput('');
    setChatLoading(true);
    
    try {
      const response = await fetch('/api/intelligence/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage })
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Add AI response to chat
        setChatMessages(prev => [...prev, {
          id: `ai-${Date.now()}`,
          sender: 'ai',
          message: data.response,
          timestamp: new Date()
        }]);
        
        // Show knowledge context info
        if (data.tree_topics_count || data.tree_people_count) {
          addNotification(`💬 Response generated using ${data.tree_topics_count} topics, ${data.tree_people_count} people, ${data.tree_projects_count} projects from your knowledge tree`);
        }
      } else {
        // Handle knowledge tree requirement error
        if (data.action_required === 'build_knowledge_tree') {
          setChatMessages(prev => [...prev, {
            id: `error-${Date.now()}`,
            sender: 'ai',
            message: `🌳 Knowledge Tree Required!\n\n${data.message}\n\nTo enable AI chat functionality, please:\n1. Go to Settings tab\n2. Complete Step 2: Build Knowledge Tree\n3. Return here to chat with full business intelligence context`,
            timestamp: new Date()
          }]);
          
          addNotification('❌ Knowledge tree required for chat - Complete Step 2 in Settings');
        } else {
          setChatMessages(prev => [...prev, {
            id: `error-${Date.now()}`,
            sender: 'ai',
            message: `❌ Chat Error: ${data.error || 'Unknown error occurred'}`,
            timestamp: new Date()
          }]);
          
          addNotification(`❌ Chat failed: ${data.error || 'Unknown error'}`);
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      setChatMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        sender: 'ai',
        message: '❌ Connection error. Please try again.',
        timestamp: new Date()
      }]);
      addNotification('❌ Chat connection failed');
    } finally {
      setChatLoading(false);
    }
  }, [chatInput, chatLoading]);

  // Entity detail functions
  const getEntityIcon = (entityType: string) => {
    switch (entityType) {
      case 'task': return <CheckSquare className="w-5 h-5" />;
      case 'person': return <Users className="w-5 h-5" />;
      case 'email': return <Mail className="w-5 h-5" />;
      case 'topic': return <TrendingUp className="w-5 h-5" />;
      case 'calendar': return <Calendar className="w-5 h-5" />;
      case 'insight': return <Zap className="w-5 h-5" />;
      default: return <Database className="w-5 h-5" />;
    }
  };

  const renderEntityDetails = (entity: any) => {
    switch (entity.type) {
      case 'task':
        return (
          <div className="space-y-3">
            <div>
              <span className="text-gray-400 text-sm">Description:</span>
              <p className="text-white">{entity.description}</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-gray-400 text-sm">Priority:</span>
                <p className={clsx('font-medium capitalize', 
                  entity.priority === 'high' ? 'text-red-400' :
                  entity.priority === 'medium' ? 'text-yellow-400' : 'text-green-400'
                )}>{entity.priority}</p>
              </div>
              <div>
                <span className="text-gray-400 text-sm">Status:</span>
                <p className="text-white capitalize">{entity.status}</p>
              </div>
            </div>
            {entity.due_date && (
              <div>
                <span className="text-gray-400 text-sm">Due Date:</span>
                <p className="text-white">{new Date(entity.due_date).toLocaleDateString()}</p>
              </div>
            )}
            {entity.confidence && (
              <div>
                <span className="text-gray-400 text-sm">AI Confidence:</span>
                <p className="text-white">{Math.round(entity.confidence * 100)}%</p>
              </div>
            )}
          </div>
        );
      
      case 'person':
        return (
          <div className="space-y-3">
            <div>
              <span className="text-gray-400 text-sm">Name:</span>
              <p className="text-white font-medium">{entity.name}</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-gray-400 text-sm">Email:</span>
                <p className="text-white text-sm">{entity.email || entity.email_address}</p>
              </div>
              <div>
                <span className="text-gray-400 text-sm">Company:</span>
                <p className="text-white">{entity.company || 'Not specified'}</p>
              </div>
            </div>
            {entity.title && (
              <div>
                <span className="text-gray-400 text-sm">Title:</span>
                <p className="text-white">{entity.title}</p>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-gray-400 text-sm">Total Emails:</span>
                <p className="text-white">{entity.total_emails || 0}</p>
              </div>
              <div>
                <span className="text-gray-400 text-sm">Engagement:</span>
                <p className="text-white">{Math.round((entity.engagement_score || 0) * 100)}%</p>
              </div>
            </div>
          </div>
        );
      
      case 'topic':
        return (
          <div className="space-y-3">
            <div>
              <span className="text-gray-400 text-sm">Topic Name:</span>
              <p className="text-white font-medium">{entity.name}</p>
            </div>
            {entity.description && (
              <div>
                <span className="text-gray-400 text-sm">Description:</span>
                <p className="text-white">{entity.description}</p>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-gray-400 text-sm">Type:</span>
                <p className="text-white capitalize">{entity.topic_type}</p>
              </div>
              <div>
                <span className="text-gray-400 text-sm">Mentions:</span>
                <p className="text-white">{entity.mention_count || 0}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-gray-400 text-sm">Confidence:</span>
                <p className="text-white">{Math.round((entity.confidence_score || 0) * 100)}%</p>
              </div>
              <div>
                <span className="text-gray-400 text-sm">Source:</span>
                <p className="text-white">{entity.user_created ? 'User Created' : 'AI Generated'}</p>
              </div>
            </div>
          </div>
        );
      
      case 'email':
        return (
          <div className="space-y-3">
            <div>
              <span className="text-gray-400 text-sm">Subject:</span>
              <p className="text-white font-medium">{entity.subject}</p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-gray-400 text-sm">From:</span>
                <p className="text-white text-sm">{entity.sender}</p>
              </div>
              <div>
                <span className="text-gray-400 text-sm">Date:</span>
                <p className="text-white">{entity.date_sent ? new Date(entity.date_sent).toLocaleDateString() : 'Unknown'}</p>
              </div>
            </div>
            {entity.recipients && (
              <div>
                <span className="text-gray-400 text-sm">To:</span>
                <p className="text-white text-sm">{entity.recipients}</p>
              </div>
            )}
            {entity.ai_summary && (
              <div>
                <span className="text-gray-400 text-sm">AI Summary:</span>
                <p className="text-white bg-blue-900/20 rounded p-2 text-sm">{entity.ai_summary}</p>
              </div>
            )}
          </div>
        );
      
      default:
        return (
          <div className="space-y-2">
            {Object.entries(entity).map(([key, value]) => {
              if (key === 'type' || key === 'id') return null;
              return (
                <div key={key}>
                  <span className="text-gray-400 text-sm capitalize">{key.replace(/_/g, ' ')}:</span>
                  <p className="text-white">{String(value)}</p>
                </div>
              );
            })}
          </div>
        );
    }
  };

  const openEntityDetail = async (entityType: string, entityId: number, entityData: any) => {
    setSelectedEntityDetail({
      type: entityType,
      id: entityId,
      title: entityData.name || entityData.description || entityData.subject || entityData.title || `${entityType} #${entityId}`,
      ...entityData
    });
    setShowEntityDetail(true);
    setLoadingEntityContext(true);
    setEntityContext(null);
    setRawSources([]);

    try {
      // Fetch detailed context
      const contextResponse = await fetch(`/api/intelligence/entity/${entityType}/${entityId}/context`);
      const contextData = await contextResponse.json();
      
      if (contextData.success) {
        setEntityContext(contextData.context);
      }

      // Fetch raw sources
      const sourcesResponse = await fetch(`/api/intelligence/entity/${entityType}/${entityId}/raw-sources`);
      const sourcesData = await sourcesResponse.json();
      
      if (sourcesData.success) {
        setRawSources(sourcesData.raw_sources);
      }
    } catch (error) {
      console.error('Error fetching entity context:', error);
      addNotification('❌ Failed to load entity details');
    } finally {
      setLoadingEntityContext(false);
    }
  };

  // Intelligence metrics component
  const IntelligenceMetricsCard = () => (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 mb-6">
      <h3 className="text-white font-semibold mb-4">📊 Intelligence Overview</h3>
      {metrics ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-400">{metrics.total_entities}</div>
            <div className="text-xs text-gray-400">Total Entities</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400">{metrics.topics}</div>
            <div className="text-xs text-gray-400">Topics</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-400">{metrics.people}</div>
            <div className="text-xs text-gray-400">People</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-400">{metrics.tasks}</div>
            <div className="text-xs text-gray-400">Tasks</div>
          </div>
        </div>
      ) : (
        <div className="text-center text-gray-400">Loading metrics...</div>
      )}
    </div>
  );

  // Proactive insights component
  const ProactiveInsightsPanel = () => (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 mb-6">
      <h3 className="text-white font-semibold mb-4">⚡ Proactive Insights</h3>
      <div className="space-y-3 max-h-64 overflow-y-auto">
        {insights.length === 0 ? (
          <div className="text-gray-400 text-sm text-center py-4">
            No insights available yet. Complete the setup workflow to generate insights.
          </div>
        ) : (
          insights.slice(0, 5).map(insight => (
            <div
              key={insight.id}
              onClick={() => openEntityDetail('insight', parseInt(insight.id), insight)}
              className="p-3 bg-gray-700/50 rounded-lg cursor-pointer hover:bg-gray-700 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-white font-medium text-sm">{insight.title}</h4>
                <div className="flex items-center gap-2">
                  <span className={clsx(
                    'text-xs px-2 py-1 rounded-full',
                    insight.priority === 'high' ? 'bg-red-500/20 text-red-300' :
                    insight.priority === 'medium' ? 'bg-yellow-500/20 text-yellow-300' :
                    'bg-green-500/20 text-green-300'
                  )}>
                    {insight.priority.toUpperCase()}
                  </span>
                  <Eye className="w-3 h-3 text-gray-400" />
                </div>
              </div>
              <p className="text-gray-400 text-xs">{insight.description}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );

  // Entity network component
  const EntityNetworkPanel = () => (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-6 mb-6">
      <h3 className="text-white font-semibold mb-4">🔗 Entity Network</h3>
      <div className="text-center text-gray-400 text-sm py-8">
        Entity relationship visualization will appear here
      </div>
    </div>
  );

  // Intelligence chat component with knowledge tree requirement
  const IntelligenceChatPanel = () => (
    <div className="bg-gray-800 rounded-lg border border-gray-700 p-6">
      <h3 className="text-white font-semibold mb-4">💬 Intelligence Assistant</h3>
      
      <div className="space-y-3 mb-4 max-h-64 overflow-y-auto">
        {chatMessages.length === 0 ? (
          <div className="text-gray-400 text-sm text-center py-4">
            Ask me about your business intelligence, relationships, or insights...
            <div className="text-xs text-yellow-400 mt-2">
              💡 Requires knowledge tree (Step 2 in Settings)
            </div>
          </div>
        ) : (
          chatMessages.map(msg => (
            <div
              key={msg.id}
              className={clsx(
                'flex',
                msg.sender === 'user' ? 'justify-end' : 'justify-start'
              )}
            >
              <div
                className={clsx(
                  'max-w-[80%] rounded-lg px-4 py-2',
                  msg.sender === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700 text-white'
                )}
              >
                <div className="text-xs opacity-70 mb-1">
                  {msg.sender === 'user' ? 'You' : 'AI Assistant'}
                </div>
                <div className="text-sm whitespace-pre-wrap">{msg.message}</div>
              </div>
            </div>
          ))
        )}
        {chatLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-700 text-white rounded-lg px-4 py-2">
              <div className="text-xs opacity-70 mb-1">AI Assistant</div>
              <div className="text-sm">Analyzing your business intelligence...</div>
            </div>
          </div>
        )}
      </div>
      
      <div className="flex gap-3">
        <input
          type="text"
          value={chatInput}
          onChange={(e) => setChatInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendChatMessage()}
          placeholder="Ask about your business intelligence..."
          className="flex-1 bg-gray-700 text-white border border-gray-600 rounded-lg px-4 py-2 focus:outline-none focus:border-blue-500 transition-colors"
        />
        <button
          onClick={sendChatMessage}
          disabled={chatLoading || !chatInput.trim()}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          {chatLoading ? '...' : 'Send'}
        </button>
      </div>
    </div>
  );

  // Settings page component
  const SettingsPage = () => (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">🚀 AI Chief of Staff Setup</h2>
        <p className="text-gray-400">
          Complete the 6-step workflow to build your comprehensive business intelligence system
        </p>
      </div>
      
      <div className="space-y-4">
        {workflowSteps.map((step, index) => (
          <div
            key={index}
            className={clsx(
              'bg-gray-800 rounded-lg border border-gray-700 p-6 transition-all',
              processingStep === index ? 'border-blue-500 bg-blue-500/5' : 'hover:bg-gray-800/80'
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="text-2xl">{step.icon}</div>
                <div>
                  <h3 className="text-white font-semibold">{step.title}</h3>
                  <p className="text-gray-400 text-sm">{step.description}</p>
                </div>
              </div>
              <button
                onClick={() => executeWorkflowStep(index)}
                disabled={processingStep !== null}
                className={clsx(
                  'px-4 py-2 rounded-lg transition-colors font-medium',
                  processingStep === index
                    ? 'bg-blue-600 text-white'
                    : 'bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50'
                )}
              >
                {processingStep === index ? '⏳ Processing...' : step.action}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Add Danger Zone at the bottom */}
      <DangerZone />
    </div>
  );

  // Initialize data on mount
  useEffect(() => {
    if (currentView === 'people') {
      fetchPeople();
    } else if (currentView === 'calendar') {
      fetchCalendarEvents();
    }
  }, [currentView]); // ✅ Fixed: removed function dependencies

  // Fetch initial data
  useEffect(() => {
    fetchIntelligenceMetrics();
    fetchProactiveInsights();
    fetchTasks();
  }, []); // ✅ Fixed: empty array - only run on mount

  // Load data on mount
  useEffect(() => {
    loadSyncSettings();
    fetchContactTiers();
    fetchTopics();
  }, []); // ✅ Fixed: empty array - only run on mount

  // Danger Zone section for database flush
  const DangerZone: React.FC = () => (
    <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-6">
      <h3 className="text-red-400 font-semibold mb-4 flex items-center gap-2">
        ⚠️ Danger Zone
      </h3>
      <div className="space-y-4">
        <div>
          <p className="text-gray-300 text-sm mb-4">
            Completely wipe all data and start fresh. This will delete all emails, tasks, people, topics, and insights permanently.
          </p>
          
          {!showFlushConfirm ? (
            <button
              onClick={() => setShowFlushConfirm(true)}
              disabled={processing}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 text-sm"
            >
              🗑️ Flush Database
            </button>
          ) : (
            <div className="space-y-3">
              <p className="text-red-300 text-sm font-medium">
                ⚠️ Are you absolutely sure? This action cannot be undone!
              </p>
              <div className="flex gap-3">
                <button
                  onClick={flushDatabase}
                  disabled={processing}
                  className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 text-sm"
                >
                  {processing ? '⏳ Flushing...' : '✅ Yes, Delete Everything'}
                </button>
                <button
                  onClick={() => setShowFlushConfirm(false)}
                  className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors text-sm"
                >
                  ❌ Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-gray-950">
      {/* Error Notification */}
      {error && (
        <div className="fixed top-4 right-4 z-50 bg-red-600 text-white px-4 py-2 rounded-lg shadow-lg">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">{error}</span>
            <button 
              onClick={() => setError(null)}
              className="ml-2 text-white hover:text-gray-200"
            >
              ×
            </button>
          </div>
        </div>
      )}

      {/* Success Notifications */}
      {notifications.map((notification, index) => (
        <div 
          key={index}
          className="fixed top-4 right-4 z-50 bg-green-600 text-white px-4 py-2 rounded-lg shadow-lg"
          style={{ top: `${4 + index * 60}px` }}
        >
          <span className="text-sm">{notification}</span>
        </div>
      ))}

      {/* Elegant Sidebar */}
      <div className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-800/50">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-gradient-to-br from-blue-500 to-purple-600 rounded-md flex items-center justify-center">
              <Brain className="w-4 h-4 text-white" />
            </div>
            <h1 className="text-sm font-semibold text-white">AI Chief of Staff</h1>
          </div>
        </div>

        {/* Search */}
        <div className="p-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-3 h-3 text-gray-500" />
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 py-1.5 text-xs bg-gray-800 text-white border border-gray-700 rounded-lg focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 space-y-0.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentView(item.id as ViewType)}
                className={clsx(
                  'w-full flex items-center gap-2 px-3 py-2 text-xs rounded-lg transition-colors',
                  currentView === item.id
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                )}
              >
                <Icon className="w-4 h-4" />
                <span className="flex-1 text-left">{item.label}</span>
                {item.count > 0 && (
                  <span className="bg-gray-700 text-gray-400 text-xs px-1.5 py-0.5 rounded text-[10px] font-medium">
                    {item.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        {/* Sync Button */}
        <div className="p-3 border-t border-gray-800/50">
          <button
            onClick={() => setCurrentView('settings')}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-purple-600/10 text-purple-400 rounded-md text-xs font-medium hover:bg-purple-600/20 transition-all mb-2"
          >
            <Settings className="w-3 h-3" />
            Setup Workflow
          </button>
          
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-1.5 px-3 py-2 bg-red-600/10 text-red-400 rounded-md text-xs font-medium hover:bg-red-600/20 transition-all"
          >
            <X className="w-3 h-3" />
            Logout
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-gray-900 border-b border-gray-800 px-4 py-3">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-white capitalize">
                {currentView}
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                {currentView === 'dashboard' && `${insights.length} insights`}
                {currentView === 'tasks' && `${tasks.length} tasks`}
                {currentView === 'people' && `${people.length} contacts`}
                {currentView === 'topics' && `${topics.length} topics`}
                {currentView === 'calendar' && `${events.length} events`}
                {currentView === 'settings' && `Build your AI Chief of Staff knowledge base`}
              </p>
            </div>
            {syncResults && (
              <div className="text-xs text-blue-400 bg-blue-900/20 px-2 py-1 rounded">
                {syncResults}
              </div>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading && currentView !== 'settings' && currentView !== 'topics' && (
            <div className="flex items-center justify-center h-64">
              <div className="flex items-center gap-2 text-gray-400">
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span className="text-sm">Loading...</span>
              </div>
            </div>
          )}
          
          {!loading && renderListView()}
        </div>
      </div>

      {/* Workflow Result Modal */}
      {showWorkflowModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-800 rounded-xl border border-gray-700 max-w-2xl w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-bold text-white">
                  {currentStepResult?.success ? '✅' : '❌'} Step {workflowStep + 1} Complete
                </h3>
                <button
                  onClick={() => setShowWorkflowModal(false)}
                  className="text-gray-400 hover:text-white"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {currentStepResult && (
                <div className="space-y-4">
                  <h4 className="text-lg text-white font-semibold">
                    {currentStepResult.title}
                  </h4>
                  
                  {currentStepResult.data && (
                    <div className="grid grid-cols-2 gap-4">
                      {Object.entries(currentStepResult.data).map(([key, value]) => {
                        if (key === 'next_step') return null;
                        return (
                          <div key={key} className="text-center">
                            <div className="text-2xl font-bold text-blue-400">{String(value)}</div>
                            <div className="text-xs text-gray-400 capitalize">
                              {key.replace(/_/g, ' ')}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {currentStepResult.data?.next_step && (
                    <div className="mt-6 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
                      <p className="text-blue-300 text-sm">
                        📋 Next: {currentStepResult.data.next_step}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Universal Entity Detail Modal */}
      {showEntityDetail && selectedEntityDetail && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg border border-gray-700 max-w-6xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    {getEntityIcon(selectedEntityDetail.type)}
                    {selectedEntityDetail.title}
                  </h3>
                  <p className="text-gray-400">
                    {selectedEntityDetail.type.charAt(0).toUpperCase() + selectedEntityDetail.type.slice(1)} Details & Source Traceability
                  </p>
                </div>
                <button
                  onClick={() => setShowEntityDetail(false)}
                  className="text-gray-400 hover:text-white"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Entity Details */}
                <div className="space-y-4">
                  <h4 className="text-white font-medium flex items-center gap-2">
                    <Database className="w-4 h-4" />
                    Analysis & Intelligence
                  </h4>
                  
                  <div className="bg-gray-700/50 rounded-lg p-4 space-y-3">
                    {renderEntityDetails(selectedEntityDetail)}
                  </div>

                  {/* Related Entities */}
                  {entityContext?.related_entities && Object.keys(entityContext.related_entities).length > 0 && (
                    <div>
                      <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                        <Network className="w-4 h-4" />
                        Related Entities
                      </h4>
                      <div className="space-y-2">
                        {Object.entries(entityContext.related_entities).map(([category, items]) => (
                          <div key={category} className="bg-gray-700/30 rounded-lg p-3">
                            <h5 className="text-sm font-medium text-blue-400 mb-2 capitalize">
                              {category.replace(/_/g, ' ')} ({Array.isArray(items) ? items.length : 0})
                            </h5>
                            <div className="space-y-1">
                              {Array.isArray(items) && items.slice(0, 3).map((item: any, index: number) => (
                                <div key={index} className="text-xs text-gray-300">
                                  {item.name || item.description || item.title || JSON.stringify(item).slice(0, 100)}
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Raw Source Content */}
                <div className="space-y-4">
                  <h4 className="text-white font-medium flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    Raw Source Content
                    {rawSources && rawSources.length > 0 && (
                      <span className="text-xs bg-blue-600 text-white px-2 py-1 rounded">
                        {rawSources.length} source{rawSources.length !== 1 ? 's' : ''}
                      </span>
                    )}
                  </h4>
                  
                  <div className="space-y-3 max-h-96 overflow-y-auto">
                    {loadingEntityContext ? (
                      <div className="text-center py-8">
                        <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-gray-400" />
                        <p className="text-gray-400 text-sm">Loading source content...</p>
                      </div>
                    ) : rawSources && rawSources.length > 0 ? (
                      rawSources.map((source: any, index: number) => (
                        <div key={index} className="bg-gray-700/50 rounded-lg p-4 border-l-4 border-blue-500">
                          <div className="flex items-center justify-between mb-2">
                            <h5 className="text-sm font-medium text-white">{source.title}</h5>
                            <div className="flex gap-2">
                              {source.relevance_score && (
                                <span className="text-xs bg-green-600 text-white px-2 py-1 rounded">
                                  {Math.round(source.relevance_score * 100)}% relevant
                                </span>
                              )}
                              <span className="text-xs bg-gray-600 text-gray-300 px-2 py-1 rounded">
                                {source.type}
                              </span>
                            </div>
                          </div>
                          
                          {source.metadata && (
                            <div className="text-xs text-gray-400 mb-3 space-y-1">
                              {source.metadata.sender && (
                                <div>From: {source.metadata.sender}</div>
                              )}
                              {source.metadata.date && (
                                <div>Date: {new Date(source.metadata.date).toLocaleDateString()}</div>
                              )}
                              {source.matched_keywords && (
                                <div>Keywords: {source.matched_keywords.join(', ')}</div>
                              )}
                            </div>
                          )}
                          
                          <div className="text-sm text-gray-300 mb-3">
                            <div className="bg-gray-800 rounded p-3 max-h-32 overflow-y-auto">
                              {source.content || 'No content available'}
                            </div>
                          </div>
                          
                          {source.metadata?.ai_analysis && (
                            <div className="text-xs">
                              <div className="text-blue-400 font-medium mb-1">AI Analysis:</div>
                              <div className="text-gray-300 bg-blue-900/20 rounded p-2">
                                {source.metadata.ai_analysis}
                              </div>
                            </div>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="text-center py-8">
                        <FileText className="w-8 h-8 mx-auto mb-2 text-gray-400 opacity-50" />
                        <p className="text-gray-400 text-sm">No source content available</p>
                        <p className="text-gray-500 text-xs mt-1">
                          This may be user-created content or system-generated data
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Traceability Footer */}
              {entityContext?.traceability && (
                <div className="mt-6 pt-4 border-t border-gray-700">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                    <div>
                      <div className="text-sm font-bold text-blue-400">{entityContext.traceability.source_count || 0}</div>
                      <div className="text-xs text-gray-400">Source Items</div>
                    </div>
                    {entityContext.traceability.confidence && (
                      <div>
                        <div className="text-sm font-bold text-green-400">
                          {Math.round((entityContext.traceability.confidence || 0) * 100)}%
                        </div>
                        <div className="text-xs text-gray-400">Confidence</div>
                      </div>
                    )}
                    {entityContext.traceability.created_at && (
                      <div>
                        <div className="text-sm font-bold text-purple-400">
                          {new Date(entityContext.traceability.created_at).toLocaleDateString()}
                        </div>
                        <div className="text-xs text-gray-400">Created</div>
                      </div>
                    )}
                    {entityContext.traceability.last_updated && (
                      <div>
                        <div className="text-sm font-bold text-yellow-400">
                          {new Date(entityContext.traceability.last_updated).toLocaleDateString()}
                        </div>
                        <div className="text-xs text-gray-400">Updated</div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IntelligenceDashboard;
