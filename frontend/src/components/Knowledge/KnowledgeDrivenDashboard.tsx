import React, { useState, useEffect } from 'react';

interface KnowledgeTopic {
  name: string;
  description: string;
  strategic_importance: number;
  current_status: string;
  key_themes: string[];
  knowledge_depth: string;
  update_frequency: string;
}

interface PipelineResults {
  success: boolean;
  pipeline_version: string;
  phases_completed: number;
  processing_summary: {
    total_emails_available: number;
    quality_filtered_emails: number;
    emails_assigned_to_topics: number;
    knowledge_topics_created: number;
    strategic_tasks_identified: number;
    knowledge_insights_generated: number;
    topics_augmented_by_agents: number;
  };
  knowledge_tree: {
    knowledge_topics: KnowledgeTopic[];
    topic_relationships: any[];
    knowledge_people: any[];
    business_intelligence: {
      industry_context?: string;
      business_stage?: string;
      strategic_priorities?: string[];
      opportunity_areas?: string[];
    };
  };
  cross_topic_intelligence: {
    strategic_tasks: Array<{
      description: string;
      rationale: string;
      priority: string;
      knowledge_topics?: string[];
    }>;
    knowledge_insights: Array<{
      title: string;
      description: string;
      insight_type: string;
      confidence?: number;
    }>;
    topic_status_updates: any[];
  };
  pipeline_efficiency: {
    quality_filter_ratio: number;
    knowledge_coverage: number;
    intelligence_density: number;
  };
}

