// Knowledge Page JavaScript Functions
// Handles Topics, Integrations, and Knowledge Base functionality

let currentMergeSourceId = null;
let allTopics = [];

// Tab switching functionality
function switchTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.style.display = 'none';
    });
    
    // Remove active class from all tabs
    document.querySelectorAll('[id$="Tab"]').forEach(tab => {
        tab.classList.remove('border-b-[#0b80ee]', 'text-white');
        tab.classList.add('border-b-transparent', 'text-[#90aecb]');
        tab.querySelector('p').classList.remove('text-white');
        tab.querySelector('p').classList.add('text-[#90aecb]');
    });
    
    // Show selected tab content
    document.getElementById(tabName + 'Content').style.display = 'block';
    
    // Add active class to selected tab
    const activeTab = document.getElementById(tabName + 'Tab');
    activeTab.classList.add('border-b-[#0b80ee]', 'text-white');
    activeTab.classList.remove('border-b-transparent', 'text-[#90aecb]');
    activeTab.querySelector('p').classList.add('text-white');
    activeTab.querySelector('p').classList.remove('text-[#90aecb]');
    
    // Load content for the selected tab
    if (tabName === 'topics') {
        loadTopicsData();
    } else if (tabName === 'integrations') {
        loadIntegrationsData();
    } else if (tabName === 'knowledgeBase') {
        loadKnowledgeBaseData();
    }
}

// ====================================
// TOPICS MANAGEMENT FUNCTIONALITY
// ====================================

async function loadTopicsData() {
    try {
        // Load topics, emails, and tasks to build consistent topic view
        const [topicsResponse, emailsResponse, tasksResponse] = await Promise.all([
            fetch('/api/topics'),
            fetch('/api/emails'),
            fetch('/api/tasks')
        ]);
        
        const [topicsData, emailsData, tasksData] = await Promise.all([
            topicsResponse.json(),
            emailsResponse.json(),
            tasksResponse.json()
        ]);
        
        if (topicsData.success) {
            const dbTopics = topicsData.topics;
            const emails = emailsData.success ? emailsData.emails : [];
            const tasks = tasksData.success ? tasksData.tasks : [];
            
            // Build comprehensive topic knowledge map (same as Knowledge Base)
            const knowledgeMap = buildTopicKnowledgeMap(dbTopics, emails, tasks);
            
            // Convert back to array with both DB and AI-discovered topics
            allTopics = Array.from(knowledgeMap.values()).map(topic => ({
                id: topic.id || null, // AI-discovered topics won't have DB IDs
                name: topic.name,
                description: topic.description,
                is_official: topic.is_official,
                confidence_score: topic.confidence_score,
                keywords: topic.keywords,
                email_count: topic.emails_count,
                task_count: topic.tasks_count,
                total_items: topic.total_items,
                knowledge_strength: topic.knowledge_strength,
                last_used: topic.last_updated,
                created_at: topic.created_at,
                updated_at: topic.last_updated,
                people_involved: topic.people_involved,
                content_strength: topic.content_strength
            }));
            
            updateTopicsStatistics(allTopics);
            renderOfficialTopics(allTopics.filter(t => t.is_official));
            renderAITopics(allTopics.filter(t => !t.is_official));
        } else {
            console.error('Failed to load topics:', topicsData.error);
            showError('Failed to load topics: ' + topicsData.error);
        }
    } catch (error) {
        console.error('Failed to load topics:', error);
        showError('Network error loading topics');
    }
}

// Helper function to refresh both Topics and Knowledge Base tabs with consistent data
async function refreshTopicsAndKnowledge() {
    // Reload topics data (which now includes AI-discovered topics)
    await loadTopicsData();
    
    // If Knowledge Base tab is active, reload it too
    const knowledgeBaseContent = document.getElementById('knowledgeBaseContent');
    if (knowledgeBaseContent && knowledgeBaseContent.style.display !== 'none') {
        await loadKnowledgeBaseData();
    }
}

function updateTopicsStatistics(topics) {
    const total = topics.length;
    const official = topics.filter(t => t.is_official).length;
    const aiDiscovered = topics.filter(t => !t.is_official).length;
    
    // Calculate recent activity (topics with activity in last 30 days)
    const recent = topics.filter(t => {
        if (!t.last_used) return false;
        const lastUsed = new Date(t.last_used);
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        return lastUsed > thirtyDaysAgo;
    }).length;
    
    // Show knowledge strength in statistics
    const strongTopics = topics.filter(t => (t.knowledge_strength || 0) >= 70).length;
    
    document.getElementById('totalTopicsCount').textContent = total;
    document.getElementById('officialTopicsCount').textContent = official;
    document.getElementById('aiTopicsCount').textContent = aiDiscovered;
    document.getElementById('activeTopicsCount').textContent = recent;
}