export const KnowledgeDrivenDashboard: React.FC = () => {
  const [pipelineResults, setPipelineResults] = useState<PipelineResults | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingPhase, setProcessingPhase] = useState('');
  const [error, setError] = useState<string | null>(null);

  const runKnowledgePipeline = async (forceRebuild = false) => {
    setIsProcessing(true);
    setError(null);
    
    try {
      setProcessingPhase('🚀 Initializing Knowledge-Driven Pipeline...');
      
      const response = await fetch('/api/email/knowledge-driven-pipeline', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        },
        body: JSON.stringify({ force_rebuild: forceRebuild })
      });

      if (!response.ok) {
        throw new Error(`Pipeline failed: ${response.statusText}`);
      }

      const results = await response.json();
      setPipelineResults(results);
      
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsProcessing(false);
      setProcessingPhase('');
    }
  };

  const getTopicColor = (importance: number) => {
    if (importance > 0.8) return 'bg-red-100 border-red-400';
    if (importance > 0.6) return 'bg-orange-100 border-orange-400';
    if (importance > 0.4) return 'bg-yellow-100 border-yellow-400';
    return 'bg-green-100 border-green-400';
  };

  const formatMetric = (value: number, isPercentage = false) => {
    if (isPercentage) {
      return `${(value * 100).toFixed(1)}%`;
    }
    return value.toLocaleString();
  };

  return (
    <div className="knowledge-driven-dashboard p-6 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto">
        
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            🧠 Knowledge-Driven AI Chief of Staff
          </h1>
          <p className="text-gray-600 text-lg">
            Smart contact filtering → Knowledge tree creation → Cross-topic intelligence → Agent augmentation
          </p>
        </div>

        {/* Pipeline Control */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Pipeline Control</h2>
          
          <div className="flex gap-4 mb-4">
            <button
              onClick={() => runKnowledgePipeline(false)}
              disabled={isProcessing}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
            >
              {isProcessing ? (
                <>
                  <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                  Processing...
                </>
              ) : (
                <>🚀 Run Knowledge Pipeline</>
              )}
            </button>
            
            <button
              onClick={() => runKnowledgePipeline(true)}
              disabled={isProcessing}
              className="bg-purple-600 text-white px-6 py-3 rounded-lg hover:bg-purple-700 disabled:opacity-50"
            >
              🔄 Rebuild Knowledge Tree
            </button>
          </div>

          {processingPhase && (
            <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded">
              <p className="text-blue-800">{processingPhase}</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border-l-4 border-red-400 p-4 rounded">
              <p className="text-red-800">Error: {error}</p>
            </div>
          )}
        </div>

        {/* Pipeline Results */}
        {pipelineResults && (
          <div>
            
            {/* Processing Summary */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                📊 Processing Summary
              </h2>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-blue-600">
                    {formatMetric(pipelineResults.processing_summary.total_emails_available)}
                  </div>
                  <div className="text-sm text-blue-800">Total Emails</div>
                </div>
                
                <div className="bg-green-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-green-600">
                    {formatMetric(pipelineResults.processing_summary.quality_filtered_emails)}
                  </div>
                  <div className="text-sm text-green-800">Quality Filtered</div>
                </div>
                
                <div className="bg-purple-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-purple-600">
                    {formatMetric(pipelineResults.processing_summary.knowledge_topics_created)}
                  </div>
                  <div className="text-sm text-purple-800">Knowledge Topics</div>
                </div>
                
                <div className="bg-orange-50 p-4 rounded-lg">
                  <div className="text-2xl font-bold text-orange-600">
                    {formatMetric(pipelineResults.processing_summary.strategic_tasks_identified)}
                  </div>
                  <div className="text-sm text-orange-800">Strategic Tasks</div>
                </div>
              </div>

              {/* Pipeline Efficiency Metrics */}
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-lg font-semibold text-gray-700">
                    {formatMetric(pipelineResults.pipeline_efficiency.quality_filter_ratio, true)}
                  </div>
                  <div className="text-sm text-gray-500">Quality Filter Ratio</div>
                </div>
                
                <div className="text-center">
                  <div className="text-lg font-semibold text-gray-700">
                    {formatMetric(pipelineResults.pipeline_efficiency.knowledge_coverage, true)}
                  </div>
                  <div className="text-sm text-gray-500">Knowledge Coverage</div>
                </div>
                
                <div className="text-center">
                  <div className="text-lg font-semibold text-gray-700">
                    {formatMetric(pipelineResults.pipeline_efficiency.intelligence_density, true)}
                  </div>
                  <div className="text-sm text-gray-500">Intelligence Density</div>
                </div>
              </div>
            </div>

            {/* Knowledge Topics */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                📚 Knowledge Topics ({pipelineResults.knowledge_tree.knowledge_topics.length})
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {pipelineResults.knowledge_tree.knowledge_topics.map((topic, index) => (
                  <div
                    key={index}
                    className={`border-2 rounded-lg p-4 ${getTopicColor(topic.strategic_importance)}`}
                  >
                    <h3 className="font-semibold text-gray-900 mb-2">{topic.name}</h3>
                    <p className="text-sm text-gray-600 mb-3 line-clamp-3">
                      {topic.description}
                    </p>
                    
                    <div className="flex justify-between items-center text-xs">
                      <span className={`px-2 py-1 rounded ${
                        topic.current_status === 'active' ? 'bg-green-100 text-green-800' :
                        topic.current_status === 'developing' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {topic.current_status}
                      </span>
                      
                      <span className="text-gray-500">
                        {(topic.strategic_importance * 100).toFixed(0)}% priority
                      </span>
                    </div>
                    
                    {topic.key_themes && topic.key_themes.length > 0 && (
                      <div className="mt-2">
                        <div className="flex flex-wrap gap-1">
                          {topic.key_themes.slice(0, 3).map((theme, themeIndex) => (
                            <span 
                              key={themeIndex}
                              className="text-xs bg-white bg-opacity-50 px-2 py-1 rounded"
                            >
                              {theme}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Cross-Topic Intelligence */}
            {pipelineResults.cross_topic_intelligence && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                
                {/* Strategic Tasks */}
                <div className="bg-white rounded-lg shadow-md p-6">
                  <h2 className="text-xl font-semibold text-gray-900 mb-4">
                    🎯 Strategic Tasks ({pipelineResults.cross_topic_intelligence.strategic_tasks?.length || 0})
                  </h2>
                  
                  <div className="space-y-4">
                    {pipelineResults.cross_topic_intelligence.strategic_tasks?.slice(0, 5).map((task, index) => (
                      <div key={index} className="border-l-4 border-blue-400 bg-blue-50 p-4 rounded">
                        <h3 className="font-medium text-gray-900 mb-1">{task.description}</h3>
                        <p className="text-sm text-gray-600 mb-2">{task.rationale}</p>
                        
                        <div className="flex justify-between items-center text-xs">
                          <span className={`px-2 py-1 rounded ${
                            task.priority === 'high' ? 'bg-red-100 text-red-800' :
                            task.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-green-100 text-green-800'
                          }`}>
                            {task.priority} priority
                          </span>
                          
                          {task.knowledge_topics && (
                            <span className="text-gray-500">
                              {task.knowledge_topics.length} topics
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Knowledge Insights */}
                <div className="bg-white rounded-lg shadow-md p-6">
                  <h2 className="text-xl font-semibold text-gray-900 mb-4">
                    💡 Knowledge Insights ({pipelineResults.cross_topic_intelligence.knowledge_insights?.length || 0})
                  </h2>
                  
                  <div className="space-y-4">
                    {pipelineResults.cross_topic_intelligence.knowledge_insights?.slice(0, 5).map((insight, index) => (
                      <div key={index} className="border-l-4 border-purple-400 bg-purple-50 p-4 rounded">
                        <h3 className="font-medium text-gray-900 mb-1">{insight.title}</h3>
                        <p className="text-sm text-gray-600 mb-2">{insight.description}</p>
                        
                        <div className="flex justify-between items-center text-xs">
                          <span className={`px-2 py-1 rounded ${
                            insight.insight_type === 'opportunity' ? 'bg-green-100 text-green-800' :
                            insight.insight_type === 'risk' ? 'bg-red-100 text-red-800' :
                            insight.insight_type === 'trend' ? 'bg-blue-100 text-blue-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {insight.insight_type}
                          </span>
                          
                          {insight.confidence && (
                            <span className="text-gray-500">
                              {(insight.confidence * 100).toFixed(0)}% confidence
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Business Intelligence Summary */}
            {pipelineResults.knowledge_tree.business_intelligence && (
              <div className="bg-white rounded-lg shadow-md p-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  🏢 Business Intelligence Summary
                </h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  <div>
                    <h3 className="font-medium text-gray-700 mb-2">Industry Context</h3>
                    <p className="text-sm text-gray-600">
                      {pipelineResults.knowledge_tree.business_intelligence.industry_context || 'Not specified'}
                    </p>
                  </div>
                  
                  <div>
                    <h3 className="font-medium text-gray-700 mb-2">Business Stage</h3>
                    <p className="text-sm text-gray-600">
                      {pipelineResults.knowledge_tree.business_intelligence.business_stage || 'Not specified'}
                    </p>
                  </div>
                  
                  <div>
                    <h3 className="font-medium text-gray-700 mb-2">Strategic Priorities</h3>
                    <div className="text-sm text-gray-600">
                      {pipelineResults.knowledge_tree.business_intelligence.strategic_priorities?.slice(0, 3).map((priority: string, index: number) => (
                        <div key={index} className="mb-1">• {priority}</div>
                      ))}
                    </div>
                  </div>
                  
                  <div>
                    <h3 className="font-medium text-gray-700 mb-2">Opportunity Areas</h3>
                    <div className="text-sm text-gray-600">
                      {pipelineResults.knowledge_tree.business_intelligence.opportunity_areas?.slice(0, 3).map((area: string, index: number) => (
                        <div key={index} className="mb-1">• {area}</div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

          </div>
        )}
      </div>
    </div>
  );
}; 