function renderOfficialTopics(topics) {
    const container = document.getElementById('officialTopicsContainer');
    
    if (topics.length === 0) {
        container.innerHTML = `
            <div class="bg-[#182734] p-4 rounded-lg border border-[#314d68] text-center">
                <div class="text-[#90aecb] mb-4">
                    <div class="text-6xl mb-2">🏷️</div>
                    <div class="text-lg">No Official Topics</div>
                    <div class="text-sm">Create your first official topic to help Claude categorize content</div>
                </div>
                <button onclick="showCreateTopicModal()" class="bg-[#0b80ee] text-white px-4 py-2 rounded hover:bg-blue-600 transition-colors">
                    Create First Topic
                </button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = topics.map(topic => `
        <div class="bg-[#182734] p-4 rounded-lg border border-[#314d68] hover:border-[#0b80ee] transition-colors">
            <div class="flex justify-between items-start">
                <div class="flex-1">
                    <div class="flex items-center gap-3 mb-2">
                        <div class="bg-green-500 w-3 h-3 rounded-full"></div>
                        <h4 class="text-white font-semibold text-lg">${escapeHtml(topic.name)}</h4>
                        <span class="bg-green-500 text-white px-2 py-1 rounded-full text-xs">Official</span>
                    </div>
                    
                    <div class="text-[#90aecb] text-sm mb-3 leading-relaxed">
                        ${escapeHtml(topic.description || 'No description available')}
                    </div>
                    
                    <div class="flex flex-wrap gap-2 mb-3">
                        ${(topic.keywords || []).map(keyword => `
                            <span class="bg-[#223649] text-[#90aecb] px-2 py-1 rounded text-xs">${escapeHtml(keyword)}</span>
                        `).join('')}
                    </div>
                    
                    <div class="flex justify-between items-center text-xs text-[#90aecb]">
                        <span>📧 ${topic.email_count || 0} emails</span>
                        <span>Updated: ${formatDate(topic.updated_at)}</span>
                    </div>
                </div>
                
                <div class="flex gap-2 ml-4">
                    <button onclick="editTopic(${topic.id})" class="text-[#0b80ee] hover:text-blue-400 p-2" title="Edit">
                        ✏️
                    </button>
                    <button onclick="showTopicAnalytics(${topic.id})" class="text-[#90aecb] hover:text-white p-2" title="Analytics">
                        📊
                    </button>
                </div>
            </div>
        </div>
    `).join('');
}

function renderAITopics(topics) {
    const container = document.getElementById('aiTopicsContainer');
    
    if (topics.length === 0) {
        container.innerHTML = `
            <div class="bg-[#182734] p-4 rounded-lg border border-[#314d68] text-center">
                <div class="text-[#90aecb] mb-4">
                    <div class="text-6xl mb-2">🤖</div>
                    <div class="text-lg">No AI-Discovered Topics</div>
                    <div class="text-sm">Process some emails to let AI discover topics automatically</div>
                </div>
                <button onclick="syncTopicsFromEmails()" class="bg-[#0b80ee] text-white px-4 py-2 rounded hover:bg-blue-600 transition-colors">
                    🔄 Sync from Emails
                </button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = topics.map((topic, index) => `
        <div class="bg-[#182734] p-4 rounded-lg border border-[#314d68] hover:border-blue-400 transition-colors">
            <div class="flex justify-between items-start">
                <div class="flex-1">
                    <div class="flex items-center gap-3 mb-2">
                        <div class="bg-blue-400 w-3 h-3 rounded-full"></div>
                        <h4 class="text-white font-semibold">${escapeHtml(topic.name)}</h4>
                        <span class="bg-blue-400 text-white px-2 py-1 rounded-full text-xs">AI-Discovered</span>
                        ${topic.confidence_score ? `<span class="text-xs text-[#90aecb]">${Math.round(topic.confidence_score * 100)}% confidence</span>` : ''}
                        ${topic.knowledge_strength ? `<span class="text-xs text-green-400">${Math.round(topic.knowledge_strength)}% strength</span>` : ''}
                    </div>
                    
                    <div class="text-[#90aecb] text-sm mb-3">
                        ${escapeHtml(topic.description || 'Auto-discovered from email content')}
                    </div>
                    
                    <div class="grid grid-cols-3 gap-3 mb-3 text-xs">
                        <div class="text-center">
                            <div class="text-white font-semibold">${topic.email_count || 0}</div>
                            <div class="text-[#90aecb] text-xs">Emails</div>
                        </div>
                        <div class="text-center">
                            <div class="text-white font-semibold">${topic.task_count || 0}</div>
                            <div class="text-[#90aecb] text-xs">Tasks</div>
                        </div>
                        <div class="text-center">
                            <div class="text-white font-semibold">${topic.total_items || 0}</div>
                            <div class="text-[#90aecb] text-xs">Items</div>
                        </div>
                    </div>
                    
                    <div class="flex justify-between items-center text-xs text-[#90aecb]">
                        <span>📧 ${topic.email_count || 0} emails</span>
                        <span>Discovered: ${formatDate(topic.created_at || topic.last_used)}</span>
                    </div>
                </div>
                
                <div class="flex gap-2 ml-4">
                    <button onclick="makeTopicOfficialByName('${escapeHtml(topic.name)}')" class="bg-green-500 text-white px-3 py-1 rounded text-xs hover:bg-green-600 transition-colors" title="Make Official">
                        ⭐ Make Official
                    </button>
                    ${topic.id ? `<button onclick="showMergeTopicModal(${topic.id}, '${escapeHtml(topic.name)}')" class="text-[#90aecb] hover:text-white p-2" title="Merge">🔀</button>` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

// Modal Functions
function showCreateTopicModal() {
    document.getElementById('createTopicModal').style.display = 'flex';
    document.getElementById('newTopicName').focus();
}

function hideCreateTopicModal() {
    document.getElementById('createTopicModal').style.display = 'none';
    // Clear form
    document.getElementById('newTopicName').value = '';
    document.getElementById('newTopicDescription').value = '';
    document.getElementById('newTopicKeywords').value = '';
}

async function createNewTopic() {
    const name = document.getElementById('newTopicName').value.trim();
    const description = document.getElementById('newTopicDescription').value.trim();
    const keywordsText = document.getElementById('newTopicKeywords').value.trim();
    
    if (!name) {
        showError('Please enter a topic name');
        return;
    }
    
    if (!description) {
        showError('Please enter a description to help Claude categorize content');
        return;
    }
    
    const keywords = keywordsText ? keywordsText.split(',').map(k => k.trim()).filter(k => k) : [];
    
    try {
        const response = await fetch('/api/topics', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                description: description,
                is_official: true,
                keywords: keywords
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(`✅ Topic "${name}" created successfully!`);
            hideCreateTopicModal();
            await refreshTopicsAndKnowledge(); // Refresh both tabs
        } else {
            showError('Failed to create topic: ' + result.error);
        }
    } catch (error) {
        console.error('Failed to create topic:', error);
        showError('Network error: ' + error.message);
    }
}

async function makeTopicOfficial(topicId) {
    // Find the topic - could be by ID or by name for AI-discovered topics
    let topic;
    if (topicId) {
        topic = allTopics.find(t => t.id === topicId);
    } else {
        // This shouldn't happen, but fallback
        return;
    }
    
    // For AI-discovered topics without database IDs, we need to create them first
    if (!topic.id) {
        // This is an AI-discovered topic, create it in the database
        try {
            const createResponse = await fetch('/api/topics', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: topic.name,
                    description: topic.description || `AI-discovered topic with ${topic.total_items || 0} knowledge items from email analysis`,
                    is_official: true,
                    keywords: topic.keywords || [topic.name.toLowerCase()]
                })
            });
            
            const createResult = await createResponse.json();
            
            if (createResult.success) {
                showSuccess(`✅ "${topic.name}" created as official topic!`);
                loadTopicsData(); // Refresh both tabs
                return;
            } else {
                showError('Failed to create topic: ' + createResult.error);
                return;
            }
        } catch (error) {
            console.error('Failed to create AI-discovered topic:', error);
            showError('Network error creating topic: ' + error.message);
            return;
        }
    }
    
    // For existing database topics, just mark as official
    if (!topic) return;
    
    if (!confirm(`Make "${topic.name}" an official topic?\n\nThis will make it available for consistent categorization by Claude.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/topics/${topic.id}/official`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(`✅ "${topic.name}" is now an official topic!`);
            await refreshTopicsAndKnowledge(); // Refresh both tabs
        } else {
            showError('Failed to make topic official: ' + result.error);
        }
    } catch (error) {
        console.error('Failed to make topic official:', error);
        showError('Network error: ' + error.message);
    }
}

function showMergeTopicModal(sourceTopicId, sourceTopicName) {
    currentMergeSourceId = sourceTopicId;
    
    // Set source topic name
    document.getElementById('mergeSourceTopic').textContent = sourceTopicName;
    
    // Populate target topic dropdown with official topics
    const officialTopics = allTopics.filter(t => t.is_official && t.id !== sourceTopicId);
    const targetSelect = document.getElementById('mergeTargetTopic');
    
    targetSelect.innerHTML = '<option value="">Select target topic...</option>' + 
        officialTopics.map(topic => `<option value="${topic.id}">${escapeHtml(topic.name)}</option>`).join('');
    
    document.getElementById('mergeTopicModal').style.display = 'flex';
}

function hideMergeTopicModal() {
    document.getElementById('mergeTopicModal').style.display = 'none';
    currentMergeSourceId = null;
}

async function confirmMergeTopics() {
    const targetTopicId = document.getElementById('mergeTargetTopic').value;
    
    if (!targetTopicId) {
        showError('Please select a target topic');
        return;
    }
    
    if (!currentMergeSourceId) {
        showError('Source topic not found');
        return;
    }
    
    const sourceTopic = allTopics.find(t => t.id === currentMergeSourceId);
    const targetTopic = allTopics.find(t => t.id == targetTopicId);
    
    if (!confirm(`Merge "${sourceTopic.name}" into "${targetTopic.name}"?\n\nThis will:\n• Move all content from "${sourceTopic.name}" to "${targetTopic.name}"\n• Delete "${sourceTopic.name}"\n• Cannot be undone`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/topics/${currentMergeSourceId}/merge`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                target_topic_id: parseInt(targetTopicId)
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(`✅ Successfully merged "${sourceTopic.name}" into "${targetTopic.name}"`);
            hideMergeTopicModal();
            await refreshTopicsAndKnowledge(); // Refresh both tabs
        } else {
            showError('Failed to merge topics: ' + result.error);
        }
    } catch (error) {
        console.error('Failed to merge topics:', error);
        showError('Network error: ' + error.message);
    }
}

async function syncTopicsFromEmails() {
    if (!confirm('Sync topics from email analysis?\n\nThis will discover new topics from your processed emails.')) {
        return;
    }
    
    try {
        const response = await fetch('/api/sync-topics', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess(`🔄 Synced ${result.topics_created} topics from ${result.total_topic_usage} topic usages!`);
            await refreshTopicsAndKnowledge(); // Refresh both tabs
        } else {
            showError('Failed to sync topics: ' + result.error);
        }
    } catch (error) {
        console.error('Failed to sync topics:', error);
        showError('Network error: ' + error.message);
    }
}

function editTopic(topicId) {
    const topic = allTopics.find(t => t.id === topicId);
    if (!topic) return;
    
    // For now, show a simple prompt - could be enhanced with a proper modal
    const newDescription = prompt(`Edit description for "${topic.name}":`, topic.description || '');
    if (newDescription !== null && newDescription !== topic.description) {
        updateTopicDescription(topicId, newDescription);
    }
}

async function updateTopicDescription(topicId, description) {
    try {
        const response = await fetch(`/api/topics/${topicId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                description: description
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showSuccess('✅ Topic description updated!');
            await refreshTopicsAndKnowledge(); // Refresh both tabs
        } else {
            showError('Failed to update topic: ' + result.error);
        }
    } catch (error) {
        console.error('Failed to update topic:', error);
        showError('Network error: ' + error.message);
    }
}

function showTopicAnalytics(topicId) {
    const topic = allTopics.find(t => t.id === topicId);
    if (!topic) return;
    
    alert(`Topic Analytics for "${topic.name}"\n\n📊 Coming Soon:\n• Email usage over time\n• Content categorization accuracy\n• Related topics analysis\n• Export topic data\n\nCurrent Stats:\n• ${topic.email_count || 0} emails categorized\n• Created: ${formatDate(topic.created_at)}\n• Last used: ${formatDate(topic.last_used)}`);
}

// ====================================
// INTEGRATIONS FUNCTIONALITY
// ====================================

async function loadIntegrationsData() {
    // For now, show static integrations data
    // In the future, this would load from an API
    console.log('Loading integrations data...');
}

// ====================================
// KNOWLEDGE BASE FUNCTIONALITY
// ====================================

async function loadKnowledgeBaseData() {
    try {
        // Load knowledge statistics and topics
        const [topicsResponse, emailsResponse, tasksResponse] = await Promise.all([
            fetch('/api/topics'),
            fetch('/api/emails'),
            fetch('/api/tasks')
        ]);
        
        const [topicsData, emailsData, tasksData] = await Promise.all([
            topicsResponse.json(),
            emailsResponse.json(),
            tasksResponse.json()
        ]);
        
        // Calculate topic-based knowledge statistics
        const topics = topicsData.success ? topicsData.topics : [];
        const emails = emailsData.success ? emailsData.emails : [];
        const tasks = tasksData.success ? tasksData.tasks : [];
        
        // Build topic knowledge map
        const topicKnowledge = buildTopicKnowledgeMap(topics, emails, tasks);
        
        // Update knowledge statistics
        updateKnowledgeStatistics(topicKnowledge, emails, tasks);
        
        // Display knowledge by topics
        displayKnowledgeByTopics(topicKnowledge);
        
    } catch (error) {
        console.error('Failed to load knowledge base data:', error);
        showError('Failed to load knowledge base data');
    }
}

function buildTopicKnowledgeMap(topics, emails, tasks) {
    const knowledgeMap = new Map();
    
    // Initialize with existing topics
    topics.forEach(topic => {
        knowledgeMap.set(topic.name, {
            id: topic.id,
            name: topic.name,
            description: topic.description,
            is_official: topic.is_official,
            confidence_score: topic.confidence_score,
            keywords: topic.keywords || [],
            knowledge_items: [],
            people_involved: new Set(),
            key_insights: [],
            decisions: [],
            opportunities: [],
            challenges: [],
            emails_count: 0,
            tasks_count: 0,
            last_updated: topic.updated_at,
            content_strength: 0
        });
    });
    
    // Add knowledge from emails
    emails.forEach(email => {
        if (email.topics && email.topics.length > 0) {
            email.topics.forEach(topicName => {
                if (!knowledgeMap.has(topicName)) {
                    // Create emerging topic
                    knowledgeMap.set(topicName, {
                        name: topicName,
                        description: 'Emerging topic discovered from email analysis',
                        is_official: false,
                        confidence_score: 0.5,
                        keywords: [topicName.toLowerCase()],
                        knowledge_items: [],
                        people_involved: new Set(),
                        key_insights: [],
                        decisions: [],
                        opportunities: [],
                        challenges: [],
                        emails_count: 0,
                        tasks_count: 0,
                        last_updated: email.email_date,
                        content_strength: 0
                    });
                }
                
                const topic = knowledgeMap.get(topicName);
                topic.emails_count++;
                topic.content_strength += 1;
                
                // Add email insights to topic
                if (email.ai_summary) {
                    topic.knowledge_items.push({
                        type: 'email_insight',
                        content: email.ai_summary,
                        source: `Email: ${email.subject}`,
                        date: email.email_date,
                        confidence: email.priority_score || 0.5
                    });
                }
                
                // Extract people involved
                if (email.sender_name) {
                    topic.people_involved.add(email.sender_name);
                }
                
                // Extract key insights if available
                if (email.key_insights && Array.isArray(email.key_insights)) {
                    email.key_insights.forEach(insight => {
                        topic.key_insights.push({
                            insight: insight,
                            source: email.subject,
                            date: email.email_date
                        });
                    });
                }
                
                // Update last updated
                if (email.email_date && (!topic.last_updated || email.email_date > topic.last_updated)) {
                    topic.last_updated = email.email_date;
                }
            });
        }
    });
    
    // Add knowledge from tasks
    tasks.forEach(task => {
        // Try to map tasks to topics based on description content
        const taskDescription = task.description.toLowerCase();
        
        knowledgeMap.forEach((topic, topicName) => {
            const topicKeywords = topic.keywords || [topicName.toLowerCase()];
            const hasMatch = topicKeywords.some(keyword => 
                taskDescription.includes(keyword.toLowerCase())
            );
            
            if (hasMatch) {
                topic.tasks_count++;
                topic.content_strength += 0.5;
                
                topic.knowledge_items.push({
                    type: 'task',
                    content: task.description,
                    source: 'Task Management',
                    date: task.created_at,
                    priority: task.priority,
                    status: task.status,
                    confidence: task.confidence || 0.7
                });
                
                if (task.assignee) {
                    topic.people_involved.add(task.assignee);
                }
            }
        });
    });
    
    // Convert people sets to arrays and calculate final scores
    knowledgeMap.forEach(topic => {
        topic.people_involved = Array.from(topic.people_involved);
        topic.total_items = topic.knowledge_items.length;
        
        // Calculate knowledge strength score
        topic.knowledge_strength = Math.min(100, 
            (topic.content_strength * 10) + 
            (topic.people_involved.length * 5) + 
            (topic.is_official ? 20 : 0)
        );
        
        // Sort knowledge items by date (newest first)
        topic.knowledge_items.sort((a, b) => new Date(b.date) - new Date(a.date));
    });
    
    return knowledgeMap;
}

function updateKnowledgeStatistics(knowledgeMap, emails, tasks) {
    const topicsWithKnowledge = Array.from(knowledgeMap.values()).filter(t => t.total_items > 0);
    const totalKnowledgeItems = topicsWithKnowledge.reduce((sum, topic) => sum + topic.total_items, 0);
    const avgTopicDepth = topicsWithKnowledge.length > 0 ? 
        Math.round(totalKnowledgeItems / topicsWithKnowledge.length) : 0;
    
    // Calculate growth (items added in the last week)
    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
    
    let newThisWeek = 0;
    topicsWithKnowledge.forEach(topic => {
        topic.knowledge_items.forEach(item => {
            if (new Date(item.date) > oneWeekAgo) {
                newThisWeek++;
            }
        });
    });
    
    // Update UI
    document.getElementById('totalTopicsWithKnowledge').textContent = topicsWithKnowledge.length;
    document.getElementById('totalKnowledgeItems').textContent = totalKnowledgeItems;
    document.getElementById('avgTopicDepth').textContent = avgTopicDepth;
    document.getElementById('knowledgeGrowthRate').textContent = `+${newThisWeek}`;
}

function displayKnowledgeByTopics(knowledgeMap) {
    const container = document.getElementById('knowledgeTopicsContainer');
    
    // Convert to array and sort by knowledge strength
    const topics = Array.from(knowledgeMap.values())
        .filter(topic => topic.total_items > 0) // Only show topics with actual knowledge
        .sort((a, b) => b.knowledge_strength - a.knowledge_strength);
    
    if (topics.length === 0) {
        container.innerHTML = `
            <div class="bg-[#182734] p-6 rounded-lg border border-[#314d68] text-center">
                <div class="text-6xl mb-4">📚</div>
                <div class="text-white text-lg mb-2">No Knowledge Topics Yet</div>
                <div class="text-[#90aecb] text-sm mb-4">
                    Process emails and create tasks to build your knowledge base by topics
                </div>
                <button onclick="syncTopicsFromEmails()" class="bg-[#0b80ee] text-white px-4 py-2 rounded hover:bg-blue-600 transition-colors">
                    🔄 Analyze Content for Topics
                </button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = topics.map(topic => {
        const strengthColor = topic.knowledge_strength >= 70 ? 'text-green-400' : 
                             topic.knowledge_strength >= 40 ? 'text-yellow-400' : 'text-blue-400';
        const strengthLabel = topic.knowledge_strength >= 70 ? 'Strong' : 
                             topic.knowledge_strength >= 40 ? 'Growing' : 'Emerging';
        
        return `
            <div class="bg-[#182734] p-4 rounded-lg border border-[#314d68] hover:border-[#0b80ee] transition-colors cursor-pointer" 
                 onclick="showTopicDetail('${escapeHtml(topic.name)}')">
                <div class="flex justify-between items-start mb-3">
                    <div class="flex-1">
                        <div class="flex items-center gap-3 mb-2">
                            <div class="${topic.is_official ? 'bg-green-500' : 'bg-blue-400'} w-3 h-3 rounded-full"></div>
                            <h4 class="text-white font-semibold text-lg">${escapeHtml(topic.name)}</h4>
                            <span class="bg-${topic.is_official ? 'green' : 'blue'}-500 text-white px-2 py-1 rounded-full text-xs">
                                ${topic.is_official ? 'Official' : 'Emerging'}
                            </span>
                            <span class="${strengthColor} text-xs font-medium">
                                ${strengthLabel} (${Math.round(topic.knowledge_strength)}%)
                            </span>
                        </div>
                        
                        <p class="text-[#90aecb] text-sm mb-3 leading-relaxed">
                            ${escapeHtml(topic.description || 'No description available')}
                        </p>
                    </div>
                </div>
                
                <div class="grid grid-cols-4 gap-3 mb-3">
                    <div class="text-center">
                        <div class="text-white font-semibold">${topic.total_items}</div>
                        <div class="text-[#90aecb] text-xs">Items</div>
                    </div>
                    <div class="text-center">
                        <div class="text-white font-semibold">${topic.emails_count}</div>
                        <div class="text-[#90aecb] text-xs">Emails</div>
                    </div>
                    <div class="text-center">
                        <div class="text-white font-semibold">${topic.tasks_count}</div>
                        <div class="text-[#90aecb] text-xs">Tasks</div>
                    </div>
                    <div class="text-center">
                        <div class="text-white font-semibold">${topic.people_involved.length}</div>
                        <div class="text-[#90aecb] text-xs">People</div>
                    </div>
                </div>
                
                <div class="flex justify-between items-center text-xs text-[#90aecb]">
                    <span>Last updated: ${formatDate(topic.last_updated)}</span>
                    <div class="flex items-center gap-2">
                        ${!topic.is_official ? `<button onclick="makeTopicOfficialByName('${escapeHtml(topic.name)}')" class="bg-green-500 text-white px-2 py-1 rounded text-xs hover:bg-green-600 transition-colors">⭐ Make Official</button>` : ''}
                        <span class="text-[#0b80ee]">Click to explore →</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function filterKnowledgeTopics(filter) {
    // Update button states
    document.querySelectorAll('[id^="filter"]').forEach(btn => {
        btn.classList.remove('bg-[#0b80ee]', 'text-white');
        btn.classList.add('bg-[#223649]', 'text-[#90aecb]');
    });
    
    const activeBtn = document.getElementById(`filter${filter.charAt(0).toUpperCase() + filter.slice(1)}`);
    if (activeBtn) {
        activeBtn.classList.add('bg-[#0b80ee]', 'text-white');
        activeBtn.classList.remove('bg-[#223649]', 'text-[#90aecb]');
    }
    
    // Filter topics (implement based on current filter)
    const topics = document.querySelectorAll('#knowledgeTopicsContainer > div');
    topics.forEach(topic => {
        const isOfficial = topic.innerHTML.includes('Official');
        const isEmerging = topic.innerHTML.includes('Emerging');
        
        let show = false;
        if (filter === 'all') show = true;
        else if (filter === 'official') show = isOfficial;
        else if (filter === 'emerging') show = isEmerging;
        
        topic.style.display = show ? 'block' : 'none';
    });
}

async function showTopicDetail(topicName) {
    const modal = document.getElementById('topicDetailModal');
    const title = document.getElementById('topicDetailTitle');
    const content = document.getElementById('topicDetailContent');
    
    title.textContent = topicName;
    content.innerHTML = '<div class="text-center py-8">Loading topic details...</div>';
    modal.style.display = 'flex';
    
    try {
        // Get detailed topic information
        const [topicsResponse, emailsResponse, tasksResponse] = await Promise.all([
            fetch('/api/topics'),
            fetch('/api/emails'),
            fetch('/api/tasks')
        ]);
        
        const [topicsData, emailsData, tasksData] = await Promise.all([
            topicsResponse.json(),
            emailsResponse.json(),
            tasksResponse.json()
        ]);
        
        // Rebuild knowledge map to get detailed data
        const topics = topicsData.success ? topicsData.topics : [];
        const emails = emailsData.success ? emailsData.emails : [];
        const tasks = tasksData.success ? tasksData.tasks : [];
        
        const knowledgeMap = buildTopicKnowledgeMap(topics, emails, tasks);
        const topic = knowledgeMap.get(topicName);
        
        if (!topic) {
            content.innerHTML = '<div class="text-red-400">Topic not found</div>';
            return;
        }
        
        // Build detailed content
        let detailHTML = `
            <div class="space-y-6">
                <div class="border-b border-[#314d68] pb-4">
                    <div class="flex items-center gap-3 mb-2">
                        <div class="${topic.is_official ? 'bg-green-500' : 'bg-blue-400'} w-4 h-4 rounded-full"></div>
                        <span class="text-lg font-semibold">${escapeHtml(topic.name)}</span>
                        <span class="bg-${topic.is_official ? 'green' : 'blue'}-500 text-white px-2 py-1 rounded-full text-xs">
                            ${topic.is_official ? 'Official Topic' : 'Emerging Topic'}
                        </span>
                    </div>
                    <p class="text-[#90aecb]">${escapeHtml(topic.description || 'No description available')}</p>
                    
                    <div class="grid grid-cols-5 gap-4 mt-4">
                        <div class="text-center">
                            <div class="text-xl font-bold text-white">${topic.total_items}</div>
                            <div class="text-[#90aecb] text-sm">Knowledge Items</div>
                        </div>
                        <div class="text-center">
                            <div class="text-xl font-bold text-blue-400">${topic.emails_count}</div>
                            <div class="text-[#90aecb] text-sm">Emails</div>
                        </div>
                        <div class="text-center">
                            <div class="text-xl font-bold text-green-400">${topic.tasks_count}</div>
                            <div class="text-[#90aecb] text-sm">Tasks</div>
                        </div>
                        <div class="text-center">
                            <div class="text-xl font-bold text-yellow-400">${topic.people_involved.length}</div>
                            <div class="text-[#90aecb] text-sm">People</div>
                        </div>
                        <div class="text-center">
                            <div class="text-xl font-bold text-purple-400">${Math.round(topic.knowledge_strength)}%</div>
                            <div class="text-[#90aecb] text-sm">Strength</div>
                        </div>
                    </div>
                </div>
        `;
        
        // People involved
        if (topic.people_involved.length > 0) {
            detailHTML += `
                <div>
                    <h4 class="text-white font-semibold mb-3">👥 People Involved</h4>
                    <div class="flex flex-wrap gap-2">
                        ${topic.people_involved.map(person => `
                            <span class="bg-[#223649] text-white px-3 py-1 rounded-full text-sm">${escapeHtml(person)}</span>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        // Knowledge items
        if (topic.knowledge_items.length > 0) {
            detailHTML += `
                <div>
                    <h4 class="text-white font-semibold mb-3">📚 Knowledge Items</h4>
                    <div class="space-y-3 max-h-60 overflow-y-auto">
                        ${topic.knowledge_items.slice(0, 10).map(item => `
                            <div class="bg-[#223649] p-3 rounded border-l-4 border-${item.type === 'email_insight' ? 'blue' : 'green'}-400">
                                <div class="flex justify-between items-start mb-2">
                                    <span class="text-xs text-[#90aecb]">${item.source}</span>
                                    <span class="text-xs text-[#90aecb]">${formatDate(item.date)}</span>
                                </div>
                                <p class="text-white text-sm">${escapeHtml(item.content.substring(0, 200))}${item.content.length > 200 ? '...' : ''}</p>
                                ${item.priority ? `<div class="mt-2"><span class="bg-${item.priority === 'high' ? 'red' : item.priority === 'medium' ? 'yellow' : 'green'}-500 text-white px-2 py-1 rounded text-xs">${item.priority} priority</span></div>` : ''}
                            </div>
                        `).join('')}
                    </div>
                    ${topic.knowledge_items.length > 10 ? `<p class="text-[#90aecb] text-sm mt-2">Showing 10 of ${topic.knowledge_items.length} items</p>` : ''}
                </div>
            `;
        }
        
        detailHTML += '</div>';
        content.innerHTML = detailHTML;
        
    } catch (error) {
        console.error('Failed to load topic details:', error);
        content.innerHTML = '<div class="text-red-400">Failed to load topic details</div>';
    }
}

function closeTopicDetail() {
    document.getElementById('topicDetailModal').style.display = 'none';
}

async function downloadKnowledgeBase() {
    try {
        // This is instant export of existing chat-ready data, no generation needed
        const response = await fetch('/api/download-knowledge-base');
        
        if (!response.ok) {
            throw new Error(`Download failed: ${response.status} ${response.statusText}`);
        }
        
        // Get the filename from headers or create a default one
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'AI_Chief_of_Staff_Knowledge_Base.json';
        
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="(.+)"/);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }
        
        // Create blob and download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        
        // Clean up
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showSuccess('✅ Knowledge base downloaded! Complete export of your emails, tasks, people, topics, and AI insights.');
        
    } catch (error) {
        console.error('Failed to download knowledge base:', error);
        showError('Failed to download knowledge base: ' + error.message);
    }
}

// ====================================
// UTILITY FUNCTIONS
// ====================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return 'Never';
    
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        if (diffDays < 30) return `${Math.ceil(diffDays / 7)} weeks ago`;
        if (diffDays < 365) return `${Math.ceil(diffDays / 30)} months ago`;
        
        return date.toLocaleDateString();
    } catch (error) {
        return 'Invalid date';
    }
}

function showSuccess(message) {
    // Simple alert for now - could be enhanced with a toast notification
    alert(message);
}

function showError(message) {
    // Simple alert for now - could be enhanced with a toast notification
    alert('❌ ' + message);
}

// Search functionality for knowledge base
document.addEventListener('DOMContentLoaded', function() {
    const knowledgeSearch = document.getElementById('knowledgeSearch');
    if (knowledgeSearch) {
        knowledgeSearch.addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            // TODO: Implement search functionality
            console.log('Searching for:', searchTerm);
        });
    }
    
    // Load initial topics data
    loadTopicsData();
});

// Close modals when clicking outside
document.addEventListener('click', function(e) {
    const createModal = document.getElementById('createTopicModal');
    const mergeModal = document.getElementById('mergeTopicModal');
    const topicDetailModal = document.getElementById('topicDetailModal');
    const promotionModal = document.getElementById('promotionModal');
    
    if (e.target === createModal) {
        hideCreateTopicModal();
    }
    
    if (e.target === mergeModal) {
        hideMergeTopicModal();
    }
    
    if (e.target === topicDetailModal) {
        closeTopicDetail();
    }
    
    if (e.target === promotionModal) {
        hideTopicPromotionModal();
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // ESC to close modals
    if (e.key === 'Escape') {
        hideCreateTopicModal();
        hideMergeTopicModal();
        closeTopicDetail();
        hideTopicPromotionModal();
    }
    
    // Ctrl/Cmd + N to create new topic
    if ((e.ctrlKey || e.metaKey) && e.key === 'n' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
        e.preventDefault();
        showCreateTopicModal();
    }
});

async function makeTopicOfficialByName(topicName) {
    const topic = allTopics.find(t => t.name === topicName);
    if (!topic) return;
    
    // Show edit modal for AI-discovered topics when promoting to official
    showTopicPromotionModal(topic);
}

function showTopicPromotionModal(topic) {
    // Create modal HTML if it doesn't exist
    let modal = document.getElementById('promotionModal');
    if (!modal) {
        const modalHTML = `
            <div id="promotionModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" style="display: none;">
                <div class="bg-[#182734] p-6 rounded-lg border border-[#314d68] max-w-2xl w-full mx-4">
                    <h3 class="text-white text-lg font-bold mb-4">🎯 Promote to Official Topic</h3>
                    
                    <div class="space-y-4">
                        <div>
                            <label class="block text-[#90aecb] text-sm mb-2">Topic Name</label>
                            <input id="promotionTopicName" type="text" readonly class="w-full p-3 bg-[#223649] text-gray-400 rounded border border-[#314d68] cursor-not-allowed">
                        </div>
                        
                        <div>
                            <label class="block text-[#90aecb] text-sm mb-2">Description (Edit to help Claude categorize content better)</label>
                            <textarea id="promotionTopicDescription" rows="4" placeholder="Describe what this topic should include and how Claude should categorize content..." class="w-full p-3 bg-[#223649] text-white rounded border border-[#314d68] focus:outline-none focus:border-[#0b80ee]"></textarea>
                        </div>
                        
                        <div>
                            <label class="block text-[#90aecb] text-sm mb-2">Keywords (comma-separated)</label>
                            <input id="promotionTopicKeywords" type="text" placeholder="e.g., project, management, planning, strategy" class="w-full p-3 bg-[#223649] text-white rounded border border-[#314d68] focus:outline-none focus:border-[#0b80ee]">
                        </div>
                        
                        <div class="bg-[#223649] p-3 rounded text-sm">
                            <div class="text-[#90aecb] mb-2">📊 Current Topic Statistics:</div>
                            <div class="text-white">
                                <div id="promotionStats">Loading...</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="flex justify-end gap-3 mt-6">
                        <button onclick="hideTopicPromotionModal()" class="px-4 py-2 bg-[#223649] text-[#90aecb] rounded hover:bg-[#314d68] transition-colors">
                            Cancel
                        </button>
                        <button onclick="confirmTopicPromotion()" class="px-6 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors">
                            ⭐ Make Official
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        modal = document.getElementById('promotionModal');
    }
    
    // Populate modal with topic data
    document.getElementById('promotionTopicName').value = topic.name;
    document.getElementById('promotionTopicDescription').value = topic.description || '';
    
    // Set keywords
    const keywords = topic.keywords || [];
    if (Array.isArray(keywords)) {
        document.getElementById('promotionTopicKeywords').value = keywords.join(', ');
    } else {
        document.getElementById('promotionTopicKeywords').value = keywords;
    }
    
    // Show statistics
    const statsHtml = `
        <div class="grid grid-cols-2 gap-2 text-sm">
            <div>📧 ${topic.email_count || 0} emails</div>
            <div>📋 ${topic.task_count || 0} tasks</div>
            <div>👥 ${topic.people_involved ? topic.people_involved.length : 0} people</div>
            <div>💪 ${Math.round(topic.knowledge_strength || 0)}% strength</div>
        </div>
    `;
    document.getElementById('promotionStats').innerHTML = statsHtml;
    
    // Store current topic for promotion
    window.currentPromotionTopic = topic;
    
    // Show modal
    modal.style.display = 'flex';
    document.getElementById('promotionTopicDescription').focus();
}

function hideTopicPromotionModal() {
    const modal = document.getElementById('promotionModal');
    if (modal) {
        modal.style.display = 'none';
    }
    window.currentPromotionTopic = null;
}

async function confirmTopicPromotion() {
    const topic = window.currentPromotionTopic;
    if (!topic) return;
    
    const name = document.getElementById('promotionTopicName').value.trim();
    const description = document.getElementById('promotionTopicDescription').value.trim();
    const keywordsText = document.getElementById('promotionTopicKeywords').value.trim();
    
    if (!description) {
        showError('Please provide a description to help Claude categorize content effectively');
        return;
    }
    
    const keywords = keywordsText ? keywordsText.split(',').map(k => k.trim()).filter(k => k) : [];
    
    try {
        // Create the topic in the database as official with user-edited description
        const createResponse = await fetch('/api/topics', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                description: description,
                is_official: true,
                keywords: keywords,
                confidence_score: topic.confidence_score || 0.8
            })
        });
        
        const createResult = await createResponse.json();
        
        if (createResult.success) {
            showSuccess(`✅ "${name}" is now an official topic with your custom description!`);
            hideTopicPromotionModal();
            await refreshTopicsAndKnowledge(); // Refresh both tabs
        } else {
            showError('Failed to create official topic: ' + createResult.error);
        }
        
    } catch (error) {
        console.error('Failed to promote topic:', error);
        showError('Network error promoting topic: ' + error.message);
    }
} 